import asyncio
import logging
import random
import sqlite3
import os
from aiohttp import web, ClientSession
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.client.session.aiohttp import AiohttpSession

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "9206110935:AAH_KGTCqUxfGS5fu1jSDYuohnrnFXgWqJ0").strip()
DB_FILE = "uyghur.db"

# --- УМНОЕ ПОДКЛЮЧЕНИЕ ---
if "PYTHONANYWHERE_DOMAIN" in os.environ:
    session = AiohttpSession(proxy="http://proxy.server:3128")
    bot = Bot(token=BOT_TOKEN, session=session)
else:
    bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()

# --- БАЗА УЙГУРСКИХ ПОСЛОВИЦ (БЕЗ № 1, 9, 18) ---
PROVERBS = [
    "📜 <b>Билим — әқил чириғи.</b>\n🇷🇺 <i>Знание — светоч разума.</i>",
    "📜 <b>Дост күндә билиниду, батур — җәңдә.</b>\n🇷🇺 <i>Друг познаётся в беде, а богатырь — в бою.</i>",
    "📜 <b>Яхши сөз — җан озуғи, яман сөз — баш қозуғи.</b>\n🇷🇺 <i>Доброе слово — пища для души, дурное слово — обуза для головы.</i>",
    "📜 <b>Көп оқуған көп билиду.</b>\n🇷🇺 <i>Кто много читает, тот много знает.</i>",
    "📜 <b>Тил — көңүлниң әйниги.</b>\n🇷🇺 <i>Язык — зеркало души.</i>",
    "📜 <b>Ана жутуң аман болса, рәңги-ройиң саман болмас.</b>\n🇷🇺 <i>Если родной край в благополучии, то и ты не будешь знать бед.</i>",
    "📜 <b>Яхшилиқ қилсаң, яхшилиқ көрисән.</b>\n🇷🇺 <i>Сделаешь добро — увидишь добро в ответ.</i>",
    "📜 <b>Бирлик бар йәрдә, тирикчилик бар.</b>\n🇷🇺 <i>Где есть единство, там есть и процветание.</i>",
    "📜 <b>Ойнап сөзлисәңму, ойлап сөзлә.</b>\n🇷🇺 <i>Даже если говоришь шутя, говори обдуманно.</i>",
    "📜 <b>Көз қорқақ, қол батур.</b>\n🇷🇺 <i>Глаза боятся, а руки делают (букв.: глаза трусливы, руки отважны).</i>",
    "📜 <b>Алтун отта билиниду, адәм — әмгәктә.</b>\n🇷🇺 <i>Золото проверяется в огне, а человек — в труде.</i>",
    "📜 <b>Ата-анаңни һөрмәтлисәң, өз балаңдин һөрмәт көрисән.</b>\n🇷🇺 <i>Будешь почитать родителей — увидишь почёт и от своих детей.</i>",
    "📜 <b>Су ичкән қудуққа түкүрмә.</b>\n🇷🇺 <i>Не плюй в колодец, из которого пьёшь воду.</i>",
    "📜 <b>Билимлик миңни йеңәр, билимсиз — бирни.</b>\n🇷🇺 <i>Знающий победит тысячу, незнающий — лишь одного.</i>",
    "📜 <b>Яхши адәм сөзидин тонулиду, яхши ат — изидин.</b>\n🇷🇺 <i>Хорошего человека узнают по словам, а хорошего коня — по следу.</i>",
    "📜 <b>Китап — билим булиғи.</b>\n🇷🇺 <i>Книга — источник знаний.</i>",
    "📜 <b>Әмгәкниң нани татлиқ.</b>\n🇷🇺 <i>Хлеб, добытый трудом, самый сладкий.</i>",
    "📜 <b>Устаз — иккинчи ата-ана.</b>\n🇷🇺 <i>Учитель — второй родитель.</i>",
    "📜 <b>Вәтәнсиз адәм — булбулсиз чаман.</b>\n🇷🇺 <i>Человек без Родины — что цветущий сад без соловья.</i>",
    "📜 <b>Қолуңдин кәлмисә, тилиң билән махтанма.</b>\n🇷🇺 <i>Если руки не умеют делать — не хвались языком.</i>",
    "📜 <b>Һүнәрлик қол ач қалмас.</b>\n🇷🇺 <i>Руки, владеющие ремеслом, никогда не останутся голодными.</i>"
]

