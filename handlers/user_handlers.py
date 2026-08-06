import logging
import re

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS
from database import (
    add_user, get_active_events, get_event, create_registration, update_user_email, get_user,
    get_user_registrations, cancel_registration, is_user_registered, get_payment_text,
    get_event_registration_count, DuplicateRegistrationError,
)
from keyboards.user_keyboards import get_main_keyboard, get_event_keyboard, get_email_confirmation_keyboard, get_events_list_keyboard, get_my_event_keyboard
from keyboards.admin_keyboards import get_check_payment_keyboard, get_admin_main_kb, get_support_reply_keyboard
import text_constants as txt

logger = logging.getLogger(__name__)

router = Router()

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class RegistrationStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_email_confirmation = State()
    waiting_for_receipt = State()


def format_price(price: float) -> str:
    return "Бесплатно" if price == 0 else f"{price} руб."


def format_event_card(event) -> str:
    return txt.EVENT_CARD_TEXT.format(
        title=event['title'],
        description=event['description'],
        location=event['location'] if event['location'] else txt.ONLINE_LOCATION,
        date_time=event['date_time'],
        price_text=format_price(event['price']),
    )

async def is_event_full(event) -> bool:
    if not event['capacity']:
        return False
    count = await get_event_registration_count(event['id'])
    return count >= event['capacity']


async def finalize_registration(message_obj: Message, state: FSMContext, bot: Bot, event_id: int, user_id: int, username: str, full_name: str):
    event = await get_event(event_id)
    if not event:
        await message_obj.answer(txt.EVENT_NOT_FOUND)
        await state.clear()
        return

    if await is_event_full(event):
        await message_obj.answer(txt.EVENT_FULL)
        await state.clear()
        return

    if event['price'] == 0:
        try:
            await create_registration(user_id, event_id, status="approved", amount=0)
        except DuplicateRegistrationError:
            await message_obj.answer(txt.DUPLICATE_REGISTRATION)
            await state.clear()
            return

        join_link = event['join_link'] if event['join_link'] else txt.NO_LINK

        await message_obj.answer(
            txt.REGISTRATION_APPROVED_FREE.format(title=event['title'], join_link=join_link),
            parse_mode="HTML"
        )

        user_display = f"@{username}" if username else full_name
        
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    txt.NEW_FREE_REGISTRATION_ADMIN.format(
                        user_display=user_display,
                        title=event['title']
                    )
                )
            except Exception as e:
                logger.warning("Не удалось уведомить админа %s: %s", admin_id, e)
        await state.clear()
    else:
        await state.set_state(RegistrationStates.waiting_for_receipt)
        
        payment_details = await get_payment_text()
        
        text_to_send = f"{txt.PAYMENT_HEADER}\n\n{payment_details}\n\n{txt.PAYMENT_FOOTER}"
            
        await message_obj.answer(text_to_send, parse_mode="HTML")

@router.message(CommandStart())
async def command_start(message: Message, state: FSMContext):
    # /start должен всегда сбрасывать любое "зависшее" состояние (например, режим поддержки
    # или незавершённую регистрацию), а не попадать в текущий state-хендлер как обычный текст.
    await state.clear()

    await add_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )

    if message.from_user.id in ADMIN_IDS:
        await message.answer(
            txt.WELCOME_ADMIN,
            reply_markup=get_admin_main_kb()
        )
    else:
        await message.answer(
            txt.WELCOME_TEXT,
            reply_markup=get_main_keyboard()
        )


class SupportStates(StatesGroup):
    waiting_for_message = State()

@router.callback_query(F.data == "contact_support")
async def contact_support_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SupportStates.waiting_for_message)
    await callback.message.answer(txt.WRITE_TO_SUPPORT)
    await callback.answer()

