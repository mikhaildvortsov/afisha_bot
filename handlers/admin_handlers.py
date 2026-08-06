import asyncio
import logging

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from config import SUPER_ADMIN_IDS
from filters import IsAdmin, IsSuperAdmin, is_super_admin
from keyboards.admin_keyboards import (
    get_confirm_keyboard,
    get_admin_main_kb,
    get_delete_event_keyboard,
    get_view_guests_keyboard,
    get_back_to_events_list_keyboard,
    get_settings_keyboard,
    get_edit_list_btn,
    get_edit_event_list_kb,
    get_edit_fields_kb,
    get_admins_keyboard,
    get_confirm_remove_admin_kb
)
from database import add_event, update_registration_status, get_registration, get_users_count, get_active_events, delete_event, get_event_participants, get_event, get_all_users, get_bot_statistics, get_payment_text, update_payment_text, update_event_field, mark_user_blocked, get_admins, add_admin, remove_admin, get_admin, get_user
import text_constants as txt
from keyboards.user_keyboards import get_support_keyboard, get_event_keyboard

logger = logging.getLogger(__name__)

router = Router()


def format_price(price: float) -> str:
    return "Бесплатно" if price == 0 else f"{price} руб."

class EditEventState(StatesGroup):
    waiting_for_new_value = State()

class EventStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_location = State()
    waiting_for_datetime = State()
    waiting_for_price = State()
    waiting_for_capacity = State()
    waiting_for_photo = State()
    waiting_for_link = State()
    waiting_for_confirmation = State()

class AdminSupportStates(StatesGroup):
    waiting_for_reply = State()

class SettingsState(StatesGroup):
    waiting_for_payment_text = State()

class AdminManageState(StatesGroup):
    waiting_for_new_admin = State()

@router.message(Command("admin"), IsAdmin())
async def admin_start(message: Message, state: FSMContext):
    await state.clear()
    is_super = await is_super_admin(message.from_user.id)
    await message.answer(txt.ADMIN_PANEL_WELCOME, reply_markup=get_admin_main_kb(is_super))

@router.message(F.text == txt.BTN_STATS, IsAdmin())
async def get_stats(message: Message, state: FSMContext):
    await state.clear()
    stats = await get_bot_statistics()

    text = txt.STATS_TEXT.format(**stats)

    await message.answer(text, parse_mode="HTML")

@router.message(F.text == txt.BTN_SETTINGS, IsAdmin())
async def show_settings(message: Message):
    current_text = await get_payment_text()
    await message.answer(
        txt.PAYMENT_SETTINGS_CURRENT.format(payment_text=current_text),
        reply_markup=get_settings_keyboard()
    )

@router.callback_query(F.data == "edit_payment_text", IsAdmin())
async def start_edit_payment_text(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsState.waiting_for_payment_text)
    await callback.message.answer(txt.PAYMENT_TEXT_PROMPT)
    await callback.answer()

@router.message(SettingsState.waiting_for_payment_text, IsAdmin())
async def process_new_payment_text(message: Message, state: FSMContext):
    if not message.text:
        await message.answer(txt.PLEASE_SEND_TEXT)
        return

    await update_payment_text(message.text)
    await message.answer(txt.PAYMENT_TEXT_UPDATED)
    await state.clear()

@router.message(F.text == txt.BTN_DELETE_EVENT, IsAdmin())
async def start_delete_event(message: Message, state: FSMContext):
    await state.clear()
    events = await get_active_events()
    if not events:
        await message.answer(txt.EMPTY_LIST)
        return

    await message.answer(txt.CHOOSE_EVENT_DELETE, reply_markup=get_delete_event_keyboard(events))

@router.callback_query(F.data.startswith("delete_event_"), IsAdmin())
async def process_delete_event(callback: CallbackQuery):
    try:
        event_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer(txt.ERROR_DATA, show_alert=True)
        return

    await delete_event(event_id)

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(txt.EVENT_DELETED)
    await callback.answer()

@router.callback_query(F.data.startswith("reply_support_"), IsAdmin())
async def start_support_reply(callback: CallbackQuery, state: FSMContext):
    try:
        user_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer(txt.ERROR_DATA, show_alert=True)
        return

    await state.update_data(reply_user_id=user_id)
    await state.set_state(AdminSupportStates.waiting_for_reply)
    await callback.message.answer(txt.SUPPORT_REPLY_PROMPT)
    await callback.answer()

