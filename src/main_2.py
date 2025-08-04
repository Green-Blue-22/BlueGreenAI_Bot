import telebot
import time
import os
import hashlib
from telebot import types
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

API_TOKEN = '8247236172:AAGcwDr5fW_THlvwwWso5jKoc4P6swG9tKA'  # Replace with your actual token
GROUP_ID = -1002869161901  # 🔁 Replace with your group ID

bot = telebot.TeleBot(API_TOKEN)
logged_in_users = set()
seen_file_ids = set()
seen_hashes = set()
login_state = {}
user_passwords = {
    2102027453: '123456',
    687977861: '1234'
}


## @bot.message_handler(func=lambda message: True)
## def debug_id(message):
##     print(message.chat.id)
## GROUP_ID = -1002869161901  # 🔁 Replace with your group ID



DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MAX_PHOTO_DELAY = 10

# ========= WATERMARK =========
def add_watermark(image_path, output_path):
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(FONT_PATH, 36)
    text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    draw.text((10, image.height - 50), text, font=font, fill="white")
    image.save(output_path)

# ========= START =========
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("/login"))
    bot.send_message(message.chat.id, "👋 Welcome! Tap /login to begin.", reply_markup=markup)

@bot.message_handler(commands=['id'])
def send_user_id(message):
    user_id = message.from_user.id
    bot.reply_to(message, f"🆔 Your Telegram User ID is: {user_id}")


# ========= LOGIN =========
@bot.message_handler(commands=['login'])
def login_start(message):
    bot.reply_to(message, "🔐 Enter password:")
    login_state[message.from_user.id] = 'awaiting_password'

@bot.message_handler(func=lambda msg: login_state.get(msg.from_user.id) == 'awaiting_password')
def handle_password(message):
    user_id = message.from_user.id
    if message.text.strip() == user_passwords.get(user_id):
        logged_in_users.add(user_id)
        bot.reply_to(message, "✅ Login success. Send camera photos.")
    else:
        bot.reply_to(message, "❌ Wrong password.")
    login_state.pop(user_id, None)

# ========= PHOTO UPLOAD =========
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.from_user.id

    if user_id not in logged_in_users:
        bot.delete_message(message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "🚫 Login with /login first.")
        return

    now = int(time.time())
    if now - message.date > MAX_PHOTO_DELAY:
        bot.delete_message(message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "❌ Please send photo via camera, not gallery.")
        return

    photo = message.photo[-1]
    if photo.file_unique_id in seen_file_ids:
        bot.delete_message(message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "⚠️ Duplicate photo (ID).")
        return
    seen_file_ids.add(photo.file_unique_id)

    # Download
    file_info = bot.get_file(photo.file_id)
    file_data = bot.download_file(file_info.file_path)
    raw_path = f"{DOWNLOAD_DIR}/{photo.file_unique_id}.jpg"
    with open(raw_path, 'wb') as f:
        f.write(file_data)

    # Hash check
    with open(raw_path, 'rb') as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    if file_hash in seen_hashes:
        os.remove(raw_path)
        bot.delete_message(message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "⚠️ Duplicate photo (hash).")
        return
    seen_hashes.add(file_hash)

    # Add watermark
    watermarked_path = f"{DOWNLOAD_DIR}/wm_{photo.file_unique_id}.jpg"
    add_watermark(raw_path, watermarked_path)

    # Upload to group
    with open(watermarked_path, 'rb') as f:
        bot.send_photo(GROUP_ID, f, caption=f"📸 From user {user_id}")

    bot.send_message(message.chat.id, "✅ Photo verified and uploaded.")
    os.remove(raw_path)
    os.remove(watermarked_path)

# ========= BLOCK OTHERS =========
@bot.message_handler(func=lambda msg: True)
def block_others(message):
    if message.content_type != 'photo':
        bot.delete_message(message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "❌ Only camera photos allowed.")

bot.polling()
