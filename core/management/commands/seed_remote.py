# core/management/commands/seed_remote.py
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Project, IntentType
from taxonomy.models import ServiceType
from content.models import Keyword


# ==========================================
# 1. فشرده‌سازی و تجمیع نیت‌ها (Intent Compression)
# ==========================================
INTENT_SEEDS = [
    ("commercial_buying", "Commercial & Buying", "نیت تجاری، استعلام قیمت و آماده خرید بودن کاربر"),
    ("emergency_local", "Emergency & Local", "نیت اورژانسی، نیاز به اعزام سیار و خدمات فوری در محل"),
    ("repair_troubleshooting", "Repair & Troubleshooting", "نیت عیب‌یابی، رفع خرابی و تعمیرات سخت‌افزاری/نرم‌افزاری"),
    ("informational", "Informational (Global)", "آموزش‌های مرجع و عمومی که به ماشین خاصی وابسته نیستند (لایه 0)"),
    ("informational_diy", "Informational DIY (Cluster)", "آموزش‌های گام‌به‌گام و عملی که مختص هر مدل ماشین هستند (لایه 3)"),
]

# ==========================================
# 2. سرویس‌های اصلی
# ==========================================
SERVICE_SEEDS = [
    {
        "code": "create_remote",
        "name": "ساخت ریموت/سوییچ/کلید",
        "slug": "create-remote-switch-key",
        "root_keyword": "ساخت ریموت",
        "description": "ساخت ریموت، سوییچ و کلید خودرو",
        "is_ecommerce": False,
        "modifiers": ["فوری", "در محل", "شبانه روزی", "اعزام فوری", "بدون نمونه", "سیار"],
    },
    {
        "code": "copy_remote",
        "name": "کپی ریموت (یدک)",
        "slug": "copy-remote",
        "root_keyword": "کپی ریموت",
        "description": "کپی و ساخت ریموت یدک خودرو",
        "is_ecommerce": False,
        "modifiers": ["یدک", "فوری", "در محل", "کددهی", "پروگرام", "تعریف کلید"],
    },
    {
        "code": "repair_remote",
        "name": "تعمیر ریموت",
        "slug": "repair-remote",
        "root_keyword": "تعمیر ریموت",
        "description": "تعمیر ریموت، برد، باتری و رفع خرابی",
        "is_ecommerce": False,
        "modifiers": ["برد", "باتری", "آب خوردگی", "فوری", "در محل", "عیب یابی", "قاب"],
    },
    {
        "code": "car_unlock",
        "name": "بازکردن درب خودرو",
        "slug": "car-unlock",
        "root_keyword": "بازکردن درب خودرو",
        "description": "خدمات باز کردن درب خودرو و رفع قفل اضطراری",
        "is_ecommerce": False,
        "modifiers": ["فوری", "بدون آسیب", "در محل", "شبانه روزی", "تضمینی"],
    },
    {
        "code": "sell_remote",
        "name": "فروش ریموت",
        "slug": "sell-remote",
        "root_keyword": "فروشگاه ریموت",
        "description": "فروش ریموت خودرو بر اساس برند و مدل",
        "is_ecommerce": True,
        "modifiers": ["اصل", "فابریک", "اورجینال", "سازگار", "جدید", "خام"],
    },
]

