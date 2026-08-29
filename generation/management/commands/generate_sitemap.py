import os
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from content.services.deployer import FTPDeployer

# ایمپورت مدل‌ها (این مسیرها را با ساختار واقعی پروژه خود تنظیم کنید)
from taxonomy.models import TaxonomyNode, ServiceType
from content.models import PageContent


class Command(BaseCommand):
    help = 'تولید فایل‌های Sitemap داینامیک و ارسال به سرور FTP'

    DOMAIN = "https://remotecyclet.ir"
    SITEMAP_DIR = "output/sitemaps"

    def handle(self, *args, **options):
            self.stdout.write(self.style.WARNING("🚀 در حال جمع‌آوری اطلاعات و ساخت سایت‌مپ‌ها..."))

            if not os.path.exists(self.SITEMAP_DIR):
                os.makedirs(self.SITEMAP_DIR)

            # لیست فایل‌های تولید شده برای قرارگیری در سایت‌مپ مادر
            sitemap_files = []

            # 1. خدمات عمومی
            services = ServiceType.objects.filter(is_active=True)
            services_urls = [f"{self.DOMAIN}/services/{s.slug}" for s in services]
            location_sevice_page = PageContent.objects.filter(
                            page_brief__location__isnull=False,
                            page_brief__service_type__isnull=False,
                            page_brief__location__parent__isnull=True,
                            generation_status=PageContent.GenerationStatus.COMPLETED,
                            publish_status=PageContent.PublishStatus.PUBLISHED,
                            page_brief__is_active=True
                        )
            for qs in location_sevice_page:
                url = f"{self.DOMAIN}/{qs.page_brief.url_path}"
                services_urls.append(url)
            self._create_xml('sitemap-services.xml', services_urls, priority="0.9", changefreq="monthly")
            sitemap_files.append('sitemap-services.xml')

            # 2. برندها
            brands = TaxonomyNode.objects.filter(kind=TaxonomyNode.Kind.BRAND, is_active=True)
            brands_urls = [f"{self.DOMAIN}/{b.slug}" for b in brands]
            self._create_xml('sitemap-brands.xml', brands_urls, priority="0.8", changefreq="weekly")
            sitemap_files.append('sitemap-brands.xml')

            # 3. مقالات وبلاگ
            blog_articles = PageContent.objects.filter(
                page_brief__keyword__intent__code='informational',
                generation_status=PageContent.GenerationStatus.COMPLETED,
                publish_status=PageContent.PublishStatus.PUBLISHED,
                page_brief__is_active=True
            )
            blog_urls = [f"{self.DOMAIN}/blog/{a.slug or a.page_brief.url_path.strip('/')}" for a in blog_articles]
            blog_urls.insert(0, f"{self.DOMAIN}/blog")
            self._create_xml('sitemap-blog.xml', blog_urls, priority="0.7", changefreq="weekly")
            sitemap_files.append('sitemap-blog.xml')

            # 4. ⭐️ دسته‌بندی هوشمند مدل‌ها بر اساس برند (پیلار و کلاسترها) ⭐️
            model_pages = PageContent.objects.filter(
                page_brief__page_level__in =[3,4],
                generation_status=PageContent.GenerationStatus.COMPLETED,
                publish_status=PageContent.PublishStatus.PUBLISHED,
                page_brief__is_active=True
            )
            
            # یک دیکشنری برای گروه‌بندی لینک‌ها: {'honda': ['url1', 'url2'], 'yamaha': ['url1']}
            brand_groups = {}
            
            for page in model_pages:
                url_path = page.slug or page.page_brief.url_path.strip('/')
                
                # استخراج نام برند از آدرس (مثلا از 'honda/click/...' کلمه 'honda' جدا می‌شود)
                parts = url_path.split('/')
                brand_slug = parts[0] if parts else 'other'
                
                full_url = f"{self.DOMAIN}/{url_path}"
                
                if brand_slug not in brand_groups:
                    brand_groups[brand_slug] = []
                brand_groups[brand_slug].append(full_url)

            # ساخت یک فایل XML مجزا برای هر برند
            for brand, urls in brand_groups.items():
                filename = f"sitemap-models-{brand}.xml"
                self._create_xml(filename, urls, priority="0.9", changefreq="daily")
                sitemap_files.append(filename) # اضافه کردن به لیست سایت‌مپ مادر

            # 5. ساخت سایت‌مپ مادر (Sitemap Index)
            # الان متغیر sitemap_files شامل تمام خدمات، وبلاگ و ده‌ها سایت‌مپ برندها است
            self._create_index_xml('sitemap.xml', sitemap_files)

            # 6. آپلود به سرور FTP
            self.stdout.write(self.style.WARNING("\n⏳ در حال آپلود فایل‌ها به سرور..."))
            deployer = FTPDeployer()
            
            files_to_upload = sitemap_files + ['sitemap.xml']
            success_count = 0
            
            for file_name in files_to_upload:
                local_path = os.path.join(self.SITEMAP_DIR, file_name)
                
                if deployer.upload_file(local_path, '/'):
                    success_count += 1
                    self.stdout.write(self.style.SUCCESS(f"✅ فایل {file_name} آپلود شد."))
                else:
                    self.stdout.write(self.style.ERROR(f"❌ خطا در آپلود {file_name}"))

            self.stdout.write(self.style.SUCCESS(f"\n🎉 عملیات به پایان رسید. {success_count} فایل آپلود شد."))

    def _create_xml(self, filename, urls, priority="0.5", changefreq="weekly"):
        current_date = now().strftime("%Y-%m-%d")
        
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        if not urls:
            urls = [self.DOMAIN]
            
        for url in urls:
            clean_url = url.replace('//', '/').replace('https:/', 'https://')
            
            xml_content += "  <url>\n"
            xml_content += f"    <loc>{clean_url}</loc>\n"
            xml_content += f"    <lastmod>{current_date}</lastmod>\n"
            xml_content += f"    <changefreq>{changefreq}</changefreq>\n"
            xml_content += f"    <priority>{priority}</priority>\n"
            xml_content += "  </url>\n"
            
        xml_content += '</urlset>'
        
        filepath = os.path.join(self.SITEMAP_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(xml_content)


    def _create_index_xml(self, filename, sitemap_files):
        current_date = now().strftime("%Y-%m-%dT%H:%M:%S+00:00")
        
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content += '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        xml_content += "  <sitemap>\n"
        xml_content += f"    <loc>{self.DOMAIN}</loc>\n"
        xml_content += f"    <lastmod>{current_date}</lastmod>\n"
        xml_content += "  </sitemap>\n"

        for sitemap_file in sitemap_files:
            xml_content += "  <sitemap>\n"
            xml_content += f"    <loc>{self.DOMAIN}/{sitemap_file}</loc>\n"
            xml_content += f"    <lastmod>{current_date}</lastmod>\n"
            xml_content += "  </sitemap>\n"
            
        xml_content += '</sitemapindex>'
        
        filepath = os.path.join(self.SITEMAP_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(xml_content)
