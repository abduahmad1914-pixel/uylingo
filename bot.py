import asyncio
import logging
import random
import sqlite3
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.client.session.aiohttp import AiohttpSession

BOT_TOKEN = os.environ.get("BOT_TOKEN", "9206110935:AAH_KGTCqUxfGS5fu1jSDYuohnrnFXgWqJ0").strip()
DB_FILE = "uyghur.db"

# --- УМНОЕ ПОДКЛЮЧЕНИЕ ---
if "PYTHONANYWHERE_DOMAIN" in os.environ:
    session = AiohttpSession(proxy="http://proxy.server:3128")
    bot = Bot(token=BOT_TOKEN, session=session)
else:
    bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()


# --- БАЗА ДАННЫХ ДЛЯ РЕЙТИНГА ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        name TEXT,
                        score INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()


def add_point(user_id, name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT score FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE users SET score = score + 1, name = ? WHERE user_id = ?", (name, user_id))
    else:
        cursor.execute("INSERT INTO users (user_id, name, score) VALUES (?, ?, 1)", (user_id, name))
    conn.commit()
    conn.close()


def get_top_users():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, score FROM users ORDER BY score DESC LIMIT 5")
    rows = cursor.fetchall()
    conn.close()
    return rows


# --- ПОСЛОВИЦЫ ---
PROVERBS = [
    {"uyghur": "Өшкә мели мал әмәс, шаптула беғи бағ әмәс.", "russian": "Козы – не скотина, персиковый сад – не сад."},
    {"uyghur": "Хаталашқандин хатани түзәтмигән яман.", "russian": "Не исправить ошибку хуже, чем ошибиться."},
    {"uyghur": "Аброюңни яштин сақла, чапиниңни – йеңидин.", "russian": "Береги честь смолоду, а чапан снову."},
    {"uyghur": "Тамчиму ташни ярар.", "russian": "Капля и та камень точит."},
    {"uyghur": "Көз қорқақ, қол батур.", "russian": "Глаза трусливы, руки храбры."},
    {"uyghur": "Қуруқ гәпкә қосақ тоймас.", "russian": "Словами сыт не будешь."},
    {"uyghur": "Тәләп қил, сәвәп қил.", "russian": "Желай, и действуй."},
    {"uyghur": "Бирлик бар йәрдә инақлиқ бар.", "russian": "Где единство, там согласие."},
    {"uyghur": "Адәм адәм билән адәм.", "russian": "Человек с людьми – человек."},
    {"uyghur": "Ана меһрини һеч ким билмәс.", "russian": "Никто материнской любви до конца не познал."},
    {"uyghur": "Атиси атмиған қоңғузни, балиси етипту тоңғузни.",
     "russian": "Отец и жука не словил, а сын кабана подстрелил."},
    {"uyghur": "Бирлик бар йәрдә — берикәт бар.", "russian": "Где единство — там изобилие."},
    {"uyghur": "Йәр – һосулниң аниси, әмгәк – униң атиси.", "russian": "Земля – мать урожая, труд – его отец."},
    {"uyghur": "Вәтән — алтун бөшүк.", "russian": "Родина — золотая колыбель."}
]

# --- СУФФИКСЫ (ТРЕНИРОВКА) ---
SUFFIX_WORDS = [
    # Твердые слова (редукция а -> и)
    {"word": "Ана (мать)", "correct": "Анилар", "wrong": "Аналәр"},
    {"word": "Ата (отец)", "correct": "Атилар", "wrong": "Аталәр"},
    {"word": "Тағ (гора)", "correct": "Тағлар", "wrong": "Тағләр"},
    {"word": "Мал (товар)", "correct": "Маллар", "wrong": "Малләр"},
    {"word": "Орун (место)", "correct": "Орунлар", "wrong": "Орунләр"},
    {"word": "Ун (мука)", "correct": "Унлар", "wrong": "Унләр"},
    {"word": "Туз (соль)", "correct": "Тузлар", "wrong": "Тузләр"},
    {"word": "Булақ (родник)", "correct": "Булақлар", "wrong": "Булақләр"},
    {"word": "Қетиқ (кефир)", "correct": "Қетиқлар", "wrong": "Қетиқләр"},
    {"word": "Бала (ребенок)", "correct": "Балилар", "wrong": "Балаләр"},

    # Мягкие слова (редукция ә -> и)
    {"word": "Мәктәп (школа)", "correct": "Мәктәпләр", "wrong": "Мәктәплар"},
    {"word": "Көл (озеро)", "correct": "Көлләр", "wrong": "Көллар"},
    {"word": "Өй (дом)", "correct": "Өйләр", "wrong": "Өйлар"},
    {"word": "Күл (зола)", "correct": "Күлләр", "wrong": "Күллар"},
    {"word": "Өмчүк (паучок)", "correct": "Өмчүкләр", "wrong": "Өмчүклар"},
    {"word": "Үмүт (надежда)", "correct": "Үмүтләр", "wrong": "Үмүтлар"},
    {"word": "Гүл (цветок)", "correct": "Гүлләр", "wrong": "Гүллар"},
    {"word": "Җүҗә (цыпленок)", "correct": "Җүҗиләр", "wrong": "Җүҗәлар"},
    {"word": "Әқил (ум)", "correct": "Әқилләр", "wrong": "Әқиллар"},
    {"word": "Тәңгә (тенге)", "correct": "Тәңгиләр", "wrong": "Тәңгәлар"}
]


# --- ГЛАВНОЕ МЕНЮ ---
def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📜 Пословицы")
    builder.button(text="📖 Грамматика")
    builder.button(text="🎯 Викторина")
    builder.button(text="🧩 Суффиксы")
    builder.button(text="🏆 Рейтинг")
    builder.adjust(2, 2, 2)
    return builder.as_markup(resize_keyboard=True)




# --- КОМАНДЫ ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Әссаламу әләйкүм! 📖\nДобро пожаловать в словарь UyLingo.\nВыбери раздел👇",
                         reply_markup=get_main_menu())