# --- БАЗА ДЛЯ ИГРЫ С СУФФИКСАМИ ---
SUFFIX_GAME_WORDS = [
    # Твёрдые слова
    {"word": "китап", "tr": "книга", "task": "Множественное число (книги)", "ans": "-лар", "opts": ["-лар", "-ләр", "-дар", "-дәр"], "res": "китаплар"},
    {"word": "тағ", "tr": "гора", "task": "Множественное число (горы)", "ans": "-лар", "opts": ["-лар", "-ләр", "-тар", "-тәр"], "res": "тағлар"},
    {"word": "бағ", "tr": "сад", "task": "Местный падеж — Орун-вақит келиш (в саду)", "ans": "-да", "opts": ["-да", "-дә", "-та", "-тә"], "res": "бағда"},
    {"word": "китап", "tr": "книга", "task": "Местный падеж — после глухой «п» (в книге)", "ans": "-та", "opts": ["-да", "-дә", "-та", "-тә"], "res": "китапта"},
    {"word": "бала", "tr": "ребёнок", "task": "Дательный падеж — Йөнилиш келиш (ребёнку)", "ans": "-ға", "opts": ["-ға", "-гә", "-қа", "-кә"], "res": "балиға"},
    {"word": "ат", "tr": "конь", "task": "Дательный падеж — после глухой «т» (коню)", "ans": "-қа", "opts": ["-ға", "-гә", "-қа", "-кә"], "res": "атқа"},
    {"word": "базар", "tr": "рынок", "task": "Исходный падеж — Чиқиш келиш (с рынка)", "ans": "-дин", "opts": ["-дин", "-тин", "-дан", "-тан"], "res": "базардин"},
    {"word": "таш", "tr": "камень", "task": "Исходный падеж — после глухой «ш» (из камня)", "ans": "-тин", "opts": ["-дин", "-тин", "-ға", "-қа"], "res": "таштин"},
    {"word": "нан", "tr": "хлеб", "task": "Родительный падеж — Егилик келиш (хлеба)", "ans": "-ниң", "opts": ["-ниң", "-ни", "-дин", "-ға"], "res": "нанниң"},
    {"word": "дост", "tr": "друг", "task": "Притяжательный суффикс «мой» (мой друг)", "ans": "-ум", "opts": ["-ум", "-үм", "-им", "-си"], "res": "достум"},
    # Мягкие слова
    {"word": "мәктәп", "tr": "школа", "task": "Множественное число (школы)", "ans": "-ләр", "opts": ["-лар", "-ләр", "-дар", "-дәр"], "res": "мәктәпләр"},
    {"word": "адәм", "tr": "человек", "task": "Множественное число (люди)", "ans": "-ләр", "opts": ["-лар", "-ләр", "-тар", "-тәр"], "res": "адәмләр"},
    {"word": "гүл", "tr": "цветок", "task": "Множественное число (цветы)", "ans": "-ләр", "opts": ["-лар", "-ләр", "-ниң", "-дин"], "res": "гүлләр"},
    {"word": "өй", "tr": "дом", "task": "Местный падеж — Орун-вақит келиш (дома)", "ans": "-дә", "opts": ["-да", "-дә", "-та", "-тә"], "res": "өйдә"},
    {"word": "мәктәп", "tr": "школа", "task": "Местный падеж — после глухой «п» (в школе)", "ans": "-тә", "opts": ["-да", "-дә", "-та", "-тә"], "res": "мәктәптә"},
    {"word": "өй", "tr": "дом", "task": "Дательный падеж — Йөнилиш келиш (домой)", "ans": "-гә", "opts": ["-ға", "-гә", "-қа", "-кә"], "res": "өйгә"},
    {"word": "мәктәп", "tr": "школа", "task": "Дательный падеж — после глухой «п» (в школу)", "ans": "-кә", "opts": ["-ға", "-гә", "-қа", "-кә"], "res": "мәктәпкә"},
    {"word": "шәһәр", "tr": "город", "task": "Исходный падеж — Чиқиш келиш (из города)", "ans": "-дин", "opts": ["-дин", "-тин", "-дә", "-тә"], "res": "шәһәрдин"},
    {"word": "дәризә", "tr": "окно", "task": "Винительный падеж — Чүшүм келиш (окно)", "ans": "-ни", "opts": ["-ни", "-ниң", "-гә", "-дә"], "res": "дәризини"},
    {"word": "көз", "tr": "глаз", "task": "Притяжательный суффикс «мой» (мой глаз)", "ans": "-үм", "opts": ["-ум", "-үм", "-им", "-ам"], "res": "көзүм"}
]

