import telebot
import time
import os
import hashlib
from telebot import types
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime


API_TOKEN = 'API_TOKEN'
GROUP_ID = -1002869161901

bot = telebot.TeleBot(API_TOKEN)
logged_in_users = set()
seen_file_ids = set()
seen_hashes = set()
login_state = {}

user_passwords = {
    2102027453: '123456',
    687977861: '1234'
}

user_name = {
    2102027453: 'SAB',
    687977861: 'RAAJ'
}

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MAX_PHOTO_DELAY = 10

# ========= WATERMARK =========
def add_watermark(image_path, output_path, user_id):
    image = Image.open(image_path).convert("RGBA")
    watermark = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark)
    font = ImageFont.truetype(FONT_PATH, 36)

    username = user_name.get(user_id, str(user_id))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Top username
    draw.text((10, 10), username, font=font, fill="blue")

    # Bottom timestamp
    draw.text((10, image.height - 50), timestamp, font=font, fill="green")

    # Diagonal watermark text
    diagonal_text = "Greenandblueservice"
    bbox = font.getbbox(diagonal_text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    angle = 45

    # Rotate the text and paste
    temp = Image.new("RGBA", (text_width, text_height), (0, 0, 0, 0))
    ImageDraw.Draw(temp).text((0, -10), diagonal_text, font=font, fill=(135, 206, 235, 255))  # semi-transparent green
    rotated = temp.rotate(angle, expand=1)

    # Paste at center
    x = (image.width - rotated.width) // 2
    y = (image.height - rotated.height) // 2
    watermark.paste(rotated, (x, y), rotated)

    # Combine original with watermark
    combined = Image.alpha_composite(image, watermark)
    combined.convert("RGB").save(output_path)


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

    file_info = bot.get_file(photo.file_id)
    file_data = bot.download_file(file_info.file_path)

    raw_path = f"{DOWNLOAD_DIR}/{photo.file_unique_id}_raw.jpg"
    with open(raw_path, 'wb') as f:
        f.write(file_data)

    with open(raw_path, 'rb') as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    if file_hash in seen_hashes:
        os.remove(raw_path)
        bot.delete_message(message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "⚠️ Duplicate photo (hash).")
        return
    seen_hashes.add(file_hash)

    watermarked_path = f"{DOWNLOAD_DIR}/{photo.file_unique_id}_wm.jpg"
    add_watermark(raw_path, watermarked_path, user_id)

    with open(watermarked_path, 'rb') as f:
        bot.send_photo(GROUP_ID, f, caption=f"📸 From user {user_name.get(user_id, user_id)}")

    bot.send_message(message.chat.id, "✅ Photo verified and uploaded.")

# ========= BLOCK OTHERS =========
@bot.message_handler(func=lambda msg: True)
def block_others(message):
    if message.content_type != 'photo':
        bot.delete_message(message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "❌ Only camera photos allowed.")

bot.polling()
