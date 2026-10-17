# -*- coding: utf-8 -*-
"""
بوت مدينة الأفق (Horizon City Bot) - لعبة حياة محاكاة تفاعلية في مجموعات تيليجرام
تعمل بالكامل على منصة Render (خدمة ويب مجانية) مع GitHub.

دعوة للوحدة:
1. المدينة العالمية الموحدة (يشترك فيها جميع اللاعبين عبر المجموعات).
2. الحديث الخاص بكل مجموعة (حسب اختيار مدير المجموعة).
"""

استيراد asyncio
استيراد التسجيل
استيراد نظام التشغيل
استيراد عشوائي
استيراد sqlite3
وقت الاستيراد
من typing استورد Optional، Dict، Any، Tuple

من aiohttp استورد Web
من aiogram استورد Bot، Dispatcher، F، Router
من aiogram.filters استورد الأمر Command
from aiogram.types import (
    رسالة،
    CallbackQuery,
    ترميز لوحة المفاتيح المضمنة،
    زر لوحة المفاتيح المضمنة،
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
# 2. بيانات العالم الافتراضي (المواقع، الوظائف، العقارات، المشاريع)
# ==========================================
المواقع: Dict[str, str] = {
    "downtown": "🏙️ وسط البلد (المركز المالي)"،
    "residential": "🏠 الحي السكني",
    "market": "🛒 الحي التجاري بكثرة",
    "education": "🎓 الجامعة والمجمع الطبي",
    "الصناعية": "🏭 المنطقة الصناعية"
    "police": "🚓 مركز الشرطة والمحكمة",
    "back_alleys": "🕶️ الأزقة الخلفية",
}

الدرجات: Dict[str, Dict[str, Any]] = {
    "management": {"name": "📜 بكالوريوس إدارة واقتصاد", "التكلفة": 1500, "الطاقة": 30},
    "الطب": {"name": "🩺 شهادة الطب العام", "التكلفة": 2500, "الطاقة": 40},
    "law_security": {"name": "⚖️ دبلوم القانون والعلوم الأمنية", "التكلفة": 1800, "الطاقة": 35},
    "الهندسة": {"name": "⚙️ بكالوريوس الهندسة الصناعية", "التكلفة": 2000, "الطاقة": 35},
}

الوظائف: Dict[str, Dict[str, Any]] = {
    "freelancer": {"name": "👷 عامل حر", "salary": 250, "energy": 20, "req_degree": None, "clean_record": False},
    "banker": {"name": "🏦 محاسب مصرفي", "salary": 650, "energy": 25, "req_degree": "management", "clean_record": True},
    "doctor": {"name": "👨‍⚕️ طبيب في المستشفى"، "salary": 900، "energy": 30، "req_degree": "medicine"، "clean_record": True},
    "police_officer": {"name": "👮 ضابط شرطة", "salary": 750, "energy": 25, "req_degree": "law_security", "clean_record": True},
    "engineer": {"name": "👷‍♂️ مهندس مهندس", "salary": 800, "energy": 25, "req_degree": "engineering", "clean_record": True},
}

المنازل: Dict[str, Dict[str, Any]] = {
    "studio": {"name": "🛏️ شقة استوديو", "base_price": 3000, "energy_regen": 15},
    "فيلا": {"name": "🏡 فيلا عائلية", "base_price": 12000, "energy_regen": 30},
    "palace": {"name": "🏰 قصر فاخر", "base_price": 50000, "energy_regen": 50},
}

المركبات: Dict[str, Dict[str, Any]] = {
    "دراجة": {"name": "🏍️ دراجة نارية"، "base_price": 2000، "travel_energy_save": 3},
    "سيدان": {"name": "🚗 سيارة سيدان", "base_price": 8500, "travel_energy_save": 6},
    "sports فاخرة": {"name": "🏎️ سيارة رياضية", "base_price": 35000, "travel_energy_save": 9},
}

أنواع الأعمال: قاموس[سلسلة نصية، قاموس[سلسلة نصية، أي]] = {
    "restaurant": {"name": "🍔 مطعم وجبات سريعة", "base_price": 10000, "hourly_input": 350},
    "supermarket": {"name": "🛒 سوبرماركت مركزي", "السعر_الأساسي": 22000, "الدخل_بالساعة": 800},
    "car_agency": {"name": "🚘 وكالة سيارات", "السعر_الأساسي": 60000, "دخل_الساعة": 2400},
    "المصنع": {"name": "🏭 إنتاج المصنع", "السعر_الأساسي": 95000, "الدخل_بالساعة": 4000},
}


# ==========================================
#3. إدارة قاعدة البيانات (SQLite)
# ==========================================
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    إرجاع الاتصال


def init_db() -> None:
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        إنشاء جدول المدن إذا لم يكن موجودًا (
            city_id INTEGER PRIMARY KEY AUTOINCREMENT,
            الاسم نص غير فارغ،
            is_global INTEGER DEFAULT 0,
            owner_chat_id عدد صحيح، القيمة الافتراضية: NULL،
            الخزانة عدد صحيح افتراضي 100000،
            price_index REAL DEFAULT 1.0,
            created_at عدد صحيح غير فارغ
        )
    """)

    cur.execute("SELECT city_id FROM cities WHERE city_id = 1")
    إذا لم يتم استدعاء الدالة cur.fetchone():
        cur.execut(
            "INSERT INTO citys (city_id, name, is_global, treasury,price_index, create_at) VALUES (1, 'مدينة الأفق العالمي', 1, 500000, 1.0, ?)",
            (int(time.time()),),
        )

    cur.execute("""
        إنشاء جدول إذا لم يكن موجودًا باسم groups (
            chat_id INTEGER PRIMARY KEY,
            city_id عدد صحيح غير فارغ،
            عنوان المجموعة (نص)،
            المفتاح الخارجي (city_id) يشير إلى المدن (city_id)
        )
    """)

    cur.execute("""
        إنشاء جدول اللاعبين إذا لم يكن موجودًا (
            user_id عدد صحيح غير فارغ،
            city_id عدد صحيح غير فارغ،
            اسم المستخدم نص غير فارغ،
            location TEXT DEFAULT 'وسط المدينة',
            النقد عدد صحيح افتراضي 1000،
            البنك INTEGER DEFAULT 500،
            الصحة عدد صحيح القيمة الافتراضية 100،
            الطاقة عدد صحيح القيمة الافتراضية 100،
            الجوع عدد صحيح، القيمة الافتراضية 100
            المستوى INTEGER DEFAULT 1،
            قيمة xp INTEGER DEFAULT الافتراضية هي 0،
            درجة نص افتراضي فارغ،
            نص الوظيفة الافتراضي 'مستقل'،
            قيمة نص المنزل الافتراضية فارغة (NULL).
            قيمة نص المركبة الافتراضية فارغة (NULL).
            المستوى المطلوب عدد صحيح القيمة الافتراضية 0،
            jail_until INTEGER DEFAULT 0,
            gang_name TEXT DEFAULT NULL,
            last_work_ts عدد صحيح القيمة الافتراضية 0،
            المفتاح الأساسي (معرف_المستخدم، معرف_المدينة)
        )
    """)

    cur.execute("""
        إنشاء جدول إذا لم يكن موجودًا (
            biz_id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_id عدد صحيح غير فارغ،
            owner_id عدد صحيح غير فارغ،
            biz_type TEXT NOT NULL,
            custom_name TEXT NOT NULL,
            created_at عدد صحيح غير فارغ
        )
    """)

    conn.commit()
    conn.close()


# ==========================================
# 4. مساعدة ثنائية للمدينة الابتكارية واللاعبين
# ==========================================
def get_group_city(chat_id: int) -> Optional[sqlite3.Row]:
    conn = get_db()
    row = conn.execute(
        """
        حدد g.chat_id، وg.city_id، وc.name AS city_name، وc.is_global، وc.treasury، وc.price_index
        من المجموعات ز
        انضم إلى المدن c بناءً على g.city_id = c.city_id
        حيث g.chat_id = ؟
        "",
        (معرف_المحادثة،)،
    ).fetchone()
    conn.close()
    صف الإرجاع