# --- СУФФИКСЫ УЙГУРСКОГО ЯЗЫКА (ДЛЯ АВТО-РАЗБОРА СЛОВ В ЧАТЕ) ---
UYGHUR_SUFFIXES = [
    ("ларда", "-ларда", "множественное число + местный падеж (в/на ком-чём)"),
    ("ләрдә", "-ләрдә", "множественное число + местный падеж (в/на ком-чём)"),
    ("лардин", "-лардин", "множественное число + исходный падеж (от/из кого-чего)"),
    ("ләрдин", "-ләрдин", "множественное число + исходный падеж (от/из кого-чего)"),
    ("ларға", "-ларға", "множественное число + дательный падеж (кому/чему/куда)"),
    ("ләргә", "-ләргә", "множественное число + дательный падеж (кому/чему/куда)"),
    ("ларниң", "-ларниң", "множественное число + Егилик келиш (чей/кого)"),
    ("ләрниң", "-ләрниң", "множественное число + Егилик келиш (чей/кого)"),
    ("ларни", "-ларни", "множественное число + винительный падеж (кого/что)"),
    ("ләрни", "-ләрни", "множественное число + винительный падеж (кого/что)"),
    ("имиз", "-имиз", "притяжательный суффикс «наш» (бизниң)"),
    ("умиз", "-умиз", "притяжательный суффикс «наш» (бизниң)"),
    ("үмиз", "-үмиз", "притяжательный суффикс «наш» (бизниң)"),
    ("иңиз", "-иңиз", "притяжательный суффикс «Ваш» (сизниң — вежл.)"),
    ("уңуз", "-уңуз", "притяжательный суффикс «Ваш» (сизниң — вежл.)"),
    ("үңүз", "-үңүз", "притяжательный суффикс «Ваш» (сизниң — вежл.)"),
    ("дики", "-дики", "суффикс местонахождения «находящийся в/на»"),
    ("тики", "-тики", "суффикс местонахождения «находящийся в/на»"),
    ("лар", "-лар", "множественное число (после твёрдых гласных)"),
    ("ләр", "-ләр", "множественное число (после мягких гласных)"),
    ("ниң", "-ниң", "родительный падеж — Егилик келиш (кого? чей?)"),
    ("дин", "-дин", "исходный падеж — Чиқиш келиш (откуда? от кого?)"),
    ("тин", "-тин", "исходный падеж — Чиқиш келиш (после глухих согласных)"),
    ("лиқ", "-лиқ", "суффикс обладания признаком или места происхождения"),
    ("лик", "-лик", "суффикс обладания признаком или качества"),
    ("луқ", "-луқ", "суффикс обладания признаком"),
    ("лүк", "-лүк", "суффикс обладания признаком"),
    ("сиз", "-сиз", "отрицательный суффикс «без» (отсутствие признака)"),
    ("миз", "-миз", "притяжательный суффикс «наш» (бизниң)"),
    ("ңиз", "-ңиз", "притяжательный суффикс «Ваш» (сизниң)"),
    ("ға", "-ға", "дательно-направительный падеж — Йөнилиш келиш (кому? куда?)"),
    ("гә", "-гә", "дательно-направительный падеж — Йөнилиш келиш (кому? куда?)"),
    ("қа", "-қа", "дательно-направительный падеж (после глухих согласных)"),
    ("кә", "-кә", "дательно-направительный падеж (после глухих согласных)"),
    ("да", "-да", "местно-временной падеж — Орун-вақит келиш (где? когда?)"),
    ("дә", "-дә", "местно-временной падеж — Орун-вақит келиш (где? когда?)"),
    ("та", "-та", "местно-временной падеж (после глухих согласных)"),
    ("тә", "-тә", "местно-временной падеж (после глухих согласных)"),
    ("ни", "-ни", "винительный падеж — Чүшүм келиш (кого? что?)"),
    ("чи", "-чи", "суффикс профессии или деятеля"),
    ("им", "-им", "притяжательный суффикс 1-го лица «мой» (мениң)"),
    ("ум", "-ум", "притяжательный суффикс 1-го лица «мой» (мениң)"),
    ("үм", "-үм", "притяжательный суффикс 1-го лица «мой» (мениң)"),
    ("иң", "-иң", "притяжательный суффикс 2-го лица «твой» (сениң)"),
    ("уң", "-уң", "притяжательный суффикс 2-го лица «твой» (сениң)"),
    ("үң", "-үң", "притяжательный суффикс 2-го лица «твой» (сениң)"),
    ("си", "-си", "притяжательный суффикс 3-го лица «его/её» (униң)"),
]

