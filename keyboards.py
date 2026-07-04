from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)


def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Kitoblar"), KeyboardButton(text="💰 Hamyonim")],
            [KeyboardButton(text="🏷 Tariflar"), KeyboardButton(text="📋 Vazifalar")],
            [KeyboardButton(text="🎲 Zar o'yini"), KeyboardButton(text="👥 Referal")],
            [KeyboardButton(text="💳 Depozit"), KeyboardButton(text="👤 Profilim")],
        ],
        resize_keyboard=True,
    )


def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Kitob qo'shish"), KeyboardButton(text="📚 Kitoblar ro'yxati")],
            [KeyboardButton(text="🏷 Tarif qo'shish"), KeyboardButton(text="🏷 Tariflar ro'yxati")],
            [KeyboardButton(text="📋 Vazifa qo'shish"), KeyboardButton(text="📋 Vazifalar ro'yxati")],
            [KeyboardButton(text="🧾 Depozitlar"), KeyboardButton(text="💸 Yechib olishlar")],
            [KeyboardButton(text="⬅️ Foydalanuvchi rejimi")],
        ],
        resize_keyboard=True,
    )


def tariffs_kb(tariffs):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for t in tariffs:
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{t['name']} — {t['price']:,} so'm / {t['duration_days']} kun",
                callback_data=f"tariff:{t['tariff_id']}",
            )
        ])
    return kb


def deposit_tariffs_kb(tariffs):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for t in tariffs:
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{t['name']} — {t['price']:,} so'm",
                callback_data=f"dep_tariff:{t['tariff_id']}",
            )
        ])
    return kb


def books_kb(books):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for b in books:
        kb.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"📖 {b['title']} (+{b['reward']:,} so'm)",
                callback_data=f"book:{b['book_id']}",
            )
        ])
    return kb


def book_actions_kb(book_id, status):
    buttons = []
    if status is None:
        buttons.append([InlineKeyboardButton(text="▶️ Boshladim", callback_data=f"start_reading:{book_id}")])
    elif status == "started":
        buttons.append([InlineKeyboardButton(text="✅ Tugatdim", callback_data=f"finish_reading:{book_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="✅ O'qib bo'lingan", callback_data="noop")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def task_done_kb(task_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Bajardim", callback_data=f"task_done:{task_id}")
    ]])


def dice_play_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🎲 Zar tashlash", callback_data="dice_play")
    ]])


def wallet_menu():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💸 Pul yechib olish", callback_data="withdraw")
    ]])


def admin_deposit_kb(deposit_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"dep_approve:{deposit_id}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"dep_reject:{deposit_id}"),
    ]])


def admin_withdrawal_kb(withdrawal_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"wd_approve:{withdrawal_id}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"wd_reject:{withdrawal_id}"),
    ]])


def cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⬅️ Bekor qilish", callback_data="cancel")
    ]])


CATEGORIES = {
    'ertak': '🥉 Ertaklar (Classic)',
    'hikoya': '🥈 Hikoyalar (Smart)',
    'roman': '🥇 Romanlar (Pro)',
    'chet_el': '💎 Chet el adabiyoti (Premium)',
}


def category_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for key, name in CATEGORIES.items():
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=name, callback_data=f"cat:{key}")
        ])
    return kb
