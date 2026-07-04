# -*- coding: utf-8 -*-
import asyncio
import logging
import random
import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import config
import database as db
import keyboards as kb
from states import AddBook, AddTariff, AddTask, Deposit, Withdraw

logging.basicConfig(level=logging.INFO)
router = Router()


def is_admin(user_id):
    return user_id in config.ADMIN_IDS


def get_week_key():
    now = datetime.datetime.now()
    return f"{now.year}-W{now.isocalendar()[1]}"


def get_user_category(user):
    if not user or not user["tariff_id"]:
        return None
    t = db.get_tariff(user["tariff_id"])
    return t["category"] if t else None


def get_daily_reward(user):
    cat = get_user_category(user)
    return config.CATEGORY_REWARDS.get(cat, 0)


# ===================== /start =====================

@router.message(CommandStart())
async def cmd_start(message: Message):
    args = message.text.split()
    referred_by = None
    if len(args) > 1 and args[1].startswith("ref"):
        try:
            referred_by = int(args[1][3:])
            if referred_by == message.from_user.id:
                referred_by = None
        except:
            referred_by = None

    existing = db.get_user(message.from_user.id)
    db.upsert_user(
        message.from_user.id,
        message.from_user.full_name,
        message.from_user.username or "",
        referred_by if not existing else None,
    )

    if is_admin(message.from_user.id):
        await message.answer("Salom, Admin! Boshqaruv panelidasiz.", reply_markup=kb.admin_menu())
    else:
        await message.answer(
            "Assalomu alaykum! 📚 <b>MutolaPlus</b> botiga xush kelibsiz!\n\n"
            "Bu yerda siz:\n"
            "• Tarif sotib olib kitoblarni o'qiy olasiz\n"
            "• Kitobni o'qib tugatganingizda hamyoningizga pul tushadi\n"
            "• Har kunlik vazifalarni bajaring va bonus oling\n"
            "• Yakshanba kuni zar o'yinida ishtirok eting\n"
            "• Do'stlaringizni taklif qilib bonus oling\n\n"
            "Quyidagi menyudan foydalaning 👇",
            reply_markup=kb.main_menu(),
            parse_mode="HTML",
        )


@router.message(F.text == "⬅️ Foydalanuvchi rejimi")
async def back_to_user(message: Message):
    await message.answer("Foydalanuvchi rejimiga o'tdingiz.", reply_markup=kb.main_menu())


# ===================== PROFIL =====================

@router.message(F.text == "👤 Profilim")
async def my_profile(message: Message):
    user = db.get_user(message.from_user.id)
    tariff_text = "Yo'q"
    if user["tariff_id"]:
        t = db.get_tariff(user["tariff_id"])
        if t:
            tariff_text = f"{t['name']} (tugash: {user['tariff_expires']})"
    await message.answer(
        f"👤 <b>Profilim</b>\n\n"
        f"Ism: {user['full_name']}\n"
        f"Balans: <b>{user['balance']:,} so'm</b>\n"
        f"Tarif: {tariff_text}",
        parse_mode="HTML",
    )


# ===================== HAMYON =====================

@router.message(F.text == "💰 Hamyonim")
async def my_wallet(message: Message):
    user = db.get_user(message.from_user.id)
    await message.answer(
        f"💰 <b>Hamyonim</b>\n\n"
        f"Joriy balans: <b>{user['balance']:,} so'm</b>\n\n"
        f"Kitob o'qib va vazifalarni bajarganda mukofot shu yerga tushadi.\n"
        f"Mablag'ni kartangizga yechib olishingiz mumkin.",
        parse_mode="HTML",
        reply_markup=kb.wallet_menu(),
    )