@router.message(SupportStates.waiting_for_message)
async def process_support_message(message: Message, state: FSMContext, bot: Bot):
    if not message.text:
        await message.answer(txt.PLEASE_SEND_TEXT)
        return

    user_message = message.text
    full_name = message.from_user.full_name
    username = f"@{message.from_user.username}" if message.from_user.username else full_name
    
    # Формируем сообщение для админа
    admin_text = txt.SUPPORT_MESSAGE_HEADER.format(
        full_name=full_name,
        username=username,
        message=user_message
    )
    
    # Отправляем админу
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                reply_markup=get_support_reply_keyboard(message.from_user.id),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning("Не удалось отправить сообщение админу %s: %s", admin_id, e)

    await message.answer(txt.SUPPORT_MESSAGE_SENT)
    await state.clear()

@router.message(F.text == txt.BTN_AFISHA)
async def show_afisha(message: Message):
    events = await get_active_events()
    
    if not events:
        await message.answer(txt.NO_EVENTS)
        return

    await message.answer(
        txt.CHOOSE_EVENT,
        reply_markup=get_events_list_keyboard(events)
    )

@router.message(F.text == txt.BTN_MY_REGISTRATIONS)
async def show_my_registrations(message: Message):
    events = await get_user_registrations(message.from_user.id)

    if not events:
        await message.answer(txt.NO_MY_REGISTRATIONS)
        return

    await message.answer(
        txt.MY_REGISTRATIONS_LIST,
        reply_markup=get_events_list_keyboard(events, callback_prefix="my_event_")
    )

@router.callback_query(F.data.startswith("show_event_"))
async def process_show_event(callback: CallbackQuery):
    try:
        event_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer(txt.ERROR_DATA, show_alert=True)
        return

    event = await get_event(event_id)

    if not event:
        await callback.answer(txt.EVENT_NOT_FOUND, show_alert=True)
        return

    is_registered = await is_user_registered(callback.from_user.id, event_id)

    await callback.message.answer_photo(
        photo=event['photo_id'],
        caption=format_event_card(event),
        reply_markup=get_event_keyboard(event['id'], is_registered=is_registered),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("my_event_"))
async def process_show_my_event(callback: CallbackQuery):
    try:
        event_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer(txt.ERROR_DATA, show_alert=True)
        return

    # Проверяем, что пользователь действительно записан
    is_registered = await is_user_registered(callback.from_user.id, event_id)
    if not is_registered:
        await callback.answer(txt.NOT_REGISTERED_ANYMORE, show_alert=True)
        return

    event = await get_event(event_id)

    if not event:
        await callback.answer(txt.EVENT_NOT_FOUND, show_alert=True)
        return

    await callback.message.answer_photo(
        photo=event['photo_id'],
        caption=format_event_card(event),
        reply_markup=get_my_event_keyboard(event['id']),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("cancel_reg_"))
async def process_cancel_registration(callback: CallbackQuery, bot: Bot):
    try:
        event_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer(txt.ERROR_DATA, show_alert=True)
        return

    # Получаем данные о мероприятии для уведомления админа
    event = await get_event(event_id)

    await cancel_registration(callback.from_user.id, event_id)
    await callback.message.delete()

    # Отправляем сообщение пользователю (вместо alert)
    if event:
        await callback.message.answer(txt.REGISTRATION_CANCELLED_USER.format(title=event['title']))
    else:
        await callback.message.answer(txt.REGISTRATION_CANCELLED_SIMPLE)

    await callback.answer()

    # Уведомляем админов
    if event:
        user_display = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
        msg_text = txt.REGISTRATION_CANCELLED_ADMIN.format(
            user_display=user_display,
            title=event['title']
        )

        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(chat_id=admin_id, text=msg_text, parse_mode="HTML")
            except Exception as e:
                logger.warning("Не удалось уведомить админа %s: %s", admin_id, e)

@router.callback_query(F.data == "dummy_callback")
async def dummy_callback_handler(callback: CallbackQuery):
    await callback.answer(txt.ALREADY_REGISTERED, show_alert=True)