def set_group_city_mode(chat_id: int, title: str, mode: str) -> Tuple[int, str]:
    conn = get_db()
    cur = conn.cursor()
    إذا كان الوضع == "عام":
        city_id = 1
        city_name = "مدينة الأفق العالمية"
    آخر:
        city_name = f"مدينة {title[:25]}"
        cur.execut(
            "INSERT INTO cities (name, is_global, owner_chat_id, treasury, price_index, created_at) VALUES (?, 0, ?, 100000, 1.0, ?)",
            (اسم_المدينة، معرف_الدردشة، int(الوقت.الوقت())),
        )
        citys_id = cur.lastrowid

    cur.execut(
        "INSERT OR REPLACE INTO groups (chat_id, city_id, group_title) VALUES (?, ?, ?)",
        (معرف_المحادثة، معرف_المدينة، العنوان)،
    )
    conn.commit()
    conn.close()
    أعد معرف المدينة واسم المدينة


def get_or_create_player(user_id: int, city_id: int, full_name: str) -> sqlite3.Row:
    conn = get_db()
    cur = conn.cursor()
    player = cur.execute(
        "SELECT * FROM players WHERE user_id = ? AND city_id = ?",
        (معرف_المستخدم، معرف_المدينة)،
    ).fetchone()
    إذا لم يكن اللاعب:
        cur.execut(
            "INSERT INTO players (user_id, city_id, username) VALUES (?, ?, ?)",
            (معرف_المستخدم، معرف_المدينة، الاسم_الكامل[:30])،
        )
        conn.commit()
        player = cur.execute(
            "SELECT * FROM players WHERE user_id = ? AND city_id = ?",
            (معرف_المستخدم، معرف_المدينة)،
        ).fetchone()
    conn.close()
    اللاعبون العائدون


def adjust_city_demand(city_id: int, delta: float) -> None:
    conn = get_db()
    city ​​= conn.execute("SELECT price_index FROM cities WHERE city_id = ?", (city_id,)).fetchone()
    إذا كانت المدينة:
        new_index = max(0.75, min(2.50, round(city["price_index"] + delta, 2)))
        conn.execute("UPDATE cities SET price_index = ? WHERE city_id = ?", (new_index, city_id))
        conn.commit()
    conn.close()


# ==========================================
# 5. بناء لوحات المفاتيح التفاعلية (لوحات المفاتيح المضمنة)
# ==========================================
def build_setup_keyboard() -> InlineKeyboardMarkup:
    إرجاع InlineKeyboardMark(
        لوحة المفاتيح المضمنة = [
            [
                زر لوحة المفاتيح المضمن (
                    text="🌐 الانضمام للمدينة العالمية الموحدة",
                    callback_data="setup_mode:global",
                )
            ],
            [
                زر لوحة المفاتيح المضمن (
                    text="🏙️ إنشاء مدينة مستقلة خاصة بالمجموعة",
                    callback_data="setup_mode:private",
                )
            ],
        ]
    )