@router.callback_query(F.data == "withdraw")
async def withdraw_start(call: CallbackQuery, state: FSMContext):
    user = db.get_user(call.from_user.id)
    if user["balance"] <= 0:
        await call.answer("Hamyoningizda mablag' yo'q.", show_alert=True)
        return
    await state.set_state(Withdraw.amount)
    await call.message.answer(
        f"Balansingiz: <b>{user['balance']:,} so'm</b>\n\nYechib olmoqchi bo'lgan summani kiriting:",
        parse_mode="HTML",
    )
    await call.answer()


@router.message(Withdraw.amount)
async def withdraw_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, summani faqat raqamda kiriting.")
        return
    amount = int(message.text)
    user = db.get_user(message.from_user.id)
    if amount <= 0 or amount > user["balance"]:
        await message.answer(f"Noto'g'ri summa. Balansingiz: {user['balance']:,} so'm.")
        return
    await state.update_data(amount=amount)
    await state.set_state(Withdraw.card)
    await message.answer("Pul o'tkaziladigan karta raqamingizni kiriting:")


@router.message(Withdraw.card)
async def withdraw_card(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    amount = data["amount"]
    card = message.text.strip()
    wid = db.create_withdrawal(message.from_user.id, amount, card)
    await state.clear()
    await message.answer(
        "✅ So'rovingiz qabul qilindi. Admin tasdiqlagandan so'ng pul kartangizga o'tkaziladi va balansingizdan ayriladi."
    )
    user = db.get_user(message.from_user.id)
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"💸 <b>Pul yechish so'rovi</b>\n\n"
                f"Foydalanuvchi: {user['full_name']} (@{user['username']})\n"
                f"ID: {message.from_user.id}\n"
                f"Summa: <b>{amount:,} so'm</b>\n"
                f"Karta: <code>{card}</code>",
                parse_mode="HTML",
                reply_markup=kb.admin_withdrawal_kb(wid),
            )
        except Exception as e:
            logging.warning(f"Admin xabar: {e}")


# ===================== TARIFLAR =====================

@router.message(F.text == "🏷 Tariflar")
async def show_tariffs(message: Message):
    tariffs = db.list_tariffs()
    if not tariffs:
        await message.answer("Hozircha tariflar mavjud emas.")
        return
    await message.answer("🏷 <b>Mavjud tariflar:</b>", reply_markup=kb.tariffs_kb(tariffs), parse_mode="HTML")


@router.callback_query(F.data.startswith("tariff:"))
async def tariff_info(call: CallbackQuery):
    t = db.get_tariff(int(call.data.split(":")[1]))
    if not t:
        await call.answer("Tarif topilmadi.", show_alert=True)
        return
    cat_names = {'ertak': 'Ertaklar', 'hikoya': 'Hikoyalar', 'roman': 'Romanlar', 'chet_el': 'Chet el adabiyoti'}
    reward = config.CATEGORY_REWARDS.get(t["category"], 0)
    await call.message.answer(
        f"🏷 <b>{t['name']}</b>\n"
        f"Narxi: {t['price']:,} so'm\n"
        f"Muddati: {t['duration_days']} kun\n"
        f"Turkum: {cat_names.get(t['category'], t['category'])}\n"
        f"Kunlik vazifa mukofoti: {reward:,} so'm\n\n"
        f"{t['description'] or ''}\n\n"
        f"Obuna bo'lish uchun <b>💳 Depozit</b> tugmasini bosing.",
        parse_mode="HTML",
    )
    await call.answer()


# ===================== DEPOZIT =====================

@router.message(F.text == "💳 Depozit")
async def deposit_start(message: Message, state: FSMContext):
    tariffs = db.list_tariffs()
    if not tariffs:
        await message.answer("Hozircha tariflar mavjud emas.")
        return
    await state.set_state(Deposit.choosing_tariff)
    await message.answer(
        "💳 <b>Depozit</b>\n\nQaysi tarifni sotib olmoqchisiz?",
        reply_markup=kb.deposit_tariffs_kb(tariffs),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("dep_tariff:"))