@router.message(AdminSupportStates.waiting_for_reply, IsAdmin())
async def send_support_reply(message: Message, state: FSMContext, bot: Bot):
    if not message.text:
        await message.answer(txt.PLEASE_SEND_TEXT)
        return

    data = await state.get_data()
    user_id = data.get('reply_user_id')

    try:
        await bot.send_message(
            chat_id=user_id,
            text=txt.SUPPORT_ANSWER_PREFIX.format(answer=message.text),
            parse_mode="HTML"
        )
        await message.answer(txt.SUPPORT_REPLY_SENT)
    except Exception as e:
        await message.answer(txt.SUPPORT_REPLY_FAILED.format(error=e))

    await state.clear()

# Фильтр на админа
@router.message(Command("new_event"), IsAdmin())
@router.message(F.text == txt.BTN_NEW_EVENT, IsAdmin())
async def start_new_event(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(EventStates.waiting_for_title)
    await message.answer(txt.NEW_EVENT_TITLE_PROMPT)

@router.message(EventStates.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    if not message.text:
        await message.answer(txt.PLEASE_SEND_TEXT)
        return

    await state.update_data(title=message.text)
    await state.set_state(EventStates.waiting_for_description)
    await message.answer(txt.NEW_EVENT_DESC_PROMPT)

@router.message(EventStates.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    if not message.text:
        await message.answer(txt.PLEASE_SEND_TEXT)
        return

    await state.update_data(description=message.text)
    await state.set_state(EventStates.waiting_for_location)
    await message.answer(txt.NEW_EVENT_LOCATION_PROMPT)

@router.message(EventStates.waiting_for_location)
async def process_location(message: Message, state: FSMContext):
    if not message.text:
        await message.answer(txt.PLEASE_SEND_TEXT)
        return

    await state.update_data(location=message.text)
    await state.set_state(EventStates.waiting_for_datetime)
    await message.answer(txt.NEW_EVENT_DATETIME_PROMPT)

@router.message(EventStates.waiting_for_datetime)
async def process_datetime(message: Message, state: FSMContext):
    if not message.text:
        await message.answer(txt.PLEASE_SEND_TEXT)
        return

    await state.update_data(date_time=message.text)
    await state.set_state(EventStates.waiting_for_price)
    await message.answer(txt.NEW_EVENT_PRICE_PROMPT)

@router.message(EventStates.waiting_for_price)
async def process_price(message: Message, state: FSMContext):
    if not message.text:
        await message.answer(txt.INVALID_NUMBER)
        return

    try:
        price = float(message.text.replace(',', '.'))
        if price < 0:
            raise ValueError
    except ValueError:
        await message.answer(txt.INVALID_NUMBER)
        return

    await state.update_data(price=price)
    await state.set_state(EventStates.waiting_for_capacity)
    await message.answer(txt.NEW_EVENT_CAPACITY_PROMPT)

@router.message(EventStates.waiting_for_capacity)
async def process_capacity(message: Message, state: FSMContext):
    if not message.text:
        await message.answer(txt.INVALID_NUMBER)
        return

    try:
        capacity = int(message.text.strip())
        if capacity < 0:
            raise ValueError
    except ValueError:
        await message.answer(txt.INVALID_NUMBER)
        return

    await state.update_data(capacity=capacity if capacity > 0 else None)
    await state.set_state(EventStates.waiting_for_photo)
    await message.answer(txt.NEW_EVENT_PHOTO_PROMPT)

@router.message(EventStates.waiting_for_photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await state.set_state(EventStates.waiting_for_link)
    await message.answer(txt.NEW_EVENT_LINK_PROMPT)

@router.message(EventStates.waiting_for_link)
async def process_link(message: Message, state: FSMContext):
    if not message.text:
        await message.answer(txt.PLEASE_SEND_TEXT)
        return

    link = message.text.strip()
    join_link = link if link != "-" else None
    await state.update_data(join_link=join_link)

    data = await state.get_data()

    preview_text = txt.EVENT_PREVIEW_TEXT.format(
        title=data['title'],
        description=data['description'],
        location=data['location'],
        date_time=data['date_time'],
        price_text=format_price(data['price']),
        link_text=join_link if join_link else txt.NONE_VALUE,
    )

    await message.answer_photo(
        photo=data['photo_id'],
        caption=preview_text,
        reply_markup=get_confirm_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(EventStates.waiting_for_confirmation)

@router.callback_query(F.data == "save_event", EventStates.waiting_for_confirmation)
async def save_event_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    event_id = await add_event(data)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(txt.EVENT_PUBLISHED, reply_markup=get_admin_main_kb())

    users = await get_all_users()

    caption = txt.EVENT_BROADCAST_TEXT.format(
        title=data['title'],
        description=data['description'],
        location=data['location'],
        date_time=data['date_time'],
        price_text=format_price(data['price']),
    )

    count = 0
    for user in users:
        # Не отправляем сообщение самому админу, который публикует
        if user['telegram_id'] == callback.from_user.id:
            continue

        try:
            await bot.send_photo(
                chat_id=user['telegram_id'],
                photo=data['photo_id'],
                caption=caption,
                reply_markup=get_event_keyboard(event_id),
                parse_mode="HTML"
            )
            count += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await bot.send_photo(
                    chat_id=user['telegram_id'],
                    photo=data['photo_id'],
                    caption=caption,
                    reply_markup=get_event_keyboard(event_id),
                    parse_mode="HTML"
                )
                count += 1
            except Exception as e2:
                logger.warning("Не удалось отправить анонс %s после ретрая: %s", user['telegram_id'], e2)
        except TelegramForbiddenError:
            # Пользователь заблокировал бота — помечаем, чтобы не слать ему больше и не искажать статистику
            await mark_user_blocked(user['telegram_id'])
        except Exception as e:
            logger.warning("Не удалось отправить анонс %s: %s", user['telegram_id'], e)

        # Не превышаем лимит Telegram (~30 сообщений/сек)
        await asyncio.sleep(0.05)

    msg = await callback.message.answer(txt.BROADCAST_DONE.format(count=count))
    await state.clear()
    await callback.answer()
    
    # Удаляем сообщение через 3 секунды
    await asyncio.sleep(3)
    try:
        await msg.delete()
    except Exception:
        pass

@router.callback_query(F.data == "cancel_event", EventStates.waiting_for_confirmation)
async def cancel_event_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await state.clear()
    await callback.answer()

@router.callback_query(F.data.startswith("approve_"), IsAdmin())
async def approve_payment(callback: CallbackQuery, bot: Bot):
    try:
        reg_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer(txt.BUTTON_DATA_ERROR, show_alert=True)
        return

    reg = await get_registration(reg_id)

    if not reg:
        await callback.answer(txt.REGISTRATION_NOT_FOUND, show_alert=True)
        return

    await update_registration_status(reg_id, "approved")

    # Удаляем кнопки и пишем "Подтверждено" в сообщение админа
    try:
        current_caption = callback.message.caption or ""
        await callback.message.edit_caption(
            caption=f"{current_caption}\n\n{txt.ADMIN_APPROVED}",
            reply_markup=None
        )
    except Exception as e:
        logger.warning("Не удалось изменить подпись сообщения админа: %s", e)
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(txt.ADMIN_APPROVED)

    # Получаем данные события для ссылки
    event = await get_event(reg['event_id'])
    join_link = event['join_link'] if event and event['join_link'] else txt.NO_LINK

    try:
        await bot.send_message(
            chat_id=reg['telegram_id'],
            text=txt.REGISTRATION_APPROVED.format(
                title=reg['event_title'] if reg['event_title'] else 'мероприятие',
                join_link=join_link
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning("Не удалось отправить уведомление пользователю: %s", e)

    await callback.answer()

@router.callback_query(F.data.startswith("reject_"), IsAdmin())
async def reject_payment(callback: CallbackQuery, bot: Bot):
    try:
        reg_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer(txt.BUTTON_DATA_ERROR, show_alert=True)
        return

    reg = await get_registration(reg_id)

    if not reg:
        await callback.answer(txt.REGISTRATION_NOT_FOUND, show_alert=True)
        return

    await update_registration_status(reg_id, "rejected")

    # Удаляем сообщение с чеком у админа
    try:
        await callback.message.delete()
    except Exception as e:
        logger.warning("Не удалось удалить сообщение админа: %s", e)
        # Если не удалилось, убираем кнопки
        await callback.message.edit_reply_markup(reply_markup=None)

    # Уведомляем пользователя и предлагаем написать в поддержку
    try:
        await bot.send_message(
            chat_id=reg['telegram_id'],
            text=txt.REGISTRATION_REJECTED,
            reply_markup=get_support_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning("Не удалось отправить уведомление пользователю: %s", e)

    await callback.answer()

@router.message(F.text == txt.BTN_MY_EVENTS_LIST, IsAdmin())
async def show_admin_events(message: Message, state: FSMContext):
    await state.clear()
    events = await get_active_events()

    if not events:
        await message.answer(txt.NO_EVENTS)
        return

    response_text = txt.MY_EVENTS_HEADER
    for event in events:
        response_text += txt.MY_EVENTS_ITEM.format(
            title=event['title'],
            date_time=event['date_time'],
            price_text=format_price(event['price']),
            id=event['id'],
        )


    await message.answer(response_text, parse_mode="HTML", reply_markup=get_edit_list_btn())

@router.message(F.text == txt.BTN_GUEST_LISTS, IsAdmin())
async def view_guests_list(message: Message, state: FSMContext):
    await state.clear()
    events = await get_active_events()
    
    if not events:
        await message.answer(txt.NO_EVENTS)
        return

    await message.answer(
        txt.CHOOSE_EVENT_GUESTS,
        reply_markup=get_view_guests_keyboard(events)
    )

@router.callback_query(F.data.startswith("view_guests_"), IsAdmin())
async def show_guest_list(callback: CallbackQuery):
    try:
        event_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer(txt.ERROR_DATA, show_alert=True)
        return

    event = await get_event(event_id)
    participants = await get_event_participants(event_id)

    if not event:
        await callback.answer(txt.EVENT_NOT_FOUND, show_alert=True)
        return

    if not participants:
        await callback.message.edit_text(
            txt.GUEST_LIST_EMPTY.format(title=event['title']),
            parse_mode="HTML",
            reply_markup=get_back_to_events_list_keyboard()
        )
        await callback.answer()
        return

    text = txt.GUEST_LIST_HEADER.format(title=event['title'], count=len(participants))

    for user in participants:
        username = f"(@{user['username']})" if user['username'] else ""
        text += f"👤 {user['full_name']} {username}\n"

    text += txt.GUEST_LIST_FOOTER.format(count=len(participants))

    # Разбиваем сообщение, если оно слишком длинное (лимит телеграма 4096 символов)
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for part in parts:
            await callback.message.answer(part, parse_mode="HTML")
        await callback.message.answer(txt.NAVIGATION, reply_markup=get_back_to_events_list_keyboard())
        await callback.message.delete()  # Удаляем исходное сообщение с кнопками
    else:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_back_to_events_list_keyboard())

    await callback.answer()

@router.callback_query(F.data == "back_to_events_list", IsAdmin())
async def back_to_events_list_handler(callback: CallbackQuery):
    events = await get_active_events()
    
    if not events:
        await callback.message.edit_text(txt.NO_EVENTS)
        await callback.answer()
        return

    await callback.message.edit_text(
        txt.CHOOSE_EVENT_GUESTS,
        reply_markup=get_view_guests_keyboard(events)
    )
    await callback.answer()

@router.callback_query(F.data == "start_edit", IsAdmin())
async def start_edit_handler(callback: CallbackQuery):
    events = await get_active_events()
    if not events:
        await callback.answer(txt.NO_EVENTS, show_alert=True)
        return
        
    await callback.message.answer(
        txt.CHOOSE_EVENT_EDIT,
        reply_markup=get_edit_event_list_kb(events)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("edit_select_"), IsAdmin())
async def select_event_to_edit(callback: CallbackQuery):
    try:
        event_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer(txt.ERROR_DATA, show_alert=True)
        return

    await callback.message.edit_text(
        txt.CHOOSE_FIELD_EDIT,
        reply_markup=get_edit_fields_kb(event_id)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("edit_"), IsAdmin())
async def edit_field_handler(callback: CallbackQuery, state: FSMContext):
    # callback.data format: edit_{field}_{id}
    # But we also have "edit_select_" which is handled above. 
    # And "edit_payment_text" which is handled separately.
    # So we need to be careful.
    
    data_parts = callback.data.split("_")
    
    # Skip if it's one of the other handlers
    if data_parts[1] == "select" or data_parts[1] == "payment":
        return

    # Extract field and event_id
    # Format can be: edit_title_123 (3 parts) or edit_date_time_123 (4 parts) or edit_photo_id_123 (4 parts)
    
    try:
        event_id = int(data_parts[-1])
        field_name = "_".join(data_parts[1:-1])
    except (ValueError, IndexError):
        await callback.answer(txt.ERROR_DATA, show_alert=True)
        return

    await state.update_data(editing_event_id=event_id, editing_field=field_name)
    await state.set_state(EditEventState.waiting_for_new_value)

    display_name = txt.EDIT_FIELD_DISPLAY_NAMES.get(field_name, txt.FIELD_VALUE_FALLBACK)

    await callback.message.answer(txt.EDIT_FIELD_PROMPT.format(display_name=display_name))
    await callback.answer()

@router.message(EditEventState.waiting_for_new_value, IsAdmin())
async def process_new_field_value(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get('editing_event_id')
    field_name = data.get('editing_field')

    if not event_id or not field_name:
        await message.answer(txt.STATE_ERROR)
        await state.clear()
        return

    new_value = None

    if field_name == "photo_id":
        if message.photo:
            new_value = message.photo[-1].file_id
        else:
            await message.answer(txt.PLEASE_SEND_PHOTO)
            return
    elif field_name == "price":
        if not message.text:
            await message.answer(txt.INVALID_NUMBER)
            return
        try:
            new_value = float(message.text.replace(',', '.'))
            if new_value < 0:
                raise ValueError
        except ValueError:
            await message.answer(txt.INVALID_NUMBER)
            return
    elif field_name == "capacity":
        if not message.text:
            await message.answer(txt.INVALID_NUMBER)
            return
        try:
            capacity = int(message.text.strip())
            if capacity < 0:
                raise ValueError
        except ValueError:
            await message.answer(txt.INVALID_NUMBER)
            return
        new_value = capacity if capacity > 0 else None
    elif field_name == "join_link":
        if not message.text:
            await message.answer(txt.PLEASE_SEND_TEXT)
            return
        new_value = message.text.strip()
        if new_value == "-":
            new_value = None
    else:
        if message.text:
            new_value = message.text
        else:
            await message.answer(txt.PLEASE_SEND_TEXT)
            return

    try:
        await update_event_field(event_id, field_name, new_value)
    except ValueError as e:
        logger.warning("Попытка обновить недопустимое поле события: %s", e)
        await message.answer(txt.ERROR_DATA)
        await state.clear()
        return

    await message.answer(
        txt.FIELD_UPDATED,
        reply_markup=get_edit_fields_kb(event_id)
    )
    await state.clear()



# --- Управление администраторами (только для суперадминов) ---

def _display_name(full_name, username, telegram_id):
    name = full_name or (f"@{username}" if username else None) or str(telegram_id)
    return name


async def _render_admins(message: Message):
    admins = await get_admins()
    text = txt.ADMINS_HEADER

    for super_id in SUPER_ADMIN_IDS:
        text += txt.ADMINS_SUPER_LINE.format(name=super_id)

    listed = [a for a in admins if a['telegram_id'] not in SUPER_ADMIN_IDS]
    if listed:
        for admin in listed:
            username = f" (@{admin['username']})" if admin['username'] else ""
            text += txt.ADMINS_LINE.format(
                name=_display_name(admin['full_name'], admin['username'], admin['telegram_id']),
                username=username
            )
        text += txt.ADMINS_HINT
    else:
        text += "\n" + txt.ADMINS_EMPTY

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_admins_keyboard(admins, SUPER_ADMIN_IDS)
    )


@router.message(F.text == txt.BTN_ADMINS, IsSuperAdmin())
async def show_admins(message: Message, state: FSMContext):
    await state.clear()
    await _render_admins(message)


@router.callback_query(F.data == "add_admin", IsSuperAdmin())
async def start_add_admin(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminManageState.waiting_for_new_admin)
    await callback.message.answer(txt.ADD_ADMIN_PROMPT)
    await callback.answer()


@router.message(AdminManageState.waiting_for_new_admin, Command("cancel"), IsSuperAdmin())
async def cancel_add_admin(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(txt.ACTION_CANCELLED)


@router.message(AdminManageState.waiting_for_new_admin, IsSuperAdmin())
async def process_new_admin(message: Message, state: FSMContext, bot: Bot):
    # Пересланное сообщение даёт и ID, и имя; иначе ждём ID числом.
    if message.forward_from:
        new_id = message.forward_from.id
        username = message.forward_from.username
        full_name = message.forward_from.full_name
    elif message.forward_sender_name:
        await message.answer(txt.ADD_ADMIN_FORWARD_HIDDEN)
        return
    else:
        raw = (message.text or "").strip()
        if not raw.isdigit():
            await message.answer(txt.ADD_ADMIN_BAD_ID)
            return
        new_id = int(raw)
        username = None
        full_name = None

    if new_id in SUPER_ADMIN_IDS:
        await message.answer(txt.ADD_ADMIN_SELF)
        await state.clear()
        return

    # Профиль из базы пользователей — если человек уже запускал бота.
    if not full_name:
        user = await get_user(new_id)
        if user:
            username = user['username']
            full_name = user['full_name']

    name = _display_name(full_name, username, new_id)
    added = await add_admin(new_id, username, full_name, message.from_user.id)

    if not added:
        await message.answer(txt.ADD_ADMIN_ALREADY.format(name=name))
        await state.clear()
        return

    await message.answer(txt.ADD_ADMIN_OK.format(name=name))
    await state.clear()

    try:
        await bot.send_message(new_id, txt.ADD_ADMIN_NOTIFY)
    except TelegramForbiddenError:
        logger.info("Новый админ %s не запускал бота — уведомление не доставлено", new_id)
    except Exception as e:
        logger.warning("Не удалось уведомить нового админа %s: %s", new_id, e)

    await _render_admins(message)


@router.callback_query(F.data.startswith("rmadmin_yes_"), IsSuperAdmin())
async def confirm_remove_admin(callback: CallbackQuery, bot: Bot):
    try:
        target_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer(txt.ERROR_DATA, show_alert=True)
        return

    if target_id in SUPER_ADMIN_IDS:
        await callback.answer(txt.REMOVE_ADMIN_PROTECTED, show_alert=True)
        return

    admin = await get_admin(target_id)
    name = _display_name(
        admin['full_name'] if admin else None,
        admin['username'] if admin else None,
        target_id
    )

    await remove_admin(target_id)
    await callback.message.edit_text(txt.REMOVE_ADMIN_OK.format(name=name))
    await callback.answer()

    try:
        await bot.send_message(target_id, txt.REMOVE_ADMIN_NOTIFY, reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        logger.info("Не удалось уведомить снятого админа %s: %s", target_id, e)

    await _render_admins(callback.message)


@router.callback_query(F.data == "rmadmin_no", IsSuperAdmin())
async def cancel_remove_admin(callback: CallbackQuery):
    await callback.message.edit_text(txt.ACTION_CANCELLED)
    await callback.answer()


@router.callback_query(F.data.startswith("rmadmin_"), IsSuperAdmin())
async def ask_remove_admin(callback: CallbackQuery):
    parts = callback.data.split("_")
    if parts[1] in ("yes", "no"):
        return

    try:
        target_id = int(parts[1])
    except (ValueError, IndexError):
        await callback.answer(txt.ERROR_DATA, show_alert=True)
        return

    if target_id in SUPER_ADMIN_IDS:
        await callback.answer(txt.REMOVE_ADMIN_PROTECTED, show_alert=True)
        return

    admin = await get_admin(target_id)
    name = _display_name(
        admin['full_name'] if admin else None,
        admin['username'] if admin else None,
        target_id
    )

    await callback.message.answer(
        txt.REMOVE_ADMIN_CONFIRM.format(name=name),
        reply_markup=get_confirm_remove_admin_kb(target_id)
    )
    await callback.answer()
