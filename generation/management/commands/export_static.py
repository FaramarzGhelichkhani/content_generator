import os
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.test import Client
from django.conf import settings

from content.services.deployer import FTPDeployer  
# ایمپورت مدل‌های لازم برای استخراج دیتا در هدر و فوتر
from taxonomy.models import ServiceType, TaxonomyNode

class Command(BaseCommand):
    help = 'رندر و ارسال صفحات ثابت (هدر، فوتر، خانه، وبلاگ) به سرور سایت'

    PAGES_CONFIG = {
        'header': {
            'type': 'template',
            'source': 'includes/header.html',
            'remote_dir': 'includes',
            'filename': 'header.html'
        },
        'footer': {
            'type': 'template',
            'source': 'includes/footer.html',
            'remote_dir': 'includes',
            'filename': 'footer.html'
        },
        'home': {
            'type': 'url',
            'source': '/?export=true', 
            'remote_dir': '/',
            'filename': 'index.html'
        },
        'blog': {
            'type': 'url',
            'source': '/blog/?export=true',
            'remote_dir': 'blog',
            'filename': 'index.html'
        }
    }

    def add_arguments(self, parser):
        parser.add_argument(
            'pages',
            nargs='*',
            type=str,
            help='نام صفحاتی که می‌خواهید آپدیت شوند. در صورت خالی بودن، همه آپدیت می‌شوند.'
        )

    def handle(self, *args, **options):
        # ⭐️ راه حل خطای DisallowedHost: اضافه کردن موقت testserver به لیست مجاز
        if 'testserver' not in settings.ALLOWED_HOSTS and '*' not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS.append('testserver')
            settings.ALLOWED_HOSTS.append('localhost')

        requested_pages = options['pages']
        if not requested_pages:
            requested_pages = list(self.PAGES_CONFIG.keys())

        deployer = FTPDeployer()
        client = Client()
        
        output_dir = "output/static_pages"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # ⭐️ استخراج دیتای داینامیک برای تزریق به هدر و فوتر
        # دقت کنید نام کلیدها (مثل brands) باید دقیقاً همان نامی باشد که در HTML استفاده کرده‌اید
        global_context = {
            'all_services': ServiceType.objects.filter(is_active=True).order_by('id'),
            'all_brands': TaxonomyNode.objects.filter(kind=TaxonomyNode.Kind.BRAND, is_active=True).order_by('id'),
            'is_export': True,
        }

        self.stdout.write(self.style.WARNING("در حال شروع پروسه رندر و آپلود..."))

        for page_name in requested_pages:
            if page_name not in self.PAGES_CONFIG:
                self.stdout.write(self.style.ERROR(f"❌ صفحه '{page_name}' تعریف نشده است."))
                continue

            config = self.PAGES_CONFIG[page_name]
            self.stdout.write(f"⏳ در حال پردازش '{page_name}'...")

            try:
                if config['type'] == 'template':
                    # ⭐️ تزریق Context گلوبال به قالب‌های هدر و فوتر
                    final_html = render_to_string(config['source'], global_context)
                
                elif config['type'] == 'url':
                    # ارسال درخواست با هاست استاندارد لوکال برای جلوگیری از ارور
                    response = client.get(config['source'], HTTP_HOST='localhost')
                    if response.status_code != 200:
                        self.stdout.write(self.style.ERROR(f"❌ خطا در رندر آدرس {config['source']} (Status: {response.status_code})"))
                        continue
                    final_html = response.content.decode('utf-8')

                local_path = os.path.join(output_dir, config['filename'])
                with open(local_path, "w", encoding="utf-8") as f:
                    f.write(final_html)

                is_uploaded = deployer.upload_file(local_path, config['remote_dir'])
                
                if is_uploaded:
                    self.stdout.write(self.style.SUCCESS(f"✅ صفحه '{page_name}' با موفقیت در مسیر {config['remote_dir']} آپلود شد."))
                else:
                    self.stdout.write(self.style.ERROR(f"❌ آپلود '{page_name}' از طریق FTP شکست خورد."))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ خطای غیرمنتظره در '{page_name}': {e}"))

        self.stdout.write(self.style.SUCCESS("🎉 پروسه به پایان رسید!"))