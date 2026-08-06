from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import re

from config import ADMIN_IDS
from database import add_user, get_active_events, get_event, create_registration, update_user_email, get_user, get_user_registrations, cancel_registration, is_user_registered, get_payment_text
from keyboards.user_keyboards import get_main_keyboard, get_event_keyboard, get_email_confirmation_keyboard, get_events_list_keyboard, get_my_event_keyboard
from keyboards.admin_keyboards import get_check_payment_keyboard, get_admin_main_kb, get_support_reply_keyboard
import text_constants as txt

router = Router()

class RegistrationStates(StatesGroup):
    waiting_for_email = State()
    waiting_for_email_confirmation = State()
    waiting_for_receipt = State()

async def finalize_registration(message_obj: Message, state: FSMContext, bot: Bot, event_id: int, user_id: int, username: str, full_name: str):
    event = await get_event(event_id)
    if not event:
        await message_obj.answer(txt.EVENT_NOT_FOUND)
        await state.clear()
        return

    if event['price'] == 0:
        await create_registration(user_id, event_id, status="approved", amount=0)
        
        join_link = event['join_link'] if event['join_link'] else "Ссылка не указана"
        
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
            except:
                pass
        await state.clear()
    else:
        await state.set_state(RegistrationStates.waiting_for_receipt)
        
        payment_details = await get_payment_text()
        
        text_to_send = f"{txt.PAYMENT_HEADER}\n\n{payment_details}\n\n{txt.PAYMENT_FOOTER}"
            
        await message_obj.answer(text_to_send, parse_mode="HTML")

class SupportStates(StatesGroup):
    waiting_for_message = State()

@router.callback_query(F.data == "contact_support")
async def contact_support_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SupportStates.waiting_for_message)
    await callback.message.answer(txt.WRITE_TO_SUPPORT)
    await callback.answer()

@router.message(SupportStates.waiting_for_message)
async def process_support_message(message: Message, state: FSMContext, bot: Bot):
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
            print(f"Не удалось отправить сообщение админу {admin_id}: {e}")
        
    await message.answer(txt.SUPPORT_MESSAGE_SENT)
    await state.clear()

@router.message(CommandStart())
async def command_start(message: Message):
    await add_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )
    
    if message.from_user.id in ADMIN_IDS:
        await message.answer(
            "👋 Привет, Админ! Выбери действие в меню:",
            reply_markup=get_admin_main_kb()
        )
    else:
        await message.answer(
            txt.WELCOME_TEXT,
            reply_markup=get_main_keyboard()
        )

@router.message(F.text == "📅 Афиша")
async def show_afisha(message: Message):
    events = await get_active_events()
    
    if not events:
        await message.answer(txt.NO_EVENTS)
        return

    await message.answer(
        "Выберите мероприятие:",
        reply_markup=get_events_list_keyboard(events)
    )

@router.message(F.text == "🎫 Мои записи")
async def show_my_registrations(message: Message):
    events = await get_user_registrations(message.from_user.id)
    
    if not events:
        await message.answer("У вас нет активных записей на мероприятия.")
        return

    await message.answer(
        "Мероприятия, на которые вы записаны:",
        reply_markup=get_events_list_keyboard(events, callback_prefix="my_event_")
    )

@router.callback_query(F.data.startswith("show_event_"))
async def process_show_event(callback: CallbackQuery):
    try:
        event_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка данных.", show_alert=True)
        return

    event = await get_event(event_id)
    
    if not event:
        await callback.answer(txt.EVENT_NOT_FOUND, show_alert=True)
        return

    price_text = "Бесплатно" if event['price'] == 0 else f"{event['price']} руб."
    location_text = event['location'] if event['location'] else "Онлайн"
    
    text = (
        f"✨ {event['title']}\n"
        f"📝 {event['description']}\n"
        f"📍 Где: {location_text}\n"
        f"📅 Когда: {event['date_time']}\n"
        f"💰 Цена: {price_text}\n"
        f"👇 Жми кнопку ниже, чтобы записаться!"
    )
    
    is_registered = await is_user_registered(callback.from_user.id, event_id)
    
    await callback.message.answer_photo(
        photo=event['photo_id'],
        caption=text,
        reply_markup=get_event_keyboard(event['id'], is_registered=is_registered),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("my_event_"))