@dp.message(F.text == "🏆 Рейтинг")
async def show_rating(message: types.Message):
    top_users = get_top_users()
    if not top_users:
        await message.answer("Пока никто не заработал баллов. Стань первым! 🥇")
        return
    text = "🏆 <b>ТОП-5 ЗНАТОКОВ:</b>\n\n"
    medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]
    for i, user in enumerate(top_users):
        text += f"{medals[i]} <b>{user[0]}</b>: {user[1]} баллов\n"
    text += "\n<i>Играй в Викторину и Суффиксы, чтобы подняться в рейтинге!</i>"
    await message.answer(text, parse_mode="HTML")


@dp.message(F.text == "🧩 Суффиксы")
async def start_suffix_game(message: types.Message):
    await send_new_suffix(message)


async def send_new_suffix(message_or_callback):
    word_data = random.choice(SUFFIX_WORDS)
    builder = InlineKeyboardBuilder()
    options = [(word_data["correct"], "suf_corr"), (word_data["wrong"], "suf_wrong")]
    random.shuffle(options)
    for text, cb_data in options:
        builder.button(text=text, callback_data=cb_data)
    text = f"🧩 <b>Выбери правильную форму множественного числа:</b>\n\n👉 <i>{word_data['word']}</i>"
    if isinstance(message_or_callback, types.Message):
        await message_or_callback.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())
    else:
        await message_or_callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())


@dp.callback_query(F.data == "suf_corr")
async def suffix_correct(callback: types.CallbackQuery):
    add_point(callback.from_user.id, callback.from_user.first_name)
    await callback.answer("✅ Правильно! +1 балл", show_alert=False)
    await send_new_suffix(callback)


@dp.callback_query(F.data == "suf_wrong")
async def suffix_wrong(callback: types.CallbackQuery):
    await callback.answer("❌ Ошибка сингармонизма или редукции!", show_alert=True)
    await send_new_suffix(callback)


def get_quiz_data():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT word, definition FROM dictionary WHERE length(definition) < 50 ORDER BY RANDOM() LIMIT 4")
    rows = cursor.fetchall()
    conn.close()
    if len(rows) < 4: return None
    correct = rows[0]
    question = correct[1]
    correct_word = correct[0]
    options = [r[0] for r in rows]
    random.shuffle(options)
    return question, correct_word, options


async def send_new_question(message_or_callback):
    data = get_quiz_data()
    if not data: return
    question, correct_word, options = data
    builder = InlineKeyboardBuilder()
    for opt in options:
        cb_data = "qzc_" if opt == correct_word else f"qzw_{correct_word[:40]}"
        builder.button(text=opt, callback_data=cb_data)
    builder.adjust(2, 2)
    text = f"🎯 <b>Как переводится:</b>\n\n<i>{question}</i>"
    if isinstance(message_or_callback, types.Message):
        await message_or_callback.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())
    else:
        await message_or_callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())