# ==========================================
# 3. ساختار مگا-پیلارها و کلاسترهای متصل (Hierarchical Structural Seeds)
# ==========================================
PILLAR_SEEDS = [
    {
        "text": "ریموت",
        "service_code": "sell_remote",
        "intent": "commercial_buying",
        "priority": 100,  # بالاترین اولویت برای لایه پیلار اصلی
        "extra": [
            "خرید ریموت", "تعمیر ریموت", "کددهی ریموت", "قیمت ریموت", "مقایسه قیمت ریموت", 
            "قاب ریموت", "باطری ریموت", "ریموت اصلی", "ریموت یدکی", "ریموت فابریکی", 
            "ساخت ریموت", "فروشگاه ریموت", "ارسال ریموت به سراسر کشور"
        ],
        "clusters": [
            {
                "text": "قیمت ریموت", 
                "intent": "commercial_buying", 
                "priority": 85, 
                "extra": ["استعلام قیمت ریموت خودرو", "لیست قیمت سوئیچ", "هزینه پروگرام ریموت", "قیمت ریموت فابریک", "ارزانترین قیمت ریموت"]
            },
            {
                "text": "قبل از خرید ریموت به چه نکاتی توجه کنیم", 
                "intent": "informational", 
                "priority": 75, 
                "extra": ["راهنمای خرید ریموت", "نکات خرید سوئیچ ماشین", "تشخیص ریموت اصلی از تقلبی", "فرکانس ریموت خودرو"]
            },
            {
                "text": "خرید ریموت", 
                "intent": "commercial_buying", 
                "priority": 90, 
                "extra": ["فروشگاه ریموت خودرو", "خرید آنلاین ریموت ماشین", "مرکز فروش سوئیچ خودرو", "قیمت خرید ریموت"]
            },
            {
                "text": "مقایسه ریموت", 
                "intent": "informational", 
                "priority": 75, 
                "extra": ["مقایسه قیمت ریموت", "انواع ریموت خودرو", "بهترین برند ریموت", "تفاوت ریموت فابریک و چینی"]
            },
            {
                "text": "بهترین ریموت", 
                "intent": "commercial_buying", 
                "priority": 80, 
                "extra": ["بهترین مارک ریموت ماشین", "ریموت با کیفیت خودرو", "راهنمای انتخاب بهترین ریموت"]
            },
            {
                "text": "ریموت فابریکی", 
                "intent": "commercial_buying", 
                "priority": 85, 
                "extra": ["قیمت ریموت فابریک", "خرید سوئیچ اورجینال", "ریموت اصلی خودرو", "ریموت فابریک دزدگیر"]
            },
            {
                "text": "ریموت اصلی", 
                "intent": "commercial_buying", 
                "priority": 85, 
                "extra": ["ریموت اورجینال ماشین", "خرید سوئیچ اصلی خودرو", "قیمت کلید فابریک"]
            },
            {
                "text": "قاب ریموت", 
                "intent": "commercial_buying", 
                "priority": 80, 
                "extra": ["خرید قاب سوئیچ", "قیمت قاب ریموت ماشین", "قاب ریموت تاشو", "تعویض قاب کلید خودرو"]
            },
            {
                "text": "باتری ریموت", 
                "intent": "commercial_buying", 
                "priority": 80, 
                "extra": ["خرید باطری ریموت", "قیمت باتری کلید ماشین", "سایز باتری ریموت خودرو", "عمر باطری سوئیچ"]
            },
        ]
    },
    {
        "text": "ساخت ریموت ",
        "service_code": "create_remote",
        "intent": "emergency_local",
        "priority": 100,  # بالاترین اولویت برای لایه پیلار دوم
        "extra": [
            "گم شدن سوئیچ", "ساخت کلید مفقودی", "کلیدساز سیار خودرو", "حذف کدهای ریموت گمشده", 
            "ساخت سوئیچ بدون نمونه", "ساخت ریموت/سوییچ/کلید", "قیمت ساخت ریموت", "هزینه کلیدسازی شبانه روزی", 
            "روشن کردن ماشین بدون کلید", "فوری", "در محل", "شبانه روزی", "اعزام فوری", "بدون نمونه", "سیار", " ساخت ریموت در محل"
        ],
        "clusters": [
            {
                "text": "کپی ریموت و ساخت سوئیچ یدک", 
                "intent": "commercial_buying", 
                "priority": 85, 
                "extra": ["قیمت کپی ریموت", "پروگرام و کددهی ریموت", "تعریف کلید دوم", "هزینه سوئیچ یدک", "ساخت ریموت دوم", "ست کردن ریموت با دیاگ", "تکثیر کلید ماشین"]
            },
            {
                "text": "در صورت گم شدن ریموت خودرو چه کنیم", 
                "intent": "informational_diy", 
                "priority": 70, 
                "extra": ["اگر ریموت گم شد چه کنیم", "بعد از گم شدن کلید خودرو چه باید کرد", "آیا با گم شدن ریموت ماشین روشن می شود", "پاک کردن کد کلید گمشده از ECU"]
            },
            {
                "text": "تعمیر ریموت و سوئیچ کیلس", 
                "intent": "repair_troubleshooting", 
                "priority": 80, 
                "extra": ["ریموت کار نمی کند", "قیمت تعمیر ریموت", "ریموت خیس شده و آب خورده", "تعمیر برد سوئیچ", "تعمیر قاب کلید شکسته", "تعمیر باتری ریموت", "عیب یابی کیلس گو"]
            },
            {
                "text": "آموزش تعویض باتری ریموت", 
                "intent": "informational_diy", 
                "priority": 75, 
                "extra": ["نحوه باز کردن قاب ریموت", "سایز باتری ریموت", "چگونه باتری کلید ماشین را عوض کنیم", "آلارم ضعیف بودن باتری ریموت"]
            },
            {
                "text": "بازکردن درب خودرو بدون کلید", 
                "intent": "emergency_local", 
                "priority": 95, 
                "extra": ["در ماشین باز نمی شود", "جا ماندن کلید داخل ماشین", "باز کردن قفل صندوق عقب", "امداد قفل سیار", "باز کردن درب ماشین بدون آسیب", "باز کردن در ماشین قفل شده"]
            },
            {
                "text": "کد دهی و پروگرام ریموت", 
                "intent": "commercial_buying", 
                "priority": 80, 
                "extra": ["آموزش کددهی ریموت", "دستگاه پروگرامر سوئیچ", "هزینه تعریف کلید ماشین", "ست کردن ریموت دزدگیر"]
            },
            {
                "text": "سوییج ریموت", 
                "intent": "commercial_buying", 
                "priority": 80, 
                "extra": ["خرید سوئیچ ریموت دار", "قیمت سوییچ ماشین", "ساخت کلید ریموت خودرو"]
            },
            {
                "text": "روشن نشدن ریموت", 
                "intent": "repair_troubleshooting", 
                "priority": 75, 
                "extra": ["علت روشن نشدن چراغ ریموت", "کار نکردن کنترل ماشین", "خرابی برد سوئیچ"]
            },
            {
                "text": "خراب شدن ریموت", 
                "intent": "repair_troubleshooting", 
                "priority": 75, 
                "extra": ["علت خراب شدن ریموت ماشین", "تعمیر سوئیچ خراب", "ریموت کار نمیکند"]
            },
            {
                "text": "از کار افتادن ریموت", 
                "intent": "repair_troubleshooting", 
                "priority": 75, 
                "extra": ["علت از کار افتادن ناگهانی ریموت", "غیرفعال شدن سوئیچ خودرو", "ست کردن مجدد ریموت"]
            },
            {
                "text": "کلید سازی", 
                "intent": "emergency_local", 
                "priority": 85, 
                "extra": ["کلیدسازی سیار", "قفل و کلید سازی شبانه روزی", "شماره کلیدساز نزدیک من"]
            },
            # لوکیشن کلاسترهای منطقه شمال و غرب تهران (کامل شده با ال اس آی محلی غنی برای اهداف ایجنت‌ها)
            {"text": "ساخت ریموت در الهیه", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار الهیه", "ساخت سوئیچ یدک الهیه", "امداد ریموت شبانه روزی الهیه", "باز کردن درب ماشین الهیه"]},
            {"text": "ساخت ریموت در زعفرانیه", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار زعفرانیه", "ساخت سوئیچ یدک زعفرانیه", "امداد ریموت شبانه روزی زعفرانیه", "باز کردن درب ماشین زعفرانیه"]},
            {"text": "ساخت ریموت در نیاوران", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار نیاوران", "ساخت سوئیچ یدک نیاوران", "امداد ریموت شبانه روزی نیاوران", "باز کردن درب ماشین نیاوران"]},
            {"text": "ساخت ریموت در فرمانیه", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار فرمانیه", "ساخت سوئیچ یدک فرمانیه", "امداد ریموت شبانه روزی فرمانیه", "باز کردن درب ماشین فرمانیه"]},
            {"text": "ساخت ریموت در ولنجک", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار ولنجک", "ساخت سوئیچ یدک ولنجک", "امداد ریموت شبانه روزی ولنجک", "باز کردن درب ماشین ولنجک"]},
            {"text": "ساخت ریموت در کامرانیه", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار کامرانیه", "ساخت سوئیچ یدک کامرانیه", "امداد ریموت شبانه روزی کامرانیه", "باز کردن درب ماشین کامرانیه"]},
            {"text": "ساخت ریموت در اقدسیه", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار اقدسیه", "ساخت سوئیچ یدک اقدسیه", "امداد ریموت شبانه روزی اقدسیه", "باز کردن درب ماشین اقدسیه"]},
            {"text": "ساخت ریموت در صادقیه", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار صادقیه", "ساخت سوئیچ یدک صادقیه", "امداد ریموت شبانه روزی صادقیه", "باز کردن درب ماشین صادقیه"]},
            {"text": "ساخت ریموت در اندرزگو", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار اندرزگو", "ساخت سوئیچ یدک اندرزگو", "امداد ریموت شبانه روزی اندرزگو", "باز کردن درب ماشین اندرزگو"]},
            {"text": "ساخت ریموت در قیطریه", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار قیطریه", "ساخت سوئیچ یدک قیطریه", "امداد ریموت شبانه روزی قیطریه", "باز کردن درب ماشین قیطریه"]},
            {"text": "ساخت ریموت در شهرک غرب", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار شهرک غرب", "ساخت سوئیچ یدک شهرک غرب", "امداد ریموت شبانه روزی شهرک غرب", "باز کردن درب ماشین شهرک غرب"]},
            {"text": "ساخت ریموت در سعادت‌آباد", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار سعادت آباد", "ساخت سوئیچ یدک سعادت آباد", "امداد ریموت شبانه روزی سعادت آباد", "باز کردن درب ماشین سعادت آباد"]},
            {"text": "ساخت ریموت در جردن", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار جردن", "ساخت سوئیچ یدک جردن", "امداد ریموت شبانه روزی جردن", "باز کردن درب ماشین جردن"]},
            {"text": "ساخت ریموت در پاسداران", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار پاسداران", "ساخت سوئیچ یدک پاسداران", "امداد ریموت شبانه روزی پاسداران", "باز کردن درب ماشین پاسداران"]},
            {"text": "ساخت ریموت در دروس", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار دروس", "ساخت سوئیچ یدک دروس", "امداد ریموت شبانه روزی دروس", "باز کردن درب ماشین دروس"]},
            {"text": "ساخت ریموت در تهرانپارس", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار تهرانپارس", "ساخت سوئیچ یدک تهرانپارس", "امداد ریموت شبانه روزی تهرانپارس", "باز کردن درب ماشین تهرانپارس"]},
            {"text": "ساخت ریموت در نارمک", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار نارمک", "ساخت سوئیچ یدک نارمک", "امداد ریموت شبانه روزی نارمک", "باز کردن درب ماشین نارمک"]},
            {"text": "ساخت ریموت در پیروزی", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار پیروزی", "ساخت سوئیچ یدک پیروزی", "امداد ریموت شبانه روزی در پیروزی", "باز کردن درب ماشین پیروزی"]},
            {"text": "ساخت ریموت شمال تهران", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار شمال تهران", "ساخت سوئیچ یدک شمال تهران", "امداد ریموت شبانه روزی شمال تهران", "باز کردن درب ماشین شمال تهران"]},
            {"text": "ساخت ریموت جنوب تهران", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار جنوب تهران", "ساخت سوئیچ یدک جنوب تهران", "امداد ریموت شبانه روزی جنوب تهران", "باز کردن درب ماشین جنوب تهران"]},
            {"text": "ساخت ریموت شرق تهران", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار شرق تهران", "ساخت سوئیچ یدک شرق تهران", "امداد ریموت شبانه روزی شرق تهران", "باز کردن درب ماشین شرق تهران"]},
            {"text": "ساخت ریموت غرب تهران", "intent": "emergency_local", "priority": 85, "extra": ["کلیدسازی سیار غرب تهران", "ساخت سوئیچ یدک غرب تهران", "امداد ریموت شبانه روزی غرب تهران", "باز کردن درب ماشین غرب تهران"]},
        ]
    }
]

GLOBAL_SEEDS = {
    "repair_remote": [
        {
            "text": "علت خالی شدن سریع باتری ریموت ماشین",
            "intent": "informational",
            "priority": 55,
            "extra": ["چرا باطری ریموت زود تمام میشود", "جریان کشی برد ریموت خودرو", "عمر مفید باتری سوئیچ", "علت داغ شدن باتری سوئیچ ماشین"]
        },
        {
            "text": "علائم خرابی برد ریموت کنترل ماشین",
            "intent": "informational",
            "priority": 50,
            "extra": ["تست سلامت برد سوئیچ", "نشانه های سوختن برد ریموت", "تعمیر برد کنترل خودرو", "علت قطع شدن سیگنال ریموت"]
        },
        {
            "text": "علت پارازیت و کم شدن برد ریموت خودرو",
            "intent": "informational",
            "priority": 50,
            "extra": ["چرا ریموت از دور کار نمیکند", "علت ضعیف شدن آنتن ریموت دزدگیر", "رفع نویز ریموت ماشین", "تقویت برد کنترل خودرو"]
        },
        {
            "text": "راهنمای نگهداری و افزایش طول عمر ریموت ماشین",
            "intent": "informational",
            "priority": 45,
            "extra": ["مراقبت از سوئیچ خودرو", "جلوگیری از خراب شدن ریموت", "تاثیر کاور سیلیکونی ریموت", "تمیز کردن برد سوئیچ ماشین"]
        }
    ],
    "copy_remote": [
        {
            "text": "فرکانس ریموت خودرو چیست و چگونه تشخیص دهیم",
            "intent": "informational",
            "priority": 55,
            "extra": ["فرکانس 315 یا 433", "دستگاه فرکانس یاب ریموت", "تشخیص فرکانس سوئیچ خودرو", "تغییر فرکانس ریموت دزدگیر"]
        },
        {
            "text": "ریموت بلوتوثی چیست و نحوه کپی آن",
            "intent": "informational",
            "priority": 50,
            "extra": ["کپی ریموت بدون دستگاه", "ریموت کپی شونده چیست", "روش خام کردن ریموت بلوتوثی", "فرکانس ریموت بلوتوثی"]
        },
        {
            "text": "ست کردن ریموت پارکینگ روی ریموت خودرو",
            "intent": "informational",
            "priority": 55,
            "extra": ["کپی ریموت درب بازکن روی دکمه ماشین", "همگام سازی ریموت پارکینگ و سوئیچ", "تعریف ریموت خانه روی ماشین", "کپی ریموت پارکینگ با ریموت دزدگیر"]
        },
        {
            "text": "خطرات کپی کردن غیرمجاز ریموت خودرو",
            "intent": "informational",
            "priority": 40,
            "extra": ["امنیت کلیدسازی خودرو", "هک سیگنال ریموت", "کپی مخفیانه سوئیچ ماشین", "روش های سرقت با ریموت کپی"]
        }
    ],
    "create_remote": [
        {
            "text": "نحوه ست کردن ریموت دزدگیر خودرو بدون دستگاه",
            "intent": "informational",
            "priority": 60,
            "extra": ["روش کددهی دستی ریموت", "ست کردن ریموت با سوئیچ باز", "تعریف ریموت دزدگیر در خانه", "پروگرام دستی سوئیچ ماشین"]
        },
        {
            "text": "سیستم ایموبیلایزر چیست و چگونه کار میکند",
            "intent": "informational",
            "priority": 50,
            "extra": ["سوییچ ضد سرقت چیست", "علائم خرابی ایموبیلایزر", "تراشه چیپ الکترونیکی کلید", "کد سوییچ خودرو چیست"]
        },
        {
            "text": "چگونه کد ریموت گمشده را پاک کنیم",
            "intent": "informational",
            "priority": 55,
            "extra": ["حذف کلید گمشده از حافظه خودرو", "غیرفعال کردن ریموت مفقود شده", "صفر کردن کد ECU", "امنیت پس از گم شدن سوئیچ"]
        },
        {
            "text": "سیگنال ریموت خودرو چگونه رمزگذاری می‌شود",
            "intent": "informational",
            "priority": 40,
            "extra": ["سیستم رولینگ کد چیست", "تفاوت فیکس کد و رولینگ کد", "امنیت موج ریموت", "رمزنگاری ضد هک سوئیچ ماشین"]
        }
    ],
    "sell_remote": [
        {
            "text": "تفاوت ریموت فابریک و دزدگیر تصویری",
            "intent": "informational",
            "priority": 45,
            "extra": ["مقایسه ریموت فابریک و دزدگیر", "مزایای دزدگیر تصویری", "معایب ریموت فابریک خودرو", "راهنمای خرید دزدگیر ماشین"]
        },
        {
            "text": "ریموت کیلس استارتر چگونه کار میکند",
            "intent": "informational",
            "priority": 50,
            "extra": ["طرز کار کلید هوشمند", "سیستم کیلس گو چیست", "ساختار ریموت استارت دار", "امنیت خودروهای کیلس استارت"]
        },
        {
            "text": "تفاوت سوئیچ کددار با کلید معمولی چیست",
            "intent": "informational",
            "priority": 45,
            "extra": ["کلید ایموبیلایزر دار چیست", "ساخت کلید معمولی بدون کد", "چیپ سوئیچ خودرو چیست", "امنیت کلید کددار خودرو"]
        },
        {
            "text": "تفاوت کلید هوشمند (Smart Key) با ریموت معمولی",
            "intent": "informational",
            "priority": 45,
            "extra": ["ویژگی های ریموت هوشمند", "تفاوت کلید تاشو و کیلس", "آپشن ریموت خودرو", "تکنولوژی کلیدهای جدید ماشین"]
        }
    ]
}

def normalize_csv_text(values):
    cleaned = []
    seen = set()
    for value in values:
        if not value:
            continue
        text = " ".join(str(value).replace("،", ",").split())
        if text and text not in seen:
            cleaned.append(text)
            seen.add(text)
    return ", ".join(cleaned)


class Command(BaseCommand):
    help = "Seed LuxRemote project with structured Hierarchical Pillar-Cluster architecture."

    def add_arguments(self, parser):
        parser.add_argument("--base-domain", required=True)
        parser.add_argument("--project-name", default="luxremote")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        base_domain = options["base_domain"].rstrip("/")
        project_name = options["project_name"]
        dry_run = options["dry_run"]

        with transaction.atomic():
            project, _ = Project.objects.get_or_create(
                name=project_name,
                defaults={
                    "base_domain": base_domain,
                    "locale": "fa-IR",
                    "is_active": True,
                },
            )
            if not dry_run:
                project.base_domain = base_domain
                project.is_active = True
                project.save()

            intent_map = self._seed_intents(dry_run=dry_run)
            service_map = self._seed_services(project, dry_run=dry_run)
            created_keywords = self._seed_keywords(project, service_map, intent_map, dry_run=dry_run)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Done: project={project.name}, intents={len(intent_map)}, "
                    f"services={len(service_map)}, hierarchical_keywords={created_keywords}"
                )
            )

    def _seed_intents(self, dry_run=False):
        intent_map = {}
        for code, name, desc in INTENT_SEEDS:
            intent, _ = IntentType.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": desc,
                    "is_active": True,
                },
            )
            if not dry_run:
                intent.name = name
                intent.description = desc
                intent.is_active = True
                intent.save()
            intent_map[code] = intent
        return intent_map

    def _seed_services(self, project, dry_run=False):
        service_map = {}
        for item in SERVICE_SEEDS:
            service, _ = ServiceType.objects.get_or_create(
                project=project,
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "slug": item["slug"],
                    "root_keyword": item["root_keyword"],
                    "description": item["description"],
                    "modifier_keywords": item["modifiers"],
                    "is_active": True,
                    "is_ecommerce": item["is_ecommerce"],
                },
            )
            if not dry_run:
                service.name = item["name"]
                service.slug = item["slug"]
                service.root_keyword = item["root_keyword"]
                service.description = item["description"]
                service.modifier_keywords = item["modifiers"]
                service.is_active = True
                service.is_ecommerce = item["is_ecommerce"]
                service.save()
            service_map[item["code"]] = service
        return service_map

    def _seed_keywords(self, project, service_map, intent_map, dry_run=False):
        created = 0

        # فاز اول: تزریق ساختار درختی پیلار و کلاسترهای متصل (لایه ۲)
        for p_data in PILLAR_SEEDS:
            service = service_map[p_data["service_code"]]
            intent = intent_map[p_data["intent"]]
            root_kw = service.root_keyword or service.name
            
            p_text = p_data["text"].strip()
            p_extra_text = normalize_csv_text(
                list(p_data.get("extra", [])) + list(service.modifier_keywords or []) + [root_kw]
            )
            
            pillar_obj, was_p_created = Keyword.objects.get_or_create(
                project=project,
                text=p_text,
                defaults={
                    "service": service,
                    "intent": intent,
                    "is_pillar": True,
                    "parent_keyword": None,
                    "extra_keywords_text": p_extra_text,
                    "status": Keyword.Status.CLASSIFIED,
                    "priority_score": p_data["priority"],
                    "source": "seed:luxremote:pillar",
                    "meta": {
                        "service_code": p_data["service_code"],
                        "intent_code": p_data["intent"],
                    },
                },
            )
            
            if was_p_created:
                created += 1
            elif not dry_run:
                pillar_obj.service = service
                pillar_obj.intent = intent
                pillar_obj.is_pillar = True
                pillar_obj.parent_keyword = None
                pillar_obj.extra_keywords_text = p_extra_text
                pillar_obj.priority_score = p_data["priority"]
                pillar_obj.save()

            for c_data in p_data["clusters"]:
                c_text = c_data["text"].strip()
                c_intent = intent_map[c_data["intent"]]
                
                c_extra_text = normalize_csv_text(
                    list(c_data.get("extra", [])) + list(service.modifier_keywords or []) + [root_kw, p_text]
                )
                
                c_obj, was_c_created = Keyword.objects.get_or_create(
                    project=project,
                    text=c_text,
                    defaults={
                        "service": service,
                        "intent": c_intent,
                        "is_pillar": False,
                        "parent_keyword": pillar_obj,
                        "extra_keywords_text": c_extra_text,
                        "status": Keyword.Status.CLASSIFIED,
                        "priority_score": c_data["priority"],
                        "source": "seed:luxremote:cluster",
                        "meta": {
                            "service_code": p_data["service_code"],
                            "intent_code": c_data["intent"],
                            "parent_pillar_text": p_text
                        },
                    },
                )
                
                if was_c_created:
                    created += 1
                elif not dry_run:
                    c_obj.service = service
                    c_obj.intent = c_intent
                    c_obj.is_pillar = False
                    c_obj.parent_keyword = pillar_obj
                    c_obj.extra_keywords_text = c_extra_text
                    c_obj.priority_score = c_data["priority"]
                    c_obj.save()

        # --------------------------------------------------------
        # فاز دوم: تزریق کلمات کلیدی آموزشی مرجع و مستقل (لایه ۰ - Global)
        # --------------------------------------------------------
        for s_code, global_items in GLOBAL_SEEDS.items():
            service = service_map[s_code]
            root_kw = service.root_keyword or service.name
            
            for g_data in global_items:
                g_text = g_data["text"].strip()
                g_intent = intent_map[g_data["intent"]]
                
                # غنی‌سازی کلمات کمکی برای کلمات لایه صفر
                g_extra_text = normalize_csv_text(
                    list(g_data.get("extra", [])) + list(service.modifier_keywords or []) + [root_kw]
                )
                
                g_obj, was_g_created = Keyword.objects.get_or_create(
                    project=project,
                    text=g_text,
                    defaults={
                        "service": service,
                        "intent": g_intent,
                        "is_pillar": False,
                        "parent_keyword": None,  # کلمات جهانی لایه صفر والد مستقیم ندارند
                        "extra_keywords_text": g_extra_text,
                        "status": Keyword.Status.CLASSIFIED,
                        "priority_score": g_data["priority"],
                        "source": "seed:luxremote:global",
                        "meta": {
                            "service_code": s_code,
                            "intent_code": g_data["intent"],
                        },
                    },
                )
                
                if was_g_created:
                    created += 1
                elif not dry_run:
                    g_obj.service = service
                    g_obj.intent = g_intent
                    g_obj.is_pillar = False
                    g_obj.parent_keyword = None
                    g_obj.extra_keywords_text = g_extra_text
                    g_obj.priority_score = g_data["priority"]
                    g_obj.save()

        return created
        