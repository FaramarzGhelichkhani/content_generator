# content/management/commands/seed_informational_pages.py
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from core.models import Project, IntentType
from taxonomy.models import ServiceType
from content.models import Keyword, PageBrief, PageContent, InternalLink

class Command(BaseCommand):
    help = 'ایجاد صفحات مقالات آموزشی (Informational) و گراف لینک‌سازی آن‌ها به پیلارهای اصلی'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        try:
            project = Project.objects.get(id=1)
        except Project.DoesNotExist:
            self.stdout.write(self.style.ERROR('پروژه با آیدی 1 یافت نشد.'))
            return

        # دریافت نیت آموزشی و کلمات کلیدی آن
        try:
            intent_info = IntentType.objects.get(code=IntentType.Code.INFORMATIONAL)
        except IntentType.DoesNotExist:
            self.stdout.write(self.style.ERROR('نیت INFORMATIONAL یافت نشد.'))
            return

        info_keywords = Keyword.objects.filter(project=project, intent=intent_info)
        
        if not info_keywords.exists():
            self.stdout.write(self.style.WARNING('هیچ کلمه کلیدی با نیت INFORMATIONAL یافت نشد.'))
            return

        # پیدا کردن پیلارهای اصلی برای لینک‌دهی (لایه ۱)
        create_service = ServiceType.objects.filter(project=project, code=ServiceType.Code.CREATE_REMOTE).first()
        shop_service = ServiceType.objects.filter(project=project, code=ServiceType.Code.SELL_REMOTE).first()

        create_pillar = PageBrief.objects.filter(project=project, service_type=create_service, page_level=1).first() if create_service else None
        shop_pillar = PageBrief.objects.filter(project=project, service_type=shop_service, page_level=1).first() if shop_service else None

        stats = {"pages_created": 0, "pages_updated": 0, "links_created": 0}

        self.stdout.write(self.style.NOTICE('--- در حال تولید صفحات مقالات آموزشی ---'))

        for kw in info_keywords:
            kw_slug = slugify(kw.text, allow_unicode=True)
            # قرار دادن مقالات در دایرکتوری blog
            url_path = f"/blog/{kw_slug}/"

            brief, created = PageBrief.objects.update_or_create(
                project=project,
                url_path=url_path, # کلید یکتا بیرون می‌ماند
                defaults={
                    "keyword": kw,
                    "service_type": None,
                    "entity": None,
                    "location": None,
                    "page_type": PageBrief.PageType.EDUCATIONAL,
                    "page_level": 1, # مقالات به عنوان صفحات مستقل سطح بالا در بلاگ
                    "target_word_count": 2500,
                }
            )
            PageContent.objects.get_or_create(page_brief=brief)
            
            if created: stats["pages_created"] += 1
            else: stats["pages_updated"] += 1

            # لینک دهی از مقاله به پیلار خدمات
            if create_pillar:
                _, lc1 = InternalLink.objects.get_or_create(
                    source_page=brief,
                    target_page=create_pillar,
                    defaults={
                        "anchor_text": "خدمات تخصصی کیلس و ریموت موتور",
                        "relation_type": InternalLink.RelationType.EDUCATIONAL,
                        "status": InternalLink.Status.PLANNED,
                        "source_reason": "هدایت کاربر از مقاله آموزشی به دریافت خدمات"
                    }
                )
                if lc1: stats["links_created"] += 1

            # لینک دهی از مقاله به پیلار فروشگاه
            if shop_pillar:
                _, lc2 = InternalLink.objects.get_or_create(
                    source_page=brief,
                    target_page=shop_pillar,
                    defaults={
                        "anchor_text": "خرید ریموت فابریک موتورسیکلت",
                        "relation_type": InternalLink.RelationType.EDUCATIONAL,
                        "status": InternalLink.Status.PLANNED,
                        "source_reason": "هدایت کاربر از مقاله آموزشی به خرید قطعه"
                    }
                )
                if lc2: stats["links_created"] += 1

        self.stdout.write(self.style.SUCCESS(
            f'پایان عملیات:\n'
            f'مقالات ساخته شده: {stats["pages_created"]}\n'
            f'مقالات آپدیت شده: {stats["pages_updated"]}\n'
            f'لینک‌های ایجاد شده: {stats["links_created"]}'
        ))
