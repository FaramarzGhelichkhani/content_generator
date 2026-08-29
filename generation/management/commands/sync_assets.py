import os
import json
import hashlib
from django.core.management.base import BaseCommand
from content.services.deployer import FTPDeployer  # ایمپورت مسیر را با پروژه خود چک کنید

class Command(BaseCommand):
    help = 'آپلود هوشمند فایل‌های استاتیک و مدیا (فقط فایل‌های جدید و تغییر یافته)'

    # مسیر فایل کش برای ذخیره وضعیت آپلودها
    STATE_FILE = 'sync_state.json'

    TARGETS = {
        'css':   {'local': 'assets/css',   'remote': 'assets/css'},
        'fonts': {'local': 'assets/fonts', 'remote': 'assets/fonts'},
        'img':   {'local': 'assets/img',   'remote': 'assets/img'},
        'media': {'local': 'media',        'remote': 'media'},
    }

    def add_arguments(self, parser):
        parser.add_argument(
            'targets',
            nargs='*',
            type=str,
            help='بخش‌هایی که می‌خواهید آپلود شوند (css, fonts, img, media).'
        )
        # اضافه کردن یک سوئیچ برای آپلود اجباری همه چیز
        parser.add_argument(
            '--force',
            action='store_true',
            help='نادیده گرفتن کش و آپلود اجباری تمام فایل‌ها',
        )

    def get_file_hash(self, filepath):
        """گرفتن اثرانگشت (MD5 Hash) از محتوای فایل برای تشخیص تغییرات"""
        hasher = hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                # خواندن فایل به صورت تکه‌ای برای جلوگیری از پر شدن رم (مناسب ویدیوها و عکس‌های سنگین)
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return None

    def handle(self, *args, **options):
        requested_targets = options['targets']
        force_upload = options['force']
        
        if not requested_targets:
            requested_targets = list(self.TARGETS.keys())

        deployer = FTPDeployer()
        
        # ۱. لود کردن وضعیت قبلی (کش)
        sync_state = {}
        if not force_upload and os.path.exists(self.STATE_FILE):
            try:
                with open(self.STATE_FILE, 'r', encoding='utf-8') as f:
                    sync_state = json.load(f)
            except json.JSONDecodeError:
                sync_state = {}

        self.stdout.write(self.style.WARNING("🚀 در حال شروع پروسه همگام‌سازی هوشمند..."))

        try:
            for target in requested_targets:
                if target not in self.TARGETS:
                    self.stdout.write(self.style.ERROR(f"❌ آرگومان '{target}' نامعتبر است."))
                    continue

                config = self.TARGETS[target]
                local_dir = config['local']
                
                if not os.path.exists(local_dir):
                    self.stdout.write(self.style.WARNING(f"⚠️ پوشه '{local_dir}' یافت نشد."))
                    continue

                self.stdout.write(self.style.WARNING(f"\n⏳ در حال اسکن '{target}'..."))
                
                uploaded_count = 0
                skipped_count = 0
                failed_count = 0

                for root, dirs, files in os.walk(local_dir):
                    for file in files:
                        local_file_path = os.path.join(root, file)
                        
                        # ۲. بررسی تغییرات فایل با هش
                        current_hash = self.get_file_hash(local_file_path)
                        
                        # اگر هش فایل با دفعه قبل یکی بود و کاربر دستور force نداده بود -> اسکیپ کن
                        if not force_upload and sync_state.get(local_file_path) == current_hash:
                            skipped_count += 1
                            continue
                        
                        remote_sub_dir = root.replace('\\', '/')
                        self.stdout.write(f"  -> آپلود: {file} ... ", ending='')
                        
                        # ۳. آپلود فایل در صورت جدید/تغییر یافته بودن
                        is_uploaded = deployer.upload_file(local_file_path, remote_sub_dir)
                        
                        if is_uploaded:
                            uploaded_count += 1
                            # ثبت هش جدید در کش
                            sync_state[local_file_path] = current_hash
                            self.stdout.write(self.style.SUCCESS("✅"))
                        else:
                            failed_count += 1
                            self.stdout.write(self.style.ERROR("❌"))
                
                # گزارش نهایی هر بخش
                self.stdout.write(self.style.SUCCESS(
                    f"🎯 '{target}': {uploaded_count} آپلود شد | {skipped_count} بدون تغییر (رد شد) | {failed_count} خطا."
                ))

        finally:
            # ۴. در نهایت (حتی در صورت کنسل کردن وسط کار)، وضعیت جدید را ذخیره کن
            with open(self.STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(sync_state, f, indent=4)
                
        self.stdout.write(self.style.SUCCESS("\n🎉 تمام عملیات به پایان رسید!"))
        