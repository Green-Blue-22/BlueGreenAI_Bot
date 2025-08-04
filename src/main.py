import telebot
import time
import os
import hashlib
from telebot import types




API_TOKEN = '8247236172:AAGcwDr5fW_THlvwwWso5jKoc4P6swG9tKA'  # Replace with your actual token
bot = telebot.TeleBot(API_TOKEN)

# ========== LOGIN USERS ==========
logged_in_users = set()

# ========== DUPLICATE CHECK STORAGE ==========
seen_file_ids = set()         # for file_unique_id method
seen_hashes = set()           # for hash method (optional)
DOWNLOAD_DIR = "downloads"    # store temporary images

os.makedirs(DOWNLOAD_DIR, exist_ok=True)



@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("/login")
    markup.add(btn1, btn2)

    bot.send_message(
        message.chat.id,
        "👋 Welcome! Use the buttons below to begin:",
        reply_markup=markup
    )



@bot.message_handler(commands=['info'])
def send_info(message):
    bot.reply_to(
        message,
        "🌐 Website: https://www.greenandbluegroups.com/\n"
        "📞 Contact Admin: +91 98653 21478"
    )

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(
        message,
        "/start - start\n"
        "/login - user login service\n"
        "/info  - whoami\n"
        "/id    - get your id info\n"
        "/help  - full details info"
    )

@bot.message_handler(commands=['id'])
def send_user_id(message):
    user_id = message.from_user.id
    bot.reply_to(message, f"🆔 Your Telegram User ID is: {user_id}")

# ========== LOGIN LOGIC ==========
login_state = {}
user_passwords = {
    2102027453: '123456',
    987654321: 'abc456'
}
logged_in_users = set()

@bot.message_handler(commands=['login'])
def login_start(message):
    bot.reply_to(message, "🔐 Please enter your password:")
    login_state[message.from_user.id] = 'awaiting_password'

@bot.message_handler(func=lambda msg: login_state.get(msg.from_user.id) == 'awaiting_password')
def handle_password(message):
    user_id = message.from_user.id
    entered_pass = message.text.strip()
    correct_pass = user_passwords.get(user_id)

    if entered_pass == correct_pass:
        logged_in_users.add(user_id)
        bot.reply_to(message, "✅ Login successful. You can now upload photos.")
    else:
        bot.reply_to(message, "❌ Incorrect password.")

    login_state.pop(user_id, None)

# ========== PHOTO HANDLER ==========
MAX_PHOTO_DELAY = 10  # seconds

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id

    if user_id not in logged_in_users:
        bot.delete_message(message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "🚫 You must login first using /login.")
        return

    msg_time = message.date
    now = int(time.time())

    # Block delayed/gallery photo
    if now - msg_time > MAX_PHOTO_DELAY:
        bot.delete_message(message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "❌ Please send a live camera photo.")
        return

    # 1️⃣ Check file_unique_id (quick duplicate detection)
    photo = message.photo[-1]  # best quality
    file_unique_id = photo.file_unique_id

    if file_unique_id in seen_file_ids:
        bot.delete_message(message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "⚠️ Duplicate photo detected (by ID).")
        return
    seen_file_ids.add(file_unique_id)

    # 2️⃣ Optional: Download and check SHA256 hash
    file_info = bot.get_file(photo.file_id)
    file_path = file_info.file_path
    downloaded_file = bot.download_file(file_path)

    temp_file = f"{DOWNLOAD_DIR}/{file_unique_id}.jpg"
    with open(temp_file, 'wb') as f:
        f.write(downloaded_file)

    # Compute hash
    with open(temp_file, 'rb') as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()

    if file_hash in seen_hashes:
        os.remove(temp_file)
        bot.delete_message(message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "⚠️ Duplicate photo detected (by hash).")
        return
    seen_hashes.add(file_hash)

    # ✅ If all checks pass
    bot.send_message(message.chat.id, "✅ Photo accepted.")
    os.remove(temp_file)

# ========== BLOCK OTHER MESSAGES ==========
@bot.message_handler(func=lambda msg: True)
def block_others(message):
    if message.content_type != 'photo':
        bot.delete_message(message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "❌ Only camera photos are allowed.")

bot.polling()



