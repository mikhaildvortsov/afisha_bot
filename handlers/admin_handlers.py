import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from config import ADMIN_IDS
from keyboards.admin_keyboards import (
    get_confirm_keyboard, 
    get_admin_main_kb, 
    get_delete_event_keyboard, 
    get_view_guests_keyboard, 
    get_back_to_events_list_keyboard,
    get_settings_keyboard,
    get_edit_list_btn,
    get_edit_event_list_kb,
    get_edit_fields_kb
)
from database import add_event, update_registration_status, get_registration, get_users_count, get_active_events, delete_event, get_event_participants, get_event, get_all_users, get_bot_statistics, get_payment_text, update_payment_text, update_event_field
import text_constants as txt
from keyboards.user_keyboards import get_support_keyboard, get_event_keyboard

router = Router()

class EditEventState(StatesGroup):
    waiting_for_new_value = State()

class EventStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_location = State()
    waiting_for_datetime = State()
    waiting_for_price = State()
    waiting_for_photo = State()
    waiting_for_link = State()
    waiting_for_confirmation = State()

class AdminSupportStates(StatesGroup):
    waiting_for_reply = State()

class SettingsState(StatesGroup):
    waiting_for_payment_text = State()

@router.message(Command("admin"), F.from_user.id.in_(ADMIN_IDS))
async def admin_start(message: Message):
    await message.answer("Добро пожаловать в панель управления", reply_markup=get_admin_main_kb())

@router.message(F.text == "📊 Статистика", F.from_user.id.in_(ADMIN_IDS))
async def get_stats(message: Message, state: FSMContext):
    await state.clear()
    stats = await get_bot_statistics()
    
    text = (
        f"📊 <b>Статистика проекта</b>\n\n"
        f"👥 Пользователей: {stats['total_users']}\n"
        f"📅 Активных событий: {stats['active_events']}\n"
        f"🎫 Выдано билетов: {stats['total_registrations']}\n"
        f"⏳ Висит на проверке: {stats['pending_checks']}\n"
        f"💰 Общая выручка: {stats['total_revenue']} руб."
    )
    
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "⚙️ Настройки", F.from_user.id.in_(ADMIN_IDS))
async def show_settings(message: Message):
    current_text = await get_payment_text()
    await message.answer(
        f"Текущие реквизиты (номер карты):\n\n{current_text}",
        reply_markup=get_settings_keyboard()
    )

@router.callback_query(F.data == "edit_payment_text", F.from_user.id.in_(ADMIN_IDS))
async def start_edit_payment_text(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsState.waiting_for_payment_text)
    await callback.message.answer("Введите ТОЛЬКО новые реквизиты (например: 0000 0000 0000 0000 (Иван)). Инструкция добавится автоматически.")
    await callback.answer()

@router.message(SettingsState.waiting_for_payment_text, F.from_user.id.in_(ADMIN_IDS))
async def process_new_payment_text(message: Message, state: FSMContext):
    new_text = message.text
    await update_payment_text(new_text)
    await message.answer("Реквизиты обновлены")
    await state.clear()

@router.message(F.text == "🗑 Удалить мероприятие", F.from_user.id.in_(ADMIN_IDS))
async def start_delete_event(message: Message, state: FSMContext):
    await state.clear()
    events = await get_active_events()
    if not events:
        await message.answer("Список пуст")
        return
    
    await message.answer("Выберите мероприятие для удаления:", reply_markup=get_delete_event_keyboard(events))

@router.callback_query(F.data.startswith("delete_event_"), F.from_user.id.in_(ADMIN_IDS))
async def process_delete_event(callback: CallbackQuery):
    event_id = int(callback.data.split("_")[2])
    await delete_event(event_id)
    
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Мероприятие удалено")
    await callback.answer()

