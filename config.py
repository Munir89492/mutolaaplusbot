import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "8643033769:AAEezX76M9iq-I8gc34mAW0tZn3TrG-JYnk")

ADMIN_IDS = [
    int(x) for x in os.getenv("ADMIN_IDS", "7640903633").split(",") if x.strip()
]

CARD_NUMBER = os.getenv("CARD_NUMBER", "9860026601988558")
CARD_OWNER = os.getenv("CARD_OWNER", "F.I.Sh.")
DB_PATH = os.getenv("DB_PATH", "ecomaskan.db")

# Har bir tarif turkumi uchun kunlik mukofot
CATEGORY_REWARDS = {
    'ertak': 7000,
    'hikoya': 10000,
    'roman': 17000,
    'chet_el': 22000,
}

REFERRAL_BONUS = 10000   # do'st tarif sotib olganda beriladi
DICE_MIN = 5000          # zar o'yini minimal yutuq
DICE_MAX = 20000         # zar o'yini maksimal yutuq
