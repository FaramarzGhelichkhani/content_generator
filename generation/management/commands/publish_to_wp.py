# generation/management/commands/publish_to_wp.py
from django.core.management.base import BaseCommand
from content.models import PageContent
from generation.services.wordpress_publisher import publish_to_wordpress

class Command(BaseCommand):
    help = "ارسال گروهی مقالات تکمیل شده به وردپرس"

    def handle(self, *args, **options):
        # پیدا کردن مقالاتی که هوش مصنوعی کامل کرده ولی هنوز منتشر نشده‌اند
        ready_pages = PageContent.objects.filter(
            generation_status=PageContent.GenerationStatus.COMPLETED,
        ).exclude(publish_status=PageContent.PublishStatus.PUBLISHED)[:10] # لیمیت ۵ تایی برای هر ران

        if not ready_pages.exists():
            self.stdout.write(self.style.WARNING("مقاله‌ی جدیدی برای انتشار یافت نشد."))
            return

        self.stdout.write(f"در حال ارسال {ready_pages.count()} مقاله به وردپرس...")

        for page in ready_pages:
            self.stdout.write(f"[*] Publishing: {page.page_brief.keyword.text}")
            success, msg = publish_to_wordpress(page)
            
            if success:
                self.stdout.write(self.style.SUCCESS(f"[+] {msg}"))
            else:
                self.stdout.write(self.style.ERROR(f"[-] {msg}"))
