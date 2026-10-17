# -*- coding: utf-8 -*-
"""
بوت مدينة الأفق (Horizon City Bot) - لعبة محاكاة حياة تفاعلية في مجموعات تيليجرام
مجهز بالكامل للعمل على منصة Render (Free Web Service) مع GitHub.
(نسخة محمية ضد أخطاء النسخ واللصق في الهواتف بدون f-strings)
"""

import asyncio
import logging
import os
import random
import sqlite3
import time
from typing import Optional, Dict, Any, Tuple

from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# ==========================================
# 1. الإعدادات الأساسية
# ==========================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")
PORT = int(os.getenv("PORT", "8080"))
DB_PATH = os.getenv("DB_PATH", "horizon_city.db")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

router = Router()

# ==========================================
# 2. بيانات العالم الافتراضي
# ==========================================
LOCATIONS: Dict[str, str] = {
    "downtown": "🏙️ وسط البلد (المركز المالي)",
    "residential": "🏠 الحي السكني",
    "market": "🛒 الحي التجاري والمطاعم",
    "education": "🎓 الجامعة والمجمع الطبي",
    "industrial": "🏭 المنطقة الصناعية والشركات",
    "police": "🚓 مركز الشرطة والمحكمة",
    "back_alleys": "🕶️ الأزقة الخلفية",
}

DEGREES: Dict[str, Dict[str, Any]] = {
    "management": {"name": "📜 بكالوريوس إدارة واقتصاد", "cost": 1500, "energy": 30},
    "medicine": {"name": "🩺 شهادة الطب العام", "cost": 2500, "energy": 40},
    "law_security": {"name": "⚖️ دبلوم القانون والعلوم الأمنية", "cost": 1800, "energy": 35},
    "engineering": {"name": "⚙️ بكالوريوس هندسة صناعية", "cost": 2000, "energy": 35},
}

JOBS: Dict[str, Dict[str, Any]] = {
    "freelancer": {"name": "👷 عامل حر", "salary": 250, "energy": 20, "req_degree": None, "clean_record": False},
    "banker": {"name": "🏦 محاسب مصرفي", "salary": 650, "energy": 25, "req_degree": "management", "clean_record": True},
    "doctor": {"name": "👨‍⚕️ طبيب في المستشفى", "salary": 900, "energy": 30, "req_degree": "medicine", "clean_record": True},
    "police_officer": {"name": "👮 ضابط شرطة", "salary": 750, "energy": 25, "req_degree": "law_security", "clean_record": True},
    "engineer": {"name": "👷‍♂️ مهندس مصانع", "salary": 800, "energy": 25, "req_degree": "engineering", "clean_record": True},
}

HOUSES: Dict[str, Dict[str, Any]] = {
    "studio": {"name": "🛏️ شقة استوديو", "base_price": 3000, "energy_regen": 15},
    "villa": {"name": "🏡 فيلا عائلية", "base_price": 12000, "energy_regen": 30},
    "palace": {"name": "🏰 قصر فاخر", "base_price": 50000, "energy_regen": 50},
}

VEHICLES: Dict[str, Dict[str, Any]] = {
    "bike": {"name": "🏍️ دراجة نارية", "base_price": 2000, "travel_energy_save": 3},
    "sedan": {"name": "🚗 سيارة سيدان", "base_price": 8500, "travel_energy_save": 6},
    "sports": {"name": "🏎️ سيارة رياضية فاخرة", "base_price": 35000, "travel_energy_save": 9},
}

BUSINESS_TYPES: Dict[str, Dict[str, Any]] = {
    "restaurant": {"name": "🍔 مطعم وجبات سريعة", "base_price": 10000, "hourly_income": 350},
    "supermarket": {"name": "🛒 سوبرماركت مركزي", "base_price": 22000, "hourly_income": 800},
    "car_agency": {"name": "🚘 وكالة سيارات", "base_price": 60000, "hourly_income": 2400},
    "factory": {"name": "🏭 مصنع إنتاج", "base_price": 95000, "hourly_income": 4000},
}


