# -*- coding: utf-8 -*-
"""
بوت مدينة الأفق (Horizon City Bot) - لعبة محاكاة تفاعلية في مجموعات تيليجرام
يعمل على Render (خدمة ويب) مع GitHub.

متغيرات البيئة المطلوبة:
  BOT_TOKEN  : توكن البوت من BotFather (إلزامي، لا تضعه في الكود أبداً)
  DB_PATH    : مسار قاعدة البيانات (اختياري، يفضّل مسار على قرص دائم مثل /data/horizon_city.db)
  PORT       : يضبطه Render تلقائياً
"""

import asyncio
import html
import logging
import os
import random
import sqlite3
import time
from typing import Any, Dict, Optional, Tuple

from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# ==========================================
# 1. الإعدادات الأساسية
# ==========================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
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
    "market": "🛒 الحي التجاري",
    "education": "🎓 الجامعة والمجمع الطبي",
    "industrial": "🏭 المنطقة الصناعية",
    "police": "🚓 مركز الشرطة والمحكمة",
    "back_alleys": "🕶️ الأزقة الخلفية",
}

DEGREES: Dict[str, Dict[str, Any]] = {
    "management": {"name": "📜 بكالوريوس إدارة واقتصاد", "cost": 1500, "energy": 30},
    "medicine": {"name": "🩺 شهادة الطب العام", "cost": 2500, "energy": 40},
    "law_security": {"name": "⚖️ دبلوم القانون والعلوم الأمنية", "cost": 1800, "energy": 35},
    "engineering": {"name": "⚙️ بكالوريوس الهندسة الصناعية", "cost": 2000, "energy": 35},
}

JOBS: Dict[str, Dict[str, Any]] = {
    "freelancer": {"name": "👷 عامل حر", "salary": 250, "energy": 20, "req_degree": None, "clean_record": False},
    "banker": {"name": "🏦 محاسب مصرفي", "salary": 650, "energy": 25, "req_degree": "management", "clean_record": True},
    "doctor": {"name": "👨‍⚕️ طبيب في المستشفى", "salary": 900, "energy": 30, "req_degree": "medicine", "clean_record": True},
    "police_officer": {"name": "👮 ضابط شرطة", "salary": 750, "energy": 25, "req_degree": "law_security", "clean_record": True},
    "engineer": {"name": "👷‍♂️ مهندس صناعي", "salary": 800, "energy": 25, "req_degree": "engineering", "clean_record": True},
}

HOUSES: Dict[str, Dict[str, Any]] = {
    "studio": {"name": "🛏️ شقة استوديو", "base_price": 3000, "energy_regen": 15},
    "villa": {"name": "🏡 فيلا عائلية", "base_price": 12000, "energy_regen": 30},
    "palace": {"name": "🏰 قصر فاخر", "base_price": 50000, "energy_regen": 50},
}

VEHICLES: Dict[str, Dict[str, Any]] = {
    "bike": {"name": "🏍️ دراجة نارية", "base_price": 2000, "travel_energy_save": 3},
    "sedan": {"name": "🚗 سيارة سيدان", "base_price": 8500, "travel_energy_save": 6},
    "sports_car": {"name": "🏎️ سيارة رياضية", "base_price": 35000, "travel_energy_save": 9},
}

BUSINESS_TYPES: Dict[str, Dict[str, Any]] = {
    "restaurant": {"name": "🍔 مطعم وجبات سريعة", "base_price": 10000, "hourly_income": 350},
    "supermarket": {"name": "🛒 سوبرماركت مركزي", "base_price": 22000, "hourly_income": 800},
    "car_agency": {"name": "🚘 وكالة سيارات", "base_price": 60000, "hourly_income": 2400},
    "factory": {"name": "🏭 مصنع إنتاج", "base_price": 95000, "hourly_income": 4000},
}


# ==========================================
# 3. قاعدة البيانات (SQLite)
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
            "INSERT INTO cities (city_id, name, is_global, treasury, price_index, created_at) "
            "VALUES (1, 'مدينة الأفق العالمية', 1, 500000, 1.0, ?)",
            (int(time.time()),),
        )

    cur.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            chat_id INTEGER PRIMARY KEY,
            city_id INTEGER NOT NULL,
            group_title TEXT,
            FOREIGN KEY (city_id) REFERENCES cities (city_id)
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
            hungry INTEGER DEFAULT 100,
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

    # ترحيل البيانات من الجدول القديم (الاسم الخاطئ) إن وُجد
    old = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='businesss'"
    ).fetchone()
    if old:
        cur.execute(
            "INSERT INTO businesses (city_id, owner_id, biz_type, custom_name, created_at) "
            "SELECT city_id, owner_id, biz_type, custom_name, created_at FROM businesss"
        )
        cur.execute("DROP TABLE businesss")

    # تصحيح الموقع الافتراضي القديم
    cur.execute("UPDATE players SET location = 'downtown' WHERE location = 'وسط المدينة'")

    conn.commit()
    conn.close()


def run_update(sql: str, params: tuple = ()) -> bool:
    """ينفذ UPDATE واحداً ويعيد True إن تأثر صف فعلاً (عملية ذرية)."""
    conn = get_db()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ==========================================
# 4. دوال مساعدة للمدينة واللاعبين
# ==========================================
def esc(text: Any) -> str:
    return html.escape(str(text), quote=False)


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
        # إن كانت للمجموعة مدينة خاصة سابقة نعيد استخدامها بدل إنشاء مدينة جديدة
        existing = cur.execute(
            "SELECT city_id, name FROM cities WHERE owner_chat_id = ? AND is_global = 0",
            (chat_id,),
        ).fetchone()
        if existing:
            city_id, city_name = existing["city_id"], existing["name"]
        else:
            city_name = f"مدينة {title[:25]}"
            cur.execute(
                "INSERT INTO cities (name, is_global, owner_chat_id, treasury, price_index, created_at) "
                "VALUES (?, 0, ?, 100000, 1.0, ?)",
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
    cur.execute(
        "INSERT OR IGNORE INTO players (user_id, city_id, username) VALUES (?, ?, ?)",
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


async def safe_edit(message: Message, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None) -> None:
    """تعديل الرسالة مع تجاهل خطأ 'message is not modified'."""
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise


# ==========================================
# 5. لوحات المفاتيح والبطاقة الرئيسية
# ==========================================
def back_button(uid: int) -> list:
    return [InlineKeyboardButton(text="🔙 العودة للمدينة", callback_data=f"main_menu:{uid}")]


def build_setup_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌐 الانضمام للمدينة العالمية الموحدة", callback_data="setup_mode:global")],
            [InlineKeyboardButton(text="🏙️ إنشاء مدينة مستقلة خاصة بالمجموعة", callback_data="setup_mode:private")],
        ]
    )


