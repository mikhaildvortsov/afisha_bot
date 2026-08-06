import aiosqlite
import datetime
import logging
import os
import re

logger = logging.getLogger(__name__)

if os.path.exists('/data'):
    DB_PATH = '/data/database.db'
else:
    DB_PATH = 'database.db'

async def create_tables():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                username TEXT,
                full_name TEXT,
                phone_number TEXT,
                email TEXT,
                date_joined TIMESTAMP
            )
        ''')
        
        # Миграция для добавления колонки email, если её нет
        try:
            await db.execute('ALTER TABLE users ADD COLUMN email TEXT')
            await db.commit()
        except aiosqlite.OperationalError:
            # Колонка уже существует
            pass

        try:
            await db.execute('ALTER TABLE users ADD COLUMN is_blocked BOOLEAN DEFAULT 0')
            await db.commit()
        except aiosqlite.OperationalError:
            pass


        await db.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                description TEXT,
                date_time TEXT,
                price REAL,
                photo_id TEXT,
                is_active BOOLEAN DEFAULT 1,
                join_link TEXT,
                location TEXT
            )
        ''')
        
        try:
            await db.execute('ALTER TABLE events ADD COLUMN join_link TEXT')
            await db.commit()
        except aiosqlite.OperationalError:
            pass

        try:
            await db.execute('ALTER TABLE events ADD COLUMN location TEXT')
            await db.commit()
        except aiosqlite.OperationalError:
            pass

        try:
            await db.execute('ALTER TABLE events ADD COLUMN capacity INTEGER')
            await db.commit()
        except aiosqlite.OperationalError:
            pass


        await db.execute('''
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_id INTEGER,
                receipt_photo_id TEXT,
                status TEXT,
                amount REAL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(event_id) REFERENCES events(id)
            )
        ''')
        
        try:
            await db.execute('ALTER TABLE registrations ADD COLUMN amount REAL')
            await db.commit()
        except aiosqlite.OperationalError:
            pass

        # Запрещаем повторную активную регистрацию одного пользователя на одно мероприятие
        try:
            await db.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_registration
                ON registrations(user_id, event_id)
                WHERE status IN ('approved', 'pending')
            ''')
            await db.commit()
        except aiosqlite.IntegrityError:
            logger.warning(
                "Не удалось создать уникальный индекс регистраций: в базе уже есть дубликаты. "
                "Нужно вручную очистить повторные записи в таблице registrations."
            )

        await db.execute('''
            CREATE TABLE IF NOT EXISTS bot_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        await db.commit()
    
    # Initialize settings
    await init_settings()

PAYMENT_INFO_PLACEHOLDER = "⚠️ Реквизиты не настроены. Администратор должен указать их в разделе «⚙️ Настройки»."


async def init_settings():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM bot_config WHERE key = 'payment_info'") as cursor:
            row = await cursor.fetchone()

        if not row:
            await db.execute(
                "INSERT INTO bot_config (key, value) VALUES (?, ?)",
                ('payment_info', PAYMENT_INFO_PLACEHOLDER)
            )
            await db.commit()
        elif row[0] and re.search(r'\d{16}', row[0]):
            # В прежних версиях кода был зашит реальный номер карты как значение по умолчанию —
            # вычищаем его из уже развёрнутых баз.
            await db.execute(
                "UPDATE bot_config SET value = ? WHERE key = 'payment_info'",
                (PAYMENT_INFO_PLACEHOLDER,)
            )
            await db.commit()

async def get_payment_text():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM bot_config WHERE key = 'payment_info'") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "Реквизиты не настроены."

async def update_payment_text(new_text):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO bot_config (key, value) VALUES (?, ?)", ('payment_info', new_text))
        await db.commit()

async def add_user(telegram_id, username, full_name):
    if telegram_id is None:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                'INSERT INTO users (telegram_id, username, full_name, date_joined) VALUES (?, ?, ?, ?)',
                (telegram_id, username, full_name, datetime.datetime.now())
            )
            await db.commit()
        except aiosqlite.IntegrityError:
            # Пользователь уже есть — раз он снова пишет боту, он его точно не заблокировал
            await db.execute('UPDATE users SET is_blocked = 0 WHERE telegram_id = ?', (telegram_id,))
            await db.commit()

async def mark_user_blocked(telegram_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE users SET is_blocked = 1 WHERE telegram_id = ?', (telegram_id,))
        await db.commit()

async def get_user(telegram_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,)) as cursor:
            return await cursor.fetchone()

async def update_user_email(telegram_id, email):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'UPDATE users SET email = ? WHERE telegram_id = ?',
            (email, telegram_id)
        )
        await db.commit()

