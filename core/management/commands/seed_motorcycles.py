# taxonomy/management/commands/seed_motorcycles.py
from django.core.management.base import BaseCommand
from core.models import Project
from taxonomy.models import TaxonomyNode

class Command(BaseCommand):
    help = 'Seed keyless/smart key motorcycle brands and models in the Iranian market'

    def handle(self, *args, **kwargs):
        try:
            project = Project.objects.get(id=1)
        except Project.DoesNotExist:
            self.stdout.write(self.style.ERROR('Project with ID 1 not found.'))
            return

        self.stdout.write(self.style.NOTICE('--- Starting Keyless Motorcycles Seeding ---'))

        # Data structure: Brands and their keyless/remote models in Iran
        motorcycle_catalog = [
            {
                "brand_name": "هوندا",
                "brand_slug": "honda",
                "brand_meta": {"en_name": "Honda", "country": "Japan"},
                "models": [
                    {
                        "name": "کلیک",
                        "slug": "click",
                        "meta": {
                            "en_name": "Honda Click / Vario",
                            "variations": ["Click 125", "Click 150", "Click 160", "Vario 150", "Vario 160"],
                            "chip_type": "Smart Key / ID47",
                            "note": "پرفروش‌ترین اسکوتر کیلس بازار ایران"
                        }
                    },
                    {
                        "name": "ای دی وی",
                        "slug": "adv",
                        "meta": {
                            "en_name": "Honda ADV",
                            "variations": ["ADV 150", "ADV 160", "ADV 350", "ADV 750"],
                            "chip_type": "Smart Key / ID47",
                            "note": "اسکوتر ادونچر کیلس"
                        }
                    },
                    {
                        "name": "پی سی ایکس",
                        "slug": "pcx",
                        "meta": {
                            "en_name": "Honda PCX",
                            "variations": ["PCX 125", "PCX 150", "PCX 160"],
                            "chip_type": "Smart Key / ID47"
                        }
                    },
                    {
                        "name": "فورزا",
                        "slug": "forza",
                        "meta": {
                            "en_name": "Honda Forza",
                            "variations": ["Forza 250", "Forza 300", "Forza 350", "Forza 750"],
                            "chip_type": "Smart Key"
                        }
                    },
                    {
                        "name": "اس اچ",
                        "slug": "sh",
                        "meta": {
                            "en_name": "Honda SH",
                            "variations": ["SH 125", "SH 150", "SH 300", "SH 350"]
                        }
                    },
                    {
                        "name": "سی بی آر / سی بی",
                        "slug": "cbr-cb",
                        "meta": {
                            "en_name": "Honda CB / CBR",
                            "variations": ["CB 250R", "CB 300R", "CB 650R", "CBR 650R", "GB 350"],
                            "chip_type": "HISS Immobilizer / Smart Key"
                        }
                    }
                ]
            },
            {
                "brand_name": "یاماها",
                "brand_slug": "yamaha",
                "brand_meta": {"en_name": "Yamaha", "country": "Japan"},
                "models": [
                    {
                        "name": "ایروکس / ان وی ایکس",
                        "slug": "aerox-nvx",
                        "meta": {
                            "en_name": "Yamaha Aerox / NVX",
                            "variations": ["Aerox 155", "NVX 155", "طرح ایروکس"],
                            "chip_type": "Smart Key 433MHz",
                            "note": "اسکوتر بسیار پرطرفدار با سیستم اسمارت کی"
                        }
                    },
                    {
                        "name": "ان مکس",
                        "slug": "nmax",
                        "meta": {
                            "en_name": "Yamaha NMAX",
                            "variations": ["NMAX 155"],
                            "chip_type": "Smart Key"
                        }
                    },
                    {
                        "name": "ایکس مکس",
                        "slug": "xmax",
                        "meta": {
                            "en_name": "Yamaha XMAX",
                            "variations": ["XMAX 250", "XMAX 300"],
                            "chip_type": "Smart Key"
                        }
                    },
                    {
                        "name": "گرند فیلانو",
                        "slug": "grand-filano",
                        "meta": {
                            "en_name": "Yamaha Grand Filano",
                            "variations": ["Grand Filano 125 Hybrid", "فازیو / Fazzio"],
                            "chip_type": "Smart Key"
                        }
                    },
                    {
                        "name": "ام تی",
                        "slug": "mt",
                        "meta": {
                            "en_name": "Yamaha MT",
                            "variations": ["MT-25", "MT-03", "MT-07", "MT-09"],
                            "chip_type": "Immobilizer Key"
                        }
                    },
                    {
                        "name": "ار ۲۵ / ار ۳",
                        "slug": "r25-r3",
                        "meta": {
                            "en_name": "Yamaha R25 / R3",
                            "variations": ["YZF-R25", "YZF-R3"],
                            "chip_type": "Immobilizer Key"
                        }
                    }
                ]
            },
            {
                "brand_name": "وسپا و پیاجیو",
                "brand_slug": "vespa-piaggio",
                "brand_meta": {"en_name": "Vespa / Piaggio", "country": "Italy"},
                "models": [
                    {
                        "name": "پریماورا",
                        "slug": "primavera",
                        "meta": {
                            "en_name": "Vespa Primavera",
                            "variations": ["Primavera 150", "Primavera 50"],
                            "chip_type": "Immobilizer Master/Service Key"
                        }
                    },
                    {
                        "name": "اسپرینت",
                        "slug": "sprint",
                        "meta": {
                            "en_name": "Vespa Sprint",
                            "variations": ["Sprint 150", "Sprint S 150"],
                            "chip_type": "Immobilizer Key"
                        }
                    },
                    {
                        "name": "جی تی اس",
                        "slug": "gts",
                        "meta": {
                            "en_name": "Vespa GTS",
                            "variations": ["GTS 250", "GTS 300 Super Tech", "GTS Keyless 2023+"],
                            "chip_type": "Smart Keyless & Immobilizer"
                        }
                    },
                    {
                        "name": "مدلی",
                        "slug": "medley",
                        "meta": {
                            "en_name": "Piaggio Medley",
                            "variations": ["Medley 150 S"],
                            "chip_type": "Immobilizer Chip"
                        }
                    },
                    {
                        "name": "بورلی",
                        "slug": "beverly",
                        "meta": {
                            "en_name": "Piaggio Beverly",
                            "variations": ["Beverly 300", "Beverly 400"],
                            "chip_type": "Smart Keyless"
                        }
                    }
                ]
            },
            {
                "brand_name": "اس وای ام",
                "brand_slug": "sym",
                "brand_meta": {"en_name": "SYM", "country": "Taiwan"},
                "models": [
                    {
                        "name": "فیدل",
                        "slug": "fiddle",
                        "meta": {
                            "en_name": "SYM Fiddle",
                            "variations": ["Fiddle 3", "Fiddle 4", "Fiddle 150 Keyless"],
                            "chip_type": "Smart Key"
                        }
                    },
                    {
                        "name": "گلکسی / لاکی",
                        "slug": "galaxy-lucky",
                        "meta": {
                            "en_name": "SYM Galaxy / Lucky",
                            "variations": ["Galaxy J200", "Galaxy FX150", "Lucky 180", "JT200"],
                            "chip_type": "Smart Key & Alarm Remote"
                        }
                    },
                    {
                        "name": "کروزیم",
                        "slug": "cruisym",
                        "meta": {
                            "en_name": "SYM Cruisym",
                            "variations": ["Cruisym 250", "Cruisym 300", "Joymax 250"],
                            "chip_type": "Smart Key"
                        }
                    },
                    {
                        "name": "ان اچ",
                        "slug": "nh",
                        "meta": {
                            "en_name": "SYM NH",
                            "variations": ["NH 190", "NH 200", "NHT", "NHX"],
                            "chip_type": "Immobilizer / Anti-Theft"
                        }
                    },
                    {
                        "name": "مکس سم",
                        "slug": "maxsym",
                        "meta": {
                            "en_name": "SYM Maxsym",
                            "variations": ["Maxsym 400", "Maxsym TL 500"],
                            "chip_type": "Smart Key"
                        }
                    }
                ]
            },
            {
                "brand_name": "بنلی",
                "brand_slug": "benelli",
                "brand_meta": {"en_name": "Benelli / Keeway", "country": "Italy-China"},
                "models": [
                    {
                        "name": "تی ان تی / بنلی دوسیلندر",
                        "slug": "tnt",
                        "meta": {
                            "en_name": "Benelli TNT",
                            "variations": ["TNT 150", "TNT 25", "TNT 249 (2-Cylinder)", "TNT 300"],
                            "chip_type": "Flip Key Immobilizer"
                        }
                    },
                    {
                        "name": "لئونچینو",
                        "slug": "leoncino",
                        "meta": {
                            "en_name": "Benelli Leoncino",
                            "variations": ["Leoncino 250", "Leoncino 500"],
                            "chip_type": "Flip Key"
                        }
                    },
                    {
                        "name": "تی آر کی",
                        "slug": "trk",
                        "meta": {
                            "en_name": "Benelli TRK",
                            "variations": ["TRK 251", "TRK 502"],
                            "chip_type": "Immobilizer Key"
                        }
                    },
                    {
                        "name": "ویست / پاناریا (کی وی)",
                        "slug": "vieste-panarea",
                        "meta": {
                            "en_name": "Keeway Vieste / Panarea",
                            "variations": ["Vieste 249", "Panarea 125", "سیتی بلید"],
                            "chip_type": "Smart Keyless"
                        }
                    },
                    {
                        "name": "کافه نرو / ستا",
                        "slug": "caffenero-setta",
                        "meta": {
                            "en_name": "Benelli Caffenero / Seta",
                            "variations": ["Caffenero 150", "Seta 125"],
                            "chip_type": "Remote / Key"
                        }
                    }
                ]
            },
            {
                "brand_name": "کی تی ام",
                "brand_slug": "ktm",
                "brand_meta": {"en_name": "KTM", "country": "Austria"},
                "models": [
                    {
                        "name": "دوک",
                        "slug": "duke",
                        "meta": {
                            "en_name": "KTM Duke",
                            "variations": ["Duke 200", "Duke 250", "Duke 390"],
                            "chip_type": "Immobilizer"
                        }
                    },
                    {
                        "name": "آر سی",
                        "slug": "rc",
                        "meta": {
                            "en_name": "KTM RC",
                            "variations": ["RC 200", "RC 250", "RC 390"],
                            "chip_type": "Immobilizer"
                        }
                    },
                    {
                        "name": "ادونچر",
                        "slug": "adventure",
                        "meta": {
                            "en_name": "KTM Adventure",
                            "variations": ["Adventure 250", "Adventure 390", "Adventure 790/890 Keyless"],
                            "chip_type": "Smart Keyless / Immobilizer"
                        }
                    }
                ]
            },
            {
                "brand_name": "زونتس",
                "brand_slug": "zontes",
                "brand_meta": {"en_name": "Zontes", "country": "China"},
                "models": [
                    {
                        "name": "سری اسکوتر زونتس",
                        "slug": "zontes-scooters",
                        "meta": {
                            "en_name": "Zontes Scooter Series",
                            "variations": ["Zontes M310", "Zontes 150D", "Zontes 350E", "Zontes 350D"],
                            "chip_type": "Smart Key Generation 2 & 3",
                            "note": "مجهز به سیستم کیلس هوشمند بدون باتری و بند مچی"
                        }
                    },
                    {
                        "name": "سری ۲۵۰ و ۳۱۰ و ۳۵۰ دنده‌ای",
                        "slug": "zontes-geared",
                        "meta": {
                            "en_name": "Zontes R/X/T/GK",
                            "variations": ["Zontes 250R", "Zontes 310T", "Zontes 310X", "Zontes GK350"],
                            "chip_type": "Smart Keyless"
                        }
                    }
                ]
            },
            {
                "brand_name": "سی اف موتو",
                "brand_slug": "cfmoto",
                "brand_meta": {"en_name": "CFMOTO", "country": "China"},
                "models": [
                    {
                        "name": "ان کی",
                        "slug": "nk",
                        "meta": {
                            "en_name": "CFMOTO NK",
                            "variations": ["NK 150", "NK 250", "NK 300", "NK 400", "NK 650"],
                            "chip_type": "Immobilizer Key"
                        }
                    },
                    {
                        "name": "اس آر",
                        "slug": "sr",
                        "meta": {
                            "en_name": "CFMOTO SR",
                            "variations": ["250SR", "300SR", "450SR"],
                            "chip_type": "Immobilizer Key"
                        }
                    },
                    {
                        "name": "سی ال ایکس",
                        "slug": "clx",
                        "meta": {
                            "en_name": "CFMOTO CL-X",
                            "variations": ["250 CL-X", "700 CL-X"],
                            "chip_type": "Immobilizer Key"
                        }
                    }
                ]
            },
            {
                "brand_name": "تی وی اس",
                "brand_slug": "tvs",
                "brand_meta": {"en_name": "TVS", "country": "India"},
                "models": [
                    {
                        "name": "ان تورک",
                        "slug": "ntorq",
                        "meta": {
                            "en_name": "TVS NTorq",
                            "variations": ["NTorq 125", "NTorq Race XP"],
                            "chip_type": "Remote / Smart Key"
                        }
                    },
                    {
                        "name": "آپاچی",
                        "slug": "apache",
                        "meta": {
                            "en_name": "TVS Apache",
                            "variations": ["RTR 160", "RTR 180", "RTR 200 4V", "RR 310"],
                            "chip_type": "Wave Key / Immobilizer"
                        }
                    },
                    {
                        "name": "ژوپیتر / وگو",
                        "slug": "jupiter-wego",
                        "meta": {
                            "en_name": "TVS Jupiter / Wego",
                            "variations": ["Jupiter 110", "Jupiter 125 SmartXonnect", "Wego 110"],
                            "chip_type": "Smart Key / Standard Key"
                        }
                    }
                ]
            },
            {
                "brand_name": "سوزوکی",
                "brand_slug": "suzuki",
                "brand_meta": {"en_name": "Suzuki", "country": "Japan"},
                "models": [
                    {
                        "name": "برگمن",
                        "slug": "burgman",
                        "meta": {
                            "en_name": "Suzuki Burgman",
                            "variations": ["Burgman Street 125", "Burgman 200", "Burgman 400"],
                            "chip_type": "Smart Keyless"
                        }
                    },
                    {
                        "name": "جی اس ایکس",
                        "slug": "gsx",
                        "meta": {
                            "en_name": "Suzuki GSX",
                            "variations": ["GSX-R 150 Keyless", "GSX-S 150", "Inazuma 250"],
                            "chip_type": "Smart Keyless & Shutter Key"
                        }
                    },
                    {
                        "name": "وی استروم",
                        "slug": "v-strom",
                        "meta": {
                            "en_name": "Suzuki V-Strom",
                            "variations": ["V-Strom 250", "V-Strom 650", "V-Strom 1050"],
                            "chip_type": "Immobilizer Key"
                        }
                    }
                ]
            },
            {
                "brand_name": "کاوازاکی",
                "brand_slug": "kawasaki",
                "brand_meta": {"en_name": "Kawasaki", "country": "Japan"},
                "models": [
                    {
                        "name": "نینجا",
                        "slug": "ninja",
                        "meta": {
                            "en_name": "Kawasaki Ninja",
                            "variations": ["Ninja 250 (2-Cylinder)", "Ninja 250 (4-Cylinder ZX-25R)", "Ninja 300", "Ninja 400"],
                            "chip_type": "KIPASS Smart Keyless / Immobilizer"
                        }
                    },
                    {
                        "name": "زد",
                        "slug": "z",
                        "meta": {
                            "en_name": "Kawasaki Z",
                            "variations": ["Z250", "Z400", "Z1000"],
                            "chip_type": "Immobilizer Key"
                        }
                    },
                    {
                        "name": "جی ۳۰۰",
                        "slug": "j300",
                        "meta": {
                            "en_name": "Kawasaki J300",
                            "variations": ["J300 ABS"],
                            "chip_type": "Immobilizer"
                        }
                    }
                ]
            },
            {
                "brand_name": "بی ام و",
                "brand_slug": "bmw",
                "brand_meta": {"en_name": "BMW Motorrad", "country": "Germany"},
                "models": [
                    {
                        "name": "سی ۴۰۰",
                        "slug": "c400",
                        "meta": {
                            "en_name": "BMW C400",
                            "variations": ["C400X", "C400GT"],
                            "chip_type": "BMW Keyless Ride Remote",
                            "note": "اسکوتر لوکس کیلس"
                        }
                    },
                    {
                        "name": "جی ۳۱۰",
                        "slug": "g310",
                        "meta": {
                            "en_name": "BMW G310",
                            "variations": ["G310R", "G310GS"],
                            "chip_type": "EWS Immobilizer Key"
                        }
                    },
                    {
                        "name": "آر ۱۲۵۰ / ۱۲۰۰",
                        "slug": "r1250-r1200",
                        "meta": {
                            "en_name": "BMW R1250 / R1200",
                            "variations": ["R1250 GS Adventure", "R1200 GS", "S1000RR"],
                            "chip_type": "Keyless Ride Remote"
                        }
                    }
                ]
            },
            {
                "brand_name": "کیمکو",
                "brand_slug": "kymco",
                "brand_meta": {"en_name": "Kymco", "country": "Taiwan"},
                "models": [
                    {
                        "name": "لایک",
                        "slug": "like",
                        "meta": {
                            "en_name": "Kymco Like",
                            "variations": ["Like 150i", "Like 200"],
                            "chip_type": "Smart Key"
                        }
                    },
                    {
                        "name": "اکسایتینگ / داون‌تاون",
                        "slug": "xciting-downtown",
                        "meta": {
                            "en_name": "Kymco Xciting / Downtown",
                            "variations": ["Downtown 250i", "Xciting 250", "Xciting 400", "AK550 Keyless"],
                            "chip_type": "Smart Keyless"
                        }
                    },
                    {
                        "name": "اجیلیتی",
                        "slug": "agility",
                        "meta": {
                            "en_name": "Kymco Agility",
                            "variations": ["Agility 150", "Agility 16+"],
                            "chip_type": "Immobilizer Key"
                        }
                    }
                ]
            },
            {
                "brand_name": "موتورهای مونتاژ و طرح‌های بازار ایران",
                "brand_slug": "iranian-assemblies",
                "brand_meta": {
                    "en_name": "Iranian Assembled & Replica Brands",
                    "note": "برندهای مونتاژکننده شامل کویر، نیرو موتور، کبیر، هانی، دینو، ثاقب و شاهین موتور"
                },
                "models": [
                    {
                        "name": "طرح کلیک کیلس",
                        "slug": "replica-click-keyless",
                        "meta": {
                            "en_name": "Click Replicas (Keyless)",
                            "variations": ["طرح کلیک هانی", "طرح کلیک کبیر", "طرح کلیک کویر S2", "طرح کلیک دینو و لاکی"],
                            "chip_type": "Remote Alarm / Keyless Module",
                            "note": "بسیار پرتیراژ در بازار ایران با تنوع کیلس و ریموت دزدگیری"
                        }
                    },
                    {
                        "name": "طرح ایروکس کیلس",
                        "slug": "replica-aerox-keyless",
                        "meta": {
                            "en_name": "Aerox Replicas (Keyless)",
                            "variations": ["طرح ایروکس کبیر NVX", "طرح ایروکس هانی", "طرح ایروکس دینو آرکس 150"],
                            "chip_type": "Smart Keyless / Remote"
                        }
                    },
                    {
                        "name": "طرح وسپا کیلس",
                        "slug": "replica-vespa-keyless",
                        "meta": {
                            "en_name": "Vespa Replicas (Keyless)",
                            "variations": ["طرح وسپا هانی 150", "طرح وسپا کلویس", "طرح وسپا پاکرو"],
                            "chip_type": "Remote / Keyless"
                        }
                    },
                    {
                        "name": "طرح ادونچر و باکسر کیلس",
                        "slug": "replica-adv-keyless",
                        "meta": {
                            "en_name": "ADV Replicas & Commuters",
                            "variations": ["طرح ADV هانی", "طرح ADV کویر", "کیلس باکسر"],
                            "chip_type": "Remote / Keyless"
                        }
                    }
                ]
            }
        ]

        total_brands_created = 0
        total_brands_updated = 0
        total_models_created = 0
        total_models_updated = 0

        for brand_data in motorcycle_catalog:
            # 1. Seed Brand Node
            brand_node, b_created = TaxonomyNode.objects.update_or_create(
                project=project,
                kind=TaxonomyNode.Kind.BRAND,
                parent=None,
                slug=brand_data["brand_slug"],
                defaults={
                    "name": brand_data["brand_name"],
                    "is_pillar_eligible": True,
                    "is_active": True,
                    "meta": brand_data["brand_meta"]
                }
            )

            if b_created:
                total_brands_created += 1
                self.stdout.write(self.style.SUCCESS(f'[BRAND CREATED] {brand_node.name} ({brand_data["brand_slug"]})'))
            else:
                total_brands_updated += 1
                self.stdout.write(self.style.WARNING(f'[BRAND UPDATED] {brand_node.name} ({brand_data["brand_slug"]})'))

            # 2. Seed Model Nodes for this Brand
            for model_info in brand_data["models"]:
                model_node, m_created = TaxonomyNode.objects.update_or_create(
                    project=project,
                    kind=TaxonomyNode.Kind.MODEL,
                    parent=brand_node,
                    slug=model_info["slug"],
                    defaults={
                        "name": model_info["name"],
                        "is_pillar_eligible": True,
                        "is_active": True,
                        "meta": model_info["meta"]
                    }
                )

                if m_created:
                    total_models_created += 1
                    self.stdout.write(f'  --> [MODEL CREATED] {model_node.name} (Slug: {model_info["slug"]})')
                else:
                    total_models_updated += 1
                    self.stdout.write(f'  --> [MODEL UPDATED] {model_node.name} (Slug: {model_info["slug"]})')

        # Summary Log
        self.stdout.write(self.style.NOTICE('--------------------------------------------------'))
        self.stdout.write(self.style.SUCCESS(
            f'Summary:\n'
            f'  Total Brands : {total_brands_created + total_brands_updated} '
            f'(Created: {total_brands_created}, Updated: {total_brands_updated})\n'
            f'  Total Models : {total_models_created + total_models_updated} '
            f'(Created: {total_models_created}, Updated: {total_models_updated})'
        ))
        self.stdout.write(self.style.NOTICE('--- Keyless Motorcycles Seeding Completed Successfully ---'))
        