async def deposit_tariff_chosen(call: CallbackQuery, state: FSMContext):
    tariff_id = int(call.data.split(":")[1])
    t = db.get_tariff(tariff_id)
    if not t:
        await call.answer("Tarif topilmadi.", show_alert=True)
        return
    await state.update_data(tariff_id=tariff_id, amount=t["price"])
    await state.set_state(Deposit.waiting_receipt)
    await call.message.answer(
        f"✅ <b>{t['name']}</b> tarifi tanlandi.\n\n"
        f"To'lov miqdori: <b>{t['price']:,} so'm</b>\n\n"
        f"Quyidagi kartaga o'tkazing:\n"
        f"💳 <code>{config.CARD_NUMBER}</code>\n"
        f"👤 {config.CARD_OWNER}\n\n"
        f"To'lovni amalga oshirgach, <b>chek rasmini (screenshot)</b> shu yerga yuboring:",
        parse_mode="HTML",
        reply_markup=kb.cancel_kb(),
    )
    await call.answer()


@router.message(Deposit.waiting_receipt, F.photo)
async def deposit_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    tariff_id = data["tariff_id"]
    amount = data["amount"]
    file_id = message.photo[-1].file_id
    t = db.get_tariff(tariff_id)
    deposit_id = db.create_deposit(message.from_user.id, tariff_id, amount, file_id)
    await state.clear()
    await message.answer(
        "✅ Chekingiz qabul qilindi! Admin tekshirib tasdiqlagandan so'ng tarifingiz faollashadi."
    )
    user = db.get_user(message.from_user.id)
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_photo(
                admin_id,
                file_id,
                caption=(
                    f"💳 <b>Yangi depozit so'rovi #{deposit_id}</b>\n\n"
                    f"Foydalanuvchi: {user['full_name']} (@{user['username']})\n"
                    f"ID: {message.from_user.id}\n"
                    f"Tarif: {t['name']}\n"
                    f"Summa: <b>{amount:,} so'm</b>"
                ),
                parse_mode="HTML",
                reply_markup=kb.admin_deposit_kb(deposit_id),
            )
        except Exception as e:
            logging.warning(f"Admin xabar: {e}")


@router.message(Deposit.waiting_receipt)
async def deposit_not_photo(message: Message):
    await message.answer("Iltimos, to'lov chekini RASM sifatida yuboring (screenshot).")


# ===================== KITOBLAR =====================

@router.message(F.text == "📚 Kitoblar")
async def show_books(message: Message):
    user = db.get_user(message.from_user.id)
    now = datetime.date.today().isoformat()
    if not user["tariff_id"] or (user["tariff_expires"] and user["tariff_expires"] < now):
        await message.answer(
            "📚 Kitoblarni ko'rish uchun avval tarif sotib olishingiz kerak.\n\n"
            "💳 <b>Depozit</b> tugmasini bosing.",
            parse_mode="HTML",
        )
        return
    cat = get_user_category(user)
    books = db.list_books(category=cat)
    if not books:
        await message.answer("Sizning turkumingizda hozircha kitoblar mavjud emas.")
        return
    cat_names = {'ertak': 'Ertaklar', 'hikoya': 'Hikoyalar', 'roman': 'Romanlar', 'chet_el': 'Chet el adabiyoti'}
    await message.answer(
        f"📚 <b>{cat_names.get(cat, '')} turkumidagi kitoblar:</b>",
        reply_markup=kb.books_kb(books),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("book:"))
async def book_chosen(call: CallbackQuery):
    book_id = int(call.data.split(":")[1])
    book = db.get_book(book_id)
    if not book:
        await call.answer("Kitob topilmadi.", show_alert=True)
        return
    progress = db.get_progress(call.from_user.id, book_id)
    status = progress["status"] if progress else None
    text = (
        f"📖 <b>{book['title']}</b>\n"
        f"Muallif: {book['author'] or '-'}\n"
        f"Mukofot: <b>{book['reward']:,} so'm</b>"
    )
    if book["file_id"]:
        await call.message.answer_document(
            book["file_id"], caption=text, parse_mode="HTML",
            reply_markup=kb.book_actions_kb(book_id, status),
        )
    else:
        await call.message.answer(text, parse_mode="HTML", reply_markup=kb.book_actions_kb(book_id, status))
    await call.answer()


