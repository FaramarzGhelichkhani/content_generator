# generation/management/commands/publish_elementor.py
from django.core.management.base import BaseCommand
from content.models import PageContent
from generation.services.elementor_publisher import publish_direct_elementor

class Command(BaseCommand):
    help = 'Publish completed pages directly to WordPress using dynamic Elementor JSON structure.'

    def handle(self, *args, **options):
        # پیدا کردن مقالاتی که نوشته شده‌اند اما هنوز پابلیش نشده‌اند
        pending_pages = PageContent.objects.filter(
            generation_status=PageContent.GenerationStatus.COMPLETED,
            publish_status=PageContent.PublishStatus.DRAFT
        )[:10] # محدودیت ۱۰تایی برای هر بار اجرا

        if not pending_pages:
            self.stdout.write(self.style.WARNING("هیچ مقاله آماده‌ای برای انتشار با المنتور یافت نشد."))
            return

        for page in pending_pages:
            self.stdout.write(f"[*] Publishing to Elementor: {page.page_brief.keyword.text}...")
            success, msg = publish_direct_elementor(page)
            
            if success:
                self.stdout.write(self.style.SUCCESS(f"[+] {msg}"))
            else:
                self.stdout.write(self.style.ERROR(f"[-] {msg}"))
                