# core/management/commands/seed_services.py
from django.core.management.base import BaseCommand
from core.models import Project
from taxonomy.models import ServiceType

class Command(BaseCommand):
    help = 'ایجاد سرویس‌های اصلی سایت (Service Types) با توصیفات جامع و بدون لحن پرامپتی'

    def handle(self, *args, **kwargs):
        try:
            project = Project.objects.get(id=1)
        except Project.DoesNotExist:
            self.stdout.write(self.style.ERROR('پروژه با آیدی 1 یافت نشد.'))
            return

        services_data = [
            {
                "code": ServiceType.Code.CREATE_REMOTE,
                "name": "ساخت ریموت موتور سیکلت",
                "slug": "create-remote",
                "root_keyword": "ساخت ریموت",
                "is_ecommerce": False,
                "description": (
                    "این سرویس به معنای تولید، پیکربندی و راه‌اندازی صفر تا صد یک ریموت یا کیلس جدید برای موتورسیکلت است. "
                    "این حالت معمولاً زمانی کاربرد دارد که موتورسوار تمام ریموت‌های خود را گم کرده است و هیچ سوئیچ یدکی برای الگوبرداری وجود ندارد. "
                    "این فرآیند شامل استخراج تخصصی کد پین از حافظه ای سی یو (ECU) یا اس سی یو (SCU)، مچ کردن سیستم ضد سرقت با سوئیچ جدید، "
                    "تراش کلید مکانیکی اضطراری از روی قفل موتور و تعریف کامل اسمارت‌کی فابریک روی سیستم الکترونیکی موتورسیکلت می‌باشد."
                ),
                "modifier_keywords": ["ساخت", "تولید", "پروگرام اولیه", "پیکربندی", "گم شدن کامل", "کددهی مستقیم"]
            },
            {
                "code": ServiceType.Code.COPY_REMOTE,
                "name": "کپی و کددهی ریموت یدک",
                "slug": "copy-remote",
                "root_keyword": "کپی ریموت",
                "is_ecommerce": False,
                "description": (
                    "این سرویس شامل تکثیر و ساخت ریموت دوم (زاپاس) از روی ریموت اصلی و فعال موتور است. "
                    "در این فرآیند، موتورسوار یک ریموت سالم در اختیار دارد و برای پیشگیری از مشکلات مفقودی، درخواست یک کلید یدک می‌کند. "
                    "عملیات شامل خواندن اطلاعات فرکانسی و کدهای ایموبلایزر از روی کلید فعال و انتقال آن به ریموت خام، "
                    "یا معرفی مستقیم یک ریموت پشتیبان به سیستم گیرنده موتور است تا هر دو ریموت به صورت موازی عمل کنند."
                ),
                "modifier_keywords": ["کپی", "یدک", "تکثیر", "زاپاس", "ریموت دوم", "دوتایی کردن", "بکاپ"]
            },
            {
                "code": ServiceType.Code.REPAIR_REMOTE,
                "name": "تعمیر کیلس و ریموت",
                "slug": "repair-remote",
                "root_keyword": "تعمیر ریموت",
                "is_ecommerce": False,
                "description": (
                    "این سرویس منحصراً بر رفع ایرادات سخت‌افزاری، الکترونیکی و فیزیکی ریموت فعلی موتورسیکلت تمرکز دارد. "
                    "مواردی مانند رفع مشکلات ناشی از آب‌خوردگی برد الکترونیکی، تعویض میکروسوئیچ‌های خراب یا گیرکرده، "
                    "لحیم‌کاری قطعات آسیب‌دیده مدار، رفع قطعی آنتن گیرنده روی برد ریموت، و برطرف کردن مشکلات مربوط به "
                    "سینک نشدن و افت سیگنال ریموت با سنسور مجاورت موتور در این دسته قرار می‌گیرند. این سرویس نیازی به ساخت کلید جدید ندارد."
                ),
                "modifier_keywords": ["تعمیر", "آبخوردگی", "تعویض دکمه", "لحیم کاری", "قطعی", "تعمیر برد", "احیا"]
            },
            {
                "code": ServiceType.Code.SELL_REMOTE,
                "name": "فروش ریموت و قطعات",
                "slug": "shop",
                "root_keyword": "خرید ریموت",
                "is_ecommerce": True,
                "description": (
                    "این سرویس به تامین و فروش قطعات فیزیکی مرتبط با سیستم کیلس و سوئیچ موتورسیکلت اختصاص دارد و جنبه کاملاً تجاری (فروشگاهی) دارد. "
                    "این بخش شامل فروش ریموت‌های خام فابریک و شرکتی، بردهای داخلی، ست کامل ماژول گیرنده (SCU)، باتری‌های مخصوص کیلس، "
                    "انواع قاب، شل (Shell) و کاورهای محافظ ژله‌ای و چرمی می‌شود. در این سرویس، صرفاً محصول به دست مشتری می‌رسد و "
                    "شامل خدمات فنی در محل، پروگرام کردن یا تعمیرات نمی‌شود."
                ),
                "modifier_keywords": ["خرید", "فروش", "قیمت", "فروشگاه", "ارسال", "اورجینال", "فابریک", "قطعه خام"]
            }
        ]

        for data in services_data:
            service, created = ServiceType.objects.update_or_create(
                project=project,
                code=data["code"],
                defaults={
                    "name": data["name"],
                    "slug": data["slug"],
                    "root_keyword": data["root_keyword"],
                    "description": data["description"],
                    "is_ecommerce": data["is_ecommerce"],
                    "modifier_keywords": data["modifier_keywords"],
                    "is_active": True
                }
            )
            status = "ایجاد شد" if created else "بروزرسانی شد"
            self.stdout.write(self.style.SUCCESS(f'[{status}] {service.name}'))

        self.stdout.write(self.style.SUCCESS('تمام سرویس‌ها با موفقیت در دیتابیس ذخیره شدند!'))
        