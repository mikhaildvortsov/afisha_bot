# --- Общие ---
WELCOME_TEXT = "👋 Привет! Добро пожаловать в бота p.​club 🌟 здесь ты сможешь зарегистрироваться на мероприятия 📝 и видеть анонсы новых событий 📢"
WELCOME_ADMIN = "👋 Привет, Админ! Выбери действие в меню:"
SUPPORT_CONTACT = "По вопросам пишите: https://t.me/psycho_clubdm"
NO_EVENTS = "😔 Пока нет активных мероприятий."
EVENT_NOT_FOUND = "⚠️ Мероприятие не найдено."
ERROR_DATA = "Ошибка данных."
CHOOSE_EVENT = "Выберите мероприятие:"
NO_LINK = "Ссылка не указана"
EVENT_FULL = "😔 К сожалению, все места на это мероприятие уже заняты."
DUPLICATE_REGISTRATION = "Вы уже подали заявку на это мероприятие. Дождитесь подтверждения."
ONLINE_LOCATION = "Онлайн"
NONE_VALUE = "Нет"

# --- Кнопки главного меню (используются и в клавиатурах, и в фильтрах хендлеров) ---
BTN_AFISHA = "📅 Афиша"
BTN_MY_REGISTRATIONS = "🎫 Мои записи"
BTN_NEW_EVENT = "➕ Создать мероприятие"
BTN_DELETE_EVENT = "🗑 Удалить мероприятие"
BTN_MY_EVENTS_LIST = "📋 Мои афиши"
BTN_STATS = "📊 Статистика"
BTN_GUEST_LISTS = "👥 Списки участников"
BTN_SETTINGS = "⚙️ Настройки"

EVENT_CARD_TEXT = (
    "✨ {title}\n"
    "📝 {description}\n"
    "📍 Где: {location}\n"
    "📅 Когда: {date_time}\n"
    "💰 Цена: {price_text}\n"
    "👇 Жми кнопку ниже, чтобы записаться!"
)

# --- Регистрация пользователя ---
NO_MY_REGISTRATIONS = "У вас нет активных записей на мероприятия."
MY_REGISTRATIONS_LIST = "Мероприятия, на которые вы записаны:"
NOT_REGISTERED_ANYMORE = "Вы больше не записаны на это мероприятие."
REGISTRATION_CANCELLED_SIMPLE = "Запись отменена."
ALREADY_REGISTERED = "Вы уже записаны на это мероприятие"
REGISTRATION_ERROR = "Ошибка регистрации. Попробуйте нажать /start и повторить."

EMAIL_CONFIRM = "Ваш Email: {email}\nВсё верно?"
EMAIL_PROMPT = "📧 Пожалуйста, введите ваш Email для связи:"
EMAIL_PROMPT_NEW = "📧 Пожалуйста, введите новый Email:"
EMAIL_INVALID = "⚠️ Некорректный формат email. Пример: example@mail.ru"

REGISTRATION_APPROVED_FREE = "Спасибо за регистрацию! До встречи на мероприятии {title}\n📎 Ссылка для входа: {join_link}"
NEW_FREE_REGISTRATION_ADMIN = "🆕 Новая регистрация (бесплатно)!\n\nПользователь: {user_display}\nМероприятие: {title}"
RECEIPT_SENT = "⏳ Чек отправлен на проверку. Ожидайте подтверждения."
REGISTRATION_APPROVED = "✅ Оплата подтверждена!\nДо встречи на мероприятии {title}\n📎 Ссылка для входа: {join_link}"
REGISTRATION_REJECTED = "❌ Оплата не принята. Свяжитесь с поддержкой."
REGISTRATION_CANCELLED_ADMIN = "⚠️ <b>Отмена записи!</b>\n\n👤 Пользователь: {user_display}\n📅 Мероприятие: {title}"
REGISTRATION_CANCELLED_USER = "Запись на мероприятие «{title}» отклонена, администратор будет уведомлен."
NEW_PAID_REGISTRATION_ADMIN = "💰 Новая заявка на оплату!\n\nПользователь: {user_display}\nМероприятие: {title}\nСумма: {price} руб."

# --- Оплата ---
PAYMENT_HEADER = "Для завершения регистрации переведите необходимую сумму по следующим реквизитам:"
PAYMENT_FOOTER = "📸 Важно: После перевода пришлите скриншот чека или квитанции ответным сообщением в этот чат.\nМы проверим оплату и сразу пришлем ваш билет!"
ADMIN_APPROVED = "✅ Подтверждено"
ADMIN_REJECTED = "❌ Отклонено"

# --- Поддержка ---
WRITE_TO_SUPPORT = "✍️ Напишите ваше обращение в поддержку, вам ответят в ближайшее время"
SUPPORT_MESSAGE_SENT = "✅ Ваше сообщение отправлено в поддержку!"
SUPPORT_MESSAGE_HEADER = "📨 <b>Обращение в поддержку (об отказе оплаты)</b>\nОт: {user_display}\n\n{message}"
SUPPORT_ANSWER_PREFIX = "📨 <b>Ответ от поддержки:</b>\n\n{answer}"
SUPPORT_REPLY_PROMPT = "✍️ Введите ваш ответ пользователю:"
SUPPORT_REPLY_SENT = "✅ Ответ отправлен!"
SUPPORT_REPLY_FAILED = "❌ Не удалось отправить сообщение: {error}"