def build_main_city_keyboard(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗺️ التنقل بين المناطق", callback_data=f"nav_menu:{uid}"),
                InlineKeyboardButton(text="👥 المتواجدون بموقعي", callback_data=f"nearby:{uid}"),
            ],
            [
                InlineKeyboardButton(text="💼 العمل والوظائف", callback_data=f"jobs_menu:{uid}"),
                InlineKeyboardButton(text="🎓 الجامعة", callback_data=f"edu_menu:{uid}"),
            ],
            [
                InlineKeyboardButton(text="🏠 العقارات والسيارات", callback_data=f"prop_menu:{uid}"),
                InlineKeyboardButton(text="🏢 تأسيس المشاريع", callback_data=f"biz_menu:{uid}"),
            ],
            [
                InlineKeyboardButton(text="🛒 المطعم والسوق", callback_data=f"market_menu:{uid}"),
                InlineKeyboardButton(text="🏦 المصرف المركزي", callback_data=f"bank_menu:{uid}"),
            ],
            [
                InlineKeyboardButton(text="🚓 الشرطة والمطلوبون", callback_data=f"police_menu:{uid}"),
                InlineKeyboardButton(text="🕶️ العصابات والسرقة", callback_data=f"crime_menu:{uid}"),
            ],
            [InlineKeyboardButton(text="🔄 تحديث البطاقة", callback_data=f"main_menu:{uid}")],
        ]
    )


