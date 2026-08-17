# generation/management/commands/auto_generate.py
from django.core.management.base import BaseCommand
from content.models import PageContent
from generation.services.orchestrator import run_orchestrator_pipeline

class Command(BaseCommand):
    help = "تولید اتوماتیک محتوا برای ۵ مقاله با بالاترین اولویت"

    def handle(self, *args, **options):
        self.stdout.write("در حال واکشی ۵ مقاله با بالاترین اولویت...")
        
        top_pending_contents = PageContent.objects.filter(
            generation_status=PageContent.GenerationStatus.PENDING
        ).select_related('page_brief__keyword').order_by(
            '-page_brief__keyword__priority_score'
        )[:5]

        if not top_pending_contents.exists():
            self.stdout.write(self.style.WARNING("هیچ مقاله‌ای در وضعیت PENDING یافت نشد."))
            return

        results = run_orchestrator_pipeline(top_pending_contents)
        
        for title, status in results:
            self.stdout.write(self.style.SUCCESS(f"{title}: {status}"))
            