@router.callback_query(F.data.startswith("start_reading:"))
async def start_reading_cb(call: CallbackQuery):
    book_id = int(call.data.split(":")[1])
    db.start_reading(call.from_user.id, book_id)
    await call.message.edit_reply_markup(reply_markup=kb.book_actions_kb(book_id, "started"))
    await call.answer("O'qishni boshladingiz! Omad! 📖")


@router.callback_query(F.data.startswith("finish_reading:"))
async def finish_reading_cb(call: CallbackQuery):
    book_id = int(call.data.split(":")[1])
    book = db.get_book(book_id)
    progress = db.get_progress(call.from_user.id, book_id)
    if not progress or progress["status"] == "finished":
        await call.answer("Bu kitob allaqachon tugatilgan.", show_alert=True)
        return
    db.finish_reading(call.from_user.id, book_id)
    db.change_balance(call.from_user.id, book["reward"])
    db.mark_reward_paid(call.from_user.id, book_id)
    await call.message.edit_reply_markup(reply_markup=kb.book_actions_kb(book_id, "finished"))
    await call.answer(f"🎉 Tabriklaymiz! {book['reward']:,} so'm hamyoningizga tushdi!", show_alert=True)


# ===================== VAZIFALAR =====================

@router.message(F.text == "📋 Vazifalar")
async def daily_tasks(message: Message):
    user = db.get_user(message.from_user.id)
    now = datetime.datetime.now()
    today = now.date().isoformat()

    if now.hour < 12:
        await message.answer(
            f"📋 <b>Kunlik vazifa</b>\n\n"
            f"Vazifa har kuni soat <b>12:00</b> da ochiladi.\n"
            f"Hozircha {12 - now.hour} soat {60 - now.minute} daqiqa qoldi.",
            parse_mode="HTML",
        )
        return

    if not user["tariff_id"]:
        await message.answer("Vazifalarni bajarish uchun avval tarif sotib olishingiz kerak.")
        return

    task = db.get_today_task(today)
    if not task:
        await message.answer(
            "📋 Bugun uchun vazifa hali qo'shilmagan.\n"
            "Kechroq qaytib ko'ring yoki admin bilan bog'laning."
        )
        return

    reward = get_daily_reward(user)
    completed = db.has_completed_task(message.from_user.id, task["task_id"])

    if completed:
        await message.answer(
            f"📋 <b>Bugungi vazifa</b>\n\n"
            f"<b>{task['title']}</b>\n\n"
            f"{task['description'] or ''}\n\n"
            f"✅ Siz bu vazifani allaqachon bajardingiz! ({reward:,} so'm olindingiz)",
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"📋 <b>Bugungi vazifa</b>\n\n"
            f"<b>{task['title']}</b>\n\n"
            f"{task['description'] or ''}\n\n"
            f"Mukofot: <b>{reward:,} so'm</b>\n\n"
            f"Vazifani bajargach quyidagi tugmani bosing:",
            parse_mode="HTML",
            reply_markup=kb.task_done_kb(task["task_id"]),
        )


@router.callback_query(F.data.startswith("task_done:"))
async def task_done_cb(call: CallbackQuery):
    task_id = int(call.data.split(":")[1])
    user = db.get_user(call.from_user.id)
    reward = get_daily_reward(user)
    success = db.complete_task(call.from_user.id, task_id, reward)
    if success:
        db.change_balance(call.from_user.id, reward)
        await call.message.edit_reply_markup()
        await call.answer(f"✅ Vazifa bajarildi! {reward:,} so'm hamyoningizga tushdi!", show_alert=True)
    else:
        await call.answer("Siz bu vazifani allaqachon bajargansiz.", show_alert=True)