# --- РАЗДЕЛЫ ГРАММАТИКИ И ПРАВИЛ ---
GRAMMAR_RULES = {
    "plural": (
        "🔢 <b>Множественное число (Көплүк сан)</b>\n\n"
        "В уйгурском языке множественное число образуется с помощью суффиксов <b>-лар</b> и <b>-ләр</b>:\n\n"
        "1️⃣ <b>-лар</b> добавляется к словам с <b>твёрдыми гласными</b> (а, о, у, ы):\n"
        "• <i>китап</i> (книга) ➔ <b>китаплар</b> (книги)\n"
        "• <i>тағ</i> (гора) ➔ <b>тағлар</b> (горы)\n"
        "• <i>бала</i> (ребёнок) ➔ <b>балилар</b> (дети — гласная «а» переходит в «и»)\n\n"
        "2️⃣ <b>-ләр</b> добавляется к словам с <b>мягкими гласных</b> (ә, ө, ү, и, е):\n"
        "• <i>мәктәп</i> (школа) ➔ <b>мәктәпләр</b> (школы)\n"
        "• <i>адәм</i> (человек) ➔ <b>адәмләр</b> (люди)\n"
        "• <i>гүл</i> (цветок) ➔ <b>гүлләр</b> (цветы)"
    ),
    "cases": (
        "📐 <b>6 падежей уйгурского языка (Келишләр)</b>\n\n"
        "1️⃣ <b>Баш келиш (Именительный — ким? немә?):</b>\n"
        "Без окончаний: <i>китап</i> (книга), <i>мәктәп</i> (школа).\n\n"
        "2️⃣ <b>Егилик келиш (Родительный — кимниң? неминиң?):</b>\n"
        "Суффикс <b>-ниң</b>: <i>китапниң</i> (книги), <i>балиниң</i> (ребёнка).\n\n"
        "3️⃣ <b>Йөнилиш келиш (Дательно-направительный — кимгә? қәйәргә?):</b>\n"
        "Суффиксы <b>-ға/-гә</b> (после звонких и гласных), <b>-қа/-кә</b> (после глухих):\n"
        "• <i>өйгә</i> (домой), <i>балиға</i> (ребёнку), <i>мәктәпкә</i> (в школу), <i>китапқа</i> (к книге).\n\n"
        "4️⃣ <b>Чүшүм келиш (Винительный — кимни? немини?):</b>\n"
        "Суффикс <b>-ни</b>: <i>китапни</i> (книгу), <i>нанни</i> (хлеб).\n\n"
        "5️⃣ <b>Орун-вақит келиш (Местный — кимдә? қәйәрдә?):</b>\n"
        "Суффиксы <b>-да/-дә</b> или <b>-та/-тә</b> (после глухих):\n"
        "• <i>өйдә</i> (дома), <i>бағда</i> (в саду), <i>мәктәптә</i> (в школе).\n\n"
        "6️⃣ <b>Чиқиш келиш (Исходный — кимдин? қәйәрдин?):</b>\n"
        "Суффиксы <b>-дин</b> или <b>-тин</b> (после глухих):\n"
        "• <i>өйдин</i> (из дома), <i>мәктәптин</i> (из школы)."
    ),
    "possessive": (
        "👤 <b>Притяжательные суффиксы (Тәвәлик қошумчилири)</b>\n\n"
        "Показывают принадлежность предмета:\n\n"
        "• <b>Мениң (Мой):</b> <b>-м / -им / -ум / -үм</b>\n"
        "  <i>апам</i> (моя мама), <i>китавим</i> (моя книга), <i>достум</i> (мой друг)\n\n"
        "• <b>Сениң (Твой):</b> <b>-ң / -иң / -уң / -үң</b>\n"
        "  <i>апаң</i> (твоя мама), <i>китавиң</i> (твоя книга), <i>достуң</i> (твой друг)\n\n"
        "• <b>Сизниң (Ваш — вежл.):</b> <b>-ңиз / -иңиз / -уңуз / -үңүз</b>\n"
        "  <i>апиңиз</i> (Ваша мама), <i>китавиңиз</i> (Ваша книга)\n\n"
        "• <b>Униң (Его / Её):</b> <b>-си / -и</b>\n"
        "  <i>аписи</i> (его мама), <i>китави</i> (его книга)\n\n"
        "• <b>Бизниң (Наш):</b> <b>-миз / -имиз / -умиз / -үмиз</b>\n"
        "  <i>апимиз</i> (наша мама), <i>вәтинимиз</i> (наша Родина)"
    ),
    "wordform": (
        "🛠 <b>Важные словообразовательные суффиксы</b>\n\n"
        "🔹 <b>-чи</b> — обозначает профессию или род занятий:\n"
        "• <i>иш</i> (работа) ➔ <b>ишчи</b> (рабочий)\n"
        "• <i>оқуш</i> (учёба) ➔ <b>оқуғучи</b> (ученик)\n\n"
        "🔹 <b>-лиқ / -лик / -луқ / -лүк</b> — наличие качества или место жительства:\n"
        "• <i>әқил</i> (ум) ➔ <b>әқиллиқ</b> (умный)\n"
        "• <i>күч</i> (сила) ➔ <b>күчлүк</b> (сильный)\n"
        "• <i>Алмута</i> ➔ <b>алмутилиқ</b> (алматинец)\n\n"
        "🔹 <b>-сиз</b> — отсутствие чего-либо («без»):\n"
        "• <i>су</i> (вода) ➔ <b>сусиз</b> (безводный / без воды)\n"
        "• <i>туз</i> (соль) ➔ <b>тузсиз</b> (без соли)\n\n"
        "🔹 <b>-дики / -тики</b> — находящийся где-либо:\n"
        "• <i>өй</i> (дом) ➔ <b>өйдики</b> (домашний / тот, что дома)\n"
        "• <i>мәктәп</i> (школа) ➔ <b>мәктәптики</b> (школьный)"
    ),
    "phonetics": (
        "🔄 <b>Чередование звуков в корне (Фонетика)</b>\n\n"
        "При добавлении суффиксов в уйгурском языке часто меняются звуки на стыке корня:\n\n"
        "1️⃣ <b>Озвончение глухих согласных (п ➔ в, қ ➔ ғ, к ➔ г)</b> перед гласной:\n"
        "• <i>кита<b>п</b></i> + им ➔ <b>китавим</b> (моя книга)\n"
        "• <i>ая<b>қ</b></i> + и ➔ <b>аяғи</b> (его нога)\n"
        "• <i>жүрә<b>к</b></i> + им ➔ <b>жүригим</b> (моё сердце)\n\n"
        "2️⃣ <b>Сужение гласных (а / ә ➔ и / е)</b> в открытом слоге:\n"
        "• <i>бал<b>а</b></i> + лар ➔ <b>балилар</b> (дети)\n"
        "• <i>ап<b>а</b></i> + си ➔ <b>аписи</b> (его мама)\n"
        "• <i>ат<b>а</b></i> + м ➔ <b>атам</b>, но: <i>ат<b>а</b></i> + миз ➔ <b>атимиз</b> (наш отец)"
    )
}

