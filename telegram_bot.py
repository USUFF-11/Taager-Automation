import asyncio
import gspread
from google.oauth2.service_account import Credentials
from telegram import (
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

# ==========================
# TELEGRAM
# ==========================
BOT_TOKEN = "8660875238:AAFxhtqmeltst3DNyF1VwKdtzNnrOayQNZE"
CHANNEL_ID = "@taagerstore"

# ==========================
# GOOGLE SHEETS
# ==========================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

creds = Credentials.from_service_account_file(
    "credentials.json",
    scopes=SCOPES,
)

client = gspread.authorize(creds)

sheet = client.open("Taager").worksheet("Products")

# أول منتج
product = sheet.get_all_records()[0]

name = product["Name"]
price = product["Selling Price"]
image = product["Image"]

caption = f"""🛍 **{name}**

💰 السعر: {price} جنيه

🚚 الشحن يحسب حسب المحافظة
"""

# ==========================
# BUTTONS
# ==========================

keyboard = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "🛒 اطلب الآن",
                url=f"https://t.me/taager_products_bot?start={product['Product ID']}",
            )
        ],
        
    ]
)

# ==========================
# SEND
# ==========================

async def main():
    bot = Bot(BOT_TOKEN)

    await bot.send_photo(
        chat_id=CHANNEL_ID,
        photo=image,
        caption=caption,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

    print("Done ✅")


asyncio.run(main())