async def process_show_my_event(callback: CallbackQuery):
    try:
        event_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка данных.", show_alert=True)
        return

    # Проверяем, что пользователь действительно записан
    is_registered = await is_user_registered(callback.from_user.id, event_id)
    if not is_registered:
        await callback.answer("Вы больше не записаны на это мероприятие.", show_alert=True)
        # Опционально: можно обновить список сообщением, но пока просто алерт
        return

    event = await get_event(event_id)
    
    if not event:
        await callback.answer(txt.EVENT_NOT_FOUND, show_alert=True)
        return

    price_text = "Бесплатно" if event['price'] == 0 else f"{event['price']} руб."
    location_text = event['location'] if event['location'] else "Онлайн"
    
    text = (
        f"✨ {event['title']}\n"
        f"📝 {event['description']}\n"
        f"📍 Где: {location_text}\n"
        f"📅 Когда: {event['date_time']}\n"
        f"💰 Цена: {price_text}\n"
        f"👇 Жми кнопку ниже, чтобы записаться!"
    )
    
    await callback.message.answer_photo(
        photo=event['photo_id'],
        caption=text,
        reply_markup=get_my_event_keyboard(event['id']),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("cancel_reg_"))
async def process_cancel_registration(callback: CallbackQuery, bot: Bot):
    try:
        event_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка данных.", show_alert=True)
        return

    # Получаем данные о мероприятии для уведомления админа
    event = await get_event(event_id)

    await cancel_registration(callback.from_user.id, event_id)
    await callback.message.delete()
    
    # Отправляем сообщение пользователю (вместо alert)
    if event:
        await callback.message.answer(txt.REGISTRATION_CANCELLED_USER.format(title=event['title']))
    else:
        await callback.message.answer("Запись отменена.")
    
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
                print(f"Не удалось уведомить админа {admin_id}: {e}")

@router.callback_query(F.data == "dummy_callback")
async def dummy_callback_handler(callback: CallbackQuery):
    await callback.answer("Вы уже записаны на это мероприятие", show_alert=True)

@router.callback_query(F.data.startswith("enroll_"))
async def process_enroll(callback: CallbackQuery, state: FSMContext, bot: Bot):
    event_id = int(callback.data.split("_")[1])
    event = await get_event(event_id)
    
    if not event:
        await callback.answer(txt.EVENT_NOT_FOUND, show_alert=True)
        return

    # Сохраняем event_id
    await state.update_data(event_id=event_id)
    
    # Проверяем, есть ли email в базе
    user = await get_user(callback.from_user.id)
    if user and user['email']:
        await state.set_state(RegistrationStates.waiting_for_email_confirmation)
        await callback.message.answer(
            f"Ваш Email: {user['email']}\nВсё верно?",
            reply_markup=get_email_confirmation_keyboard()
        )
    else:
        await state.set_state(RegistrationStates.waiting_for_email)
        await callback.message.answer("📧 Пожалуйста, введите ваш Email для связи:")
        
    await callback.answer()

@router.callback_query(F.data == "confirm_email", RegistrationStates.waiting_for_email_confirmation)
async def confirm_email_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    event_id = data.get('event_id')
    
    # Удаляем сообщение с вопросом "Всё верно?"
    try:
        await callback.message.delete()
    except:
        pass
        
    await finalize_registration(callback.message, state, bot, event_id, callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
    await callback.answer()

@router.callback_query(F.data == "change_email", RegistrationStates.waiting_for_email_confirmation)
async def change_email_handler(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RegistrationStates.waiting_for_email)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("📧 Пожалуйста, введите новый Email:")
    await callback.answer()

@router.message(RegistrationStates.waiting_for_email)
async def process_email(message: Message, state: FSMContext, bot: Bot):
    email = message.text.strip()
    
    # Строгая валидация email через регулярное выражение
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    
    if not re.match(email_regex, email):
        await message.answer("⚠️ Некорректный формат email. Пример: example@mail.ru")
        return
        
    await update_user_email(message.from_user.id, email)
    
    data = await state.get_data()
    event_id = data.get('event_id')
    
    await finalize_registration(message, state, bot, event_id, message.from_user.id, message.from_user.username, message.from_user.full_name)

@router.message(RegistrationStates.waiting_for_receipt, F.photo)
async def process_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    event_id = data.get('event_id')
    event = await get_event(event_id)
    photo_id = message.photo[-1].file_id

    # Убеждаемся, что пользователь есть в базе
    await add_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )
    
    # Создаем регистрацию со статусом pending
    reg_id = await create_registration(
        telegram_id=message.from_user.id,
        event_id=event_id,
        receipt_photo_id=photo_id,
        status="pending",
        amount=event['price']
    )

    if reg_id is None:
        await message.answer("Ошибка регистрации. Попробуйте нажать /start и повторить.")
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
            await bot.send_photo(
                chat_id=admin_id,
                photo=photo_id,
                caption=caption,
                reply_markup=get_check_payment_keyboard(reg_id)
            )
        except:
            pass
