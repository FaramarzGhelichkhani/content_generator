# taxonomy/management/commands/seed_locations.py
from django.core.management.base import BaseCommand
from core.models import Project
from taxonomy.models import Location  
class Command(BaseCommand):
    help = 'ایجاد شهرها و محله‌های هدف (تهران، کرج و محلات تهران)'

    def handle(self, *args, **kwargs):
        try:
            project = Project.objects.get(id=1)
        except Project.DoesNotExist:
            self.stdout.write(self.style.ERROR('پروژه با آیدی 1 یافت نشد.'))
            return

        # ۱. ساخت شهرهای اصلی (بدون والد)
        tehran, created = Location.objects.update_or_create(
            project=project, 
            name="تهران",
            defaults={"slug": "tehran", "parent": None, "is_active": True}
        )
        t_status = "ایجاد شد" if created else "بروزرسانی شد"
        self.stdout.write(self.style.SUCCESS(f'[{t_status}] شهر: {tehran.name}'))

        karaj, created = Location.objects.update_or_create(
            project=project, 
            name="کرج",
            defaults={"slug": "karaj", "parent": None, "is_active": True}
        )
        k_status = "ایجاد شد" if created else "بروزرسانی شد"
        self.stdout.write(self.style.SUCCESS(f'[{k_status}] شهر: {karaj.name}'))

        # ۲. لیست محله‌ها و مناطق تهران
        # اسلاگ‌ها به صورت انگلیسی (پینگلیش) نوشته شده‌اند تا URL ها تمیز و استاندارد باشند.
        tehran_neighborhoods = [
            {"name": "الهیه", "slug": "elahiyeh"},
            {"name": "زعفرانیه", "slug": "zaferaniyeh"},
            {"name": "ونک", "slug": "vanak"},
            {"name": "پیروزی", "slug": "pirouzi"},
            {"name": "نارمک", "slug": "narmak"},  # اشتباه تایپی نارمگ اصلاح شد
            {"name": "نیاوران", "slug": "niavaran"},
            {"name": "فرمانیه", "slug": "farmanieh"},
            {"name": "ولنجک", "slug": "velanjak"},
            {"name": "کامرانیه", "slug": "kamranieh"},
            {"name": "اقدسیه", "slug": "aghdasieh"},
            {"name": "قیطریه", "slug": "gheytarieh"},
            {"name": "شهرک غرب", "slug": "shahrak-gharb"},
            {"name": "تهرانپارس", "slug": "tehranpars"},
            {"name": "سعادت آباد", "slug": "saadat-abad"},
            {"name": "صادقیه", "slug": "sadeghieh"},
            {"name": "پاسداران", "slug": "pasdaran"},
            {"name": "شمال تهران", "slug": "north-tehran"},
            {"name": "غرب تهران", "slug": "west-tehran"},
            {"name": "شرق تهران", "slug": "east-tehran"},
            {"name": "جنوب تهران", "slug": "south-tehran"},
        ]

        # ۳. ساخت محله‌ها (با والد = تهران)
        for nh in tehran_neighborhoods:
            obj, created = Location.objects.update_or_create(
                project=project,
                name=nh["name"],
                defaults={
                    "slug": nh["slug"],
                    "parent": tehran,
                    "is_active": True
                }
            )
            status = "ایجاد شد" if created else "بروزرسانی شد"
            self.stdout.write(self.style.SUCCESS(f'  -- [{status}] محله/منطقه: {obj.name}'))

        self.stdout.write(self.style.SUCCESS('تمام شهرها و محله‌ها با موفقیت در دیتابیس ذخیره شدند!'))