@router.callback_query(F.data.startswith("enroll_"))
async def process_enroll(callback: CallbackQuery, state: FSMContext, bot: Bot):
    try:
        event_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer(txt.ERROR_DATA, show_alert=True)
        return

    event = await get_event(event_id)
    
    if not event:
        await callback.answer(txt.EVENT_NOT_FOUND, show_alert=True)
        return

    if await is_event_full(event):
        await callback.answer(txt.EVENT_FULL, show_alert=True)
        return

    # Сохраняем event_id
    await state.update_data(event_id=event_id)
    
    # Проверяем, есть ли email в базе
    user = await get_user(callback.from_user.id)
    if user and user['email']:
        await state.set_state(RegistrationStates.waiting_for_email_confirmation)
        await callback.message.answer(
            txt.EMAIL_CONFIRM.format(email=user['email']),
            reply_markup=get_email_confirmation_keyboard()
        )
    else:
        await state.set_state(RegistrationStates.waiting_for_email)
        await callback.message.answer(txt.EMAIL_PROMPT)


    await callback.answer()

@router.callback_query(F.data == "confirm_email", RegistrationStates.waiting_for_email_confirmation)
async def confirm_email_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    event_id = data.get('event_id')
    
    # Удаляем сообщение с вопросом "Всё верно?"
    try:
        await callback.message.delete()
    except Exception as e:
        logger.warning("Не удалось удалить сообщение с подтверждением email: %s", e)


    await finalize_registration(callback.message, state, bot, event_id, callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
    await callback.answer()

@router.callback_query(F.data == "change_email", RegistrationStates.waiting_for_email_confirmation)
async def change_email_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RegistrationStates.waiting_for_email)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(txt.EMAIL_PROMPT_NEW)
    await callback.answer()

@router.message(RegistrationStates.waiting_for_email)
async def process_email(message: Message, state: FSMContext, bot: Bot):
    if not message.text:
        await message.answer(txt.EMAIL_INVALID)
        return

    email = message.text.strip()

    if not EMAIL_REGEX.match(email):
        await message.answer(txt.EMAIL_INVALID)
        return


    await update_user_email(message.from_user.id, email)
    
    data = await state.get_data()
    event_id = data.get('event_id')
    
    await finalize_registration(message, state, bot, event_id, message.from_user.id, message.from_user.username, message.from_user.full_name)

@router.message(RegistrationStates.waiting_for_receipt, F.photo | F.document)
async def process_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    event_id = data.get('event_id')
    event = await get_event(event_id)
    if not event:
        await message.answer(txt.EVENT_NOT_FOUND)
        await state.clear()
        return

    if await is_event_full(event):
        await message.answer(txt.EVENT_FULL)
        await state.clear()
        return

    is_document = message.document is not None
    receipt_file_id = message.document.file_id if is_document else message.photo[-1].file_id

    # Убеждаемся, что пользователь есть в базе
    await add_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )

    # Создаем регистрацию со статусом pending
    try:
        reg_id = await create_registration(
            telegram_id=message.from_user.id,
            event_id=event_id,
            receipt_photo_id=receipt_file_id,
            status="pending",
            amount=event['price']
        )
    except DuplicateRegistrationError:
        await message.answer(txt.DUPLICATE_REGISTRATION)
        await state.clear()
        return

    if reg_id is None:
        await message.answer(txt.REGISTRATION_ERROR)
        await state.clear()
        return

    await message.answer(txt.RECEIPT_SENT)
    await state.clear()

    # Отправляем админу
    user_display = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name

    caption = txt.NEW_PAID_REGISTRATION_ADMIN.format(
        user_display=user_display,
        title=event['title'],
        price=event['price']
    )

    for admin_id in ADMIN_IDS:
        try:
            if is_document:
                await bot.send_document(
                    chat_id=admin_id,
                    document=receipt_file_id,
                    caption=caption,
                    reply_markup=get_check_payment_keyboard(reg_id)
                )
            else:
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=receipt_file_id,
                    caption=caption,
                    reply_markup=get_check_payment_keyboard(reg_id)
                )
        except Exception as e:
            logger.warning("Не удалось отправить чек админу %s: %s", admin_id, e)