# --- Админ-панель ---
ADMIN_PANEL_WELCOME = "Добро пожаловать в панель управления"
STATS_TEXT = (
    "📊 <b>Статистика проекта</b>\n\n"
    "👥 Пользователей: {total_users}\n"
    "📅 Активных событий: {active_events}\n"
    "🎫 Выдано билетов: {total_registrations}\n"
    "⏳ Висит на проверке: {pending_checks}\n"
    "💰 Общая выручка: {total_revenue} руб."
)

PAYMENT_SETTINGS_CURRENT = "Текущие реквизиты для оплаты:\n\n{payment_text}"
PAYMENT_TEXT_PROMPT = "Введите ТОЛЬКО новые реквизиты (например: 0000 0000 0000 0000 (Иван)). Инструкция добавится автоматически."
PAYMENT_TEXT_UPDATED = "Реквизиты обновлены"

EMPTY_LIST = "Список пуст"
CHOOSE_EVENT_DELETE = "Выберите мероприятие для удаления:"
EVENT_DELETED = "Мероприятие удалено"

# --- Создание мероприятия ---
NEW_EVENT_TITLE_PROMPT = "📝 Введите название мероприятия:"
NEW_EVENT_DESC_PROMPT = "📄 Введите описание мероприятия:"
NEW_EVENT_LOCATION_PROMPT = "📌 Где будет проходить мероприятие? (Напишите адрес или 'Онлайн')"
NEW_EVENT_DATETIME_PROMPT = "🗓 Введите дату и время проведения (например, 20.10.2023 18:00):"
NEW_EVENT_PRICE_PROMPT = "💰 Введите цену (число, 0 если бесплатно):"
NEW_EVENT_CAPACITY_PROMPT = "👥 Сколько мест доступно? (0 — без ограничений)"
NEW_EVENT_PHOTO_PROMPT = "🖼 Пришлите фото афиши:"
NEW_EVENT_LINK_PROMPT = "🔗 Теперь пришлите ссылку, которую получит клиент после оплаты (ссылка на канал, группу или место встречи). Если ссылки нет, напишите прочерк (-)."
INVALID_NUMBER = "⚠️ Пожалуйста, введите корректное число."

EVENT_PREVIEW_TEXT = (
    "<b>Предпросмотр:</b>\n\n"
    "✨ {title}\n"
    "📝 {description}\n"
    "📍 Где: {location}\n"
    "📅 Когда: {date_time}\n"
    "💰 Цена: {price_text}\n"
    "🔗 Ссылка для входа: {link_text}\n"
    "👇 Жми кнопку ниже, чтобы записаться!"
)
EVENT_PUBLISHED = "✅ Мероприятие опубликовано!"
EVENT_BROADCAST_TEXT = (
    "✨ {title}\n"
    "📝 {description}\n"
    "📌 Где: {location}\n"
    "📅 Когда: {date_time}\n"
    "💰 Цена: {price_text}\n"
    "👇 Жми кнопку ниже, чтобы записаться!"
)
BROADCAST_DONE = "📢 Рассылка завершена. Отправлено {count} пользователям."

REGISTRATION_NOT_FOUND = "Регистрация не найдена."
BUTTON_DATA_ERROR = "Ошибка данных кнопки. Создайте новую заявку."

GUEST_LIST_EMPTY = "📋 <b>Список участников на {title}</b>\n\nПока никто не записался."
GUEST_LIST_HEADER = "📋 <b>Список участников на {title}</b>\nВсего записей: {count}\n\n"
GUEST_LIST_FOOTER = "\nИтого: {count} человека."
CHOOSE_EVENT_GUESTS = "Выберите мероприятие, чтобы посмотреть список гостей:"
NAVIGATION = "Навигация:"

MY_EVENTS_HEADER = "<b>📋 Ваши активные мероприятия:</b>\n\n"
MY_EVENTS_ITEM = "🔹 <b>{title}</b>\n📅 {date_time} | 💰 {price_text}\n🆔 ID: {id}\n➖➖➖➖➖➖➖➖➖➖\n"
FIELD_VALUE_FALLBACK = "значение"
CHOOSE_EVENT_EDIT = "Выберите мероприятие для редактирования:"
CHOOSE_FIELD_EDIT = "Выберите поле для редактирования:"
EDIT_FIELD_PROMPT = "Введите новое {display_name}:"
STATE_ERROR = "Ошибка состояния. Попробуйте снова."
PLEASE_SEND_PHOTO = "Пожалуйста, отправьте фото."
PLEASE_SEND_TEXT = "Пожалуйста, отправьте текст."
FIELD_UPDATED = "✅ Успешно обновлено"

EDIT_FIELD_DISPLAY_NAMES = {
    "title": "название",
    "description": "описание",
    "location": "место проведения",
    "date_time": "дату и время",
    "price": "цену",
    "photo_id": "фото",
    "join_link": "ссылку",
    "capacity": "лимит мест (0 — без ограничений)",
}