def build_main_city_keyboard(uid: int) -> InlineKeyboardMarkup:
    إرجاع InlineKeyboardMark(
        لوحة المفاتيح المضمنة = [
            [
                InlineKeyboardButton(text="🗺️ الطيران بين الشوارع", callback_data=f"nav_menu:{uid}"),
                InlineKeyboardButton(text="👥 المتواجدون بموقعي", callback_data=f"nearby:{uid}"),
            ],
            [
                InlineKeyboardButton(text="💼 العمل والوظائف", callback_data=f"jobs_menu:{uid}"),
                InlineKeyboardButton(text="🎓 المدرسة والجامعة", callback_data=f"edu_menu:{uid}"),
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
            [
                InlineKeyboardButton(text="🔄 تحديث بطاقة المدينة", callback_data=f"main_menu:{uid}"),
            ],
        ]
    )


def format_player_dashboard(player: sqlite3.Row, city: sqlite3.Row) -> str:
    loc_name = LOCATIONS.get(player["location"], player["location"])
    job_name = JOBS.get(player["job"], {}).get("name", "بدون عمل")
    degree_name = DEGREES.get(player["degree"], {}).get("name", "لا يوجد") if player["degree"] else "لا يوجد"
    house_name = HOUSES.get(player["house"], {}).get("name", "بلا مسكن") if player["house"] else "بلا مسكن"
    Vehicle_name = VEHICLES.get(player["vehicle"], {}).get("name", "المشي على الأقدام") إذا كان اللاعب["vehicle"] آخر "المشي على الأقدام"
    gang_text = player["gang_name"] if player["gang_name"] else "مفاوض"

    الآن = int(الوقت.الوقت())
    إذا كان اللاعب["jail_until"] > الآن:
        remaining_min = max(1, (player["jail_until"] - now) // 60)
        jail_status = f"\n🔒 **الحالة الأمنية:** موقوف في السجن ({remaining_min} دقيقة متبقية)"
    elif player["wanted_level"] > 0:
        jail_status = f"\n🚨 **الحالة الأمنية:** مطلوب للشرطة (درجة الخطورة: {player['wanted_level']} ⭐)"
    آخر:
        jail_status = "\n= **الحالة الأمنية:** تم إصلاحها"

    mode_label = "🌐 عالمية مشتركة" if city["is_global"] else "🏙️ خاصة بالمجموعة"

    يعود (
        f"🏙️ **{city['city_name']}** ({mode_label})\n"
        f"📊 مؤشر المنتجات الحالي: `{int(city['price_index'] * 100)}%` | خزينة المدينة: `{city['treasury']:,}$`\n\n"
        f"👤 **المواطن:** {player['username']} (المستوى {player['level']} ⭐)\n"
        f"📍 **الموقع الحالي:** {loc_name}\n"
        f"❤️ الصحة: ​​`{لاعب['الصحة']}%` | ⚡ الطاقة: `{لاعب['طاقة']}%` | 🍔 الشبع: `{لاعب['جوع']}%`\n"
        f"💵 النقد بالمحفظة: `{player['cash']:,}$` | 🏦 النقد الشخصي: `{player['bank']:,}$`\n"
        f"💼 الوظيفة: {job_name} | 🎓 لأنها: {degree_name}\n"
        f"🏠 المسكن: {house_name} | 🚗 سماعه: {vehicle_name}\n"
        f"🕶️ الانتماء: {gang_text}"
        f"{jail_status}"
    )


# ==========================================
#6.إرشادات المجموعة والإعدادات
# ==========================================
@router.message(Command("start", "البدء", "اعداد_المدينة"))
async def cmd_start_or_setup(message: Message) -> None:
    إذا كان نوع المحادثة "خاص":
        انتظر الرد على الرسائل (
            "👋 أهلاً بك في **بوت مدينة الأفق التفاعلية**!\n\n"
            "لبدء اللعب، أضف البوت إلى مجموعتك ثم أرسل أمر `/اعداد_المدينة` ليختار مدير المجموعة نظام المدينة، "
            "وبعدها يمكن لجميع الأعضاء كتابة `/المدينة` للبدء في العمل للجميع.",
            parse_mode="Markdown",
        )
        يعود

    انتظر الرد على الرسائل (
        "⚙️ **إعداد نظام المدينة في المجموعة**\n\n"
        "يمكن لمدير أو مشرف اختيار نظام العالم الذي سيعيش فيه أعضاء المجموعة:\n"
        "1️⃣ **المدينة العالمية الموحدة:** يشاركون في المجموعة في مدينة اشتركوا مع المجموعات الأخرى.\n"
        "2️⃣ **مدينة مستقلة خاصة بالمجموعة:** تُنشأ مدينة كاملة ومرافقها مخصصة لأعضاء هذه المجموعة فقط.",
        reply_markup=build_setup_keyboard(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("setup_mode:"))
async def cb_setup_mode(callback: CallbackQuery, bot: Bot) -> None:
    member = await bot.get_chat_member(callback.message.chat.id, callback.from_user.id)
    إذا لم يكن وضع العضو من بين ("administrator" أو "creator"):
        wait callback.answer("❌ هذا الخيار مخصص لمدير ومشرفي المجموعة فقط!", show_alert=True)
        يعود

    mode = callback.data.split(":")[1]
    العنوان = callback.message.chat.title أو "المجموعة"
    _, city_name = set_group_city_mode(callback.message.chat.id, title, mode)

    mode_desc = (
        "🌐 تم ربط المجموعة بـ **المدينة العالمية الموحدة** فعالة!"
        إذا كان الوضع == "عالمي"
        else f"🏙️ تم إنشاء **{city_name}** كمدينة كاملة ومستقلة خاصة بمجموعتكم!"
    )
    await callback.message.edit_text(
        f"{mode_desc}\n\n"
        f"🏛️ جميع المجموعات (المنازل، الشامل، المطاعم، الجامعة، الشركات، المصرف، الشرطة، الجرحى) أصبحت الآن!\n"
        f"👉 اكتبوا أمر `/المدينة` لفتح بطاقة حياتك وتجول في المدينة.",
        parse_mode="Markdown",
    )
    انتظار رد الاتصال.إجابة("تم حفظ إعدادات المدينة!")


@router.message(Command("city", "المدينة", "حياتي"))
async def cmd_open_city(message: Message) -> None:
    إذا كان نوع المحادثة "خاص":
        wait message.answer("⚠️ يرجى استخدام أمر `/المدينة` داخل مجموعة تيليجرام مفعّلة."")
        يعود

    city ​​= get_group_city(message.chat.id)
    إن لم تكن المدينة:
        انتظر الرد على الرسائل (
            "⚠️ لم يتم اختيار نظام المدينة لهذه المجموعة بعد!\n"
            "يرجى من مدير المجموعة الضغط على الزر أدناه لتفعيل المدينة:"،
            reply_markup=build_setup_keyboard(),
        )
        يعود

    player = get_or_create_player(
        message.from_user.id,
        city["city_id"],
        message.from_user.full_name أو "اسم المستخدم"،
    )
    text = format_player_dashboard(player, city)
    انتظر الرد على الرسائل (
        نص،
        reply_markup=build_main_city_keyboard(message.from_user.id),
        parse_mode="Markdown",
    )


# ==========================================
# 7. التحقق من ملكية لوحة الأزرار
# ==========================================
def check_owner_and_city(callback: CallbackQuery) -> Optional[Tuple[sqlite3.Row, sqlite3.Row]]:
    parts = callback.data.split(":")
    owner_id = int(parts[-1])
    إذا كان callback.from_user.id != owner_id:
        لا شيء
    city ​​= get_group_city(callback.message.chat.id)
    إن لم تكن المدينة:
        لا شيء
    player = get_or_create_player(
        callback.from_user.id,
        city["city_id"],
        callback.from_user.full_name أو "اسم المستخدم"،
    )
    لاعب العودة، المدينة


@router.callback_query(F.data.startswith("main_menu:"))
async def cb_main_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    إذا لم يكن res:
        Wait callback.answer("⚠️ هذه اللوحة خاصة بلاعب آخر! اكتب /المدينة لفتح لوحتك.", show_alert=True)
        يعود
    اللاعب، المدينة = res
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )
    انتظر رد الاستدعاء.


# ==========================================
#8. نظام الطيران بين مناطق ومناطق المدينة
# ==========================================
@router.callback_query(F.data.startswith("nav_menu:"))
async def cb_nav_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، _ = res
    uid = player["user_id"]

    إذا كان اللاعب["jail_until"] > int(time.time()):
        wait callback.answer("🔒 لا يمكنك الطيران أثناء فترة التوقيف في السجن!", show_alert=True)
        يعود

    الأزرار = []
    for loc_key, loc_title in LOCATIONS.items():
        prefix = "📍 " if player["location"] == loc_key else "🚶 "
        buttons.append([InlineKeyboardButton(text=f"{prefix}{loc_title}", callback_data=f"move:{loc_key}:{uid}")])
    Buttons.append([InlineKeyboardButton(text="🔙 العودة للمدينة", callback_data=f"main_menu:{uid}")])

    await callback.message.edit_text(
        "🗺️ **خريطة شوارع ومناطق المدينة**\ناختر المنطقة التي تريد الانتقال إليها (امتلاك مجهزة بمركبات مجهزة):"،
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown",
    )
    انتظر رد الاستدعاء.


@router.callback_query(F.data.startswith("move:"))
async def cb_move_location(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، المدينة = res
    _, target_loc, _ = callback.data.split(":")

    إذا كان موقع اللاعب يساوي موقع الهدف:
        wait callback.answer("أنت متواجد بالفعل في هذه المنطقة!")
        يعود

    save = VEHICLES.get(player["vehicle"], {}).get("travel_energy_save", 0) if player["vehicle"] else 0
    تكلفة_الطاقة = الحد_الأقصى(2، 10 - التوفير)

    إذا كانت طاقة اللاعب أقل من تكلفة الطاقة:
        wait callback.answer(f"⚡ طاقتك غير كافية للتنقل! تحتاج {energy_cost}% طاقة (توجيه للمطعم أو استرح في ألف)."، show_alert=True)
        يعود

    conn = get_db()
    conn.execute(
        "تحديث بيانات اللاعبين: تعيين الموقع = ؟، الطاقة = الطاقة - ؟ حيث معرف المستخدم = ؟ ومعرف المدينة = ؟"
        (target_loc, energy_cost, player["user_id"], city["city_id"]),
    )
    conn.commit()
    conn.close()

    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    wait callback.answer(f"✔ ثم إلى {LOCATIONS[target_loc]} (-{energy_cost}% طاقة)")
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("nearby:"))
async def cb_nearby_players(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، المدينة = res
    conn = get_db()
    other = conn.execute(
        "SELECT username, job, wanted_level FROM players WHERE city_id = ? AND location = ? LIMIT 15",
        (city["city_id"], player["location"]),
    ).fetchall()
    conn.close()

    loc_title = LOCATIONS.get(player["location"], player["location"])
    lines = [f"👥 **المتواجدون حاليًا في {loc_title}:**\n"]
    بالنسبة للصف في الآخرين:
        job_title = JOBS.get(row["job"], {}).get("name", "اسمك");
        wanted_tag ​​= f" 🚨( قد {row['wanted_level']}⭐)" if row["wanted_level"] > 0 else ""
        lines.append(f"• **{row['username']}** — {job_title}{wanted_tag}")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 العودة للمدينة", callback_data=f"main_menu:{player['user_id']}")]]]
    )
    await callback.message.edit_text("\n".join(lines), reply_markup=kb, parse_mode="Markdown")
    انتظر رد الاستدعاء.


# ==========================================
# 9. التعليم والوظائف التجريبية
# ==========================================
@router.callback_query(F.data.startswith("edu_menu:"))
async def cb_edu_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، _ = res
    uid = player["user_id"]

    الأزرار = []
    for deg_key, deg in DEGREES.items():
        buttons.append(
            [
                زر لوحة المفاتيح المضمن (
                    text=f"{deg['name']} ({deg['cost']}$ | -{deg['energy']}⚡)"،
                    callback_data=f"study:{deg_key}:{uid}",
                )
            ]
        )
    Buttons.append([InlineKeyboardButton(text="🔙 العودة للمدينة", callback_data=f"main_menu:{uid}")])

    await callback.message.edit_text(
        "🎓 **الجامعة المركزية ومعهد التدريب**\ناختر التخصص الذي ترغب بدراسته لفتح الوظائف العليا في المدينة المنورة:"،
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown",
    )
    انتظر رد الاستدعاء.


@router.callback_query(F.data.startswith("study:"))
async def cb_study_degree(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، المدينة = res
    _, deg_key, _ = callback.data.split(":")
    deg = DEGREES[deg_key]

    إذا كان رصيد اللاعب أقل من التكلفة:
        Wait callback.answer(f"💵 رصيدك النقدي غير النقدي! تحتاج إلى {deg['cost']}$.", show_alert=True)
        يعود
    إذا كانت طاقة اللاعب أقل من طاقة الدرجة:
        wait callback.answer(f"⚡ طاقتك غير كافية للكمبيوتر! تحتاج إلى {deg['energy']}% طاقة.", show_alert=True)
        يعود

    conn = get_db()
    conn.execute(
        "تحديث بيانات اللاعبين: تعيين الرصيد النقدي = الرصيد النقدي - ؟، الطاقة = الطاقة - ؟، الدرجة = ؟، نقاط الخبرة = نقاط الخبرة + 50، الموقع = 'التعليم' حيث يكون معرف المستخدم = ؟ ومعرف المدينة = ؟"
        (deg["cost"], deg["energy"], deg_key, player["user_id"], city["city_id"]),
    )
    conn.execute("UPDATE cities SET treasury = treasury + ? WHERE city_id = ?", (deg["cost"], city["city_id"]))
    conn.commit()
    conn.close()

    wait callback.answer(f"🎉 مبارك! حصلت على {deg['name']} فعال!", show_alert=True)
    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    city ​​= get_group_city(callback.message.chat.id)
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("jobs_menu:"))
async def cb_jobs_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، _ = res
    uid = player["user_id"]

    الأزرار = [
        [InlineKeyboardButton(text="💰 إنجاز نوبة عمل الآن واستلام الراتب", callback_data=f"work_shift:{uid}")]
    ]
    for job_key, job in JOBS.items():
        buttons.append(
            [
                زر لوحة المفاتيح المضمن (
                    text=f"تقديم: {job['name']} (الراتب: {job['salary']}$)",
                    callback_data=f"apply_job:{job_key}:{uid}",
                )
            ]
        )
    Buttons.append([InlineKeyboardButton(text="🔙 العودة للمدينة", callback_data=f"main_menu:{uid}")])

    await callback.message.edit_text(
        "💼 **مكتب التوظيف التجريبي**\nيمكنك إنجاز نوبة عمل في وظيفتك الحالية أو الظهور على وظيفة جديدة:"،
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown",
    )
    انتظر رد الاستدعاء.


@router.callback_query(F.data.startswith("apply_job:"))
async def cb_apply_job(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، المدينة = res
    _, job_key, _ = callback.data.split(":")
    job = JOBS[job_key]

    إذا كان job["req_degree"] و player["degree"] != job["req_degree"]:
        req_name = DEGREES[job["req_degree"]]["name"]
        wait callback.answer(f"🎓 هذه الوظائف المطلوبة المطلوبة على: {req_name} من الجامعة الجديدة!", show_alert=True)
        يعود

    إذا كان job["clean_record"] و player["wanted_level"] > 0:
        wait callback.answer("🚨 لا يمكن قبولك في وظيفة عادية وليك بلاغات الحكومة في الشرطة!", show_alert=True)
        يعود

    conn = get_db()
    conn.execute(
        "تحديث اللاعبين، تعيين الوظيفة = ؟ حيث معرف المستخدم = ؟ ومعرف المدينة = ?",
        (مفتاح_الوظيفة، اللاعب["معرف_المستخدم"]، المدينة["معرف_المدينة"])،
    )
    conn.commit()
    conn.close()

    wait callback.answer(f"✅ تم تعيينك في الوظيفة: {job['name']}!", show_alert=True)
    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("work_shift:"))
async def cb_work_shift(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، المدينة = res

    إذا كان اللاعب["jail_until"] > int(time.time()):
        wait callback.answer("🔒 لا يمكنك العمل أثناء وجودك في السجن!", show_alert=True)
        يعود

    job = JOBS.get(player["job"], JOBS["freelancer"])
    إذا كانت طاقة اللاعب أقل من طاقة الوظيفة أو جوع اللاعب أقل من 15:
        wait callback.answer("⚡ طاقتك أو مستوى الشبع منخفض للغاية! تناول طعام الإفطار في مطعم أو استرح في آلاف.", show_alert=True)
        يعود

    الراتب = عدد صحيح (الوظيفة["الراتب"] * المدينة["مؤشر الأسعار"])
    new_xp = player["xp"] + 25
    المستوى_الجديد = 1 + (الخبرة_الجديدة // 100)

    conn = get_db()
    conn.execute(
        """
        تحديث اللاعبين
        SET cash = cash + ?, energy = energy - ?, hungry = MAX(0, hungry - 15), xp = ?, level = ?
        حيث يكون user_id = ؟ و city_id = ؟
        "",
        (الراتب، الوظيفة["الطاقة"]، الخبرة الجديدة، المستوى الجديد، اللاعب["معرف المستخدم"]، المدينة["معرف المدينة"])،
    )
    conn.commit()
    conn.close()

    adjust_city_demand(city["city_id"], -0.01)
    wait callback.answer(f"💵 أنجزت عملك كـ {job['name']} ماتت على {salary}$ (+25 خبرة)!", show_alert=True)
    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    city ​​= get_group_city(callback.message.chat.id)
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
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، المدينة = res
    uid = player["user_id"]
    idx = city["price_index"]

    سعر_الوجبة = int(80 * idx)
    med_price = int(150 * idx)
    rest_price = int(100 * idx)

    kb = InlineKeyboardMarkup(
        لوحة المفاتيح المضمنة = [
            [InlineKeyboardButton(text=f"🍔 الإفطار (+40 شبع، +25 طاقة) — {meal_price}$"، callback_data=f"buy_item:meal:{uid}")],
            [InlineKeyboardButton(text=f"💊 حقيبة إسعافية (+50 صحة) — {med_price}$", callback_data=f"buy_item:med:{uid}")],
            [InlineKeyboardButton(text=f"🛌 استراحة في المنزل/الفندق (+50 طاقة) — {rest_price}$", callback_data=f"buy_item:rest:{uid}")],
            [InlineKeyboardButton(text="🔙 العودة للمدينة", callback_data=f"main_menu:{uid}")],
        ]
    )
    await callback.message.edit_text(
        f"🛒 **سوق المدينة والمستشفى**\nالأسعار حسب العرض والطلب في المدينة (المؤشر الحالي `{int(idx*100)}%`):",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    انتظر رد الاستدعاء.


@router.callback_query(F.data.startswith("buy_item:"))
async def cb_buy_item(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، المدينة = res
    _, item_type, _ = callback.data.split(":")
    idx = city["price_index"]

    conn = get_db()
    إذا كان نوع العنصر يساوي "وجبة":
        التكلفة = عدد صحيح (80 * idx)
        إذا كان رصيد اللاعب أقل من التكلفة:
            Wait callback.answer("💵 رصيدك النقدي غير الصغير!", show_alert=True)
            conn.close()
            يعود
        conn.execute(
            "تحديث بيانات اللاعبين: تعيين الرصيد النقدي = الرصيد النقدي - ؟، الجوع = الحد الأدنى (100، الجوع + 40)، الطاقة = الحد الأدنى (100، الطاقة + 25)، الموقع = 'السوق' حيث معرف المستخدم = ؟ ومعرف المدينة = ؟",
            (التكلفة، اللاعب["معرف_المستخدم"]، المدينة["معرف_المدينة"])،
        )
        msg = "🍔فات الشهية واستعدت نشاطك!"
    elif item_type == "med":
        التكلفة = عدد صحيح (150 * idx)
        إذا كان رصيد اللاعب أقل من التكلفة:
            Wait callback.answer("💵 رصيدك النقدي غير الصغير!", show_alert=True)
            conn.close()
            يعود
        conn.execute(
            "تحديث جدول اللاعبين: تعيين الرصيد النقدي = الرصيد النقدي - ؟، الصحة = الحد الأدنى (100، الصحة + 50)، الموقع = 'التعليم' حيث معرف المستخدم = ؟ ومعرف المدينة = ؟",
            (التكلفة، اللاعب["معرف_المستخدم"]، المدينة["معرف_المدينة"])،
        )
        msg = "💊 تلقيت العلاج في مستشفى واستعدت صحتك!"
    آخر:
        التكلفة = 0 إذا كان اللاعب["house"] وإلا int(100 * idx)
        إذا كان رصيد اللاعب أقل من التكلفة:
            Wait callback.answer("💵 رصيدك النقدي غير الصغير ودفعة الفندق!", show_alert=True)
            conn.close()
            يعود
        regen = HOUSES.get(player["house"], {}).get("energy_regen", 35) + 25
        conn.execute(
            "تحديث اللاعبين SET cash = cash - ?, energy = MIN(100, energy + ?), location = 'residential' WHERE user_id = ? AND city_id = ?",
            (التكلفة، التجديد، اللاعب["معرف_المستخدم"]، المدينة["معرف_المدينة"])،
        )
        msg = "🛌 أنت الآن من الروح الجميلة وأستعدت طاقتك!"

    conn.commit()
    conn.close()
    adjust_city_demand(city["city_id"], 0.02)
    await callback.answer(msg, show_alert=True)

    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    city ​​= get_group_city(callback.message.chat.id)
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("bank_menu:"))
async def cb_bank_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، _ = res
    uid = player["user_id"]

    kb = InlineKeyboardMarkup(
        لوحة المفاتيح المضمنة = [
            [
                InlineKeyboardButton(text="📥 إيداع كل النقد بالمصرف", callback_data=f"bank_op:dep_all:{uid}"),
                InlineKeyboardButton(text="📤 سحب 1,000$ نقدًا"، callback_data=f"bank_op:wit_1000:{uid}"),
            ],
            [
                InlineKeyboardButton(text="📤 سحب كل الرصيد", callback_data=f"bank_op:wit_all:{uid}"),
            ],
            [InlineKeyboardButton(text="🔙 العودة للمدينة", callback_data=f"main_menu:{uid}")],
        ]
    )
    await callback.message.edit_text(
        f"🏦 **المصرف المركزي**\n"
        f"💵 النقد في محفظتك: `{player['cash']:,}$` (معرض للسرقة)\n"
        f"🏦 رصيدك الجنسي: `{player['bank']:,}$` (يحصل على عوائد ادخارية دورية)\n\n"
        f"💡 *لتحويل مال لصديق في المجموعة: قم بالرد (رد) على رسالته وكتب:* `تحويل 500`"،
        reply_markup=kb,
        parse_mode="Markdown",
    )
    انتظر رد الاستدعاء.


@router.callback_query(F.data.startswith("bank_op:"))
async def cb_bank_op(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، المدينة = res
    _, op, _ = callback.data.split(":")

    conn = get_db()
    إذا كانت قيمة op تساوي "dep_all":
        إذا كان رصيد اللاعب أقل من أو يساوي صفرًا:
            wait callback.answer("ليس لديك نقد للإيداع!", show_alert=True)
            conn.close()
            يعود
        conn.execute(
            "تحديث بيانات اللاعبين: تعيين رصيد البنك = رصيد البنك + النقد، النقد = 0، الموقع = 'وسط المدينة' حيث معرف المستخدم = ؟ ومعرف المدينة = ؟",
            (player["user_id"], city["city_id"]),
        )
        msg = ""تم إيداع جميع أموالك النقدية في حسابك الخاص!"
    elif op == "wit_1000":
        أمت = دقيقة (1000، لاعب ["البنك"])
        إذا كانت القيمة أقل من أو تساوي صفرًا:
            wait callback.answer("رصيدك لكل الجسم!", show_alert=True)
            conn.close()
            يعود
        conn.execute(
            "تحديث بيانات اللاعبين: تعيين رصيد البنك = رصيد البنك - ؟، رصيد النقد = رصيد النقد + ؟، الموقع = 'وسط المدينة' حيث معرف المستخدم = ؟ ومعرف المدينة = ؟،
            (المبلغ، المبلغ، اللاعب["معرف_المستخدم"]، المدينة["معرف_المدينة"])،
        )
        msg = f"✅ تم سحب {amt}$ إلى محفظتك النقدية."
    آخر:
        إذا كان player["bank"] <= 0:
            wait callback.answer("رصيدك لكل الجسم!", show_alert=True)
            conn.close()
            يعود
        conn.execute(
            "تحديث بيانات اللاعبين: تعيين الرصيد النقدي = الرصيد النقدي + رصيد البنك، رصيد البنك = 0، الموقع = 'وسط المدينة' حيث معرف المستخدم = ؟ ومعرف المدينة = ؟",
            (player["user_id"], city["city_id"]),
        )
        msg = ""تم سحب كامل الرصيد إلى محفظتك."

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
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، المدينة = res
    uid = player["user_id"]
    idx = city["price_index"]

    الأزرار = []
    for h_key, h in HOUSES.items():
        السعر = int(h["base_price"] * idx)
        buttons.append([InlineKeyboardButton(text=f"شراء {h['name']} ({price:,}$)", callback_data=f"buy_house:{h_key}:{uid}")])
    for v_key, v in VEHICLES.items():
        السعر = int(v["base_price"] * idx)
        buttons.append([InlineKeyboardButton(text=f"شراء {v['name']} ({price:,}$)", callback_data=f"buy_veh:{v_key}:{uid}")])
    Buttons.append([InlineKeyboardButton(text="🔙 العودة للمدينة", callback_data=f"main_menu:{uid}")])

    await callback.message.edit_text(
        "🏠 **سوق عقود ومعرض السيارات**\nامتلاك منزل مع راحة مجانية و استعادة أسرع للطلب، وامتلاك مركبة تحدد جهد الجر:"،
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown",
    )
    انتظر رد الاستدعاء.


@router.callback_query(F.data.startswith("buy_house:"))
async def cb_buy_house(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، المدينة = res
    _, h_key, _ = callback.data.split(":")
    house = HOUSES[h_key]
    السعر = int(house["base_price"] * city["price_index"])

    إذا كان رصيد اللاعب أقل من السعر:
        wait callback.answer(f"💵 تحتاج إلى {price:,}$نقودًا في محفظتك لشراء {house['name']}!", show_alert=True)
        يعود

    conn = get_db()
    conn.execute(
        "تحديث بيانات اللاعبين: تعيين الرصيد النقدي = الرصيد النقدي - ؟، المنزل = ؟، الموقع = 'سكني' حيث معرف المستخدم = ؟ ومعرف المدينة = ؟،
        (السعر، h_key، player["user_id"]، city["city_id"])،
    )
    conn.commit()
    conn.close()
    adjust_city_demand(city["city_id"], 0.03)
    wait callback.answer(f"🏡 مبارك! أصبحت مالكًا لـ {house['name']}!", show_alert=True)

    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    city ​​= get_group_city(callback.message.chat.id)
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("buy_veh:"))
async def cb_buy_veh(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، المدينة = res
    _, v_key, _ = callback.data.split(":")
    veh = VEHICLES[v_key]
    السعر = int(veh["base_price"] * city["price_index"])

    إذا كان رصيد اللاعب أقل من السعر:
        wait callback.answer(f"💵 تحتاج إلى {price:,}$ نقدًا لشراء {veh['name']}!", show_alert=True)
        يعود

    conn = get_db()
    conn.execute(
        "تحديث جدول اللاعبين: تعيين الرصيد النقدي = الرصيد النقدي - ؟، المركبة = ؟، الموقع = 'السوق' حيث معرف المستخدم = ؟ ومعرف المدينة = ؟،
        (السعر، المفتاح الافتراضي، اللاعب["معرف المستخدم"]، المدينة["معرف المدينة"])،
    )
    conn.commit()
    conn.close()
    adjust_city_demand(city["city_id"], 0.02)
    wait callback.answer(f"🚗 مبارك! اشتريت {veh['name']} فعال!", show_alert=True)

    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    city ​​= get_group_city(callback.message.chat.id)
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("biz_menu:"))
async def cb_biz_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، المدينة = res
    uid = player["user_id"]
    idx = city["price_index"]

    conn = get_db()
    مملوكة = conn.execute(
        "SELECT custom_name, biz_type FROM businesss WHERE city_id = ? AND owner_id = ?",
        (city["city_id"], uid),
    ).fetchall()
    conn.close()

    owned_lines = [f"• {r['custom_name']} (+{BUSINESS_TYPES[r['biz_type']]['hourly_income']}$ كل ساعة)" for r in owned]
    تملك_نص = "\n".join(OWN_LINES) إذا تملكها_خطوط أخرى "لا تملك المشاريع التجارية بعد."

    الأزرار = []
    for b_key, b in BUSINESS_TYPES.items():
        السعر = int(b["base_price"] * idx)
        buttons.append(
            [
                زر لوحة المفاتيح المضمن (
                    text=f"تأسيس {b['name']} ({price:,}$ | إختيار: +{b['hourly_venue']}$)",
                    callback_data=f"buy_biz:{b_key}:{uid}",
                )
            ]
        )
    Buttons.append([InlineKeyboardButton(text="🔙 العودة للمدينة", callback_data=f"main_menu:{uid}")])

    await callback.message.edit_text(
        f"🏢 **غرفة التجارة والمشاريع الاستثمارية**\n"
        f"المشاريع تدر أرباحاً تلقائية تُودع في حسابك الشخصي حتى وأنت غير متصل:\n\n"
        f"📋 **مشاريعك الحالية:**\n{OWN_text}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown",
    )
    انتظر رد الاستدعاء.


@router.callback_query(F.data.startswith("buy_biz:"))
async def cb_buy_biz(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، المدينة = res
    _, b_key, _ = callback.data.split(":")
    biz = BUSINESS_TYPES[b_key]
    السعر = int(biz["base_price"] * city["price_index"])

    إذا كان رصيد اللاعب أقل من السعر:
        wait callback.answer(f"💵 تحتاج إلى {price:,}$ نقدًا لتأسيس {biz['name']}!", show_alert=True)
        يعود

    conn = get_db()
    conn.execute(
        "تحديث بيانات اللاعبين، تعيين الرصيد النقدي = الرصيد النقدي - ؟، الموقع = 'صناعي' حيث معرف المستخدم = ؟ ومعرف المدينة = ؟",
        (السعر، اللاعب["معرف_المستخدم"]، المدينة["معرف_المدينة"])،
    )
    conn.execute(
        "INSERT INTO businesss (city_id, owner_id, biz_type, custom_name, created_at) VALUES (?, ?, ?, ?, ?)",
        (city["city_id"], player["user_id"], b_key, f"{biz['name']} ({player['username']})", int(time.time())),
    )
    conn.commit()
    conn.close()

    wait callback.answer(f"🎉 مبارك! أسست مشروع {biz['name']} وسيبدأ بإدرار الاندرويد الوكيل!", show_alert=True)
    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )


# ==========================================
#12. نظام الشرطة، العصابات، والسرقة الافتراضية المتوازنة
# ==========================================
@router.callback_query(F.data.startswith("crime_menu:"))
async def cb_crime_menu(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، _ = res
    uid = player["user_id"]

    kb = InlineKeyboardMarkup(
        لوحة المفاتيح المضمنة = [
            [InlineKeyboardButton(text="🕶️ عملية سطو افتراضية على متجر خزنة (-25⚡)", callback_data=f"do_heist:store:{uid}")],
            [InlineKeyboardButton(text="🏦التجربة الكبرى: خزنة المصرف (-45⚡ | شهادة عالية)", callback_data=f"do_heist:bank:{uid}")],
            [InlineKeyboardButton(text="🏴 الانضمام/تأسيس عصابة الصقور", callback_data=f"join_gang:الصقور:{uid}")],
            [InlineKeyboardButton(text="🏴 الانضمام/تأسيس عصابة الظل", callback_data=f"join_gang:الظل:{uid}")],
            [InlineKeyboardButton(text="🔙 العودة للمدينة", callback_data=f"main_menu:{uid}")],
        ]
    )
    await callback.message.edit_text(
        "🕶️ **الأزقة الخلفية والعصابات (نظام الاحتمالات خيالي)**\n"
        "⚠️ كل العملية تحمل جزء من الفشل وتترك مطلوبًا تمنىًا تضعك على قائمة المطلوبين للشرطة!\n"
        "💡 *لسرقة محفظة اللاعب الأخير في المجموعة: رد (Reply) على رسالته بكلمة:* `سرقة`",
        reply_markup=kb,
        parse_mode="Markdown",
    )
    انتظر رد الاستدعاء.


@router.callback_query(F.data.startswith("join_gang:"))
async def cb_join_gang(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، المدينة = res
    _, g_name, _ = callback.data.split(":")

    conn = get_db()
    conn.execute(
        "تحديث اللاعبين SET gang_name = ?, location = 'back_alleys' WHERE user_id = ? AND city_id = ?",
        (f"الشخصية {g_name}", player["user_id"], city["city_id"]),
    )
    conn.commit()
    conn.close()

    wait callback.answer(f"🕶️ انضممت الآن إلى عصابة {g_name}!", show_alert=True)
    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("do_heist:"))
async def cb_do_heist(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، المدينة = res
    _, target, _ = callback.data.split(":")

    إذا كان اللاعب["jail_until"] > int(time.time()):
        wait callback.answer("🔒 أنت موقوف في السجن حاليًا!", show_alert=True)
        يعود

    energy_req = 25 إذا كان الهدف == "store" وإلا 45
    إذا كانت طاقة اللاعب أقل من الطاقة المطلوبة:
        wait callback.answer(f"⚡ طاقتك غير كافية! تحتاج {energy_req}% طاقة.", show_alert=True)
        يعود

    gang_bonus = 12 إذا كان player["gang_name"] وإلا 0
    فرصة النجاح = (55 إذا كان الهدف == "متجر" وإلا 30) + مكافأة العصابة
    roll = random.randint(1, 100)

    conn = get_db()
    إذا كانت نتيجة الرمية أقل من أو تساوي فرصة النجاح:
        الغنائم = random.randint(400, 900) إذا كان الهدف == "متجر" وإلا random.randint(2000, 4500)
        wanted_add = 1 إذا كان الهدف == "store" وإلا 3
        conn.execute(
            "تحديث بيانات اللاعبين: تعيين الرصيد النقدي = الرصيد النقدي + ؟، الطاقة = الطاقة - ؟، مستوى المطلوبين = مستوى المطلوبين + ؟، الموقع = 'الأزقة الخلفية' حيث يكون معرف المستخدم = ؟ ومعرف المدينة = ؟"
            (الغنائم، طلب الطاقة، إضافة مطلوب، اللاعب["معرف المستخدم"]، المدينة["معرف المدينة"])،
        )
        conn.commit()
        conn.close()
        انتظر رد الاستدعاء.
            f"🕶️ بعد الانتهاء من الوصول إلى {loot}$! لكن المدينة رصدت بعدك (+{wanted_add}⭐ مطلوب للشرطة)."،
            show_alert=True,
        )
    آخر:
        غرامة = 250 إذا كان الهدف == "متجر" وإلا 800
        jail_sec = 180 إذا كان الهدف هو "متجر" وإلا 360
        jail_until = int(time.time()) + jail_sec
        conn.execute(
            """
            تحديث اللاعبين
            SET cash = MAX(0, cash - ?), energy = energy - ?, wanted_level = 0, jail_until = ?, location = 'police'
            حيث يكون user_id = ؟ و city_id = ؟
            "",
            (غرامة، متطلبات الطاقة، السجن حتى، اللاعب["معرف المستخدم"]، المدينة["معرف المدينة"])،
        )
        conn.commit()
        conn.close()
        انتظر رد الاستدعاء.
            f"🚓 طلق جرس الإنذار وألقت دورية الشرطة القبض عليك! غرامة {fine}$ وتوقيف لمدة {jail_sec // 60} راحة.",
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
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، المدينة = res
    uid = player["user_id"]

    conn = get_db()
    قائمة_المطلوبين = conn.execute(
        "SELECT user_id, username, wanted_level, location FROM players WHERE city_id = ? AND wanted_level > 0 ORDER BY wanted_level DESC LIMIT 10",
        (city["city_id"],),
    ).fetchall()
    conn.close()

    Lines = ["🚓 **مركز قيادة الشرطة والمحكمة**\n"]
    الأزرار = []
    إذا كانت قائمة المطلوبين:
        lines.append("📋 **قائمة المطلوبين أمنيًا في المدينة:**")
        لكل عنصر w في قائمة المطلوبين:
            loc_ar = LOCATIONS.get(w["location"], w["location"])
            lines.append(f"• **{w['username']}** — الخطورة: `{w['wanted_level']}⭐` — آخر وضوح: {loc_ar}")
            إذا كان player["job"] == "police_officer" و w["user_id"] != uid:
                buttons.append(
                    [
                        زر لوحة المفاتيح المضمن (
                            text=f"🚔 ملاحقة ولقاء بمقبض على {w['username']} (+350$ مكافأة)"،
                            callback_data=f"arrest:{w['user_id']}:{uid}",
                        )
                    ]
                )
    آخر:
        lines.append("✔ المدينة آمنة حاليًا ولا يوجد مطلوبون على القائمة.")

    إذا كان مستوى اللاعب المطلوب أكبر من 0:
        تكلفة_الكفالة = مستوى_المطلوب_للاعب * 400
        buttons.append(
            [InlineKeyboardButton(text=f"⚖️ تعرف على نفسك اتفاق مشترك ({bail_cost}$)", callback_data=f"pay_bail:{uid}")]
        )

    Buttons.append([InlineKeyboardButton(text="🔙 العودة للمدينة", callback_data=f"main_menu:{uid}")])
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="Markdown",
    )
    انتظر رد الاستدعاء.


@router.callback_query(F.data.startswith("arrest:"))
async def cb_arrest_wanted(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    ضابط، مدينة = سكن
    _, target_uid_str, _ = callback.data.split(":")
    target_uid = int(target_uid_str)

    إذا كان اسم الضابط["الوظيفة"] لا يساوي "ضابط شرطة":
        wait callback.answer("⚠️ يجب أن تعمل كضابط شرطة وتوجيهات القبض!", show_alert=True)
        يعود

    conn = get_db()
    المشتبه به = conn.execute(
        "SELECT * FROM players WHERE user_id = ? AND city_id = ?",
        (target_uid, city["city_id"]),
    ).fetchone()

    إذا لم يكن مشتبهاً به أو كان مستوى_المطلوب_للمشتبه_به أقل من أو يساوي 0:
        conn.close()
        Wait callback.answer("هذا اللاعب لم يعد مطلوبًا للشرطة!", show_alert=True)
        يعود

    المكافأة = مستوى_المطلوب_للمشتبه_به * 350
    الغرامة = المشتبه به["المستوى المطلوب"] * 300
    jail_until = int(time.time()) + 240

    conn.execute(
        "تحديث اللاعبين SET wanted_level = 0, jail_until = ?, cash = MAX(0, cash - ?), location = 'police' WHERE user_id = ? AND city_id = ?",
        (jail_until, fine, target_uid, city["city_id"]),
    )
    conn.execute(
        "تحديث جدول اللاعبين: تعيين الرصيد النقدي = الرصيد النقدي + ؟، نقاط الخبرة = نقاط الخبرة + 40 حيث يكون معرف المستخدم = ؟ ومعرف المدينة = ؟"
        (مكافأة، ضابط["معرف_المستخدم"]، مدينة["معرف_المدينة"])،
    )
    conn.commit()
    conn.close()

    wait callback.answer(f"🚔 ألقيت القبض على {suspect['username']} الذي تم مكافأة {reward}$!", show_alert=True)
    officer = get_or_create_player(officer["user_id"], city["city_id"], officer["username"])
    await callback.message.edit_text(
        format_player_dashboard(officer, city),
        reply_markup=build_main_city_keyboard(officer["user_id"]),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("pay_bail:"))
async def cb_pay_bail(callback: CallbackQuery) -> None:
    res = check_owner_and_city(callback)
    إذا لم يكن res:
        wait callback.answer("⚠️ هذه اللوحة الخاصة بلاعب آخر!", show_alert=True)
        يعود
    اللاعب، المدينة = res
    تكلفة_الكفالة = مستوى_المطلوب_للاعب * 400
    إذا كان رصيد اللاعب النقدي أقل من تكلفة الكفالة:
        wait callback.answer(f"💵 تحتاج إلى {bail_cost}$ نقدًا لتسوية ملفك الضبط!", show_alert=True)
        يعود

    conn = get_db()
    conn.execute(
        "تحديث بيانات اللاعبين: تعيين الرصيد النقدي = الرصيد النقدي - ؟، مستوى المطلوب = 0، الموقع = 'الشرطة' حيث معرف المستخدم = ؟ ومعرف المدينة = ؟",
        (bail_cost, player["user_id"], city["city_id"]),
    )
    conn.execute("UPDATE cities SET treasury = treasury + ? WHERE city_id = ?", (bail_cost, city["city_id"]))
    conn.commit()
    conn.close()

    wait callback.answer(""اتفاقية اتفاقية وضعك وأصبح سجلك الثقافي الشامل!", show_alert=True)
    player = get_or_create_player(player["user_id"], city["city_id"], player["username"])
    city ​​= get_group_city(callback.message.chat.id)
    await callback.message.edit_text(
        format_player_dashboard(player, city),
        reply_markup=build_main_city_keyboard(player["user_id"]),
        parse_mode="Markdown",
    )


# ==========================================
# 13.الأوامر التفاعلية (الرد) بين الأعضاء
# ==========================================
@router.message(F.text.startswith("تحويل"))
async def msg_reply_transfer(message: Message) -> None:
    إذا لم تكن الرسالة هي الرد على الرسالة أو لم تكن الرسالة هي الرد على الرسالة من المستخدم:
        يعود
    city ​​= get_group_city(message.chat.id)
    إن لم تكن المدينة:
        يعود

    الأجزاء = الرسالة.النص.التجريد().تقسيم()
    إذا كان طول (الأجزاء) أقل من 2 أو لم يكن الجزء [1].isdigit():
        wait message.reply("⚠️ الصيغة الصحيحة للإجابة على رسالة العضو: `تحويل 500`"، parse_mode="Markdown")
        يعود

    المبلغ = عدد صحيح (الأجزاء[1])
    إذا كان المبلغ ≤ 0:
        يعود

    sender = get_or_create_player(message.from_user.id, city["city_id"], message.from_user.full_name or " شهر")
    receiver_user = message.reply_to_message.from_user
    إذا كان المستخدم المُستقبِل روبوتًا أو كان مُعرِّف المستخدم المُستقبِل يساوي مُعرِّف المستخدم المُرسِل:
        wait message.reply("⚠️ لا يمكنك التحول لشخص أو لبوت!")
        يعود

    receiver = get_or_create_player(receiver_user.id, city["city_id"], receiver_user.full_name or " ]

    إذا كان المبلغ المدفوع نقدًا أقل من المبلغ الإجمالي:
        Wait message.reply("💵 رصيدك النقدي في البنك غير متكامل لإتمام التحويل!")
        يعود

    conn = get_db()
    conn.execute(
        "تحديث جدول اللاعبين، تعيين الرصيد النقدي = الرصيد النقدي - ؟ حيث معرف المستخدم = ؟ ومعرف المدينة = ?",
        (المبلغ، المرسل["معرف_المستخدم"]، المدينة["معرف_المدينة"])،
    )
    conn.execute(
        "تحديث جدول اللاعبين، تعيين الرصيد النقدي = الرصيد النقدي + ؟ حيث يكون معرف المستخدم = ؟ ومعرف المدينة = ?",
        (المبلغ، المستلم["معرف_المستخدم"]، المدينة["معرف_المدينة"])،
    )
    conn.commit()
    conn.close()

    انتظر الرد على الرسالة.
        f"💸 تم تحويل `{amount:,}$` من **{sender['username']}** إلى **{receiver['username']}** فعال!",
        parse_mode="Markdown",
    )


@router.message(F.text == "سرقة")
async def msg_reply_pickpocket(message: Message) -> None:
    إذا لم تكن الرسالة هي الرد على الرسالة أو لم تكن الرسالة هي الرد على الرسالة من المستخدم:
        يعود
    city ​​= get_group_city(message.chat.id)
    إن لم تكن المدينة:
        يعود

    thief = get_or_create_player(message.from_user.id, city["city_id"], message.from_user.full_name or " بطل")
    victim_user = message.reply_to_message.from_user
    إذا كان المستخدم الضحية روبوتًا أو كان معرف المستخدم الضحية يساوي معرف المستخدم المرسل:
        يعود

    إذا كان thief["jail_until"] > int(time.time()):
        Wait message.reply("🔒 أنت موقوف في السجن ولا يمكنك القيام بأي نشاط!")
        يعود
    إذا كانت طاقة اللص أقل من 15:
        انتظر الرسالة. الرد ("⚡ طاقتك منخفضة جدًا!")
        يعود

    victim = get_or_create_player(victim_user.id, city["city_id"], victim_user.full_name or " بطل")
    إذا كان المبلغ النقدي للضحية أقل من 50:
        wait message.reply(f"🤷‍♂️ محفظة **{victim['username']}** شبه انجليزي (أقل من 50$)، وضع كل أمواله في المصرف!", parse_mode="Markdown")
        يعود

    conn = get_db()
    إذا كان عدد الأرقام العشوائية (1، 100) أقل من أو يساوي 45:
        مسروق = الحد الأقصى (25، عدد صحيح (الضحية["نقود"] * عشوائي.موحد (0.10، 0.25)))
        conn.execute(
            "تحديث بيانات اللاعبين: تعيين الرصيد النقدي = الرصيد النقدي + ؟، الطاقة = الطاقة - 15، مستوى_المطلوب = مستوى_المطلوب + 1 حيث معرف_المستخدم = ؟ ومعرف_المدينة = ؟،
            (مسروق، اللص["معرف_المستخدم"]، المدينة["معرف_المدينة"])،
        )
        conn.execute(
            "تحديث جدول اللاعبين، تعيين الرصيد النقدي = الرصيد النقدي - ؟ حيث معرف المستخدم = ؟ ومعرف المدينة = ?",
            (مسروق، الضحية["معرف_المستخدم"]، المدينة["معرف_المدينة"])،
        )
        conn.commit()
        conn.close()
        انتظر الرد على الرسالة.
            f"🕶️ قادر **{thief['username']}** من نشل `{stolen}$` من المحفظة **{victim['username']}**! "
            f"(أصبح مطلوباً للشرطة 🚨 — نصيحة: وأودعوا تمويلكم في المصرف لحمايتها)."،
            parse_mode="Markdown",
        )
    آخر:
        conn.execute(
            "تحديث بيانات اللاعبين: تعيين الطاقة = الطاقة - 15، مستوى_المطلوب = مستوى_المطلوب + 1 حيث معرف_المستخدم = ؟ ومعرف_المدينة = ؟"
            (thief["user_id"], city["city_id"]),
        )
        conn.commit()
        conn.close()
        انتظر الرد على الرسالة.
            f"🚨 لا تنسى **{victim['username']}** لمحاولة سرقة وفشل خطة **{thief['username']}** وتم تمكن الشرطة!",
            parse_mode="Markdown",
        )


# ==========================================
# 14.محرك الزمن التلقائي للمدينة + خادم ويب لـ Render
# ==========================================
async def city_tick_engine() -> None:
    """دورة حياة المدينة كل 15 دقيقة: أرباح الشركات، فوائد المصرف، وجديد الطاقة"""
    بينما صحيح:
        await asyncio.sleep(900)
        يحاول:
            conn = get_db()
            cur = conn.cursor()

            businesss = cur.execute("SELECT city_id, owner_id, biz_type FROM businesss").fetchall()
            بالنسبة لـ b في الشركات:
                الدخل = BUSINESS_TYPES.get(b["biz_type"], {}).get("hourly_income", 200)
                cur.execut(
                    "تحديث اللاعبين SET bank = bank + ? WHERE user_id = ? AND city_id = ?",
                    (الدخل، b["owner_id"]، b["city_id"])،
                )

            cur.execut(
                """
                تحديث اللاعبين
                SET energy = MIN(100, energy + CASE WHEN house IS NOT NULL THEN 20 ELSE 10 END),
                    bank = bank + CAST(bank * 0.01 AS INTEGER)
                """
            )

            conn.commit()
            conn.close()
            logger.info("تم تنفيذ الدورة الزمنية التلقائية للفعالية."")
        باستثناء الاستثناء كما يلي:
            logger.error(f" خطأ في الزمن: {exc}")


async def handle_health_check(request: web.Request) -> web.Response:
    """ صفحة فحص النشاط لمنصة Render ولمنع سكون البناء لتكوين قالب"""
    return web.Response(text="يعمل روبوت مدينة هورايزون على مدار الساعة طوال أيام الأسبوع!")


async def start_render_web_server() -> None:
    """تشغيل خادم HTTP خفيف على المنفذ PORT ليتوافق مع Render Free Web Service"""
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    app.router.add_get("/health", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    logger.info(f"🌐 خادم الويب الخاص بـ Render يعمل على المنفذ {PORT}")


# ==========================================
# 15. تشغيل نقطة بوت
# ==========================================
async def main() -> None:
    init_db()
    await start_render_web_server()

    إذا كان رمز البوت يساوي "ضع رمز البوت الخاص بك هنا":
        logger.warning("⚠️ يرجى إضافة عناصر متغيرة إلى BOT_TOKEN في إعدادات Render!")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    asyncio.create_task(city_tick_engine())

    logger.info("🚀 بوت مدينة الأفق يعمل الآن...")
    await dp.start_polling(bot)


إذا كان __name__ == "__main__":
    asyncio.run(main())
