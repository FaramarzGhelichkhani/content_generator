from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import re
from urllib.parse import quote
import xml.etree.ElementTree as ET

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from content.services.deployer import FTPDeployer
from taxonomy.models import TaxonomyNode, ServiceType
from content.models import PageContent


class Command(BaseCommand):
    help = "تولید، اعتبارسنجی و آپلود سایت‌مپ‌های ریموت سیکلت"

    DOMAIN = "https://remotecyclet.ir"
    NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"

    MAX_URLS = 50_000
    MAX_BYTES = 50 * 1024 * 1024

    def handle(self, *args, **options):

        self.sitemap_dir = (
            Path(settings.BASE_DIR) / "output" / "sitemaps"
        )

        self.sitemap_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        ET.register_namespace("", self.NAMESPACE)

        self.stdout.write(
            self.style.WARNING("در حال ساخت سایت‌مپ‌ها...")
        )

        sitemap_files = []

        # ==========================================
        # 1. صفحات اصلی سایت
        # ==========================================

        self._add_sitemap(
            "sitemap-pages.xml",
            ["", "shop"],
            sitemap_files,
        )

        # ==========================================
        # 2. خدمات عمومی
        # ==========================================

        services = (
            ServiceType.objects
            .filter(is_active=True)
            .exclude(slug="shop")
        )

        service_paths = [
            f"services/{service.slug}"
            for service in services
            if service.slug
        ]

        # خدمات وابسته به موقعیت مکانی
        location_service_pages = (
            PageContent.objects.filter(
                page_brief__location__isnull=False,
                page_brief__service_type__isnull=False,
                page_brief__location__parent__isnull=True,

                generation_status=(
                    PageContent.GenerationStatus.COMPLETED
                ),

                publish_status=(
                    PageContent.PublishStatus.PUBLISHED
                ),

                page_brief__is_active=True,
            )
            .select_related("page_brief")
            .distinct()
        )

        for page in location_service_pages:

            path = page.page_brief.url_path

            if path:
                service_paths.append(path)

        self._add_sitemap(
            "sitemap-services.xml",
            service_paths,
            sitemap_files,
        )

        # ==========================================
        # 3. برندهای موتورسیکلت
        # ==========================================

        brand_slugs = list(
            TaxonomyNode.objects.filter(
                kind=TaxonomyNode.Kind.BRAND,
                is_active=True,
            ).values_list("slug", flat=True)
        )

        brand_slugs = [
            slug.strip("/")
            for slug in brand_slugs
            if slug
        ]

        self._add_sitemap(
            "sitemap-brands.xml",
            brand_slugs,
            sitemap_files,
        )

        active_brands = set(brand_slugs)

        # ==========================================
        # 4. مقالات وبلاگ
        # ==========================================

        blog_articles = (
            PageContent.objects.filter(

                page_brief__keyword__intent__code=(
                    "informational"
                ),

                generation_status=(
                    PageContent.GenerationStatus.COMPLETED
                ),

                publish_status=(
                    PageContent.PublishStatus.PUBLISHED
                ),

                page_brief__is_active=True,
            )
            .select_related("page_brief")
            .distinct()
        )

        blog_paths = ["blog"]

        for article in blog_articles:

            full_path = (
                article.page_brief.url_path or ""
            ).strip("/")

            slug = (
                article.slug or ""
            ).strip("/")

            if full_path.startswith("blog/"):

                blog_paths.append(full_path)

            elif slug.startswith("blog/"):

                blog_paths.append(slug)

            elif slug:

                blog_paths.append(f"blog/{slug}")

            elif full_path:

                blog_paths.append(f"blog/{full_path}")

        self._add_sitemap(
            "sitemap-blog.xml",
            blog_paths,
            sitemap_files,
        )

        # ==========================================
        # 5. صفحات مدل‌ها بر اساس برند
        # ==========================================

        model_pages = (
            PageContent.objects.filter(

                page_brief__page_level__in=[3, 4],

                generation_status=(
                    PageContent.GenerationStatus.COMPLETED
                ),

                publish_status=(
                    PageContent.PublishStatus.PUBLISHED
                ),

                page_brief__is_active=True,
            )
            .select_related("page_brief")
            .distinct()
        )

        brand_groups = defaultdict(list)

        for page in model_pages:

            # استفاده از مسیر کامل صفحه
            path = (
                page.page_brief.url_path or ""
            ).strip("/")

            if not path:

                self.stderr.write(
                    self.style.WARNING(
                        f"صفحه {page.pk} مسیر url_path ندارد."
                    )
                )

                continue

            # استخراج برند از ابتدای مسیر
            brand_slug = path.split("/", 1)[0]

            # بررسی وجود برند فعال
            if brand_slug not in active_brands:

                self.stderr.write(
                    self.style.WARNING(
                        f"مسیر {path!r} متعلق به برند "
                        "فعال شناخته‌شده نیست."
                    )
                )

                continue

            # اعتبارسنجی نام برند برای ساخت فایل
            if not re.fullmatch(
                r"[A-Za-z0-9_-]+",
                brand_slug
            ):

                raise CommandError(
                    f"slug برند نامعتبر است: {brand_slug!r}"
                )

            brand_groups[brand_slug].append(path)

        # تولید فایل جداگانه برای هر برند
        for brand_slug, paths in sorted(
            brand_groups.items()
        ):

            self._add_sitemap(
                f"sitemap-models-{brand_slug}.xml",
                paths,
                sitemap_files,
            )

        # ==========================================
        # 6. ساخت Sitemap Index
        # ==========================================

        self._create_index_xml(
            "sitemap.xml",
            sitemap_files,
        )

        # ==========================================
        # 7. اعتبارسنجی فایل‌ها
        # ==========================================

        files_to_upload = [
            *sitemap_files,
            "sitemap.xml"
        ]

        self._validate_files(
            files_to_upload,
            sitemap_files,
        )

        # ==========================================
        # 8. آپلود FTP
        # ==========================================

        self.stdout.write(
            self.style.WARNING(
                "در حال آپلود فایل‌های XML..."
            )
        )

        deployer = FTPDeployer()

        failed = []

        # ابتدا زیرسایت‌مپ‌ها آپلود می‌شوند
        for filename in sitemap_files:

            local_path = (
                self.sitemap_dir / filename
            )

            success = deployer.upload_file(
                str(local_path),
                "/"
            )

            if success:

                self.stdout.write(
                    self.style.SUCCESS(
                        f"آپلود شد: {filename}"
                    )
                )

            else:

                failed.append(filename)

                self.stderr.write(
                    self.style.ERROR(
                        f"آپلود ناموفق: {filename}"
                    )
                )

        # در صورت خطا، سایت‌مپ مادر آپلود نشود
        if failed:

            raise CommandError(
                "آپلود سایت‌مپ مادر متوقف شد. "
                "فایل‌های ناموفق: "
                + ", ".join(failed)
            )

        # آپلود سایت‌مپ مادر در آخرین مرحله
        index_path = (
            self.sitemap_dir / "sitemap.xml"
        )

        if not deployer.upload_file(
            str(index_path),
            "/"
        ):

            raise CommandError(
                "آپلود sitemap.xml ناموفق بود."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"عملیات موفق بود. "
                f"{len(files_to_upload)} فایل آپلود شد."
            )
        )

    # ==============================================
    # ساخت URL استاندارد
    # ==============================================

    def _make_url(self, path):

        path = str(path or "").strip().strip("/")

        path = re.sub(
            r"/+",
            "/",
            path
        )

        if not path:
            return f"{self.DOMAIN}/"

        if (
            "?" in path
            or "#" in path
            or "\\" in path
            or "://" in path
            or any(
                part in {".", ".."}
                for part in path.split("/")
            )
        ):

            raise CommandError(
                f"مسیر URL نامعتبر است: {path!r}"
            )

        encoded_path = quote(
            path,
            safe="/-._~%"
        )

        return (
            f"{self.DOMAIN}/{encoded_path}/"
        )

    # ==============================================
    # افزودن فایل سایت‌مپ
    # ==============================================

    def _add_sitemap(
        self,
        filename,
        paths,
        sitemap_files
    ):

        # حذف URLهای تکراری
        urls = list(
            dict.fromkeys(
                self._make_url(path)
                for path in paths
            )
        )

        if not urls:

            self.stdout.write(
                self.style.WARNING(
                    f"بدون URL؛ رد شد: {filename}"
                )
            )

            return

        self._create_xml(
            filename,
            urls
        )

        sitemap_files.append(filename)

        self.stdout.write(
            f"{filename}: {len(urls)} URL"
        )

    # ==============================================
    # ساخت XML سایت‌مپ
    # ==============================================

    def _create_xml(
        self,
        filename,
        urls
    ):

        if len(urls) > self.MAX_URLS:

            raise CommandError(
                f"{filename}: تعداد URL بیش از حد مجاز است."
            )

        namespace = self.NAMESPACE

        root = ET.Element(
            f"{{{namespace}}}urlset"
        )

        for url in urls:

            url_element = ET.SubElement(
                root,
                f"{{{namespace}}}url"
            )

            ET.SubElement(
                url_element,
                f"{{{namespace}}}loc"
            ).text = url

        tree = ET.ElementTree(root)

        ET.indent(
            tree,
            space="  "
        )

        filepath = (
            self.sitemap_dir / filename
        )

        tree.write(
            filepath,
            encoding="utf-8",
            xml_declaration=True
        )

        if filepath.stat().st_size > self.MAX_BYTES:

            raise CommandError(
                f"{filename}: حجم فایل بیش از حد مجاز است."
            )

    # ==============================================
    # ساخت سایت‌مپ مادر
    # ==============================================

    def _create_index_xml(
        self,
        filename,
        sitemap_files
    ):

        namespace = self.NAMESPACE

        root = ET.Element(
            f"{{{namespace}}}sitemapindex"
        )

        for sitemap_file in sitemap_files:

            sitemap_element = ET.SubElement(
                root,
                f"{{{namespace}}}sitemap"
            )

            ET.SubElement(
                sitemap_element,
                f"{{{namespace}}}loc"
            ).text = (
                f"{self.DOMAIN}/{sitemap_file}"
            )

            # تاریخ واقعی تغییر فایل XML
            local_file = (
                self.sitemap_dir / sitemap_file
            )

            if local_file.exists():

                actual_mtime = datetime.fromtimestamp(
                    local_file.stat().st_mtime,
                    tz=timezone.utc
                ).isoformat(
                    timespec="seconds"
                )

                ET.SubElement(
                    sitemap_element,
                    f"{{{namespace}}}lastmod"
                ).text = actual_mtime

        tree = ET.ElementTree(root)

        ET.indent(
            tree,
            space="  "
        )

        tree.write(
            self.sitemap_dir / filename,
            encoding="utf-8",
            xml_declaration=True
        )

    # ==============================================
    # اعتبارسنجی XML
    # ==============================================

    def _validate_files(
        self,
        filenames,
        child_filenames
    ):

        namespace = {
            "sm": self.NAMESPACE
        }

        for filename in filenames:

            filepath = (
                self.sitemap_dir / filename
            )

            if not filepath.is_file():

                raise CommandError(
                    f"فایل پیدا نشد: {filename}"
                )

            if filepath.stat().st_size > self.MAX_BYTES:

                raise CommandError(
                    f"حجم فایل زیاد است: {filename}"
                )

            try:

                document = ET.parse(filepath)

            except ET.ParseError as exc:

                raise CommandError(
                    f"XML نامعتبر: {filename}: {exc}"
                ) from exc

            # اعتبارسنجی Sitemap Index
            if filename == "sitemap.xml":

                actual = [
                    el.text
                    for el in document.findall(
                        ".//sm:sitemap/sm:loc",
                        namespace
                    )
                ]

                expected = [
                    f"{self.DOMAIN}/{name}"
                    for name in child_filenames
                ]

                if actual != expected:

                    raise CommandError(
                        "محتوای Sitemap Index "
                        "با فایل‌های تولیدی مطابقت ندارد."
                    )

                if any(
                    not url.endswith(".xml")
                    for url in actual
                ):

                    raise CommandError(
                        "Sitemap Index به صفحه HTML اشاره می‌کند."
                    )

            # اعتبارسنجی سایت‌مپ‌های معمولی
            else:

                urls = [
                    el.text or ""
                    for el in document.findall(
                        ".//sm:url/sm:loc",
                        namespace
                    )
                ]

                if not urls:

                    raise CommandError(
                        f"سایت‌مپ بدون URL: {filename}"
                    )

                if len(urls) != len(set(urls)):

                    raise CommandError(
                        f"URL تکراری در {filename}"
                    )

                if len(urls) > self.MAX_URLS:

                    raise CommandError(
                        f"تعداد URL زیاد است: {filename}"
                    )

                if any(
                    not url.startswith(
                        f"{self.DOMAIN}/"
                    )
                    or not url.endswith("/")
                    for url in urls
                ):

                    raise CommandError(
                        f"URL غیر canonical در {filename}"
                    )

        self.stdout.write(
            self.style.SUCCESS(
                "اعتبارسنجی محلی XMLها موفق بود."
            )
        )