@router.callback_query(F.data.startswith("reply_support_"), F.from_user.id.in_(ADMIN_IDS))
async def start_support_reply(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[2])
    await state.update_data(reply_user_id=user_id)
    await state.set_state(AdminSupportStates.waiting_for_reply)
    await callback.message.answer("✍️ Введите ваш ответ пользователю:")
    await callback.answer()

@router.message(AdminSupportStates.waiting_for_reply, F.from_user.id.in_(ADMIN_IDS))
async def send_support_reply(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user_id = data.get('reply_user_id')
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=txt.SUPPORT_ANSWER_PREFIX.format(answer=message.text),
            parse_mode="HTML"
        )
        await message.answer("✅ Ответ отправлен!")
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить сообщение: {e}")
        
    await state.clear()

# Фильтр на админа
@router.message(Command("new_event"), F.from_user.id.in_(ADMIN_IDS))
@router.message(F.text == "➕ Создать мероприятие", F.from_user.id.in_(ADMIN_IDS))
async def start_new_event(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(EventStates.waiting_for_title)
    await message.answer("📝 Введите название мероприятия:")

@router.message(EventStates.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(EventStates.waiting_for_description)
    await message.answer("📄 Введите описание мероприятия:")

@router.message(EventStates.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(EventStates.waiting_for_location)
    await message.answer("📌 Где будет проходить мероприятие? (Напишите адрес или 'Онлайн')")

@router.message(EventStates.waiting_for_location)
async def process_location(message: Message, state: FSMContext):
    await state.update_data(location=message.text)
    await state.set_state(EventStates.waiting_for_datetime)
    await message.answer("🗓 Введите дату и время проведения (например, 20.10.2023 18:00):")

@router.message(EventStates.waiting_for_datetime)
async def process_datetime(message: Message, state: FSMContext):
    await state.update_data(date_time=message.text)
    await state.set_state(EventStates.waiting_for_price)
    await message.answer("💰 Введите цену (число, 0 если бесплатно):")

@router.message(EventStates.waiting_for_price)
async def process_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(',', '.'))
        if price < 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите корректное число.")
        return

    await state.update_data(price=price)
    await state.set_state(EventStates.waiting_for_photo)
    await message.answer("🖼 Пришлите фото афиши:")

@router.message(EventStates.waiting_for_photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await state.set_state(EventStates.waiting_for_link)
    await message.answer("🔗 Теперь пришлите ссылку, которую получит клиент после оплаты (ссылка на канал, группу или место встречи). Если ссылки нет, напишите прочерк (-).")

@router.message(EventStates.waiting_for_link)
async def process_link(message: Message, state: FSMContext):
    link = message.text.strip()
    join_link = link if link != "-" else None
    await state.update_data(join_link=join_link)
    
    data = await state.get_data()
    
    price_text = "Бесплатно" if data['price'] == 0 else f"{data['price']} руб."
    link_text = join_link if join_link else "Нет"
    
    preview_text = (
        f"<b>Предпросмотр:</b>\n\n"
        f"✨ {data['title']}\n"
        f"📝 {data['description']}\n"
        f"📍 Где: {data['location']}\n"
        f"📅 Когда: {data['date_time']}\n"
        f"💰 Цена: {price_text}\n"
        f"🔗 Ссылка для входа: {link_text}\n"
        f"👇 Жми кнопку ниже, чтобы записаться!"
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
    await callback.message.answer("✅ Мероприятие опубликовано!", reply_markup=get_admin_main_kb())
    
    users = await get_all_users()
    price_text = "Бесплатно" if data['price'] == 0 else f"{data['price']} руб."
    
    caption = (
        f"✨ {data['title']}\n"
        f"📝 {data['description']}\n"
        f"📌 Где: {data['location']}\n"
        f"📅 Когда: {data['date_time']}\n"
        f"💰 Цена: {price_text}\n"
        f"👇 Жми кнопку ниже, чтобы записаться!"
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
        except Exception:
            continue
            
    msg = await callback.message.answer(f"📢 Рассылка завершена. Отправлено {count} пользователям.")
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

@router.callback_query(F.data.startswith("approve_"), F.from_user.id.in_(ADMIN_IDS))
async def approve_payment(callback: CallbackQuery, bot: Bot):
    try:
        reg_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("Ошибка данных кнопки. Создайте новую заявку.", show_alert=True)
        return

    reg = await get_registration(reg_id)
    
    if not reg:
        await callback.answer("Регистрация не найдена.", show_alert=True)
        return
        
    await update_registration_status(reg_id, "approved")
    
    # Удаляем кнопки и пишем "Подтверждено" в сообщение админа
    try:
        current_caption = callback.message.caption or ""
        await callback.message.edit_caption(
            caption=f"{current_caption}\n\n{txt.ADMIN_APPROVED}",
            reply_markup=None
        )
    except:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(txt.ADMIN_APPROVED)
    
    # Получаем данные события для ссылки
    event = await get_event(reg['event_id'])
    join_link = event['join_link'] if event and event['join_link'] else "Ссылка не указана"

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
        # Логируем ошибку, если нужно, но главное не роняем хендлер
        print(f"Не удалось отправить уведомление пользователю: {e}")
    
    await callback.answer()

@router.callback_query(F.data.startswith("reject_"), F.from_user.id.in_(ADMIN_IDS))
async def reject_payment(callback: CallbackQuery, bot: Bot):
    try:
        reg_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("Ошибка данных кнопки. Создайте новую заявку.", show_alert=True)
        return

    reg = await get_registration(reg_id)
    
    if not reg:
        await callback.answer("Регистрация не найдена.", show_alert=True)
        return
        
    await update_registration_status(reg_id, "rejected")
    
    # Удаляем сообщение с чеком у админа
    try:
        await callback.message.delete()
    except Exception as e:
        print(f"Не удалось удалить сообщение админа: {e}")
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
         print(f"Не удалось отправить уведомление пользователю: {e}")
    
    await callback.answer()

@router.message(F.text == "📋 Мои афиши", F.from_user.id.in_(ADMIN_IDS))
async def show_admin_events(message: Message, state: FSMContext):
    await state.clear()
    events = await get_active_events()
    
    if not events:
        await message.answer(txt.NO_EVENTS)
        return

    response_text = "<b>📋 Ваши активные мероприятия:</b>\n\n"
    for event in events:
        price_text = "Бесплатно" if event['price'] == 0 else f"{event['price']} руб."
        response_text += (
            f"🔹 <b>{event['title']}</b>\n"
            f"📅 {event['date_time']} | 💰 {price_text}\n"
            f"🆔 ID: {event['id']}\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
        )
    
    await message.answer(response_text, parse_mode="HTML", reply_markup=get_edit_list_btn())

@router.message(F.text == "👥 Списки участников", F.from_user.id.in_(ADMIN_IDS))
async def view_guests_list(message: Message, state: FSMContext):
    await state.clear()
    events = await get_active_events()
    
    if not events:
        await message.answer(txt.NO_EVENTS)
        return

    await message.answer(
        "Выберите мероприятие, чтобы посмотреть список гостей:",
        reply_markup=get_view_guests_keyboard(events)
    )

@router.callback_query(F.data.startswith("view_guests_"), F.from_user.id.in_(ADMIN_IDS))
async def show_guest_list(callback: CallbackQuery):
    try:
        event_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка данных.", show_alert=True)
        return

    event = await get_event(event_id)
    participants = await get_event_participants(event_id)
    
    if not event:
        await callback.answer("Мероприятие не найдено.", show_alert=True)
        return

    if not participants:
        await callback.message.edit_text(
            f"📋 <b>Список участников на {event['title']}</b>\n\n"
            "Пока никто не записался.",
            parse_mode="HTML",
            reply_markup=get_back_to_events_list_keyboard()
        )
        await callback.answer()
        return

    text = f"📋 <b>Список участников на {event['title']}</b>\n"
    text += f"Всего записей: {len(participants)}\n\n"
    
    for user in participants:
        username = f"(@{user['username']})" if user['username'] else ""
        text += f"👤 {user['full_name']} {username}\n"
    
    text += f"\nИтого: {len(participants)} человека."
    
    # Разбиваем сообщение, если оно слишком длинное (лимит телеграма 4096 символов)
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for part in parts:
            await callback.message.answer(part, parse_mode="HTML")
        await callback.message.answer("Навигация:", reply_markup=get_back_to_events_list_keyboard())
        await callback.message.delete() # Удаляем исходное сообщение с кнопками
    else:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_back_to_events_list_keyboard())
        
    await callback.answer()

@router.callback_query(F.data == "back_to_events_list", F.from_user.id.in_(ADMIN_IDS))
async def back_to_events_list_handler(callback: CallbackQuery):
    events = await get_active_events()
    
    if not events:
        await callback.message.edit_text(txt.NO_EVENTS)
        await callback.answer()
        return

    await callback.message.edit_text(
        "Выберите мероприятие, чтобы посмотреть список гостей:",
        reply_markup=get_view_guests_keyboard(events)
    )
    await callback.answer()

@router.callback_query(F.data == "start_edit", F.from_user.id.in_(ADMIN_IDS))
async def start_edit_handler(callback: CallbackQuery):
    events = await get_active_events()
    if not events:
        await callback.answer(txt.NO_EVENTS, show_alert=True)
        return
        
    await callback.message.answer(
        "Выберите мероприятие для редактирования:",
        reply_markup=get_edit_event_list_kb(events)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("edit_select_"), F.from_user.id.in_(ADMIN_IDS))
async def select_event_to_edit(callback: CallbackQuery):
    try:
        event_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("Ошибка данных.", show_alert=True)
        return

    await callback.message.edit_text(
        "Выберите поле для редактирования:",
        reply_markup=get_edit_fields_kb(event_id)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("edit_"), F.from_user.id.in_(ADMIN_IDS))
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
        await callback.answer("Ошибка данных.", show_alert=True)
        return
        
    await state.update_data(editing_event_id=event_id, editing_field=field_name)
    await state.set_state(EditEventState.waiting_for_new_value)
    
    field_display_names = {
        "title": "название",
        "description": "описание",
        "location": "место проведения",
        "date_time": "дату и время",
        "price": "цену",
        "photo_id": "фото",
        "join_link": "ссылку"
    }
    
    display_name = field_display_names.get(field_name, "значение")
    
    await callback.message.answer(f"Введите новое {display_name}:")
    await callback.answer()

@router.message(EditEventState.waiting_for_new_value, F.from_user.id.in_(ADMIN_IDS))
async def process_new_field_value(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get('editing_event_id')
    field_name = data.get('editing_field')
    
    if not event_id or not field_name:
        await message.answer("Ошибка состояния. Попробуйте снова.")
        await state.clear()
        return

    new_value = None
    
    if field_name == "photo_id":
        if message.photo:
            new_value = message.photo[-1].file_id
        else:
            await message.answer("Пожалуйста, отправьте фото.")
            return
    elif field_name == "price":
        try:
            new_value = float(message.text.replace(',', '.'))
            if new_value < 0: raise ValueError
        except ValueError:
            await message.answer("Пожалуйста, введите корректное число.")
            return
    elif field_name == "join_link":
        new_value = message.text.strip()
        if new_value == "-":
            new_value = None
    else:
        if message.text:
            new_value = message.text
        else:
            await message.answer("Пожалуйста, отправьте текст.")
            return

    await update_event_field(event_id, field_name, new_value)
    
    await message.answer(
        "✅ Успешно обновлено",
        reply_markup=get_edit_fields_kb(event_id)
    )
    await state.clear()