# --- БАЗА ДАННЫХ ДЛЯ РЕЙТИНГА И СЛОВАРЯ ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        name TEXT,
                        score INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def get_dict_table_and_cols(cursor):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('users', 'sqlite_sequence')")
    tables = [r[0] for r in cursor.fetchall()]
    if not tables:
        return None, None, None
    table = "words" if "words" in tables else tables[0]
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall() if row[1].lower() != "id"]
    if len(cols) >= 2:
        return table, cols[0], cols[1]
    return None, None, None

def add_point(user_id: int, name: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, name, score) VALUES (?, ?, 0)", (user_id, name))
    cursor.execute("UPDATE users SET score = score + 1, name = ? WHERE user_id = ?", (name, user_id))
    conn.commit()
    conn.close()

def get_top_users():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, score FROM users ORDER BY score DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_quiz_data():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    table, col1, col2 = get_dict_table_and_cols(cursor)
    if not table:
        conn.close()
        return None
    cursor.execute(f"SELECT {col1}, {col2} FROM {table} WHERE {col1} IS NOT NULL AND {col2} IS NOT NULL ORDER BY RANDOM() LIMIT 4")
    rows = cursor.fetchall()
    conn.close()
    if len(rows) < 4:
        return None
    correct = rows[0]
    question = str(correct[1]).strip()
    correct_word = str(correct[0]).strip()
    options = [str(r[0]).strip() for r in rows]
    random.shuffle(options)
    return question, correct_word, options

