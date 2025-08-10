import telebot
from telebot import types
import sqlite3
import time

# Конфигурация
TOKEN = '8454099090:AAEoptSYB91CITwn1DcUFtUv9vtcvUm9saI'
ADMINS = [1068856695, 8018529527]  # Ваши ID админов
DB_NAME = 'db.db'

bot = telebot.TeleBot(TOKEN)

# Создаем таблицы в базе данных
def create_tables():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT
    )
    ''')
    conn.commit()
    conn.close()

create_tables()

# Обработчик заявок
@bot.chat_join_request_handler()
def lalala(message: telebot.types.ChatJoinRequest):
    user = message.from_user
    user_info = f"Новая заявка!\n\nИмя: {user.first_name}\nФамилия: {user.last_name or '-'}\nUsername: @{user.username}\nID: {user.id}"
    
    # Отправляем админам
    for admin_id in ADMINS:
        try:
            bot.send_message(admin_id, user_info)
        except:
            pass
    
    # Просим пользователя ввести /accept
    bot.send_message(user.id, "Чтобы вас приняли в канал, введите команду /accept")

# Обработчик команды /accept
@bot.message_handler(commands=['accept'])
def handle_accept(message):
    user = message.from_user
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Добавляем пользователя в БД
    cursor.execute('INSERT OR IGNORE INTO users (id, username, first_name, last_name) VALUES (?, ?, ?, ?)',
                   (user.id, user.username, user.first_name, user.last_name))
    conn.commit()
    
    if cursor.rowcount > 0:
        bot.reply_to(message, "✅ Ваша заявка находиться на стадии проверки")
        
        # Уведомляем админов
        for admin_id in ADMINS:
            try:
                bot.send_message(admin_id, f"👤 Пользователь @{user.username} (ID: {user.id}) добавлен в базу!")
            except:
                pass
    else:
        bot.reply_to(message, "✅ Ваша заявка находиться на стадии проверки")

    conn.close()

# Админ-панель
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in ADMINS:
        return

    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("📊 Статистика", callback_data='stats'))
    markup.row(types.InlineKeyboardButton("📣 Рассылка", callback_data='broadcast'))
    markup.row(types.InlineKeyboardButton("✅ Проверка пользователей", callback_data='validate'))
    
    bot.send_message(message.chat.id, "Админ-панель:", reply_markup=markup)

# Обработчик инлайн-кнопок
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.data == 'stats':
        show_stats(call.message)
    elif call.data == 'broadcast':
        start_broadcast(call.message)
    elif call.data == 'validate':
        validate_users(call.message)
    elif call.data == 'cancel_broadcast':
        cancel_broadcast(call.message)

# Показать статистику
def show_stats(message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    
    bot.send_message(message.chat.id, f"👥 Всего пользователей: {count}")

# Начать рассылку
def start_broadcast(message):
    msg = bot.send_message(message.chat.id, "Введите сообщение для рассылки (или /cancel для отмены):")
    bot.register_next_step_handler(msg, process_broadcast_message)

# Обработка сообщения для рассылки
def process_broadcast_message(message):
    if message.text == '/cancel':
        bot.send_message(message.chat.id, "❌ Рассылка отменена")
        return
        
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Отменить", callback_data='cancel_broadcast'))
    
    bot.send_message(message.chat.id, "Рассылка началась...", reply_markup=markup)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users")
    users = cursor.fetchall()
    conn.close()
    
    success = 0
    fail = 0
    
    for user in users:
        try:
            bot.copy_message(user[0], message.chat.id, message.message_id)
            success += 1
        except:
            fail += 1
            # Удаляем невалидного пользователя
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user[0],))
            conn.commit()
            conn.close()
        
        time.sleep(0.05)  # Защита от ограничений
    
    bot.send_message(message.chat.id, f"📊 Результат рассылки:\n\nОтправлено: {success} пользователей\nНе удалось: {fail} пользователей")

# Проверка пользователей
def validate_users(message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users")
    users = cursor.fetchall()
    conn.close()
    
    valid = 0
    invalid = 0
    
    for user in users:
        try:
            msg = bot.send_message(user[0], "🔒")
            bot.delete_message(chat_id=user[0], message_id=msg.message_id)
            valid += 1
        except:
            invalid += 1
            # Удаляем невалидного пользователя
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user[0],))
            conn.commit()
            conn.close()
        
        time.sleep(0.05)
    
    bot.send_message(message.chat.id, f"✅ Результат проверки:\n\nВалидные: {valid} пользователей\nУдалено: {invalid} пользователей")

# Отмена рассылки
def cancel_broadcast(message):
    bot.send_message(message.chat.id, "❌ Рассылка отменена")

if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling(allowed_updates = telebot.util.update_types)