async def add_event(data):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('''
            INSERT INTO events (title, description, date_time, price, photo_id, join_link, location, capacity, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['title'], data['description'], data['date_time'], data['price'], data['photo_id'],
            data.get('join_link'), data.get('location'), data.get('capacity'), True
        ))
        await db.commit()
        return cursor.lastrowid

async def get_event_registration_count(event_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('''
            SELECT COUNT(*) FROM registrations
            WHERE event_id = ? AND status IN ('approved', 'pending')
        ''', (event_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT telegram_id FROM users WHERE is_blocked = 0') as cursor:
            return await cursor.fetchall()

async def get_user_registrations(telegram_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Get internal user id
        cursor = await db.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
        user_row = await cursor.fetchone()
        if not user_row:
            return []
        internal_user_id = user_row[0]
        
        async with db.execute('''
            SELECT e.* 
            FROM registrations r
            JOIN events e ON r.event_id = e.id
            WHERE r.user_id = ? AND r.status IN ('approved', 'pending')
        ''', (internal_user_id,)) as cursor:
            return await cursor.fetchall()

async def cancel_registration(telegram_id, event_id):
    async with aiosqlite.connect(DB_PATH) as db:
        # Get internal user id
        cursor = await db.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
        user_row = await cursor.fetchone()
        if not user_row:
            return
        internal_user_id = user_row[0]
        
        await db.execute('''
            DELETE FROM registrations 
            WHERE user_id = ? AND event_id = ?
        ''', (internal_user_id, event_id))
        await db.commit()

async def is_user_registered(telegram_id, event_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
        user_row = await cursor.fetchone()
        if not user_row:
            return False
        internal_user_id = user_row[0]
        
        async with db.execute('''
            SELECT 1 FROM registrations 
            WHERE user_id = ? AND event_id = ? AND status IN ('approved', 'pending')
        ''', (internal_user_id, event_id)) as cursor:
            return await cursor.fetchone() is not None

async def get_active_events():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM events WHERE is_active = 1') as cursor:
            return await cursor.fetchall()

async def get_event(event_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM events WHERE id = ?', (event_id,)) as cursor:
            return await cursor.fetchone()

async def delete_event(event_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE events SET is_active = 0 WHERE id = ?', (event_id,))
        await db.commit()

ALLOWED_EVENT_FIELDS = {
    'title', 'description', 'date_time', 'price', 'photo_id', 'join_link', 'location', 'capacity'
}

async def update_event_field(event_id, field_name, new_value):
    if field_name not in ALLOWED_EVENT_FIELDS:
        raise ValueError(f"Недопустимое поле для обновления: {field_name}")
    async with aiosqlite.connect(DB_PATH) as db:
        query = f"UPDATE events SET {field_name} = ? WHERE id = ?"
        await db.execute(query, (new_value, event_id))
        await db.commit()

class DuplicateRegistrationError(Exception):
    """Пользователь уже имеет активную (pending/approved) регистрацию на это мероприятие."""


async def create_registration(telegram_id, event_id, receipt_photo_id=None, status='pending', amount=0):
    async with aiosqlite.connect(DB_PATH) as db:
        # Get internal user id
        cursor = await db.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
        user_row = await cursor.fetchone()
        if not user_row:
            return None
        internal_user_id = user_row[0]

        try:
            cursor = await db.execute('''
                INSERT INTO registrations (user_id, event_id, receipt_photo_id, status, amount)
                VALUES (?, ?, ?, ?, ?)
            ''', (internal_user_id, event_id, receipt_photo_id, status, amount))
            await db.commit()
            return cursor.lastrowid
        except aiosqlite.IntegrityError as e:
            raise DuplicateRegistrationError(str(e)) from e

async def get_registration(registration_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT r.*, u.telegram_id, e.title as event_title 
            FROM registrations r
            JOIN users u ON r.user_id = u.id
            JOIN events e ON r.event_id = e.id
            WHERE r.id = ?
        ''', (registration_id,)) as cursor:
            return await cursor.fetchone()

async def update_registration_status(registration_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('UPDATE registrations SET status = ? WHERE id = ?', (status, registration_id))
        await db.commit()

async def get_users_count():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT COUNT(*) FROM users') as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

async def get_bot_statistics():
    async with aiosqlite.connect(DB_PATH) as db:
        stats = {}
        
        # Total users
        async with db.execute('SELECT COUNT(*) FROM users') as cursor:
            res = await cursor.fetchone()
            stats['total_users'] = res[0] if res else 0
            
        # Active events
        async with db.execute('SELECT COUNT(*) FROM events WHERE is_active = 1') as cursor:
            res = await cursor.fetchone()
            stats['active_events'] = res[0] if res else 0
            
        # Total approved registrations
        async with db.execute("SELECT COUNT(*) FROM registrations WHERE status = 'approved'") as cursor:
            res = await cursor.fetchone()
            stats['total_registrations'] = res[0] if res else 0
            
        # Pending checks
        async with db.execute("SELECT COUNT(*) FROM registrations WHERE status = 'pending'") as cursor:
            res = await cursor.fetchone()
            stats['pending_checks'] = res[0] if res else 0
            
        # Total revenue
        async with db.execute("""
            SELECT SUM(amount) 
            FROM registrations 
            WHERE status = 'approved'
        """) as cursor:
            res = await cursor.fetchone()
            stats['total_revenue'] = res[0] if res and res[0] is not None else 0
            
        return stats

async def get_event_participants(event_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT u.full_name, u.username
            FROM registrations r
            JOIN users u ON r.user_id = u.id
            WHERE r.event_id = ? AND r.status = 'approved'
        ''', (event_id,)) as cursor:
            return await cursor.fetchall()