# ===================== ZAR O'YINI =====================

@router.message(F.text == "🎲 Zar o'yini")
async def dice_game(message: Message):
    now = datetime.datetime.now()
    weekday = now.weekday()  # 6 = yakshanba
    hour = now.hour

    if weekday != 6 or hour < 17:
        days = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
        today = days[weekday]
        await message.answer(
            f"🎲 <b>Zar o'yini</b>\n\n"
            f"Zar o'yini faqat <b>Yakshanba kuni soat 17:00</b> dan keyin ochiladi!\n\n"
            f"Bugun: {today}\n"
            f"Soat: {now.strftime('%H:%M')}\n\n"
            f"Keyingi yakshanba kuni qaytib keling! 🎯",
            parse_mode="HTML",
        )
        return

    user = db.get_user(message.from_user.id)
    if not user["tariff_id"]:
        await message.answer("Zar o'yinida ishtirok etish uchun avval tarif sotib olishingiz kerak.")
        return

    week_key = get_week_key()
    play = db.get_dice_play(message.from_user.id, week_key)
    if play:
        await message.answer(
            f"🎲 <b>Zar o'yini</b>\n\n"
            f"Siz bu haftada allaqachon o'yin o'ynagansiz!\n"
            f"Yutuq: <b>{play['amount_won']:,} so'm</b>\n\n"
            f"Keyingi yakshanba kuni qaytib keling!",
            parse_mode="HTML",
        )
        return

    await message.answer(
        "🎲 <b>Zar o'yini</b>\n\n"
        f"Bu hafta bitta imkoniyatingiz bor! Yutuq: <b>{config.DICE_MIN:,} - {config.DICE_MAX:,} so'm</b>\n\n"
        "Zar tashlash uchun quyidagi tugmani bosing:",
        parse_mode="HTML",
        reply_markup=kb.dice_play_kb(),
    )


@router.callback_query(F.data == "dice_play")
async def dice_play_cb(call: CallbackQuery):
    now = datetime.datetime.now()
    if now.weekday() != 6 or now.hour < 17:
        await call.answer("Zar o'yini hali ochilmagan!", show_alert=True)
        return

    week_key = get_week_key()
    if db.get_dice_play(call.from_user.id, week_key):
        await call.answer("Siz bu haftada allaqachon o'ynagansiz!", show_alert=True)
        return

    amount = random.randint(config.DICE_MIN, config.DICE_MAX)
    db.save_dice_play(call.from_user.id, week_key, amount)
    db.change_balance(call.from_user.id, amount)

    await call.message.edit_text(
        f"🎲 <b>Zar tashlandi!</b>\n\n"
        f"🎉 Tabriklaymiz! Siz <b>{amount:,} so'm</b> yutdingiz!\n"
        f"Mablag' hamyoningizga o'tkazildi.\n\n"
        f"Keyingi yakshanba kuni qaytib keling!",
        parse_mode="HTML",
    )
    await call.answer()


# ===================== REFERAL =====================

@router.message(F.text == "👥 Referal")
async def referral(message: Message):
    bot_username = "MutolaPlusBot"
    link = f"https://t.me/{bot_username}?start=ref{message.from_user.id}"
    await message.answer(
        f"👥 <b>Referal tizimi</b>\n\n"
        f"Do'stlaringizni taklif qiling!\n"
        f"Do'stingiz tarif sotib olganda sizga <b>{config.REFERRAL_BONUS:,} so'm</b> bonus beriladi.\n\n"
        f"Sizning referal havolangiz:\n"
        f"<code>{link}</code>\n\n"
        f"Havolani nusxalab do'stlaringizga yuboring!",
        parse_mode="HTML",
    )


# ===================== ADMIN: KITOB =====================

