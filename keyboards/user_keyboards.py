from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard():
    keyboard = [
        [KeyboardButton(text="📅 Афиша")],
        [KeyboardButton(text="🎫 Мои записи")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_event_keyboard(event_id, is_registered=False):
    if is_registered:
        keyboard = [
            [InlineKeyboardButton(text="✅ Вы уже записаны", callback_data="dummy_callback")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton(text="✍️ Записаться", callback_data=f"enroll_{event_id}")]
        ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_my_event_keyboard(event_id):
    keyboard = [
        [InlineKeyboardButton(text="❌ Отменить запись", callback_data=f"cancel_reg_{event_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_support_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="✍️ Написать в поддержку", callback_data="contact_support")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_email_confirmation_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="✅ Да", callback_data="confirm_email")],
        [InlineKeyboardButton(text="📝 Изменить", callback_data="change_email")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_events_list_keyboard(events, callback_prefix="show_event_"):
    buttons = []
    for event in events:
        buttons.append([InlineKeyboardButton(text=event['title'], callback_data=f"{callback_prefix}{event['id']}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
