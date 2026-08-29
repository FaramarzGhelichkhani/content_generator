# content/management/commands/seed_models_pages.py
from django.core.management.base import BaseCommand
from taxonomy.models import TaxonomyNode
from content.services.model_page_generator import ModelPageGeneratorService

class Command(BaseCommand):
    help = 'ایجاد صفحات پیلار و کلاستر برای مدل‌های موتور به همراه لینک‌سازی'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE('درحال پردازش صفحات مدل‌ها...'))
        
        try:
            # گرفتن تمام مدل‌های فعال
            models = TaxonomyNode.objects.filter(kind=TaxonomyNode.Kind.MODEL, is_active=True)
            
            # فراخوانی سرویس یکپارچه
            service = ModelPageGeneratorService(project_id=1)
            stats = service.process_models(models)
            
            self.stdout.write(self.style.SUCCESS(
                f'عملیات موفقیت‌آمیز بود!\n'
                f'صفحات ساخته شده: {stats["pages_created"]}\n'
                f'صفحات آپدیت شده: {stats["pages_updated"]}\n'
                f'لینک‌های ایجاد شده: {stats["links_created"]}'
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'خطا در اجرا: {str(e)}'))
            