def get_random_word():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    table, col1, col2 = get_dict_table_and_cols(cursor)
    if not table:
        conn.close()
        return None
    cursor.execute(f"SELECT {col1}, {col2} FROM {table} WHERE {col1} IS NOT NULL AND {col2} IS NOT NULL ORDER BY RANDOM() LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return row

def generate_stem_variants(stem: str):
    variants = [stem]
    if stem.endswith("в"):
        variants.append(stem[:-1] + "п")
    if stem.endswith("ғ"):
        variants.append(stem[:-1] + "қ")
    if stem.endswith("г"):
        variants.append(stem[:-1] + "к")
    if stem.endswith("и") and len(stem) >= 3:
        variants.append(stem[:-1] + "а")
        variants.append(stem[:-1] + "ә")
    return variants

def search_word_in_db(query_text: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    table, col1, col2 = get_dict_table_and_cols(cursor)
    if not table:
        conn.close()
        return [], [], None
    cursor.execute(f"SELECT {col1}, {col2} FROM {table}")
    all_rows = cursor.fetchall()
    conn.close()

    q = query_text.strip().lower()
    exact_matches = []
    partial_matches = []

    for r in all_rows:
        w1 = str(r[0]).strip() if r[0] else ""
        w2 = str(r[1]).strip() if r[1] else ""
        w1_low, w2_low = w1.lower(), w2.lower()

        if q == w1_low or q == w2_low:
            exact_matches.append((w1, w2))
        elif q in w1_low or q in w2_low:
            partial_matches.append((w1, w2))

    if exact_matches:
        return exact_matches[:10], partial_matches[:10], None

    suffix_info = None
    for sfx, sfx_display, sfx_meaning in UYGHUR_SUFFIXES:
        if q.endswith(sfx) and len(q) > len(sfx) + 1:
            raw_stem = q[:-len(sfx)]
            stem_candidates = generate_stem_variants(raw_stem)
            for candidate in stem_candidates:
                for r in all_rows:
                    w1 = str(r[0]).strip() if r[0] else ""
                    w2 = str(r[1]).strip() if r[1] else ""
                    if candidate == w1.lower():
                        exact_matches.append((w1, w2))
                if exact_matches:
                    suffix_info = (exact_matches[0][0], sfx_display, sfx_meaning)
                    return exact_matches[:10], partial_matches[:10], suffix_info

    return exact_matches[:10], partial_matches[:10], None

# --- ГЛАВНОЕ МЕНЮ ---
def get_main_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🎯 Викторина")
    builder.button(text="🧩 Игра с суффиксами")
    builder.button(text="🎲 Случайное слово")
    builder.button(text="📚 Правила и суффиксы")
    builder.button(text="📜 Пословицы")
    builder.button(text="🏆 Рейтинг")
    builder.adjust(2, 2, 2)
    return builder.as_markup(resize_keyboard=True)

def get_grammar_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="🧩 Запустить игру с суффиксами", callback_data="start_sfx_game")
    builder.button(text="🔢 Множественное число (-лар/-ләр)", callback_data="gram_plural")
    builder.button(text="📐 6 падежей (Келишләр)", callback_data="gram_cases")
    builder.button(text="👤 Притяжательность (Мой/Твой)", callback_data="gram_possessive")
    builder.button(text="🛠 Суффиксы (-чи, -лиқ, -сиз)", callback_data="gram_wordform")
    builder.button(text="🔄 Чередование звуков (п➔в, қ➔ғ)", callback_data="gram_phonetics")
    builder.adjust(1)
    return builder.as_markup()

# --- КОМАНДА /START ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    init_db()
    text = (
        f"Ассаламу алейкум, <b>{message.from_user.first_name}</b>! 👋\n"
        "Добро пожаловать в <b>UyLingo</b> — умный бот-словарь и тренажёр уйгурского языка.\n\n"
        "🔎 <b>Как переводить слова:</b>\n"
        "Просто напиши любое слово (на русском или уйгурском, даже с суффиксами!) прямо в чат — я найду перевод и разберу окончание.\n\n"
        "Выбирай нужный раздел в меню ниже 👇"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_main_kb())

# --- ВИКТОРИНА СЛОВ ---
async def send_new_question(message_or_callback):
    data = get_quiz_data()
    if not data:
        if isinstance(message_or_callback, types.Message):
            await message_or_callback.answer("⚠️ В базе данных недостаточно слов для викторины.")
        return
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

@dp.message(F.text.contains("Викторина"))
async def start_quiz(message: types.Message):
    await send_new_question(message)

@dp.callback_query(F.data == "qzc_")
async def quiz_correct(callback: types.CallbackQuery):
    add_point(callback.from_user.id, callback.from_user.first_name)
    await callback.answer("✅ Правильно! +1 балл", show_alert=False)
    await send_new_question(callback)

@dp.callback_query(F.data.startswith("qzw_"))
async def quiz_wrong(callback: types.CallbackQuery):
    right_ans = callback.data.replace("qzw_", "")
    await callback.answer(f"❌ Неверно! Правильный ответ: {right_ans}", show_alert=True)
    await send_new_question(callback)

# --- ИГРА С СУФФИКСАМИ (ТРЕНАЖЁР) ---
async def send_suffix_question(message_or_callback):
    item = random.choice(SUFFIX_GAME_WORDS)
    opts = item["opts"].copy()
    random.shuffle(opts)

    builder = InlineKeyboardBuilder()
    for opt in opts:
        if opt == item["ans"]:
            cb_data = f"sfx_ok_{item['res']}"
        else:
            cb_data = f"sfx_err_{item['ans']}_{item['res']}"
        builder.button(text=opt, callback_data=cb_data)
    builder.adjust(2, 2)

    text = (
        f"🧩 <b>Игра с суффиксами:</b>\n\n"
        f"Слово: <b>{item['word']}</b> (<i>{item['tr']}</i>)\n"
        f"Задание: <b>{item['task']}</b>\n\n"
        f"Какой суффикс нужно добавить к слову <b>{item['word']}___</b>?"
    )
    if isinstance(message_or_callback, types.Message):
        await message_or_callback.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())
    else:
        await message_or_callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())