@dp.message(F.text == "🎯 Викторина")
async def start_quiz(message: types.Message):
    await send_new_question(message)


@dp.callback_query(F.data == "qzc_")
async def quiz_correct(callback: types.CallbackQuery):
    add_point(callback.from_user.id, callback.from_user.first_name)
    await callback.answer("✅ Правильно! +1 балл", show_alert=False)
    await send_new_question(callback)


@dp.callback_query(F.data.startswith("qzw_"))
async def quiz_wrong(callback: types.CallbackQuery):
    correct_word = callback.data.split("_", 1)[1]
    await callback.answer(f"❌ Неверно!\nОтвет: {correct_word}", show_alert=True)
    await send_new_question(callback)


@dp.message(F.text == "📜 Пословицы")
async def show_proverb(message: types.Message):
    p = random.choice(PROVERBS)
    await message.answer(f"📜 <b>{p['uyghur']}</b>\n🇷🇺 {p['russian']}", parse_mode="HTML")


@dp.message(F.text == "📖 Грамматика")
async def show_grammar(message: types.Message):
    text = (
        "📖 <b>Основы уйгурской грамматики и фонетики</b>\n\n"
        "<b>1. Специфические гласные (ә, ө, ү):</b>\n"
        "• <b>/ә/</b> — мягче, чем /а/. Пример: <i>әнә</i> (вон), <i>әш</i> (вить).\n"
        "• <b>/ө/</b> — огубленный, похож на /ё/ в 'Лёля'. Пример: <i>көл</i> (озеро), <i>өй</i> (дом).\n"
        "• <b>/ү/</b> — узкий, мягкий, похож на /ю/. Пример: <i>гүл</i> (цветок), <i>җүҗә</i> (цыпленок).\n\n"
        "<b>2. Специфические согласные (қ, ғ, җ, һ, ң):</b>\n"
        "• <b>/қ/</b> — глубокозаднеязычный, твердый. Пример: <i>қаттиқ</i> (твердый).\n"
        "• <b>/ғ/</b> — щелевой звонкий, похож на /х/ с голосом. Пример: <i>тағ</i> (гора).\n"
        "• <b>/җ/</b> — звонкая аффриката, похожа на английский /дж/. Пример: <i>җүп</i> (пара), <i>җүҗә</i> (цыпленок).\n"
        "• <b>/һ/</b> — глухой фарингальный, произносится с придыханием (как 'ah'). Пример: <i>һә</i> (да), <i>һәммә</i> (все).\n"
        "• <b>/ң/</b> — носовой сонант (как 'нг' с зажатым носом). Пример: <i>таң</i> (утро).\n\n"
        "<b>3. Закон сингармонизма:</b>\n"
        "Слова делятся на твердые (а, о, у) и мягкие (ә, ө, ү).\n"
        "Мягким словам — мягкие суффиксы (-ләр): <i>Мәктәп ➔ Мәктәпләр</i>.\n"
        "Твердым словам — твердые суффиксы (-лар): <i>Тағ ➔ Тағлар</i>.\n\n"
        "<b>4. Редукция широких гласных (/а/, /ә/):</b>\n"
        "В безударной позиции в середине слова широкие гласные сужаются и переходят в /и/:\n"
        "<i>Қача ➔ қачиға</i>, <i>бала ➔ балиға</i>.\n"
        "При образовании глаголов: <i>бар-а-мән ➔ баримән</i>, <i>яз-а-мән ➔ язимән</i>."
    )
    await message.answer(text, parse_mode="HTML")


@dp.message(F.text == "🔍 Поиск слова")
async def prompt_search(message: types.Message):
    await message.answer("Просто напиши мне любое слово прямо в чат, и я найду его перевод! ✍️")

    @dp.message(F.text == "🔍 Поиск слова")
    async def prompt_search(message: types.Message):
        await message.answer("Просто напиши мне нужное слово прямо в чат, и я найду его перевод! ✍️")

    if not results:
        await message.answer(f"Слово «{q}» не найдено.")
        return

    for word, definition in results:
        await message.answer(f"<b>{word}</b>\n\n{definition}", parse_mode="HTML")


# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
async def health_check(request):
    return web.Response(text="UyLingo Bot is running!")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def main():
    logging.basicConfig(level=logging.INFO)
    init_db()
    await start_web_server()
    print("Бот успешно запущен со всеми функциями!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())