# content/management/commands/seed_service_brands_pillars.py
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Project
from taxonomy.models import ServiceType, TaxonomyNode, Location
from content.models import Keyword, PageBrief, PageContent, InternalLink

class Command(BaseCommand):
    help = 'ایجاد صفحات پیلار سطح بالا و گراف لینک‌سازی بدون ساخت کلمه کلیدی جدید'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        try:
            project = Project.objects.get(id=1)
        except Project.DoesNotExist:
            self.stdout.write(self.style.ERROR('پروژه با آیدی 1 یافت نشد.'))
            return

        # پیدا کردن سرویس و کلیدواژه مبنا (ساخت ریموت) برای تخصیص به برندها و شهرها
        try:
            create_service = ServiceType.objects.get(project=project, code=ServiceType.Code.CREATE_REMOTE)
            create_keyword = Keyword.objects.get(project=project, text=create_service.root_keyword)
        except (ServiceType.DoesNotExist, Keyword.DoesNotExist):
            self.stdout.write(self.style.ERROR('سرویس "ساخت ریموت" یا کلیدواژه آن یافت نشد. لطفا کامندهای قبلی را اجرا کنید.'))
            return

        # ---------------------------------------------------------
        # ۱. ساخت PageBrief برای سرویس‌های اصلی
        # ---------------------------------------------------------
        services = ServiceType.objects.filter(project=project, is_active=True)
        service_briefs = []
        create_service_brief = None # برای نگهداری رفرنس صفحه ساخت ریموت

        for service in services:
            # استفاده از کلیدواژه موجود بدون ساخت کلیدواژه جدید
            kw = Keyword.objects.get(project=project, text=service.root_keyword)

            # تعیین URL (فروشگاه بدون پیشوند، بقیه با پیشوند services)
            url_path = f"/{service.slug}/" if service.is_ecommerce else f"/services/{service.slug}/"

            brief, created = PageBrief.objects.update_or_create(
                project=project,
                url_path=url_path,  # فقط فیلدهای یونیک بیرون می‌مانند
                defaults={
                    "service_type": service,
                    "entity": None,
                    "location": None,
                    "page_level": 1,
                    "keyword": kw,
                    "page_type": PageBrief.PageType.PILLAR,
                    "target_word_count": 3000,
                }
            )
            PageContent.objects.get_or_create(page_brief=brief)
            service_briefs.append(brief)
            
            if service.code == ServiceType.Code.CREATE_REMOTE:
                create_service_brief = brief
                
            status = "ایجاد شد" if created else "بروزرسانی شد"
            self.stdout.write(self.style.SUCCESS(f'[سرویس] صفحه {brief.url_path} {status}'))

        # ---------------------------------------------------------
        # ۲. ساخت صفحات اصلی برندها (بر پایه سرویس و کلیدواژه ساخت ریموت)
        # ---------------------------------------------------------
        brand_briefs = []
        top_brands = TaxonomyNode.objects.filter(project=project, kind=TaxonomyNode.Kind.BRAND, parent=None)
        
        for brand in top_brands:
            # اسلاگ مستقیم بدون پیشوند /brands/
            b_brief, created = PageBrief.objects.update_or_create(
                project=project, 
                url_path=f"/{brand.slug}/", # فقط فیلدهای یونیک بیرون می‌مانند
                defaults={
                    "service_type": create_service, 
                    "entity": brand, 
                    "location": None,
                    "page_level": 2,
                    "keyword": create_keyword, 
                    "page_type": PageBrief.PageType.PILLAR, 
                    "target_word_count": 2500,
                }
            )
            PageContent.objects.get_or_create(page_brief=b_brief)
            brand_briefs.append(b_brief)

        # ---------------------------------------------------------
        # ۳. ساخت صفحات اصلی شهرها (بر پایه سرویس و کلیدواژه ساخت ریموت)
        # ---------------------------------------------------------
        city_briefs = []
        top_cities = Location.objects.filter(project=project, parent=None)
        
        for city in top_cities:
            # اسلاگ مستقیم بدون پیشوند /locations/
            c_brief, created = PageBrief.objects.update_or_create(
                project=project, 
                url_path=f"/{city.slug}/{create_service.slug}/", # فقط فیلدهای یونیک بیرون می‌مانند
                defaults={
                    "service_type": create_service, 
                    "entity": None, 
                    "location": city, 
                    "page_level": 1,
                    "keyword": create_keyword, 
                    "page_type": PageBrief.PageType.CLUSTER, 
                    "target_word_count": 2500,
                }
            )
            PageContent.objects.get_or_create(page_brief=c_brief)
            city_briefs.append(c_brief)

        # ---------------------------------------------------------
        # ۴. بافتن شبکه لینک‌سازی داخلی (Internal Links)
        # ---------------------------------------------------------
        self.stdout.write(self.style.NOTICE('--- در حال تولید گراف لینک‌سازی داخلی ---'))
        links_created = 0

        # الف) لینک‌های افقی بین سرویس‌های اصلی (Horizontal)
        for source_brief in service_briefs:
            for target_brief in service_briefs:
                if source_brief != target_brief:
                    _, created = InternalLink.objects.get_or_create(
                        source_page=source_brief,
                        target_page=target_brief,
                        defaults={
                            "anchor_text": target_brief.service_type.name,
                            "relation_type": InternalLink.RelationType.HORIZONTAL,
                            "status": InternalLink.Status.PLANNED,
                            "source_reason": "ارتباط افقی بین پیلارهای اصلی خدمات"
                        }
                    )
                    if created: links_created += 1

            # ب) لینک از تمام سرویس‌های اصلی به صفحات برندها
            for b_brief in brand_briefs:
                anchor = f"خدمات ریموت {b_brief.entity.name}" if not source_brief.service_type.is_ecommerce else f"خرید ریموت {b_brief.entity.name}"
                _, created = InternalLink.objects.get_or_create(
                    source_page=source_brief,
                    target_page=b_brief,
                    defaults={
                        "anchor_text": anchor,
                        "relation_type": InternalLink.RelationType.RELATED,
                        "status": InternalLink.Status.PLANNED,
                        "source_reason": "هدایت از سرویس اصلی به صفحه برند"
                    }
                )
                if created: links_created += 1

        # ج) لینک‌های عمودی بین شهر (کلاستر) و پیلار (ساخت ریموت)
        if create_service_brief:
            for c_brief in city_briefs:
                # ۱. لینک رو به بالا (از کلاستر شهر به پیلار ساخت ریموت)
                _, created1 = InternalLink.objects.get_or_create(
                    source_page=c_brief,
                    target_page=create_service_brief,
                    defaults={
                        "anchor_text": "خدمات ساخت ریموت موتور",
                        "relation_type": InternalLink.RelationType.VERTICAL,
                        "status": InternalLink.Status.PLANNED,
                        "source_reason": "انتقال اعتبار از کلاستر محلی به پیلار اصلی"
                    }
                )
                # ۲. لینک رو به پایین (از پیلار ساخت ریموت به کلاستر شهر)
                _, created2 = InternalLink.objects.get_or_create(
                    source_page=create_service_brief,
                    target_page=c_brief,
                    defaults={
                        "anchor_text": f"ساخت ریموت در {c_brief.location.name}",
                        "relation_type": InternalLink.RelationType.VERTICAL,
                        "status": InternalLink.Status.PLANNED,
                        "source_reason": "معرفی شعب و مناطق تحت پوشش"
                    }
                )
                if created1: links_created += 1
                if created2: links_created += 1

        # د) لینک رو به بالا از صفحات برند به پیلار اصلی (ساخت ریموت)
        if create_service_brief:
            for b_brief in brand_briefs:
                _, created = InternalLink.objects.get_or_create(
                    source_page=b_brief,
                    target_page=create_service_brief,
                    defaults={
                        "anchor_text": "مرکز تخصصی ساخت ریموت موتور",
                        "relation_type": InternalLink.RelationType.VERTICAL,
                        "status": InternalLink.Status.PLANNED,
                        "source_reason": "انتقال اعتبار از صفحه برند به پیلار اصلی خدمات"
                    }
                )
                if created: links_created += 1

        self.stdout.write(self.style.SUCCESS(f'{links_created}'))
        