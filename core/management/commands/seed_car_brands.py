from django.core.management.base import BaseCommand
from django.utils.text import slugify
from core.models import Project
from taxonomy.models import TaxonomyNode

class Command(BaseCommand):
    help = 'ایجاد داده‌های اولیه برای برندها و مدل‌های خودرو با اسلاگ‌های کاملاً انگلیسی'

    def handle(self, *args, **kwargs):
        project = Project.objects.first()
        if not project:
            self.stdout.write(self.style.ERROR('هیچ پروژه‌ای در دیتابیس یافت نشد! لطفاً ابتدا یک پروژه بسازید.'))
            return

        # ساختار داده: { "slug_برند_انگلیسی": {"name": "نام_فارسی_برند", "models": {"نام_فارسی_مدل": "slug_مدل_انگلیسی"}} }
        car_data = {
            "benz": {
                "name": "بنز",
                "models": {"C200": "c200", "C250": "c250", "C300": "c300", "E200": "e200", "E250": "e250", "S500": "s500", "CLS500": "cls500", "CLA200": "cla200", "GLA200": "gla200"}
            },
            "bmw": {
                "name": "بی ام و",
                "models": {"528i": "528i", "530i": "530i", "730li": "730li", "740li": "740li", "X3": "x3", "X4": "x4", "X6": "x6", "320i": "320i", "328i": "328i"}
            },
            "hyundai": {
                "name": "هیوندا",
                "models": {"سانتافه": "santafe", "توسان": "tucson", "سوناتا": "sonata", "النترا": "elantra", "آزرا": "azera", "اکسنت": "accent", "وراکروز": "veracruz"}
            },
            "kia": {
                "name": "کیا",
                "models": {"اسپورتیج": "sportage", "سورنتو": "sorento", "اپتیما": "optima", "سراتو": "cerato", "پیکانتو": "picanto", "موهاوی": "mohave", "کادنزا": "cadenza"}
            },
            "toyota": {
                "name": "تویوتا",
                "models": {"لندکروز": "land-cruiser", "پرادو": "prado", "هایلوکس": "hilux", "راوفور": "rav4", "کمری": "camry", "کرولا": "corolla", "سی اچ آر": "chr", "یاریس": "yaris"}
            },
            "mitsubishi": {
                "name": "میتسوبیشی",
                "models": {"لنسر": "lancer", "اوتلندر": "outlander", "ای اس ایکس": "asx", "پاجرو": "pajero"}
            },
            "nissan": {
                "name": "نیسان",
                "models": {"ماکسیما": "maxima", "تیانا": "teana", "جوک": "juke", "ایکس تریل": "x-trail", "قشقایی": "qashqai", "مورانو": "murano"}
            },
            "renault": {
                "name": "رنو",
                "models": {"تندر 90": "tondar-90", "ساندرو": "sandero", "ساندرو استپ وی": "stepway", "مگان": "megane", "تالیسمان": "talisman", "کولیوس": "koleos", "داستر": "duster"}
            },
            "mazda": {
                "name": "مزدا",
                "models": {"مزدا 3": "3", "مزدا 3 نیو": "3-new", "مزدا 323": "323"}
            },
            "volkswagen": {
                "name": "فولکس واگن",
                "models": {"تیگوان": "tiguan", "پاسات": "passat", "گلف": "golf"}
            },
            "porsche": {
                "name": "پورشه",
                "models": {"ماکان": "macan", "کاین": "cayenne", "پانامرا": "panamera", "باکستر": "boxster"}
            },
            "lexus": {
                "name": "لکسوس",
                "models": {"RX350": "rx350", "NX200t": "nx200t", "LX570": "lx570", "IS250": "is250"}
            },
            "volvo": {
                "name": "ولوو",
                "models": {"XC90": "xc90", "XC60": "xc60", "V40": "v40"}
            },
            "suzuki": {
                "name": "سوزوکی",
                "models": {"ویتارا": "vitara", "کیزاشی": "kizashi"}
            },
            "ssangyong": {
                "name": "سانگ یانگ",
                "models": {"تیوولی": "tivoli", "رکستون": "rexton", "کوراندو": "korando"}
            },
            "chery": {
                "name": "چری",
                "models": {"تیگو 5": "tiggo-5", "تیگو 7": "tiggo-7", "آریزو 5": "arrizo-5", "آریزو 6": "arrizo-6"}
            },
            "mvm": {
                "name": "ام وی ام",
                "models": {"X33": "x33", "X55": "x55", "X22": "x22", "315": "315"}
            },
            "lifan": {
                "name": "لیفان",
                "models": {"X70": "x70", "X60": "x60", "X50": "x50", "820": "820", "620": "620"}
            },
            "jac": {
                "name": "جک",
                "models": {"S5": "s5", "S3": "s3", "J5": "j5", "J4": "j4"}
            },
            "haima": {
                "name": "هایما",
                "models": {"S7": "s7", "S5": "s5", "S8": "s8"}
            },
            "haval": {
                "name": "هاوال",
                "models": {"H2": "h2", "H6": "h6", "H9": "h9"}
            },
            "dongfeng": {
                "name": "دانگ فنگ",
                "models": {"اچ سی کراس": "h30-cross", "دیگنیتی": "dignity", "فیدلیتی": "fidelity"}
            },
            "baic": {
                "name": "بایک",
                "models": {"سنوا": "senova", "سابرینا": "sabrina", "X25": "x25"}
            },
            "faw": {
                "name": "بسترن",
                "models": {"B30": "b30", "B50": "b50"}
            },
            "geely": {
                "name": "جیلی",
                "models": {"امگرند": "emgrand", "GC6": "gc6"}
            },
            "mg": {
                "name": "ام جی",
                "models": {"360": "360", "350": "350", "GS": "gs", "ZS": "zs"}
            },
            "brilliance": {
                "name": "برلیانس",
                "models": {"H330": "h330", "H320": "h320", "H220": "h220", "V5": "v5"}
            },
            "byd": {
                "name": "بی وای دی",
                "models": {"S6": "s6", "S7": "s7"}
            }
        }

        total_brands_created = 0
        total_models_created = 0

        for brand_slug, brand_info in car_data.items():
            brand_name = brand_info["name"]

            # اسلاگ برند مستقیما از کلید دیکشنری (انگلیسی) استفاده می‌شود
            brand_node, created = TaxonomyNode.objects.get_or_create(
                project=project,
                kind=TaxonomyNode.Kind.BRAND,
                slug=slugify(brand_slug),
                defaults={
                    'name': brand_name,
                    'parent': None,
                    'is_active': True,
                }
            )

            if created:
                total_brands_created += 1
                self.stdout.write(self.style.SUCCESS(f'+ برند ایجاد شد: {brand_name} (Slug: {brand_slug})'))

            # ایجاد مدل‌های مربوط به این برند
            for model_name, model_slug in brand_info["models"].items():
                # در اینجا اسلاگ مدل مستقیماً همان مقدار انگلیسی تعریف شده است بدون ترکیب با برند
                final_model_slug = slugify(model_slug)
                
                model_node, model_created = TaxonomyNode.objects.get_or_create(
                    project=project,
                    kind=TaxonomyNode.Kind.MODEL,
                    parent=brand_node, 
                    slug=final_model_slug,
                    defaults={
                        'name': model_name,
                        'is_active': True,
                    }
                )

                if model_created:
                    total_models_created += 1
                    self.stdout.write(f'  ---> مدل ایجاد شد: {model_name} (Slug: {final_model_slug})')

        self.stdout.write(self.style.SUCCESS('====================================='))
        self.stdout.write(self.style.SUCCESS(f'عملیات با موفقیت پایان یافت!'))
        self.stdout.write(self.style.SUCCESS(f'تعداد {total_brands_created} برند و {total_models_created} مدل به دیتابیس اضافه شد.'))