def format_player_dashboard(player: sqlite3.Row, city: sqlite3.Row) -> str:
    loc_name = LOCATIONS.get(player["location"], LOCATIONS["downtown"])
    job_name = JOBS.get(player["job"], {}).get("name", "بدون عمل")
    degree_name = DEGREES[player["degree"]]["name"] if player["degree"] in DEGREES else "لا يوجد"
    house_name = HOUSES[player["house"]]["name"] if player["house"] in HOUSES else "بلا مسكن"
    vehicle_name = VEHICLES[player["vehicle"]]["name"] if player["vehicle"] in VEHICLES else "المشي على الأقدام"
    gang_text = esc(player["gang_name"]) if player["gang_name"] else "مستقل"

    now = int(time.time())
    if player["jail_until"] > now:
        remaining_min = max(1, (player["jail_until"] - now + 59) // 60)
        jail_status = f"\n🔒 <b>الحالة الأمنية:</b> موقوف في السجن ({remaining_min} دقيقة متبقية)"
    elif player["wanted_level"] > 0:
        jail_status = f"\n🚨 <b>الحالة الأمنية:</b> مطلوب للشرطة (الخطورة: {player['wanted_level']} ⭐)"
    else:
        jail_status = "\n✨ <b>الحالة الأمنية:</b> سجل نظيف"

    mode_label = "🌐 عالمية مشتركة" if city["is_global"] else "🏙️ خاصة بالمجموعة"

    return (
        f"🏙️ <b>{esc(city['city_name'])}</b> ({mode_label})\n"
        f"📊 مؤشر الأسعار: <code>{int(city['price_index'] * 100)}%</code> | "
        f"خزينة المدينة: <code>{city['treasury']:,}$</code>\n\n"
        f"👤 <b>المواطن:</b> {esc(player['username'])} (المستوى {player['level']} ⭐)\n"
        f"📍 <b>الموقع:</b> {loc_name}\n"
        f"❤️ الصحة: <code>{player['health']}%</code> | ⚡ الطاقة: <code>{player['energy']}%</code> | "
        f"🍔 الشبع: <code>{player['hungry']}%</code>\n"
        f"💵 النقد في المحفظة: <code>{player['cash']:,}$</code> | 🏦 رصيد البنك: <code>{player['bank']:,}$</code>\n"
        f"💼 الوظيفة: {job_name} | 🎓 الشهادة: {degree_name}\n"
        f"🏠 المسكن: {house_name} | 🚗 المركبة: {vehicle_name}\n"
        f"🕶️ الانتماء: {gang_text}"
        f"{jail_status}"
    )


async def show_dashboard(callback: CallbackQuery, user_id: int) -> None:
    """يعيد قراءة اللاعب والمدينة من قاعدة البيانات ويعرض البطاقة."""
    city = get_group_city(callback.message.chat.id)
    if not city:
        return
    player = get_or_create_player(user_id, city["city_id"], callback.from_user.full_name or "مواطن")
    await safe_edit(callback.message, format_player_dashboard(player, city), build_main_city_keyboard(user_id))


# ==========================================
# 6. أوامر البداية والإعداد
# ==========================================
# ملاحظة: أوامر تيليجرام (/command) تقبل أحرفاً لاتينية فقط، لذلك نوفر
# أوامر لاتينية + كلمات عربية عادية (بدون /) لنفس الوظيفة.
@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    if message.chat.type == "private":
        await message.answer(
            "👋 أهلاً بك في <b>بوت مدينة الأفق التفاعلية</b>!\n\n"
            "لبدء اللعب أضف البوت إلى مجموعتك، ثم أرسل <code>/setup</code> "
            "ليختار مشرف المجموعة نظام المدينة، وبعدها يكتب الأعضاء <code>/city</code> "
            "أو كلمة <code>المدينة</code> لفتح بطاقة حياتهم."
        )
        return
    await cmd_setup(message)


@router.message(Command("setup"))
@router.message(F.text.in_({"اعداد المدينة", "اعداد_المدينة", "إعداد المدينة"}))
async def cmd_setup(message: Message) -> None:
    if message.chat.type == "private":
        await message.answer("⚠️ هذا الأمر يعمل داخل المجموعات فقط.")
        return
    await message.answer(
        "⚙️ <b>إعداد نظام المدينة في المجموعة</b>\n\n"
        "يختار مشرف المجموعة النظام الذي سيعيش فيه الأعضاء:\n"
        "1️⃣ <b>المدينة العالمية الموحدة:</b> تشترك المجموعة مع بقية المجموعات في مدينة واحدة.\n"
        "2️⃣ <b>مدينة مستقلة:</b> مدينة كاملة خاصة بأعضاء هذه المجموعة فقط.",
        reply_markup=build_setup_keyboard(),
    )


@router.callback_query(F.data.startswith("setup_mode:"))
async def cb_setup_mode(callback: CallbackQuery, bot: Bot) -> None:
    member = await bot.get_chat_member(callback.message.chat.id, callback.from_user.id)
    if member.status not in ("administrator", "creator"):
        await callback.answer("❌ هذا الخيار مخصص لمشرفي المجموعة فقط!", show_alert=True)
        return

    mode = callback.data.split(":")[1]
    title = callback.message.chat.title or "المجموعة"
    _, city_name = set_group_city_mode(callback.message.chat.id, title, mode)

    mode_desc = (
        "🌐 تم ربط المجموعة بـ <b>المدينة العالمية الموحدة</b>!"
        if mode == "global"
        else f"🏙️ تم تفعيل <b>{esc(city_name)}</b> كمدينة مستقلة خاصة بمجموعتكم!"
    )
    await safe_edit(
        callback.message,
        f"{mode_desc}\n\n"
        "🏛️ أصبحت جميع المرافق متاحة: المنازل، السوق، المطاعم، الجامعة، المشاريع، المصرف، الشرطة.\n"
        "👉 اكتبوا <code>/city</code> أو كلمة <code>المدينة</code> لفتح بطاقة حياتكم.",
    )
    await callback.answer("تم حفظ إعدادات المدينة!")


@router.message(Command("city"))
@router.message(F.text.in_({"المدينة", "حياتي"}))
async def cmd_open_city(message: Message) -> None:
    if message.chat.type == "private":
        await message.answer("⚠️ يرجى استخدام هذا الأمر داخل مجموعة تيليجرام مفعّلة.")
        return

    city = get_group_city(message.chat.id)
    if not city:
        await message.answer(
            "⚠️ لم يتم اختيار نظام المدينة لهذه المجموعة بعد!\n"
            "يرجى من مشرف المجموعة اختيار النظام:",
            reply_markup=build_setup_keyboard(),
        )
        return

    player = get_or_create_player(message.from_user.id, city["city_id"], message.from_user.full_name or "مواطن")
    await message.answer(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(message.from_user.id),
    )


# ==========================================
# 7. التحقق من ملكية اللوحة
# ==========================================
NOT_YOURS = "⚠️ هذه اللوحة لاعب آخر! اكتب /city لفتح لوحتك."


def check_owner_and_city(callback: CallbackQuery) -> Optional[Tuple[sqlite3.Row, sqlite3.Row]]:
    try:
        owner_id = int(callback.data.split(":")[-1])
    except ValueError:
        return None
    if callback.from_user.id != owner_id:
        return None
    city = get_group_city(callback.message.chat.id)
    if not city:
        return None
    player = get_or_create_player(callback.from_user.id, city["city_id"], callback.from_user.full_name or "مواطن")
    return player, city


@router.callback_query(F.data.startswith("main_menu:"))
async def cb_main_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, city = res
    await safe_edit(callback.message, format_player_dashboard(player, city), build_main_city_keyboard(player["user_id"]))
    await callback.answer()


# ==========================================
# 8. التنقل بين المناطق
# ==========================================
@router.callback_query(F.data.startswith("nav_menu:"))
async def cb_nav_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, _ = res
    uid = player["user_id"]

    if player["jail_until"] > int(time.time()):
        await callback.answer("🔒 لا يمكنك التنقل أثناء فترة التوقيف في السجن!", show_alert=True)
        return

    buttons = []
    for loc_key, loc_title in LOCATIONS.items():
        prefix = "📍 " if player["location"] == loc_key else "🚶 "
        buttons.append([InlineKeyboardButton(text=f"{prefix}{loc_title}", callback_data=f"move:{loc_key}:{uid}")])
    buttons.append(back_button(uid))

    await safe_edit(
        callback.message,
        "🗺️ <b>خريطة مناطق المدينة</b>\nاختر المنطقة التي تريد الانتقال إليها:",
        InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("move:"))
async def cb_move_location(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, city = res
    _, target_loc, _ = callback.data.split(":")

    if target_loc not in LOCATIONS:
        await callback.answer("منطقة غير معروفة!", show_alert=True)
        return
    if player["jail_until"] > int(time.time()):
        await callback.answer("🔒 لا يمكنك التنقل أثناء السجن!", show_alert=True)
        return
    if player["location"] == target_loc:
        await callback.answer("أنت متواجد بالفعل في هذه المنطقة!")
        return

    save = VEHICLES[player["vehicle"]]["travel_energy_save"] if player["vehicle"] in VEHICLES else 0
    energy_cost = max(2, 10 - save)

    ok = run_update(
        "UPDATE players SET location = ?, energy = energy - ? "
        "WHERE user_id = ? AND city_id = ? AND energy >= ?",
        (target_loc, energy_cost, player["user_id"], city["city_id"], energy_cost),
    )
    if not ok:
        await callback.answer(f"⚡ طاقتك غير كافية للتنقل! تحتاج {energy_cost}%.", show_alert=True)
        return

    await callback.answer(f"✔️ وصلت إلى {LOCATIONS[target_loc]} (-{energy_cost}% طاقة)")
    await show_dashboard(callback, player["user_id"])


@router.callback_query(F.data.startswith("nearby:"))
async def cb_nearby_players(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, city = res
    conn = get_db()
    others = conn.execute(
        "SELECT username, job, wanted_level FROM players WHERE city_id = ? AND location = ? LIMIT 15",
        (city["city_id"], player["location"]),
    ).fetchall()
    conn.close()

    loc_title = LOCATIONS.get(player["location"], player["location"])
    lines = [f"👥 <b>المتواجدون حالياً في {loc_title}:</b>\n"]
    for row in others:
        job_title = JOBS.get(row["job"], {}).get("name", "عامل حر")
        wanted_tag = f" 🚨 (مطلوب {row['wanted_level']}⭐)" if row["wanted_level"] > 0 else ""
        lines.append(f"• <b>{esc(row['username'])}</b> — {job_title}{wanted_tag}")

    kb = InlineKeyboardMarkup(inline_keyboard=[back_button(player["user_id"])])
    await safe_edit(callback.message, "\n".join(lines), kb)
    await callback.answer()


# ==========================================
# 9. التعليم والوظائف
# ==========================================
@router.callback_query(F.data.startswith("edu_menu:"))
async def cb_edu_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, _ = res
    uid = player["user_id"]

    buttons = [
        [InlineKeyboardButton(
            text=f"{deg['name']} ({deg['cost']}$ | -{deg['energy']}⚡)",
            callback_data=f"study:{deg_key}:{uid}",
        )]
        for deg_key, deg in DEGREES.items()
    ]
    buttons.append(back_button(uid))

    await safe_edit(
        callback.message,
        "🎓 <b>الجامعة المركزية</b>\nاختر التخصص الذي ترغب بدراسته لفتح الوظائف العليا:",
        InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("study:"))
async def cb_study_degree(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, city = res
    _, deg_key, _ = callback.data.split(":")
    deg = DEGREES.get(deg_key)
    if not deg:
        await callback.answer("تخصص غير معروف!", show_alert=True)
        return

    ok = run_update(
        "UPDATE players SET cash = cash - ?, energy = energy - ?, degree = ?, xp = xp + 50, location = 'education' "
        "WHERE user_id = ? AND city_id = ? AND cash >= ? AND energy >= ?",
        (deg["cost"], deg["energy"], deg_key, player["user_id"], city["city_id"], deg["cost"], deg["energy"]),
    )
    if not ok:
        await callback.answer(
            f"❌ تحتاج إلى {deg['cost']}$ نقداً و{deg['energy']}% طاقة للدراسة.", show_alert=True
        )
        return

    run_update("UPDATE cities SET treasury = treasury + ? WHERE city_id = ?", (deg["cost"], city["city_id"]))
    await callback.answer(f"🎉 مبارك! حصلت على {deg['name']}!", show_alert=True)
    await show_dashboard(callback, player["user_id"])


@router.callback_query(F.data.startswith("jobs_menu:"))
async def cb_jobs_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, _ = res
    uid = player["user_id"]

    buttons = [[InlineKeyboardButton(text="💰 إنجاز نوبة عمل واستلام الراتب", callback_data=f"work_shift:{uid}")]]
    for job_key, job in JOBS.items():
        buttons.append([InlineKeyboardButton(
            text=f"تقديم: {job['name']} ({job['salary']}$)",
            callback_data=f"apply_job:{job_key}:{uid}",
        )])
    buttons.append(back_button(uid))

    await safe_edit(
        callback.message,
        "💼 <b>مكتب التوظيف</b>\nأنجز نوبة عمل في وظيفتك الحالية أو قدّم على وظيفة جديدة:",
        InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("apply_job:"))
async def cb_apply_job(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, city = res
    _, job_key, _ = callback.data.split(":")
    job = JOBS.get(job_key)
    if not job:
        await callback.answer("وظيفة غير معروفة!", show_alert=True)
        return

    if job["req_degree"] and player["degree"] != job["req_degree"]:
        req_name = DEGREES[job["req_degree"]]["name"]
        await callback.answer(f"🎓 هذه الوظيفة تتطلب شهادة: {req_name}", show_alert=True)
        return
    if job["clean_record"] and player["wanted_level"] > 0:
        await callback.answer("🚨 لا يمكن قبولك في وظيفة رسمية وأنت مطلوب للشرطة!", show_alert=True)
        return

    run_update(
        "UPDATE players SET job = ? WHERE user_id = ? AND city_id = ?",
        (job_key, player["user_id"], city["city_id"]),
    )
    await callback.answer(f"✅ تم تعيينك في الوظيفة: {job['name']}!", show_alert=True)
    await show_dashboard(callback, player["user_id"])


@router.callback_query(F.data.startswith("work_shift:"))
async def cb_work_shift(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, city = res
    now = int(time.time())

    if player["jail_until"] > now:
        await callback.answer("🔒 لا يمكنك العمل أثناء وجودك في السجن!", show_alert=True)
        return

    job = JOBS.get(player["job"], JOBS["freelancer"])
    salary = int(job["salary"] * city["price_index"])

    ok = run_update(
        """
        UPDATE players
        SET cash = cash + ?, energy = energy - ?, hungry = MAX(0, hungry - 15),
            xp = xp + 25, level = 1 + ((xp + 25) / 100), last_work_ts = ?
        WHERE user_id = ? AND city_id = ? AND energy >= ? AND hungry >= 15 AND jail_until <= ?
        """,
        (salary, job["energy"], now, player["user_id"], city["city_id"], job["energy"], now),
    )
    if not ok:
        await callback.answer("⚡ طاقتك أو شبعك منخفض! تناول طعاماً أو استرح.", show_alert=True)
        return

    adjust_city_demand(city["city_id"], -0.01)
    await callback.answer(f"💵 عملت كـ {job['name']} وحصلت على {salary}$ (+25 خبرة)!", show_alert=True)
    await show_dashboard(callback, player["user_id"])


# ==========================================
# 10. السوق والمصرف
# ==========================================
@router.callback_query(F.data.startswith("market_menu:"))
async def cb_market_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, city = res
    uid = player["user_id"]
    idx = city["price_index"]

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🍔 وجبة (+40 شبع، +25 طاقة) — {int(80 * idx)}$", callback_data=f"buy_item:meal:{uid}")],
            [InlineKeyboardButton(text=f"💊 حقيبة إسعافية (+50 صحة) — {int(150 * idx)}$", callback_data=f"buy_item:med:{uid}")],
            [InlineKeyboardButton(text=f"🛌 استراحة (+طاقة) — {int(100 * idx)}$", callback_data=f"buy_item:rest:{uid}")],
            back_button(uid),
        ]
    )
    await safe_edit(
        callback.message,
        f"🛒 <b>سوق المدينة والمستشفى</b>\nالأسعار حسب العرض والطلب (المؤشر الحالي <code>{int(idx * 100)}%</code>):",
        kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_item:"))
async def cb_buy_item(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, city = res
    _, item_type, _ = callback.data.split(":")
    idx = city["price_index"]
    uid, cid = player["user_id"], city["city_id"]

    if item_type == "meal":
        cost = int(80 * idx)
        ok = run_update(
            "UPDATE players SET cash = cash - ?, hungry = MIN(100, hungry + 40), energy = MIN(100, energy + 25), "
            "location = 'market' WHERE user_id = ? AND city_id = ? AND cash >= ?",
            (cost, uid, cid, cost),
        )
        msg = "🍔 تناولت الوجبة واستعدت نشاطك!"
    elif item_type == "med":
        cost = int(150 * idx)
        ok = run_update(
            "UPDATE players SET cash = cash - ?, health = MIN(100, health + 50), location = 'education' "
            "WHERE user_id = ? AND city_id = ? AND cash >= ?",
            (cost, uid, cid, cost),
        )
        msg = "💊 تلقيت العلاج واستعدت صحتك!"
    elif item_type == "rest":
        cost = 0 if player["house"] else int(100 * idx)
        regen = (HOUSES[player["house"]]["energy_regen"] if player["house"] in HOUSES else 35) + 25
        ok = run_update(
            "UPDATE players SET cash = cash - ?, energy = MIN(100, energy + ?), location = 'residential' "
            "WHERE user_id = ? AND city_id = ? AND cash >= ?",
            (cost, regen, uid, cid, cost),
        )
        msg = "🛌 استرحت واستعدت طاقتك!"
    else:
        await callback.answer("عنصر غير معروف!", show_alert=True)
        return

    if not ok:
        await callback.answer("💵 رصيدك النقدي لا يكفي!", show_alert=True)
        return

    adjust_city_demand(cid, 0.02)
    await callback.answer(msg, show_alert=True)
    await show_dashboard(callback, uid)


@router.callback_query(F.data.startswith("bank_menu:"))
async def cb_bank_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, _ = res
    uid = player["user_id"]

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📥 إيداع كل النقد", callback_data=f"bank_op:dep_all:{uid}"),
                InlineKeyboardButton(text="📤 سحب 1,000$", callback_data=f"bank_op:wit_1000:{uid}"),
            ],
            [InlineKeyboardButton(text="📤 سحب كل الرصيد", callback_data=f"bank_op:wit_all:{uid}")],
            back_button(uid),
        ]
    )
    await safe_edit(
        callback.message,
        f"🏦 <b>المصرف المركزي</b>\n"
        f"💵 النقد في محفظتك: <code>{player['cash']:,}$</code> (معرض للسرقة)\n"
        f"🏦 رصيدك في البنك: <code>{player['bank']:,}$</code> (آمن ويحقق عائداً)\n\n"
        f"💡 <i>لتحويل مال لصديق: رد على رسالته بـ</i> <code>تحويل 500</code>",
        kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bank_op:"))
async def cb_bank_op(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, city = res
    _, op, _ = callback.data.split(":")
    uid, cid = player["user_id"], city["city_id"]

    if op == "dep_all":
        ok = run_update(
            "UPDATE players SET bank = bank + cash, cash = 0, location = 'downtown' "
            "WHERE user_id = ? AND city_id = ? AND cash > 0",
            (uid, cid),
        )
        msg = "✅ تم إيداع أموالك في حسابك البنكي!" if ok else "ليس لديك نقد للإيداع!"
    elif op == "wit_1000":
        ok = run_update(
            "UPDATE players SET cash = cash + MIN(1000, bank), bank = bank - MIN(1000, bank), location = 'downtown' "
            "WHERE user_id = ? AND city_id = ? AND bank > 0",
            (uid, cid),
        )
        msg = "✅ تم السحب إلى محفظتك." if ok else "رصيدك البنكي فارغ!"
    elif op == "wit_all":
        ok = run_update(
            "UPDATE players SET cash = cash + bank, bank = 0, location = 'downtown' "
            "WHERE user_id = ? AND city_id = ? AND bank > 0",
            (uid, cid),
        )
        msg = "✅ تم سحب كامل الرصيد إلى محفظتك." if ok else "رصيدك البنكي فارغ!"
    else:
        await callback.answer("عملية غير معروفة!", show_alert=True)
        return

    await callback.answer(msg, show_alert=True)
    await show_dashboard(callback, uid)


# ==========================================
# 11. العقارات والسيارات والمشاريع
# ==========================================
@router.callback_query(F.data.startswith("prop_menu:"))
async def cb_prop_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, city = res
    uid = player["user_id"]
    idx = city["price_index"]

    buttons = []
    for h_key, h in HOUSES.items():
        buttons.append([InlineKeyboardButton(
            text=f"شراء {h['name']} ({int(h['base_price'] * idx):,}$)", callback_data=f"buy_house:{h_key}:{uid}")])
    for v_key, v in VEHICLES.items():
        buttons.append([InlineKeyboardButton(
            text=f"شراء {v['name']} ({int(v['base_price'] * idx):,}$)", callback_data=f"buy_veh:{v_key}:{uid}")])
    buttons.append(back_button(uid))

    await safe_edit(
        callback.message,
        "🏠 <b>سوق العقارات ومعرض السيارات</b>\nامتلاك منزل يمنحك استعادة أسرع للطاقة، والمركبة توفر طاقة التنقل:",
        InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_house:"))
async def cb_buy_house(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, city = res
    _, h_key, _ = callback.data.split(":")
    house = HOUSES.get(h_key)
    if not house:
        await callback.answer("عقار غير معروف!", show_alert=True)
        return
    price = int(house["base_price"] * city["price_index"])

    ok = run_update(
        "UPDATE players SET cash = cash - ?, house = ?, location = 'residential' "
        "WHERE user_id = ? AND city_id = ? AND cash >= ?",
        (price, h_key, player["user_id"], city["city_id"], price),
    )
    if not ok:
        await callback.answer(f"💵 تحتاج إلى {price:,}$ نقداً لشراء {house['name']}!", show_alert=True)
        return

    run_update("UPDATE cities SET treasury = treasury + ? WHERE city_id = ?", (price, city["city_id"]))
    adjust_city_demand(city["city_id"], 0.03)
    await callback.answer(f"🏡 مبارك! أصبحت مالكاً لـ {house['name']}!", show_alert=True)
    await show_dashboard(callback, player["user_id"])


@router.callback_query(F.data.startswith("buy_veh:"))
async def cb_buy_veh(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, city = res
    _, v_key, _ = callback.data.split(":")
    veh = VEHICLES.get(v_key)
    if not veh:
        await callback.answer("مركبة غير معروفة!", show_alert=True)
        return
    price = int(veh["base_price"] * city["price_index"])

    ok = run_update(
        "UPDATE players SET cash = cash - ?, vehicle = ?, location = 'market' "
        "WHERE user_id = ? AND city_id = ? AND cash >= ?",
        (price, v_key, player["user_id"], city["city_id"], price),
    )
    if not ok:
        await callback.answer(f"💵 تحتاج إلى {price:,}$ نقداً لشراء {veh['name']}!", show_alert=True)
        return

    run_update("UPDATE cities SET treasury = treasury + ? WHERE city_id = ?", (price, city["city_id"]))
    adjust_city_demand(city["city_id"], 0.02)
    await callback.answer(f"🚗 مبارك! اشتريت {veh['name']}!", show_alert=True)
    await show_dashboard(callback, player["user_id"])


@router.callback_query(F.data.startswith("biz_menu:"))
async def cb_biz_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, city = res
    uid = player["user_id"]
    idx = city["price_index"]

    conn = get_db()
    owned = conn.execute(
        "SELECT custom_name, biz_type FROM businesses WHERE city_id = ? AND owner_id = ?",
        (city["city_id"], uid),
    ).fetchall()
    conn.close()

    owned_lines = [
        f"• {esc(r['custom_name'])} (+{BUSINESS_TYPES[r['biz_type']]['hourly_income']}$ كل ساعة)"
        for r in owned if r["biz_type"] in BUSINESS_TYPES
    ]
    owned_text = "\n".join(owned_lines) if owned_lines else "لا تملك مشاريع تجارية بعد."

    buttons = []
    for b_key, b in BUSINESS_TYPES.items():
        price = int(b["base_price"] * idx)
        buttons.append([InlineKeyboardButton(
            text=f"تأسيس {b['name']} ({price:,}$ | دخل: +{b['hourly_income']}$)",
            callback_data=f"buy_biz:{b_key}:{uid}",
        )])
    buttons.append(back_button(uid))

    await safe_edit(
        callback.message,
        f"🏢 <b>غرفة التجارة والمشاريع</b>\nالمشاريع تدر أرباحاً تلقائية تُضاف إلى رصيدك البنكي:\n\n"
        f"📋 <b>مشاريعك:</b>\n{owned_text}",
        InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_biz:"))
async def cb_buy_biz(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, city = res
    _, b_key, _ = callback.data.split(":")
    biz = BUSINESS_TYPES.get(b_key)
    if not biz:
        await callback.answer("مشروع غير معروف!", show_alert=True)
        return
    price = int(biz["base_price"] * city["price_index"])

    ok = run_update(
        "UPDATE players SET cash = cash - ?, location = 'industrial' "
        "WHERE user_id = ? AND city_id = ? AND cash >= ?",
        (price, player["user_id"], city["city_id"], price),
    )
    if not ok:
        await callback.answer(f"💵 تحتاج إلى {price:,}$ نقداً لتأسيس {biz['name']}!", show_alert=True)
        return

    conn = get_db()
    conn.execute(
        "INSERT INTO businesses (city_id, owner_id, biz_type, custom_name, created_at) VALUES (?, ?, ?, ?, ?)",
        (city["city_id"], player["user_id"], b_key, f"{biz['name']} ({player['username']})", int(time.time())),
    )
    conn.execute("UPDATE cities SET treasury = treasury + ? WHERE city_id = ?", (price, city["city_id"]))
    conn.commit()
    conn.close()

    await callback.answer(f"🎉 مبارك! أسست مشروع {biz['name']}!", show_alert=True)
    await show_dashboard(callback, player["user_id"])


# ==========================================
# 12. الشرطة والعصابات والسرقة
# ==========================================
@router.callback_query(F.data.startswith("crime_menu:"))
async def cb_crime_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, _ = res
    uid = player["user_id"]

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🕶️ سطو على متجر (-25⚡)", callback_data=f"do_heist:store:{uid}")],
            [InlineKeyboardButton(text="🏦 خزنة المصرف (-45⚡)", callback_data=f"do_heist:bank:{uid}")],
            [InlineKeyboardButton(text="🏴 عصابة الصقور", callback_data=f"join_gang:الصقور:{uid}")],
            [InlineKeyboardButton(text="🏴 عصابة الظل", callback_data=f"join_gang:الظل:{uid}")],
            back_button(uid),
        ]
    )
    await safe_edit(
        callback.message,
        "🕶️ <b>الأزقة الخلفية والعصابات</b>\n"
        "⚠️ عمليات السطو قد تضعك على قائمة المطلوبين!\n"
        "💡 <i>لسرقة لاعب: رد على رسالته بكلمة</i> <code>سرقة</code>",
        kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("join_gang:"))
async def cb_join_gang(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, city = res
    _, g_name, _ = callback.data.split(":")
    if g_name not in ("الصقور", "الظل"):
        await callback.answer("عصابة غير معروفة!", show_alert=True)
        return

    run_update(
        "UPDATE players SET gang_name = ?, location = 'back_alleys' WHERE user_id = ? AND city_id = ?",
        (f"عصابة {g_name}", player["user_id"], city["city_id"]),
    )
    await callback.answer(f"🕶️ انضممت إلى عصابة {g_name}!", show_alert=True)
    await show_dashboard(callback, player["user_id"])


@router.callback_query(F.data.startswith("do_heist:"))
async def cb_do_heist(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, city = res
    _, target, _ = callback.data.split(":")
    now = int(time.time())
    uid, cid = player["user_id"], city["city_id"]

    if target not in ("store", "bank"):
        await callback.answer("هدف غير معروف!", show_alert=True)
        return
    if player["jail_until"] > now:
        await callback.answer("🔒 أنت في السجن حالياً!", show_alert=True)
        return

    energy_req = 25 if target == "store" else 45
    gang_bonus = 12 if player["gang_name"] else 0
    success_chance = (55 if target == "store" else 30) + gang_bonus
    success = random.randint(1, 100) <= success_chance

    if success:
        loot = random.randint(400, 900) if target == "store" else random.randint(2000, 4500)
        wanted_add = 1 if target == "store" else 3
        ok = run_update(
            "UPDATE players SET cash = cash + ?, energy = energy - ?, wanted_level = wanted_level + ?, "
            "location = 'back_alleys' WHERE user_id = ? AND city_id = ? AND energy >= ? AND jail_until <= ?",
            (loot, energy_req, wanted_add, uid, cid, energy_req, now),
        )
        msg = f"🕶️ نجحت في السطو وحصلت على {loot}$! (+{wanted_add}⭐ مطلوب)"
    else:
        fine = 250 if target == "store" else 800
        jail_until = now + (180 if target == "store" else 360)
        ok = run_update(
            "UPDATE players SET cash = MAX(0, cash - ?), energy = energy - ?, wanted_level = 0, "
            "jail_until = ?, location = 'police' WHERE user_id = ? AND city_id = ? AND energy >= ? AND jail_until <= ?",
            (fine, energy_req, jail_until, uid, cid, energy_req, now),
        )
        msg = f"🚓 ألقت الشرطة القبض عليك! غرامة {fine}$ وسجن."

    if not ok:
        await callback.answer(f"⚡ طاقتك غير كافية! تحتاج {energy_req}%.", show_alert=True)
        return

    await callback.answer(msg, show_alert=True)
    await show_dashboard(callback, uid)


@router.callback_query(F.data.startswith("police_menu:"))
async def cb_police_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, city = res
    uid = player["user_id"]

    conn = get_db()
    wanted_list = conn.execute(
        "SELECT user_id, username, wanted_level, location FROM players "
        "WHERE city_id = ? AND wanted_level > 0 ORDER BY wanted_level DESC LIMIT 10",
        (city["city_id"],),
    ).fetchall()
    conn.close()

    lines = ["🚓 <b>مركز الشرطة والمحكمة</b>\n"]
    buttons = []
    if wanted_list:
        lines.append("📋 <b>قائمة المطلوبين:</b>")
        for w in wanted_list:
            loc_ar = LOCATIONS.get(w["location"], w["location"])
            lines.append(f"• <b>{esc(w['username'])}</b> — الخطورة: <code>{w['wanted_level']}⭐</code> — {loc_ar}")
            if player["job"] == "police_officer" and w["user_id"] != uid:
                buttons.append([InlineKeyboardButton(
                    text=f"🚔 القبض على {w['username']}",
                    callback_data=f"arrest:{w['user_id']}:{uid}",
                )])
    else:
        lines.append("✔️ المدينة آمنة ولا يوجد مطلوبون.")

    if player["wanted_level"] > 0:
        bail_cost = player["wanted_level"] * 400
        buttons.append([InlineKeyboardButton(text=f"⚖️ دفع الكفالة ({bail_cost}$)", callback_data=f"pay_bail:{uid}")])

    buttons.append(back_button(uid))
    await safe_edit(callback.message, "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("arrest:"))
async def cb_arrest_wanted(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    officer, city = res
    _, target_uid_str, _ = callback.data.split(":")
    target_uid = int(target_uid_str)
    cid = city["city_id"]

    if officer["job"] != "police_officer":
        await callback.answer("⚠️ يجب أن تعمل كضابط شرطة!", show_alert=True)
        return
    if target_uid == officer["user_id"]:
        await callback.answer("لا يمكنك القبض على نفسك!", show_alert=True)
        return

    conn = get_db()
    suspect = conn.execute(
        "SELECT * FROM players WHERE user_id = ? AND city_id = ?", (target_uid, cid)
    ).fetchone()
    if not suspect or suspect["wanted_level"] <= 0:
        conn.close()
        await callback.answer("هذا اللاعب لم يعد مطلوباً!", show_alert=True)
        return

    reward = suspect["wanted_level"] * 350
    fine = suspect["wanted_level"] * 300
    jail_until = int(time.time()) + 240

    # شرط wanted_level > 0 يمنع القبض المزدوج من ضابطين في آن واحد
    cur = conn.execute(
        "UPDATE players SET wanted_level = 0, jail_until = ?, cash = MAX(0, cash - ?), location = 'police' "
        "WHERE user_id = ? AND city_id = ? AND wanted_level > 0",
        (jail_until, fine, target_uid, cid),
    )
    if cur.rowcount == 0:
        conn.close()
        await callback.answer("سبقك ضابط آخر للقبض عليه!", show_alert=True)
        return
    conn.execute(
        "UPDATE players SET cash = cash + ?, xp = xp + 40 WHERE user_id = ? AND city_id = ?",
        (reward, officer["user_id"], cid),
    )
    conn.commit()
    conn.close()

    await callback.answer(f"🚔 قبضت على {suspect['username']} واستلمت مكافأة {reward}$!", show_alert=True)
    await show_dashboard(callback, officer["user_id"])


@router.callback_query(F.data.startswith("pay_bail:"))
async def cb_pay_bail(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    if not res:
        await callback.answer(NOT_YOURS, show_alert=True)
        return
    player, city = res
    bail_cost = player["wanted_level"] * 400

    ok = run_update(
        "UPDATE players SET cash = cash - wanted_level * 400, wanted_level = 0, location = 'police' "
        "WHERE user_id = ? AND city_id = ? AND wanted_level > 0 AND cash >= wanted_level * 400",
        (player["user_id"], city["city_id"]),
    )
    if not ok:
        await callback.answer(f"💵 تحتاج إلى {bail_cost}$ لدفع الكفالة!", show_alert=True)
        return

    run_update("UPDATE cities SET treasury = treasury + ? WHERE city_id = ?", (bail_cost, city["city_id"]))
    await callback.answer("✅ تم تسوية سجلك الأمني وأصبح نظيفاً!", show_alert=True)
    await show_dashboard(callback, player["user_id"])


# ==========================================
# 13. أوامر الرد (تحويل وسرقة)
# ==========================================
# تنبيه: لتصل هذه الرسائل النصية للبوت داخل المجموعات يجب تعطيل
# وضع الخصوصية: BotFather → /setprivacy → اختر البوت → Disable
@router.message(F.text.startswith("تحويل"))
async def msg_reply_transfer(message: Message) -> None:
    if not message.reply_to_message or not message.reply_to_message.from_user:
        return
    city = get_group_city(message.chat.id)
    if not city:
        return

    parts = message.text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.reply("⚠️ الصيغة: <code>تحويل 500</code> بالرد على رسالة اللاعب")
        return

    amount = int(parts[1])
    if amount <= 0:
        return

    receiver_user = message.reply_to_message.from_user
    if receiver_user.is_bot or receiver_user.id == message.from_user.id:
        return

    cid = city["city_id"]
    sender = get_or_create_player(message.from_user.id, cid, message.from_user.full_name or "مواطن")
    receiver = get_or_create_player(receiver_user.id, cid, receiver_user.full_name or "مواطن")

    conn = get_db()
    cur = conn.execute(
        "UPDATE players SET cash = cash - ? WHERE user_id = ? AND city_id = ? AND cash >= ?",
        (amount, sender["user_id"], cid, amount),
    )
    if cur.rowcount == 0:
        conn.close()
        await message.reply("💵 رصيدك النقدي غير كافٍ!")
        return
    conn.execute(
        "UPDATE players SET cash = cash + ? WHERE user_id = ? AND city_id = ?",
        (amount, receiver["user_id"], cid),
    )
    conn.commit()
    conn.close()

    await message.reply(f"💸 تم تحويل <code>{amount:,}$</code> إلى <b>{esc(receiver['username'])}</b>!")


@router.message(F.text == "سرقة")
async def msg_reply_pickpocket(message: Message) -> None:
    if not message.reply_to_message or not message.reply_to_message.from_user:
        return
    city = get_group_city(message.chat.id)
    if not city:
        return

    victim_user = message.reply_to_message.from_user
    if victim_user.is_bot or victim_user.id == message.from_user.id:
        return

    cid = city["city_id"]
    now = int(time.time())
    thief = get_or_create_player(message.from_user.id, cid, message.from_user.full_name or "مواطن")
    victim = get_or_create_player(victim_user.id, cid, victim_user.full_name or "مواطن")

    if thief["jail_until"] > now:
        await message.reply("🔒 أنت مسجون حالياً!")
        return
    if thief["energy"] < 15:
        await message.reply("⚡ طاقتك منخفضة جداً!")
        return
    if victim["cash"] < 50:
        await message.reply(f"🤷‍♂️ محفظة <b>{esc(victim['username'])}</b> فارغة تقريباً!")
        return

    conn = get_db()
    spent = conn.execute(
        "UPDATE players SET energy = energy - 15, wanted_level = wanted_level + 1 "
        "WHERE user_id = ? AND city_id = ? AND energy >= 15 AND jail_until <= ?",
        (thief["user_id"], cid, now),
    )
    if spent.rowcount == 0:
        conn.close()
        await message.reply("⚡ لا يمكنك تنفيذ العملية الآن!")
        return

    if random.randint(1, 100) <= 45:
        wanted_amount = max(25, int(victim["cash"] * random.uniform(0.10, 0.25)))
        # نسرق فقط ما هو متوفر فعلاً لدى الضحية
        cur = conn.execute(
            "UPDATE players SET cash = cash - ? WHERE user_id = ? AND city_id = ? AND cash >= ?",
            (wanted_amount, victim["user_id"], cid, wanted_amount),
        )
        if cur.rowcount:
            conn.execute(
                "UPDATE players SET cash = cash + ? WHERE user_id = ? AND city_id = ?",
                (wanted_amount, thief["user_id"], cid),
            )
            conn.commit()
            conn.close()
            await message.reply(
                f"🕶️ نجحت في نشل <code>{wanted_amount}$</code> من <b>{esc(victim['username'])}</b>!"
            )
            return
    conn.commit()
    conn.close()
    await message.reply("🚨 فشلت محاولة السرقة وتم رصدك أمنياً!")


# ==========================================
# 14. محرك الزمن وخادم الويب (Keep-Alive)
# ==========================================
async def city_tick_engine() -> None:
    while True:
        await asyncio.sleep(900)  # كل 15 دقيقة
        try:
            conn = get_db()
            cur = conn.cursor()
            businesses = cur.execute("SELECT city_id, owner_id, biz_type FROM businesses").fetchall()
            for b in businesses:
                income = BUSINESS_TYPES.get(b["biz_type"], {}).get("hourly_income", 200) // 4
                cur.execute(
                    "UPDATE players SET bank = bank + ? WHERE user_id = ? AND city_id = ?",
                    (income, b["owner_id"], b["city_id"]),
                )
            cur.execute(
                """
                UPDATE players
                SET energy = MIN(100, energy + CASE WHEN house IS NOT NULL THEN 20 ELSE 10 END),
                    hungry = MAX(0, hungry - 3),
                    bank = bank + CAST(bank * 0.01 AS INTEGER)
                """
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.error("خطأ في محرك الزمن: %s", exc)


async def handle_health_check(request: web.Request) -> web.Response:
    return web.Response(text="Horizon City Bot is running!")


async def start_render_web_server() -> None:
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    app.router.add_get("/health", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    logger.info("🌐 خادم الويب يعمل على المنفذ %s", PORT)


# ==========================================
# 15. نقطة التشغيل
# ==========================================
async def main() -> None:
    if not BOT_TOKEN:
        raise SystemExit("متغير البيئة BOT_TOKEN غير مضبوط!")

    init_db()
    await start_render_web_server()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    asyncio.create_task(city_tick_engine())

    logger.info("🚀 بوت مدينة الأفق يعمل الآن...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