@router.message(F.text == "➕ Kitob qo'shish")
async def admin_add_book(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AddBook.title)
    await message.answer("Kitob nomini kiriting:")


@router.message(AddBook.title)
async def add_book_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AddBook.author)
    await message.answer("Muallifini kiriting ('-' bo'lsa):")


@router.message(AddBook.author)
async def add_book_author(message: Message, state: FSMContext):
    await state.update_data(author=message.text)
    await state.set_state(AddBook.file)
    await message.answer("Kitob faylini (PDF) yuboring yoki '-' yozing:")


@router.message(AddBook.file, F.document)
async def add_book_file(message: Message, state: FSMContext):
    await state.update_data(file_id=message.document.file_id)
    await state.set_state(AddBook.reward)
    await message.answer("Mukofot summasini kiriting (so'mda):")


@router.message(AddBook.file)
async def add_book_file_skip(message: Message, state: FSMContext):
    await state.update_data(file_id=None)
    await state.set_state(AddBook.reward)
    await message.answer("Mukofot summasini kiriting (so'mda):")


@router.message(AddBook.reward)
async def add_book_reward(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, raqam kiriting.")
        return
    await state.update_data(reward=int(message.text))
    await state.set_state(AddBook.category)
    await message.answer("Kitob qaysi turkumga tegishli?", reply_markup=kb.category_kb())


@router.callback_query(F.data.startswith("cat:"), AddBook.category)
async def add_book_category(call: CallbackQuery, state: FSMContext):
    category = call.data.split(":")[1]
    data = await state.get_data()
    db.add_book(data["title"], data["author"], data.get("file_id"), data["reward"], category)
    await state.clear()
    cat_names = {'ertak': 'Ertaklar', 'hikoya': 'Hikoyalar', 'roman': 'Romanlar', 'chet_el': 'Chet el adabiyoti'}
    await call.message.answer(
        f"✅ '{data['title']}' kitobi {cat_names.get(category, '')} turkumiga qo'shildi.",
        reply_markup=kb.admin_menu(),
    )
    await call.answer()


@router.message(F.text == "📚 Kitoblar ro'yxati")
async def admin_books_list(message: Message):
    if not is_admin(message.from_user.id):
        return
    books = db.list_books()
    if not books:
        await message.answer("Kitoblar yo'q.")
        return
    cat_names = {'ertak': '🥉', 'hikoya': '🥈', 'roman': '🥇', 'chet_el': '💎'}
    text = "\n".join([
        f"{cat_names.get(b['category'], '📖')} #{b['book_id']} {b['title']} — {b['reward']:,} so'm"
        for b in books
    ])
    await message.answer(f"📚 Kitoblar:\n\n{text}")


# ===================== ADMIN: TARIF =====================

@router.message(F.text == "🏷 Tarif qo'shish")
async def admin_add_tariff(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AddTariff.name)
    await message.answer("Tarif nomini kiriting:")


@router.message(AddTariff.name)
async def add_tariff_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddTariff.price)
    await message.answer("Narxini kiriting (so'mda):")