# ==========================================
# 3. إدارة قاعدة البيانات (SQLite)
# ==========================================
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cities (
            city_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            is_global INTEGER DEFAULT 0,
            owner_chat_id INTEGER DEFAULT NULL,
            treasury INTEGER DEFAULT 100000,
            price_index REAL DEFAULT 1.0,
            created_at INTEGER NOT NULL
        )
    """)

    cur.execute("SELECT city_id FROM cities WHERE city_id = 1")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO cities (city_id, name, is_global, treasury, price_index, created_at) VALUES (1, 'مدينة الأفق العالمية', 1, 500000, 1.0, ?)",
            (int(time.time()),),
        )

    cur.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            chat_id INTEGER PRIMARY KEY,
            city_id INTEGER NOT NULL,
            group_title TEXT,
            FOREIGN KEY (city_id) REFERENCES cities(city_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER NOT NULL,
            city_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            location TEXT DEFAULT 'downtown',
            cash INTEGER DEFAULT 1000,
            bank INTEGER DEFAULT 500,
            health INTEGER DEFAULT 100,
            energy INTEGER DEFAULT 100,
            hunger INTEGER DEFAULT 100,
            level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            degree TEXT DEFAULT NULL,
            job TEXT DEFAULT 'freelancer',
            house TEXT DEFAULT NULL,
            vehicle TEXT DEFAULT NULL,
            wanted_level INTEGER DEFAULT 0,
            jail_until INTEGER DEFAULT 0,
            gang_name TEXT DEFAULT NULL,
            last_work_ts INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, city_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS businesses (
            biz_id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_id INTEGER NOT NULL,
            owner_id INTEGER NOT NULL,
            biz_type TEXT NOT NULL,
            custom_name TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# ==========================================
# 4. دوال مساعدة لإدارة المدن واللاعبين
# ==========================================
def get_group_city(chat_id: int) -> Optional[sqlite3.Row]:
    conn = get_db()
    row = conn.execute(
        """
        SELECT g.chat_id, g.city_id, c.name AS city_name, c.is_global, c.treasury, c.price_index
        FROM groups g
        JOIN cities c ON g.city_id = c.city_id
        WHERE g.chat_id = ?
        """,
        (chat_id,),
    ).fetchone()
    conn.close()
    return row


def set_group_city_mode(chat_id: int, title: str, mode: str) -> Tuple[int, str]:
    conn = get_db()
    cur = conn.cursor()
    if mode == "global":
        city_id = 1
        city_name = "مدينة الأفق العالمية"
    else:
        city_name = "مدينة " + str(title[:25])
        cur.execute(
            "INSERT INTO cities (name, is_global, owner_chat_id, treasury, price_index, created_at) VALUES (?, 0, ?, 100000, 1.0, ?)",
            (city_name, chat_id, int(time.time())),
        )
        city_id = cur.lastrowid

    cur.execute(
        "INSERT OR REPLACE INTO groups (chat_id, city_id, group_title) VALUES (?, ?, ?)",
        (chat_id, city_id, title),
    )
    conn.commit()
    conn.close()
    return city_id, city_name


def get_or_create_player(user_id: int, city_id: int, full_name: str) -> sqlite3.Row:
    conn = get_db()
    cur = conn.cursor()
    player = cur.execute(
        "SELECT * FROM players WHERE user_id = ? AND city_id = ?",
        (user_id, city_id),
    ).fetchone()
    if not player:
        cur.execute(
            "INSERT INTO players (user_id, city_id, username) VALUES (?, ?, ?)",
            (user_id, city_id, full_name[:30]),
        )
        conn.commit()
        player = cur.execute(
            "SELECT * FROM players WHERE user_id = ? AND city_id = ?",
            (user_id, city_id),
        ).fetchone()
    conn.close()
    return player


def adjust_city_demand(city_id: int, delta: float) -> None:
    conn = get_db()
    city = conn.execute("SELECT price_index FROM cities WHERE city_id = ?", (city_id,)).fetchone()
    if city:
        new_index = max(0.75, min(2.50, round(city["price_index"] + delta, 2)))
        conn.execute("UPDATE cities SET price_index = ? WHERE city_id = ?", (new_index, city_id))
        conn.commit()
    conn.close()


# ==========================================
# 5. بناء لوحات الأزرار التفاعلية (Inline Keyboards)
# ==========================================
def build_setup_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌐 الانضمام للمدينة العالمية الموحدة",
                    callback_data="setup_mode:global",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏙️ إنشاء مدينة مستقلة خاصة بالمجموعة",
                    callback_data="setup_mode:private",
                )
            ],
        ]
    )


def build_main_city_keyboard(uid: int) -> InlineKeyboardMarkup:
    u_str = str(uid)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗺️ التنقل بين الشوارع", callback_data="nav_menu:" + u_str),
                InlineKeyboardButton(text="👥 المتواجدون بموقعي", callback_data="nearby:" + u_str),
            ],
            [
                InlineKeyboardButton(text="💼 العمل والوظائف", callback_data="jobs_menu:" + u_str),
                InlineKeyboardButton(text="🎓 المدرسة والجامعة", callback_data="edu_menu:" + u_str),
            ],
            [
                InlineKeyboardButton(text="🏠 العقارات والسيارات", callback_data="prop_menu:" + u_str),
                InlineKeyboardButton(text="🏢 تأسيس المشاريع", callback_data="biz_menu:" + u_str),
            ],
            [
                InlineKeyboardButton(text="🛒 المطعم والسوق", callback_data="market_menu:" + u_str),
                InlineKeyboardButton(text="🏦 المصرف المركزي", callback_data="bank_menu:" + u_str),
            ],
            [
                InlineKeyboardButton(text="🚓 الشرطة والمطلوبون", callback_data="police_menu:" + u_str),
                InlineKeyboardButton(text="🕶️ العصابات والسرقة", callback_data="crime_menu:" + u_str),
            ],
            [
                InlineKeyboardButton(text="🔄 تحديث بطاقة المدينة", callback_data="main_menu:" + u_str),
            ],
        ]
    )


def format_player_dashboard(player: sqlite3.Row, city: sqlite3.Row) -> str:
    loc_name = LOCATIONS.get(player["location"], player["location"])
    job_name = JOBS.get(player["job"], {}).get("name", "بدون عمل")
    degree_name = DEGREES.get(player["degree"], {}).get("name", "لا يوجد") if player["degree"] else "لا يوجد"
    house_name = HOUSES.get(player["house"], {}).get("name", "بلا مسكن") if player["house"] else "بلا مسكن"
    vehicle_name = VEHICLES.get(player["vehicle"], {}).get("name", "مشيًا على الأقدام") if player["vehicle"] else "مشيًا على الأقدام"
    gang_text = player["gang_name"] if player["gang_name"] else "مستقل"

    now = int(time.time())
    if player["jail_until"] > now:
        remaining_min = max(1, (player["jail_until"] - now) // 60)
        jail_status = "\n🔒 **الحالة الأمنية:** موقوف في السجن (" + str(remaining_min) + " دقيقة متبقية)"
    elif player["wanted_level"] > 0:
        jail_status = "\n🚨 **الحالة الأمنية:** مطلوب للشرطة (درجة الخطورة: " + str(player["wanted_level"]) + " ⭐)"
    else:
        jail_status = "\n✅ **الحالة الأمنية:** سجل مدني نظيف"

    mode_label = "🌐 عالمية مشتركة" if city["is_global"] else "🏙️ خاصة بالمجموعة"
    price_pct = str(int(city["price_index"] * 100))

    return (
        "🏙️ **" + str(city["city_name"]) + "** (" + mode_label + ")\n"
        "📊 مؤشر الأسعار الحالي: `" + price_pct + "%` | خزينة المدينة: `" + str(city["treasury"]) + "$`\n\n"
        "👤 **المواطن:** " + str(player["username"]) + " (المستوى " + str(player["level"]) + " ⭐)\n"
        "📍 **الموقع الحالي:** " + loc_name + "\n"
        "❤️ الصحة: `" + str(player["health"]) + "%` | ⚡ الطاقة: `" + str(player["energy"]) + "%` | 🍔 الشبع: `" + str(player["hunger"]) + "%`\n"
        "💵 النقد بالمحفظة: `" + str(player["cash"]) + "$` | 🏦 الرصيد المصرفي: `" + str(player["bank"]) + "$`\n"
        "💼 الوظيفة: " + job_name + " | 🎓 الشهادة: " + degree_name + "\n"
        "🏠 المسكن: " + house_name + " | 🚗 المركبة: " + vehicle_name + "\n"
        "🕶️ الانتماء: " + gang_text
        + jail_status
    )


# ==========================================
# 6. معالجات أوامر المجموعة والإعدادات
# ==========================================
@router.message(Command("start", "البدء", "اعداد_المدينة"))
async def cmd_start_or_setup(message: Message) -> None:
    if message.chat.type == "private":
        await message.answer(
            "👋 أهلاً بك في **بوت مدينة الأفق التفاعلية**!\n\n"
            "لبدء اللعب، أضف البوت إلى مجموعتك ثم أرسل أمر `/اعداد_المدينة` ليختار مدير المجموعة نظام المدينة، "
            "وبعدها يمكن لجميع الأعضاء كتابة `/المدينة` لبدء حياتهم الافتراضية معًا.",
            parse_mode="Markdown",
        )
        return

    await message.answer(
        "⚙️ **إعداد نظام المدينة في المجموعة**\n\n"
        "يمكن لمدير أو مشرف المجموعة اختيار نظام العالم الذي سيعيش فيه أعضاء المجموعة:\n"
        "1️⃣ **المدينة العالمية الموحدة:** يعيش أعضاء المجموعة في مدينة كبرى مشتركة مع المجموعات الأخرى.\n"
        "2️⃣ **مدينة مستقلة خاصة بالمجموعة:** تُنشأ مدينة كاملة بجميع مرافقها مخصصة لأعضاء هذه المجموعة فقط.",
        reply_markup=build_setup_keyboard(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("setup_mode:"))
async def cb_setup_mode(callback: CallbackQuery, bot: Bot) -> None:
    member = await bot.get_chat_member(callback.message.chat.id, callback.from_user.id)
    if member.status not in ("administrator", "creator"):
        await callback.answer("❌ هذا الخيار مخصص لمدير ومشرفي المجموعة فقط!", show_alert=True)
        return

    mode = callback.data.split(":")[1]
    title = callback.message.chat.title or "المجموعة"
    _, city_name = set_group_city_mode(callback.message.chat.id, title, mode)

    if mode == "global":
        mode_desc = "🌐 تم ربط المجموعة بـ **المدينة العالمية الموحدة** بنجاح!"
    else:
        mode_desc = "🏙️ تم إنشاء **" + city_name + "** كمدينة كاملة ومستقلة خاصة بمجموعتكم!"

    await callback.message.edit_text(
        mode_desc + "\n\n"
        "🏛️ جميع المرافق (المنازل، الأسواق، المطاعم، الجامعة، الشركات، المصرف، الشرطة، والعصابات) أصبحت مفتوحة الآن!\n"
        "👈 اكتبوا أمر `/المدينة` لفتح بطاقة حياتكم والتجول في المدينة.",
        parse_mode="Markdown",
    )
    await callback.answer("تم حفظ إعدادات المدينة!")


@router.message(Command("city", "المدينة", "حياتي"))
async def cmd_open_city(message: Message) -> None:
    if message.chat.type == "private":
        await message.answer("⚠️ يرجى استخدام أمر `/المدينة` داخل مجموعة تيليجرام مفعّلة.")
        return

    city = get_group_city(message.chat.id)
    if not city:
        await message.answer(
            "⚠️ لم يتم اختيار نظام المدينة لهذه المجموعة بعد!\n"
            "يرجى من مدير المجموعة الضغط على الزر أدناه لتفعيل المدينة:",
            reply_markup=build_setup_keyboard(),
        )
        return

    player = get_or_create_player(
        message.from_user.id,
        city["city_id"],
        message.from_user.full_name or "مواطن",
    )
    text = format_player_dashboard(player, city)
    await message.answer(
        text,
        reply_markup=build_main_city_keyboard(message.from_user.id),
        parse_mode="Markdown",
    )


# ==========================================
# 7. التحقق من ملكية لوحة الأزرار
# ==========================================
def check_owner_and_city(callback: CallbackQuery) -> Optional[Tuple[sqlite3.Row, sqlite3.Row]]:
    parts = callback.data.split(":")
    owner_id = int(parts[-1])
    if callback.from_user.id != owner_id:
        return None
    city = get_group_city(callback.message.chat.id)
    if not city:
        return None
    player = get_or_create_player(
        callback.from_user.id,
        city["city_id"],
        callback.from_user.full_name or "مواطن",
    )
    return player, city


@router.callback_query(F.data.startswith("main_menu:"))
async def cb_main_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر! اكتب /المدينة لفتح لوحتك.", show_alert=True)
        return
    player, city = res
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )
    await callback.answer()


# ==========================================
# 8. نظام التنقل بين شوارع ومناطق المدينة
# ==========================================
@router.callback_query(F.data.startswith("nav_menu:"))
async def cb_nav_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, _ = res
    u_str = str(player["user_id"])

    if player["jail_until"] > int(time.time()):
        await callback.answer("🔒 لا يمكنك التنقل في المدينة أثناء فترة التوقيف في السجن!", show_alert=True)
        return

    buttons = []
    for loc_key, loc_title in LOCATIONS.items():
        prefix = "📍 " if player["location"] == loc_key else "🚶 "
        buttons.append([InlineKeyboardButton(text=prefix + loc_title, callback_data="move:" + loc_key + ":" + u_str)])
    buttons.append([InlineKeyboardButton(text="🔙 العودة للمدينة", callback_data="main_menu:" + u_str)])

    await callback.message.edit_text(
        "🗺️ **خريطة شوارع ومناطق المدينة**\nاختر المنطقة التي تريد الانتقال إليها (امتلاك مركبة يوفر طاقة التنقل):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("move:"))
async def cb_move_location(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, city = res
    _, target_loc, _ = callback.data.split(":")

    if player["location"] == target_loc:
        await callback.answer("أنت متواجد بالفعل في هذه المنطقة!")
        return

    save = VEHICLES.get(player["vehicle"], {}).get("travel_energy_save", 0) if player["vehicle"] else 0
    energy_cost = max(2, 10 - save)

    if player["energy"] < energy_cost:
        await callback.answer("⚡ طاقتك غير كافية للتنقل! تحتاج " + str(energy_cost) + "% طاقة (توجّه للمطعم أو استرح في منزلك).", show_alert=True)
        return

    conn = get_db()
    conn.execute(
        "UPDATE players SET location = ?, energy = energy - ? WHERE user_id = ? AND city_id = ?",
        (target_loc, energy_cost, player["user_id"], city["city_id"]),
    )
    conn.commit()
    conn.close()

    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    await callback.answer("✅ انتقلت إلى " + LOCATIONS[target_loc] + " (-" + str(energy_cost) + "% طاقة)")
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("nearby:"))
async def cb_nearby_players(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, city = res
    conn = get_db()
    others = conn.execute(
        "SELECT username, job, wanted_level FROM players WHERE city_id = ? AND location = ? LIMIT 15",
        (city["city_id"], player["location"]),
    ).fetchall()
    conn.close()

    loc_title = LOCATIONS.get(player["location"], player["location"])
    lines = ["👥 **المتواجدون حاليًا في " + loc_title + ":**\n"]
    for row in others:
        job_title = JOBS.get(row["job"], {}).get("name", "مواطن")
        wanted_tag = " 🚨(مطلوب " + str(row["wanted_level"]) + "⭐)" if row["wanted_level"] > 0 else ""
        lines.append("• **" + str(row["username"]) + "** — " + job_title + wanted_tag)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 العودة للمدينة", callback_data="main_menu:" + str(player["user_id"]))]]
    )
    await callback.message.edit_text("\n".join(lines), reply_markup=kb, parse_mode="Markdown")
    await callback.answer()


# ==========================================
# 9. التعليم والوظائف والعمل
# ==========================================
@router.callback_query(F.data.startswith("edu_menu:"))
async def cb_edu_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, _ = res
    u_str = str(player["user_id"])

    buttons = []
    for deg_key, deg in DEGREES.items():
        btn_txt = deg["name"] + " (" + str(deg["cost"]) + "$ | -" + str(deg["energy"]) + "⚡)"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=btn_txt,
                    callback_data="study:" + deg_key + ":" + u_str,
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="🔙 العودة للمدينة", callback_data="main_menu:" + u_str)])

    await callback.message.edit_text(
        "🎓 **الجامعة المركزية ومعهد التدريب**\nاختر التخصص الذي ترغب بدراسته لفتح الوظائف العليا في المدينة:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("study:"))
async def cb_study_degree(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, city = res
    _, deg_key, _ = callback.data.split(":")
    deg = DEGREES[deg_key]

    if player["cash"] < deg["cost"]:
        await callback.answer("💵 رصيدك النقدي غير كافٍ! تحتاج إلى " + str(deg["cost"]) + "$.", show_alert=True)
        return
    if player["energy"] < deg["energy"]:
        await callback.answer("⚡ طاقتك غير كافية للدراسة! تحتاج إلى " + str(deg["energy"]) + "% طاقة.", show_alert=True)
        return

    conn = get_db()
    conn.execute(
        "UPDATE players SET cash = cash - ?, energy = energy - ?, degree = ?, xp = xp + 50, location = 'education' WHERE user_id = ? AND city_id = ?",
        (deg["cost"], deg["energy"], deg_key, player["user_id"], city["city_id"]),
    )
    conn.execute("UPDATE cities SET treasury = treasury + ? WHERE city_id = ?", (deg["cost"], city["city_id"]))
    conn.commit()
    conn.close()

    await callback.answer("🎉 مبارك! حصلت على " + deg["name"] + " بنجاح!", show_alert=True)
    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    city = get_group_city(callback.message.chat.id)
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("jobs_menu:"))
async def cb_jobs_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, _ = res
    u_str = str(player["user_id"])

    buttons = [
        [InlineKeyboardButton(text="💰 إنجاز نوبة عمل الآن واستلام الراتب", callback_data="work_shift:" + u_str)]
    ]
    for job_key, job in JOBS.items():
        buttons.append(
            [
                InlineKeyboardButton(
                    text="تقديم: " + job["name"] + " (الراتب: " + str(job["salary"]) + "$)",
                    callback_data="apply_job:" + job_key + ":" + u_str,
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="🔙 العودة للمدينة", callback_data="main_menu:" + u_str)])

    await callback.message.edit_text(
        "💼 **مكتب التوظيف والعمل**\nيمكنك إنجاز نوبة عمل في وظيفتك الحالية أو التقديم على وظيفة جديدة:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("apply_job:"))
async def cb_apply_job(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, city = res
    _, job_key, _ = callback.data.split(":")
    job = JOBS[job_key]

    if job["req_degree"] and player["degree"] != job["req_degree"]:
        req_name = DEGREES[job["req_degree"]]["name"]
        await callback.answer("🎓 هذه الوظيفة تتطلب الحصول على: " + req_name + " من الجامعة أولاً!", show_alert=True)
        return

    if job["clean_record"] and player["wanted_level"] > 0:
        await callback.answer("🚨 لا يمكن قبولك في وظيفة رسمية وعليك بلاغات أمنية في الشرطة!", show_alert=True)
        return

    conn = get_db()
    conn.execute(
        "UPDATE players SET job = ? WHERE user_id = ? AND city_id = ?",
        (job_key, player["user_id"], city["city_id"]),
    )
    conn.commit()
    conn.close()

    await callback.answer("✅ تم تعيينك في وظيفة: " + job["name"] + "!", show_alert=True)
    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("work_shift:"))
async def cb_work_shift(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, city = res

    if player["jail_until"] > int(time.time()):
        await callback.answer("🔒 لا يمكنك العمل أثناء وجودك في السجن!", show_alert=True)
        return

    job = JOBS.get(player["job"], JOBS["freelancer"])
    if player["energy"] < job["energy"] or player["hunger"] < 15:
        await callback.answer("⚡ طاقتك أو مستوى الشبع منخفض جدًا! تناول وجبة في المطعم أو استرح في منزلك.", show_alert=True)
        return

    salary = int(job["salary"] * city["price_index"])
    new_xp = player["xp"] + 25
    new_level = 1 + (new_xp // 100)

    conn = get_db()
    conn.execute(
        """
        UPDATE players
        SET cash = cash + ?, energy = energy - ?, hunger = MAX(0, hunger - 15), xp = ?, level = ?
        WHERE user_id = ? AND city_id = ?
        """,
        (salary, job["energy"], new_xp, new_level, player["user_id"], city["city_id"]),
    )
    conn.commit()
    conn.close()

    adjust_city_demand(city["city_id"], -0.01)
    await callback.answer("💵 أنجزت عملك كـ " + job["name"] + " وحصلت على " + str(salary) + "$ (+25 خبرة)!", show_alert=True)
    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    city = get_group_city(callback.message.chat.id)
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )


# ==========================================
# 10. المطاعم والسوق والمصرف المركزي
# ==========================================
@router.callback_query(F.data.startswith("market_menu:"))
async def cb_market_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, city = res
    u_str = str(player["user_id"])
    idx = city["price_index"]

    meal_price = str(int(80 * idx))
    med_price = str(int(150 * idx))
    rest_price = str(int(100 * idx))

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🍔 وجبة متكاملة (+40 شبع، +25 طاقة) — " + meal_price + "$", callback_data="buy_item:meal:" + u_str)],
            [InlineKeyboardButton(text="💊 حقيبة إسعاف وعلاج (+50 صحة) — " + med_price + "$", callback_data="buy_item:med:" + u_str)],
            [InlineKeyboardButton(text="🛌 استراحة في المنزل/الفندق (+50 طاقة) — " + rest_price + "$", callback_data="buy_item:rest:" + u_str)],
            [InlineKeyboardButton(text="🔙 العودة للمدينة", callback_data="main_menu:" + u_str)],
        ]
    )
    await callback.message.edit_text(
        "🛒 **سوق المدينة والمطاعم والمستشفى**\nالأسعار تتغير تلقائيًا حسب العرض والطلب في المدينة (المؤشر الحالي `" + str(int(idx * 100)) + "%`):",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_item:"))
async def cb_buy_item(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, city = res
    _, item_type, _ = callback.data.split(":")
    idx = city["price_index"]

    conn = get_db()
    if item_type == "meal":
        cost = int(80 * idx)
        if player["cash"] < cost:
            await callback.answer("💵 رصيدك النقدي غير كافٍ!", show_alert=True)
            conn.close()
            return
        conn.execute(
            "UPDATE players SET cash = cash - ?, hunger = MIN(100, hunger + 40), energy = MIN(100, energy + 25), location = 'market' WHERE user_id = ? AND city_id = ?",
            (cost, player["user_id"], city["city_id"]),
        )
        msg = "🍔 تناولت وجبة شهية واستعدت نشاطك!"
    elif item_type == "med":
        cost = int(150 * idx)
        if player["cash"] < cost:
            await callback.answer("💵 رصيدك النقدي غير كافٍ!", show_alert=True)
            conn.close()
            return
        conn.execute(
            "UPDATE players SET cash = cash - ?, health = MIN(100, health + 50), location = 'education' WHERE user_id = ? AND city_id = ?",
            (cost, player["user_id"], city["city_id"]),
        )
        msg = "💊 تلقيت العلاج في المستشفى واستعدت صحتك!"
    else:
        cost = 0 if player["house"] else int(100 * idx)
        if player["cash"] < cost:
            await callback.answer("💵 رصيدك النقدي غير كافٍ لدفع أجرة الفندق!", show_alert=True)
            conn.close()
            return
        regen = HOUSES.get(player["house"], {}).get("energy_regen", 35) + 25
        conn.execute(
            "UPDATE players SET cash = cash - ?, energy = MIN(100, energy + ?), location = 'residential' WHERE user_id = ? AND city_id = ?",
            (cost, regen, player["user_id"], city["city_id"]),
        )
        msg = "🛌 أخذت قسطًا من الراحة واستعدت طاقتك!"

    conn.commit()
    conn.close()
    adjust_city_demand(city["city_id"], 0.02)
    await callback.answer(msg, show_alert=True)

    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    city = get_group_city(callback.message.chat.id)
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("bank_menu:"))
async def cb_bank_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, _ = res
    u_str = str(player["user_id"])

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📥 إيداع كل النقد بالمصرف", callback_data="bank_op:dep_all:" + u_str),
                InlineKeyboardButton(text="📤 سحب 1,000$ نقدًا", callback_data="bank_op:wit_1000:" + u_str),
            ],
            [
                InlineKeyboardButton(text="📤 سحب كل الرصيد", callback_data="bank_op:wit_all:" + u_str),
            ],
            [InlineKeyboardButton(text="🔙 العودة للمدينة", callback_data="main_menu:" + u_str)],
        ]
    )
    await callback.message.edit_text(
        "🏦 **المصرف المركزي**\n"
        "💵 النقد في محفظتك: `" + str(player["cash"]) + "$` (معرض للسرقة)\n"
        "🏦 رصيدك المصرفي الآمن: `" + str(player["bank"]) + "$` (يحصل على عوائد ادخارية دورية)\n\n"
        "💡 *لتحويل مال لصديق في المجموعة: قم بالرد (Reply) على رسالته واكتب:* `تحويل 500`",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bank_op:"))
async def cb_bank_op(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, city = res
    _, op, _ = callback.data.split(":")

    conn = get_db()
    if op == "dep_all":
        if player["cash"] <= 0:
            await callback.answer("ليس لديك نقد لإيداعه!", show_alert=True)
            conn.close()
            return
        conn.execute(
            "UPDATE players SET bank = bank + cash, cash = 0, location = 'downtown' WHERE user_id = ? AND city_id = ?",
            (player["user_id"], city["city_id"]),
        )
        msg = "✅ تم إيداع جميع أموالك النقدية في حسابك المصرفي الآمن!"
    elif op == "wit_1000":
        amt = min(1000, player["bank"])
        if amt <= 0:
            await callback.answer("رصيدك المصرفي فارغ!", show_alert=True)
            conn.close()
            return
        conn.execute(
            "UPDATE players SET bank = bank - ?, cash = cash + ?, location = 'downtown' WHERE user_id = ? AND city_id = ?",
            (amt, amt, player["user_id"], city["city_id"]),
        )
        msg = "✅ تم سحب " + str(amt) + "$ إلى محفظتك النقدية."
    else:
        if player["bank"] <= 0:
            await callback.answer("رصيدك المصرفي فارغ!", show_alert=True)
            conn.close()
            return
        conn.execute(
            "UPDATE players SET cash = cash + bank, bank = 0, location = 'downtown' WHERE user_id = ? AND city_id = ?",
            (player["user_id"], city["city_id"]),
        )
        msg = "✅ تم سحب كامل الرصيد المصرفي إلى محفظتك."

    conn.commit()
    conn.close()
    await callback.answer(msg, show_alert=True)
    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )


# ==========================================
# 11. العقارات والسيارات وتأسيس المشاريع
# ==========================================
@router.callback_query(F.data.startswith("prop_menu:"))
async def cb_prop_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, city = res
    u_str = str(player["user_id"])
    idx = city["price_index"]

    buttons = []
    for h_key, h in HOUSES.items():
        price = str(int(h["base_price"] * idx))
        buttons.append([InlineKeyboardButton(text="شراء " + h["name"] + " (" + price + "$)", callback_data="buy_house:" + h_key + ":" + u_str)])
    for v_key, v in VEHICLES.items():
        price = str(int(v["base_price"] * idx))
        buttons.append([InlineKeyboardButton(text="شراء " + v["name"] + " (" + price + "$)", callback_data="buy_veh:" + v_key + ":" + u_str)])
    buttons.append([InlineKeyboardButton(text="🔙 العودة للمدينة", callback_data="main_menu:" + u_str)])

    await callback.message.edit_text(
        "🏠 **سوق العقارات ومعرض السيارات**\nامتلاك منزل يمنحك راحة مجانية واستعادة أسرع للطاقة، وامتلاك مركبة يقلل جهد التنقل:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_house:"))
async def cb_buy_house(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, city = res
    _, h_key, _ = callback.data.split(":")
    house = HOUSES[h_key]
    price = int(house["base_price"] * city["price_index"])

    if player["cash"] < price:
        await callback.answer("💵 تحتاج إلى " + str(price) + "$ نقدًا في محفظتك لشراء " + house["name"] + "!", show_alert=True)
        return

    conn = get_db()
    conn.execute(
        "UPDATE players SET cash = cash - ?, house = ?, location = 'residential' WHERE user_id = ? AND city_id = ?",
        (price, h_key, player["user_id"], city["city_id"]),
    )
    conn.commit()
    conn.close()
    adjust_city_demand(city["city_id"], 0.03)
    await callback.answer("🏡 مبارك! أصبحت مالكًا لـ " + house["name"] + "!", show_alert=True)

    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    city = get_group_city(callback.message.chat.id)
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("buy_veh:"))
async def cb_buy_veh(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, city = res
    _, v_key, _ = callback.data.split(":")
    veh = VEHICLES[v_key]
    price = int(veh["base_price"] * city["price_index"])

    if player["cash"] < price:
        await callback.answer("💵 تحتاج إلى " + str(price) + "$ نقدًا لشراء " + veh["name"] + "!", show_alert=True)
        return

    conn = get_db()
    conn.execute(
        "UPDATE players SET cash = cash - ?, vehicle = ?, location = 'market' WHERE user_id = ? AND city_id = ?",
        (price, v_key, player["user_id"], city["city_id"]),
    )
    conn.commit()
    conn.close()
    adjust_city_demand(city["city_id"], 0.02)
    await callback.answer("🚗 مبارك! اشتريت " + veh["name"] + " بنجاح!", show_alert=True)

    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    city = get_group_city(callback.message.chat.id)
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("biz_menu:"))
async def cb_biz_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, city = res
    u_str = str(player["user_id"])
    idx = city["price_index"]

    conn = get_db()
    owned = conn.execute(
        "SELECT custom_name, biz_type FROM businesses WHERE city_id = ? AND owner_id = ?",
        (city["city_id"], player["user_id"]),
    ).fetchall()
    conn.close()

    owned_lines = []
    for r in owned:
        inc = str(BUSINESS_TYPES[r["biz_type"]]["hourly_income"])
        owned_lines.append("• " + str(r["custom_name"]) + " (+" + inc + "$ كل دورة)")
    owned_text = "\n".join(owned_lines) if owned_lines else "لا تملك مشاريع تجارية بعد."

    buttons = []
    for b_key, b in BUSINESS_TYPES.items():
        price = str(int(b["base_price"] * idx))
        inc = str(b["hourly_income"])
        buttons.append(
            [
                InlineKeyboardButton(
                    text="تأسيس " + b["name"] + " (" + price + "$ | ربح: +" + inc + "$)",
                    callback_data="buy_biz:" + b_key + ":" + u_str,
                )
            ]
        )
    buttons.append([InlineKeyboardButton(text="🔙 العودة للمدينة", callback_data="main_menu:" + u_str)])

    await callback.message.edit_text(
        "🏢 **غرفة التجارة والمشاريع الاستثمارية**\n"
        "المشاريع تدر أرباحًا تلقائية تُودع في حسابك المصرفي حتى وأنت غير متصل:\n\n"
        "📋 **مشاريعك الحالية:**\n" + owned_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_biz:"))
async def cb_buy_biz(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, city = res
    _, b_key, _ = callback.data.split(":")
    biz = BUSINESS_TYPES[b_key]
    price = int(biz["base_price"] * city["price_index"])

    if player["cash"] < price:
        await callback.answer("💵 تحتاج إلى " + str(price) + "$ نقدًا لتأسيس " + biz["name"] + "!", show_alert=True)
        return

    conn = get_db()
    conn.execute(
        "UPDATE players SET cash = cash - ?, location = 'industrial' WHERE user_id = ? AND city_id = ?",
        (price, player["user_id"], city["city_id"]),
    )
    custom_title = biz["name"] + " (" + str(player["username"]) + ")"
    conn.execute(
        "INSERT INTO businesses (city_id, owner_id, biz_type, custom_name, created_at) VALUES (?, ?, ?, ?, ?)",
        (city["city_id"], player["user_id"], b_key, custom_title, int(time.time())),
    )
    conn.commit()
    conn.close()

    await callback.answer("🎉 مبارك! أسست مشروع " + biz["name"] + " وسيبدأ بإدرار الأرباح تلقائيًا!", show_alert=True)
    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )


# ==========================================
# 12. نظام الشرطة، العصابات، والسرقات الافتراضية المتوازنة
# ==========================================
@router.callback_query(F.data.startswith("crime_menu:"))
async def cb_crime_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, _ = res
    u_str = str(player["user_id"])

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🕶️ عملية سطو افتراضية على خزنة متجر (-25⚡)", callback_data="do_heist:store:" + u_str)],
            [InlineKeyboardButton(text="🏦 عملية كبرى: خزنة المصرف (-45⚡ | مخاطرة عالية)", callback_data="do_heist:bank:" + u_str)],
            [InlineKeyboardButton(text="🏴 الانضمام/تأسيس عصابة الصقور", callback_data="join_gang:الصقور:" + u_str)],
            [InlineKeyboardButton(text="🏴 الانضمام/تأسيس عصابة الظل", callback_data="join_gang:الظل:" + u_str)],
            [InlineKeyboardButton(text="🔙 العودة للمدينة", callback_data="main_menu:" + u_str)],
        ]
    )
    await callback.message.edit_text(
        "🕶️ **الأزقة الخلفية والعصابات (نظام احتمالات خيالي)**\n"
        "⚠️ كل عملية تحمل نسبة فشل وتترك أثرًا أمنيًا يضعك على قائمة المطلوبين للشرطة!\n"
        "💡 *لسرقة محفظة لاعب آخر في المجموعة: رد (Reply) على رسالته بكلمة:* `سرقة`",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("join_gang:"))
async def cb_join_gang(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, city = res
    _, g_name, _ = callback.data.split(":")

    conn = get_db()
    conn.execute(
        "UPDATE players SET gang_name = ?, location = 'back_alleys' WHERE user_id = ? AND city_id = ?",
        ("عصابة " + g_name, player["user_id"], city["city_id"]),
    )
    conn.commit()
    conn.close()

    await callback.answer("🕶️ انضممت الآن إلى عصابة " + g_name + "!", show_alert=True)
    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("do_heist:"))
async def cb_do_heist(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, city = res
    _, target, _ = callback.data.split(":")

    if player["jail_until"] > int(time.time()):
        await callback.answer("🔒 أنت موقوف في السجن حاليًا!", show_alert=True)
        return

    energy_req = 25 if target == "store" else 45
    if player["energy"] < energy_req:
        await callback.answer("⚡ طاقتك غير كافية! تحتاج " + str(energy_req) + "% طاقة.", show_alert=True)
        return

    gang_bonus = 12 if player["gang_name"] else 0
    success_chance = (55 if target == "store" else 30) + gang_bonus
    roll = random.randint(1, 100)

    conn = get_db()
    if roll <= success_chance:
        loot = random.randint(400, 900) if target == "store" else random.randint(2000, 4500)
        wanted_add = 1 if target == "store" else 3
        conn.execute(
            "UPDATE players SET cash = cash + ?, energy = energy - ?, wanted_level = wanted_level + ?, location = 'back_alleys' WHERE user_id = ? AND city_id = ?",
            (loot, energy_req, wanted_add, player["user_id"], city["city_id"]),
        )
        conn.commit()
        conn.close()
        await callback.answer(
            "🕶️ نجحت العملية الافتراضية وحصلت على " + str(loot) + "$! لكن كاميرات المدينة رصدت أثرك (+" + str(wanted_add) + "⭐ مطلوب للشرطة).",
            show_alert=True,
        )
    else:
        fine = 250 if target == "store" else 800
        jail_sec = 180 if target == "store" else 360
        jail_until = int(time.time()) + jail_sec
        conn.execute(
            """
            UPDATE players
            SET cash = MAX(0, cash - ?), energy = energy - ?, wanted_level = 0, jail_until = ?, location = 'police'
            WHERE user_id = ? AND city_id = ?
            """,
            (fine, energy_req, jail_until, player["user_id"], city["city_id"]),
        )
        conn.commit()
        conn.close()
        await callback.answer(
            "🚓 انطلق جرس الإنذار وألقت دورية الشرطة القبض عليك! غرامة " + str(fine) + "$ وتوقيف لمدة " + str(jail_sec // 60) + " دقائق.",
            show_alert=True,
        )

    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("police_menu:"))
async def cb_police_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, city = res
    u_str = str(player["user_id"])

    conn = get_db()
    wanted_list = conn.execute(
        "SELECT user_id, username, wanted_level, location FROM players WHERE city_id = ? AND wanted_level > 0 ORDER BY wanted_level DESC LIMIT 10",
        (city["city_id"],),
    ).fetchall()
    conn.close()

    lines = ["🚓 **مركز قيادة الشرطة والمحكمة**\n"]
    buttons = []
    if wanted_list:
        lines.append("📋 **قائمة المطلوبين أمنيًا في المدينة:**")
        for w in wanted_list:
            loc_ar = LOCATIONS.get(w["location"], w["location"])
            lines.append("• **" + str(w["username"]) + "** — الخطورة: `" + str(w["wanted_level"]) + "⭐` — آخر رصد: " + loc_ar)
            if player["job"] == "police_officer" and w["user_id"] != player["user_id"]:
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text="🚔 ملاحقة وإلقاء قبض على " + str(w["username"]) + " (+350$ مكافأة)",
                            callback_data="arrest:" + str(w["user_id"]) + ":" + u_str,
                        )
                    ]
                )
    else:
        lines.append("✅ المدينة آمنة حاليًا ولا يوجد مطلوبون على القائمة.")

    if player["wanted_level"] > 0:
        bail_cost = str(player["wanted_level"] * 400)
        buttons.append(
            [InlineKeyboardButton(text="⚖️ تسليم نفسك ودفع غرامة تسوية (" + bail_cost + "$)", callback_data="pay_bail:" + u_str)]
        )

    buttons.append([InlineKeyboardButton(text="🔙 العودة للمدينة", callback_data="main_menu:" + u_str)])
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("arrest:"))
async def cb_arrest_wanted(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    officer, city = res
    _, target_uid_str, _ = callback.data.split(":")
    target_uid = int(target_uid_str)

    if officer["job"] != "police_officer":
        await callback.answer("⚠️ يجب أن تعمل كضابط شرطة لتنفيذ مهام القبض!", show_alert=True)
        return

    conn = get_db()
    suspect = conn.execute(
        "SELECT * FROM players WHERE user_id = ? AND city_id = ?",
        (target_uid, city["city_id"]),
    ).fetchone()

    if not suspect or suspect["wanted_level"] <= 0:
        conn.close()
        await callback.answer("هذا اللاعب لم يعد مطلوبًا للشرطة!", show_alert=True)
        return

    reward = suspect["wanted_level"] * 350
    fine = suspect["wanted_level"] * 300
    jail_until = int(time.time()) + 240

    conn.execute(
        "UPDATE players SET wanted_level = 0, jail_until = ?, cash = MAX(0, cash - ?), location = 'police' WHERE user_id = ? AND city_id = ?",
        (jail_until, fine, target_uid, city["city_id"]),
    )
    conn.execute(
        "UPDATE players SET cash = cash + ?, xp = xp + 40 WHERE user_id = ? AND city_id = ?",
        (reward, officer["user_id"], city["city_id"]),
    )
    conn.commit()
    conn.close()

    await callback.answer("🚔 ألقيت القبض على " + str(suspect["username"]) + " وحصلت على مكافأة " + str(reward) + "$!", show_alert=True)
    officer = get_or_create_player(officer["user_id"], city["city_id"], officer["username"])
    await callback.message.edit_text(
        format_player_dashboard(officer, city),
        reply_markup=build_main_city_keyboard(officer["user_id"]),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("pay_bail:"))
async def cb_pay_bail(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر!", show_alert=True)
        return
    player, city = res
    bail_cost = player["wanted_level"] * 400
    if player["cash"] < bail_cost:
        await callback.answer("💵 تحتاج إلى " + str(bail_cost) + "$ نقدًا لتسوية ملفك القضائي!", show_alert=True)
        return

    conn = get_db()
    conn.execute(
        "UPDATE players SET cash = cash - ?, wanted_level = 0, location = 'police' WHERE user_id = ? AND city_id = ?",
        (bail_cost, player["user_id"], city["city_id"]),
    )
    conn.execute("UPDATE cities SET treasury = treasury + ? WHERE city_id = ?", (bail_cost, city["city_id"]))
    conn.commit()
    conn.close()

    await callback.answer("✅ تمت تسوية وضعك القانوني وأصبح سجلك المدني نظيفًا!", show_alert=True)
    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    city = get_group_city(callback.message.chat.id)
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )


# ==========================================
# 13. أوامر التفاعل المباشر بالرد (Reply) بين أعضاء المجموعة
# ==========================================
@router.message(F.text.startswith("تحويل "))
async def msg_reply_transfer(message: Message) -> None:
    if not message.reply_to_message or not message.reply_to_message.from_user:
        return
    city = get_group_city(message.chat.id)
    if not city:
        return

    parts = message.text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.reply("⚠️ الصيغة الصحيحة بالرد على رسالة العضو: `تحويل 500`", parse_mode="Markdown")
        return

    amount = int(parts[1])
    if amount <= 0:
        return

    sender = get_or_create_player(message.from_user.id, city["city_id"], message.from_user.full_name or "مواطن")
    receiver_user = message.reply_to_message.from_user
    if receiver_user.is_bot or receiver_user.id == message.from_user.id:
        await message.reply("⚠️ لا يمكنك التحويل لنفسك أو لبوت!")
        return

    receiver = get_or_create_player(receiver_user.id, city["city_id"], receiver_user.full_name or "مواطن")

    if sender["cash"] < amount:
        await message.reply("💵 رصيدك النقدي في المحفظة غير كافٍ لإتمام التحويل!")
        return

    conn = get_db()
    conn.execute(
        "UPDATE players SET cash = cash - ? WHERE user_id = ? AND city_id = ?",
        (amount, sender["user_id"], city["city_id"]),
    )
    conn.execute(
        "UPDATE players SET cash = cash + ? WHERE user_id = ? AND city_id = ?",
        (amount, receiver["user_id"], city["city_id"]),
    )
    conn.commit()
    conn.close()

    await message.reply(
        "💸 تم تحويل `" + str(amount) + "$` من **" + str(sender["username"]) + "** إلى **" + str(receiver["username"]) + "** بنجاح!",
        parse_mode="Markdown",
    )


@router.message(F.text == "سرقة")
async def msg_reply_pickpocket(message: Message) -> None:
    if not message.reply_to_message or not message.reply_to_message.from_user:
        return
    city = get_group_city(message.chat.id)
    if not city:
        return

    thief = get_or_create_player(message.from_user.id, city["city_id"], message.from_user.full_name or "مواطن")
    victim_user = message.reply_to_message.from_user
    if victim_user.is_bot or victim_user.id == message.from_user.id:
        return

    if thief["jail_until"] > int(time.time()):
        await message.reply("🔒 أنت موقوف في السجن ولا يمكنك القيام بأي نشاط!")
        return
    if thief["energy"] < 15:
        await message.reply("⚡ طاقتك منخفضة جدًا!")
        return

    victim = get_or_create_player(victim_user.id, city["city_id"], victim_user.full_name or "مواطن")
    if victim["cash"] < 50:
        await message.reply("🤷‍♂️ محفظة **" + str(victim["username"]) + "** شبه فارغة (أقل من 50$)، وضع كل أمواله في المصرف!", parse_mode="Markdown")
        return

    conn = get_db()
    if random.randint(1, 100) <= 45:
        stolen = max(25, int(victim["cash"] * random.uniform(0.10, 0.25)))
        conn.execute(
            "UPDATE players SET cash = cash + ?, energy = energy - 15, wanted_level = wanted_level + 1 WHERE user_id = ? AND city_id = ?",
            (stolen, thief["user_id"], city["city_id"]),
        )
        conn.execute(
            "UPDATE players SET cash = cash - ? WHERE user_id = ? AND city_id = ?",
            (stolen, victim["user_id"], city["city_id"]),
        )
        conn.commit()
        conn.close()
        await message.reply(
            "🕶️ تمكن **" + str(thief["username"]) + "** من نشل `" + str(stolen) + "$` من محفظة **" + str(victim["username"]) + "**! "
            "(أصبح مطلوبًا للشرطة 🚨 — نصيحة: أودعوا أموالكم في المصرف لحمايتها).",
            parse_mode="Markdown",
        )
    else:
        conn.execute(
            "UPDATE players SET energy = energy - 15, wanted_level = wanted_level + 1 WHERE user_id = ? AND city_id = ?",
            (thief["user_id"], city["city_id"]),
        )
        conn.commit()
        conn.close()
        await message.reply(
            "🚨 انتبه **" + str(victim["username"]) + "** لمحاولة السرقة وفشلت خطة **" + str(thief["username"]) + "** وتم إبلاغ الشرطة!",
            parse_mode="Markdown",
        )


# ==========================================
# 14. محرك الزمن التلقائي للمدينة + خادم ويب لـ Render
# ==========================================
async def city_tick_engine() -> None:
    """دورة حياة المدينة كل 15 دقيقة: أرباح الشركات، فوائد المصرف، وتجديد الطاقة"""
    while True:
        await asyncio.sleep(900)
        try:
            conn = get_db()
            cur = conn.cursor()

            businesses = cur.execute("SELECT city_id, owner_id, biz_type FROM businesses").fetchall()
            for b in businesses:
                income = BUSINESS_TYPES.get(b["biz_type"], {}).get("hourly_income", 200)
                cur.execute(
                    "UPDATE players SET bank = bank + ? WHERE user_id = ? AND city_id = ?",
                    (income, b["owner_id"], b["city_id"]),
                )

            cur.execute(
                """
                UPDATE players
                SET energy = MIN(100, energy + CASE WHEN house IS NOT NULL THEN 20 ELSE 10 END),
                    bank = bank + CAST(bank * 0.01 AS INTEGER)
                """
            )

            conn.commit()
            conn.close()
            logger.info("تم تنفيذ دورة الزمن التلقائية للمدن بنجاح.")
        except Exception as exc:
            logger.error("خطأ في محرك الزمن: " + str(exc))


async def handle_health_check(request: web.Request) -> web.Response:
    return web.Response(text="Horizon City Bot is running 24/7!")


async def start_render_web_server() -> None:
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    app.router.add_get("/health", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    logger.info("🌐 خادم الويب المدمج لـ Render يعمل على المنفذ " + str(PORT))


# ==========================================
# 15. نقطة تشغيل البوت
# ==========================================
async def main() -> None:
    init_db()
    await start_render_web_server()

    if BOT_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
        logger.warning("⚠️ يرجى إضافة متغير البيئة BOT_TOKEN في إعدادات Render!")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    asyncio.create_task(city_tick_engine())

    logger.info("🚀 بوت مدينة الأفق يعمل الآن...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
