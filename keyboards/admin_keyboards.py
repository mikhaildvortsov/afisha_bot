from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

import text_constants as txt

def get_confirm_keyboard():
    buttons = [
        [InlineKeyboardButton(text="✅ Опубликовать", callback_data="save_event")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_event")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_check_payment_keyboard(registration_id: int):
    buttons = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve_{registration_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{registration_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_main_kb():
    keyboard = [
        [KeyboardButton(text=txt.BTN_NEW_EVENT), KeyboardButton(text=txt.BTN_DELETE_EVENT)],
        [KeyboardButton(text=txt.BTN_MY_EVENTS_LIST), KeyboardButton(text=txt.BTN_STATS)],
        [KeyboardButton(text=txt.BTN_GUEST_LISTS), KeyboardButton(text=txt.BTN_SETTINGS)]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_settings_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="✏️ Изменить реквизиты", callback_data="edit_payment_text")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_view_guests_keyboard(events):
    buttons = []
    for event in events:
        buttons.append([InlineKeyboardButton(text=event['title'], callback_data=f"view_guests_{event['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_delete_event_keyboard(events):
    buttons = []
    for event in events:
        buttons.append([InlineKeyboardButton(text=event['title'], callback_data=f"delete_event_{event['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_support_reply_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply_support_{user_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_to_events_list_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_events_list")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_edit_list_btn():
    keyboard = [
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data="start_edit")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_edit_event_list_kb(events):
    buttons = []
    for event in events:
        buttons.append([InlineKeyboardButton(text=event['title'], callback_data=f"edit_select_{event['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_edit_fields_kb(event_id):
    buttons = [
        [InlineKeyboardButton(text="📝 Название", callback_data=f"edit_title_{event_id}")],
        [InlineKeyboardButton(text="📄 Описание", callback_data=f"edit_description_{event_id}")],
        [InlineKeyboardButton(text="📍 Место", callback_data=f"edit_location_{event_id}")],
        [InlineKeyboardButton(text="📅 Дата", callback_data=f"edit_date_time_{event_id}")],
        [InlineKeyboardButton(text="💰 Цена", callback_data=f"edit_price_{event_id}")],
        [InlineKeyboardButton(text="👥 Лимит мест", callback_data=f"edit_capacity_{event_id}")],
        [InlineKeyboardButton(text="🖼 Фото", callback_data=f"edit_photo_id_{event_id}")],
        [InlineKeyboardButton(text="🔗 Ссылка", callback_data=f"edit_join_link_{event_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="start_edit")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