@router.message(AddTariff.price)
async def add_tariff_price(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Raqam kiriting.")
        return
    await state.update_data(price=int(message.text))
    await state.set_state(AddTariff.duration)
    await message.answer("Muddatini kiriting (necha kun):")


@router.message(AddTariff.duration)
async def add_tariff_duration(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Raqam kiriting.")
        return
    await state.update_data(duration_days=int(message.text))
    await state.set_state(AddTariff.category)
    await message.answer("Tarif qaysi turkumga tegishli?", reply_markup=kb.category_kb())


@router.callback_query(F.data.startswith("cat:"), AddTariff.category)
async def add_tariff_category(call: CallbackQuery, state: FSMContext):
    await state.update_data(category=call.data.split(":")[1])
    await state.set_state(AddTariff.description)
    await call.message.answer("Qisqacha tavsif kiriting ('-' bo'lsa):")
    await call.answer()


@router.message(AddTariff.description)
async def add_tariff_description(message: Message, state: FSMContext):
    data = await state.get_data()
    desc = "" if message.text == "-" else message.text
    db.add_tariff(data["name"], data["price"], data["duration_days"], data["category"], desc)
    await state.clear()
    await message.answer(f"✅ '{data['name']}' tarifi qo'shildi.", reply_markup=kb.admin_menu())


@router.message(F.text == "🏷 Tariflar ro'yxati")
async def admin_tariffs_list(message: Message):
    if not is_admin(message.from_user.id):
        return
    tariffs = db.list_tariffs()
    if not tariffs:
        await message.answer("Tariflar yo'q.")
        return
    text = "\n".join([
        f"#{t['tariff_id']} {t['name']} — {t['price']:,} so'm / {t['duration_days']} kun"
        for t in tariffs
    ])
    await message.answer(f"🏷 Tariflar:\n\n{text}")


# ===================== ADMIN: VAZIFA =====================

@router.message(F.text == "📋 Vazifa qo'shish")
async def admin_add_task(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.set_state(AddTask.title)
    today = datetime.date.today().isoformat()
    await message.answer(f"Bugungi ({today}) vazifa sarlavhasini kiriting:")


@router.message(AddTask.title)
async def add_task_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AddTask.description)
    await message.answer("Vazifa tavsifini kiriting ('-' bo'lsa):")


@router.message(AddTask.description)
async def add_task_description(message: Message, state: FSMContext):
    data = await state.get_data()
    today = datetime.date.today().isoformat()
    desc = "" if message.text == "-" else message.text
    db.add_daily_task(today, data["title"], desc)
    await state.clear()
    await message.answer(f"✅ Bugungi vazifa qo'shildi!", reply_markup=kb.admin_menu())


@router.message(F.text == "📋 Vazifalar ro'yxati")
async def admin_tasks_list(message: Message):
    if not is_admin(message.from_user.id):
        return
    today = datetime.date.today().isoformat()
    task = db.get_today_task(today)
    if task:
        await message.answer(f"📋 Bugungi vazifa:\n\n<b>{task['title']}</b>\n{task['description'] or ''}", parse_mode="HTML")
    else:
        await message.answer("Bugun uchun vazifa yo'q. '📋 Vazifa qo'shish' tugmasini bosing.")


# ===================== ADMIN: DEPOZIT =====================

@router.message(F.text == "🧾 Depozitlar")
async def admin_deposits(message: Message):
    if not is_admin(message.from_user.id):
        return
    deposits = db.list_pending_deposits()
    if not deposits:
        await message.answer("Kutilayotgan depozit so'rovlari yo'q.")
        return
    for d in deposits:
        user = db.get_user(d["user_id"])
        t = db.get_tariff(d["tariff_id"])
        await message.answer(
            f"💳 #{d['deposit_id']} — {user['full_name']} (@{user['username']})\n"
            f"Tarif: {t['name'] if t else '-'}\nSumma: {d['amount']:,} so'm",
            reply_markup=kb.admin_deposit_kb(d["deposit_id"]),
        )


@router.callback_query(F.data.startswith("dep_approve:"))
async def dep_approve(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id):
        return
    deposit_id = int(call.data.split(":")[1])
    d = db.get_deposit(deposit_id)
    if not d or d["status"] != "pending":
        await call.answer("Bu so'rov allaqachon ko'rib chiqilgan.", show_alert=True)
        return
    db.decide_deposit(deposit_id, "approved")
    t = db.get_tariff(d["tariff_id"])
    import datetime as dt
    expires = (dt.date.today() + dt.timedelta(days=t["duration_days"])).isoformat()
    db.set_user_tariff(d["user_id"], t["tariff_id"], expires)

    # Referal bonus
    referrer_id = db.get_referrer(d["user_id"])
    if referrer_id:
        db.change_balance(referrer_id, config.REFERRAL_BONUS)
        try:
            await bot.send_message(
                referrer_id,
                f"🎉 Do'stingiz tarif sotib oldi! Sizga <b>{config.REFERRAL_BONUS:,} so'm</b> referal bonus berildi!",
                parse_mode="HTML",
            )
        except:
            pass

    await call.message.edit_caption(call.message.caption + "\n\n✅ TASDIQLANDI")
    await bot.send_message(
        d["user_id"],
        f"✅ Depozitingiz tasdiqlandi!\n<b>{t['name']}</b> tarifi {expires} sanasigacha faol.",
        parse_mode="HTML",
    )
    await call.answer("Tasdiqlandi.")


@router.callback_query(F.data.startswith("dep_reject:"))
async def dep_reject(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id):
        return
    deposit_id = int(call.data.split(":")[1])
    d = db.get_deposit(deposit_id)
    if not d or d["status"] != "pending":
        await call.answer("Bu so'rov allaqachon ko'rib chiqilgan.", show_alert=True)
        return
    db.decide_deposit(deposit_id, "rejected")
    await call.message.edit_caption(call.message.caption + "\n\n❌ RAD ETILDI")
    await bot.send_message(d["user_id"], "❌ Depozitingiz tasdiqlanmadi. Admin bilan bog'laning.")
    await call.answer("Rad etildi.")


# ===================== ADMIN: YECHIB OLISH =====================

@router.message(F.text == "💸 Yechib olishlar")
async def admin_withdrawals(message: Message):
    if not is_admin(message.from_user.id):
        return
    withdrawals = db.list_pending_withdrawals()
    if not withdrawals:
        await message.answer("Kutilayotgan so'rovlar yo'q.")
        return
    for w in withdrawals:
        user = db.get_user(w["user_id"])
        await message.answer(
            f"💸 #{w['withdrawal_id']} — {user['full_name']} (@{user['username']})\n"
            f"Summa: {w['amount']:,} so'm\nKarta: {w['card_number']}",
            reply_markup=kb.admin_withdrawal_kb(w["withdrawal_id"]),
        )


@router.callback_query(F.data.startswith("wd_approve:"))
async def wd_approve(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id):
        return
    wid = int(call.data.split(":")[1])
    w = db.get_withdrawal(wid)
    if not w or w["status"] != "pending":
        await call.answer("Bu so'rov allaqachon ko'rib chiqilgan.", show_alert=True)
        return
    db.decide_withdrawal(wid, "approved")
    db.change_balance(w["user_id"], -w["amount"])
    await call.message.edit_text(call.message.text + "\n\n✅ TASDIQLANDI — pul o'tkazing!")
    await bot.send_message(w["user_id"], f"✅ {w['amount']:,} so'm kartangizga o'tkazildi.")
    await call.answer("Tasdiqlandi.")


@router.callback_query(F.data.startswith("wd_reject:"))
async def wd_reject(call: CallbackQuery, bot: Bot):
    if not is_admin(call.from_user.id):
        return
    wid = int(call.data.split(":")[1])
    w = db.get_withdrawal(wid)
    if not w or w["status"] != "pending":
        await call.answer("Bu so'rov allaqachon ko'rib chiqilgan.", show_alert=True)
        return
    db.decide_withdrawal(wid, "rejected")
    await call.message.edit_text(call.message.text + "\n\n❌ RAD ETILDI")
    await bot.send_message(w["user_id"], "❌ Pul yechish so'rovingiz rad etildi. Balans o'zgarishsiz qoldi.")
    await call.answer("Rad etildi.")


# ===================== UTILITY =====================

@router.callback_query(F.data == "cancel")
async def cancel_cb(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("Bekor qilindi.", reply_markup=kb.main_menu())
    await call.answer()


@router.callback_query(F.data == "noop")
async def noop_cb(call: CallbackQuery):
    await call.answer()


# ===================== MAIN =====================

async def main():
    db.init_db()
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