@dp.message(F.text.contains("Игра с суффиксами"))
async def start_sfx_game_msg(message: types.Message):
    await send_suffix_question(message)

@dp.callback_query(F.data == "start_sfx_game")
async def start_sfx_game_cb(callback: types.CallbackQuery):
    await callback.answer()
    await send_suffix_question(callback)

@dp.callback_query(F.data.startswith("sfx_ok_"))
async def sfx_game_correct(callback: types.CallbackQuery):
    res_word = callback.data.replace("sfx_ok_", "")
    add_point(callback.from_user.id, callback.from_user.first_name)
    await callback.answer(f"✅ Отлично! Получилось слово: {res_word} (+1 балл)", show_alert=False)
    await send_suffix_question(callback)

@dp.callback_query(F.data.startswith("sfx_err_"))
async def sfx_game_wrong(callback: types.CallbackQuery):
    parts = callback.data.replace("sfx_err_", "").split("_", 1)
    right_sfx = parts[0]
    res_word = parts[1] if len(parts) > 1 else ""
    await callback.answer(f"❌ Ошибка! Нужен суффикс {right_sfx} ➔ {res_word}", show_alert=True)
    await send_suffix_question(callback)

# --- ПРАВИЛА И СУФФИКСЫ ---
@dp.message(F.text.contains("Правила") | F.text.contains("Грамматика"))
async def grammar_menu_handler(message: types.Message):
    text = (
        "📚 <b>Правила и суффиксы уйгурского языка</b>\n\n"
        "Выбери тему ниже, чтобы изучить правила с примерами, или запусти тренажёр суффиксов!\n"
        "💡 <i>Подсказка: ты также можешь написать любое уйгурское слово с суффиксом прямо в чат, и я автоматически выделю корень и объясню суффикс!</i>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_grammar_kb())

@dp.callback_query(F.data.startswith("gram_"))
async def grammar_topic_callback(callback: types.CallbackQuery):
    topic = callback.data.replace("gram_", "")
    rule_text = GRAMMAR_RULES.get(topic, "Раздел обновляется.")
    await callback.message.edit_text(rule_text, parse_mode="HTML", reply_markup=get_grammar_kb())
    await callback.answer()

# --- СЛУЧАЙНОЕ СЛОВО, ПОСЛОВИЦЫ И РЕЙТИНГ ---
@dp.message(F.text.contains("Случайное слово") | F.text.contains("Слово дня"))
async def random_word_handler(message: types.Message):
    row = get_random_word()
    if row:
        await message.answer(f"🎲 <b>Случайное слово:</b>\n\n🔹 <b>{row[0]}</b> — {row[1]}", parse_mode="HTML")
    else:
        await message.answer("⚠️ База слов пуста.")

@dp.message(F.text.contains("Пословиц"))
async def proverb_handler(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Ещё пословица", callback_data="next_proverb")
    await message.answer(random.choice(PROVERBS), parse_mode="HTML", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "next_proverb")
async def next_proverb_callback(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Ещё пословица", callback_data="next_proverb")
    await callback.message.edit_text(random.choice(PROVERBS), parse_mode="HTML", reply_markup=builder.as_markup())
    await callback.answer()

@dp.message(F.text.contains("Рейтинг") | F.text.contains("Топ"))
async def rating_handler(message: types.Message):
    rows = get_top_users()
    if not rows:
        await message.answer("🏆 Пока никто не набрал баллов. Сыграй в викторину или игру с суффиксами первым!")
        return
    lines = ["🏆 <b>Топ знатоков UyLingo:</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, (name, score) in enumerate(rows, 1):
        icon = medals[i - 1] if i <= 3 else f"{i}."
        lines.append(f"{icon} <b>{name}</b> — {score} б.")
    await message.answer("\n".join(lines), parse_mode="HTML")

@dp.message(F.text.contains("Поиск слова"))
async def old_search_btn_handler(message: types.Message):
    await message.answer(
        "✍️ Просто напиши нужное слово прямо в чат, и я сразу найду его перевод!",
        reply_markup=get_main_kb()
    )

# --- ПЕРЕВОД ЛЮБОГО СЛОВА + АВТОМАТИЧЕСКИЙ РАЗБОР СУФФИКСОВ ---
@dp.message(F.text)
async def translate_text(message: types.Message):
    query = message.text.strip()
    exact, partial, suffix_info = search_word_in_db(query)

    if exact:
        res = "\n".join([f"🔹 <b>{w1}</b> — {w2}" for w1, w2 in exact])
        if suffix_info:
            root_word, sfx_display, sfx_meaning = suffix_info
            msg = (
                f"🧩 <b>Разбор слова «{query}»:</b>\n"
                f"• Корень: <b>{root_word}</b>\n"
                f"• Суффикс: <b>{sfx_display}</b> (<i>{sfx_meaning}</i>)\n\n"
                f"✅ <b>Перевод корня:</b>\n{res}"
            )
            await message.answer(msg, parse_mode="HTML")
        else:
            await message.answer(f"✅ <b>Перевод:</b>\n\n{res}", parse_mode="HTML")
    elif partial:
        res = "\n".join([f"🔸 <b>{w1}</b> — {w2}" for w1, w2 in partial])
        await message.answer(f"🔎 <b>Точного совпадения нет, но есть похожие слова:</b>\n\n{res}", parse_mode="HTML")
    else:
        await message.answer(
            "😕 Такого слова пока нет в словаре.\n"
            "Попробуй написать слово в начальной форме или загляни в раздел «📚 Правила и суффиксы»!"
        )

# --- ВЕБ-СЕРВЕР И БУДИЛЬНИК ДЛЯ RENDER (РАБОТА 24/7) ---
async def handle_ping(request):
    return web.Response(text="UyLingo Bot is alive 24/7!")

async def keep_alive_loop():
    url = os.environ.get("RENDER_EXTERNAL_URL")
    while True:
        await asyncio.sleep(300)
        if url:
            try:
                async with ClientSession() as session:
                    async with session.get(url) as resp:
                        logging.info(f"Keep-alive ping: {resp.status}")
            except Exception as e:
                logging.warning(f"Keep-alive error: {e}")

async def main():
    init_db()
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/ping", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    asyncio.create_task(keep_alive_loop())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
