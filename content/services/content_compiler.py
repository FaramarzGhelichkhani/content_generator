import os
import json
import logging
from typing import List, Dict, Any

from django.template.loader import render_to_string
from django.db import transaction
from django.conf import settings

from content.models import PageContent, PageBrief
# ایمپورت مدل موجودیت‌ها برای دریافت مدل‌های برند
from taxonomy.models import ServiceType, TaxonomyNode

logger = logging.getLogger(__name__)


class PageContentCompiler:
    """
    Service class responsible for rendering PageContent JSON blocks into HTML
    and storing the result directly in the database (compiled_body),
    as well as exporting them to static HTML files for SSG deployment.
    """

    def get_template_name(self, brief: PageBrief) -> str:
        page_type = brief.page_type
        level = brief.page_level
        keyword_text = brief.keyword.text if brief.keyword else ""

        if page_type == PageBrief.PageType.EDUCATIONAL:
            return "pages/educational.html"
        if page_type == PageBrief.PageType.CLUSTER and level == 4:
            return "pages/cluster.html"
        if page_type == PageBrief.PageType.PILLAR:
            if level == 1:
                return "pages/service.html"
            if level == 2:
                return "pages/brand-page.html"
            if level == 3:
                if "ساخت ریموت" in keyword_text:
                    return "pages/model_create_remote.html"
                if "ریموت" == keyword_text:
                    return "pages/model_shop_remote.html"

        logger.warning("No specific template rule matched for PageBrief ID %d. Using fallback.", brief.pk)
        return "pages/default.html"

    def _parse_blocks(self, blocks_data: Any) -> List[Dict[str, Any]]:
        """
        در معماری جدید، بلاک‌ها به صورت یک 'لیست' برگردانده می‌شوند تا قالب بتواند
        به ترتیب روی آن‌ها حلقه بزند و هیچ بلاکی جا نیفتد.
        """
        if not blocks_data:
            return []

        if isinstance(blocks_data, str):
            try:
                blocks_list = json.loads(blocks_data)
            except json.JSONDecodeError:
                logger.error("Failed to decode blocks_json string.")
                return []
        elif isinstance(blocks_data, list):
            blocks_list = blocks_data
        else:
            return []

        parsed_blocks = []
        for block in blocks_list:
            if not isinstance(block, dict):
                continue
            
            block_type = block.get('block_type') or block.get('type')
            if not block_type:
                continue
            
            content = block.get('content', '')
            title = block.get('title', '')

            # بررسی اینکه آیا محتوا خود یک JSON است (مثل مشخصات فنی یا FAQ)
            parsed_data = None
            is_json = False
            if content:
                try:
                    parsed_data = json.loads(content)
                    if isinstance(parsed_data, (dict, list)):
                        is_json = True
                except (json.JSONDecodeError, TypeError):
                     pass
            
            parsed_blocks.append({
                'type': block_type,
                'title': title,
                'content': content,
                'data': parsed_data if is_json else {},
                'is_json': is_json,
                'image_url': block.get('image_url') or block.get('url', ''),
                'caption': block.get('caption', ''),
            })
                
        return parsed_blocks

    def compile_and_save(self, page_content: PageContent) -> bool:
        try:
            brief = page_content.page_brief
            if not brief:
                raise ValueError(f"PageContent ID {page_content.pk} has no associated PageBrief.")

            template_name = self.get_template_name(brief)
            blocks_list = self._parse_blocks(page_content.blocks_json)

            # --- استخراج مدل‌های زیرمجموعه از دیتابیس برای صفحه برند ---
            brand_models = []
            if brief.entity and brief.entity.kind == TaxonomyNode.Kind.BRAND:
                brand_models = TaxonomyNode.objects.filter(
                    parent=brief.entity,
                    kind=TaxonomyNode.Kind.MODEL,
                    is_active=True
                ).order_by('sort_order')

            all_services = ServiceType.objects.filter(is_active=True)

            context = {
                "page": page_content,
                "brief": brief,
                "blocks": blocks_list,         # حالا این یک لیست است نه دیکشنری
                "brand_models": brand_models,  # ارسال مدل‌ها به قالب
                "faq": page_content.faq_json,
                "all_services": all_services,
                "schema": page_content.schema_json,
            }

            rendered_html = render_to_string(template_name, context)

            with transaction.atomic():
                page_content.compiled_body = rendered_html
                page_content.save(update_fields=['compiled_body', 'publish_status', 'generation_status', 'updated_at'])

            logger.info("Successfully compiled HTML for PageContent ID %d", page_content.pk)
            return True

        except Exception as e:
            logger.exception("Error compiling page for PageContent ID %d: %s", page_content.pk, str(e))
            self._mark_as_failed(page_content, str(e))
            return False

    def _mark_as_failed(self, page_content: PageContent, error_message: str) -> None:
        try:
            page_content.publish_status = PageContent.PublishStatus.DRAFT
        except Exception as db_error:
            logger.error("Failed to update error status for PageContent ID %d: %s", page_content.pk, db_error)

    # =========================================================================
    # متدهای جدید برای خروجی گرفتن استاتیک سایت (Static Site Generation / SSI)
    # =========================================================================

    def generate_static_html(self, page_content: PageContent) -> str:
        """
        این متد بدنه کامپایل شده (compiled_body) را درون فایل master_layout.html
        تزریق می‌کند. متغیر is_export را روی True تنظیم می‌کند تا تگ‌های SSI 
        (شامل هدر و فوتر) جایگزین رندر زنده شوند.
        """
        if not page_content.compiled_body:
            # اگر محتوا هنوز رندر نشده است، آن را کامپایل کنید
            self.compile_and_save(page_content)
            page_content.refresh_from_db()

        context = {
            "page": page_content,
            "brief": page_content.page_brief,
            "is_export": True,  # این فلگ به فایل master_layout.html می‌فهماند که تگ SSI بگذارد
        }
        
        # رندر نهایی کل صفحه با قالب اصلی
        final_html = render_to_string("master_layout.html", context)
        return final_html

    def export_to_static_files(self, page_content: PageContent, output_dir: str = "output") -> str:
            """
            یک آبجکت PageContent دریافت کرده و فایل استاتیک آن را در پوشه خروجی تولید می‌کند.
            برای اجرا، وضعیت تولید باید COMPLETED باشد و بدنه کامپایل شده (compiled_body) وجود داشته باشد.
            """
            # ۱. بررسی شرط کامل بودن پروسه تولید
            if page_content.generation_status != PageContent.GenerationStatus.COMPLETED:
                error_msg = f"Cannot export PageContent ID {page_content.pk}: generation_status is '{page_content.generation_status}', expected 'COMPLETED'."
                logger.error(error_msg)
                raise ValueError(error_msg)

            # ۲. بررسی وجود بادیِ کامپایل شده
            if not page_content.compiled_body:
                error_msg = f"Cannot export PageContent ID {page_content.pk}: compiled_body is empty."
                logger.error(error_msg)
                raise ValueError(error_msg)

            brief = page_content.page_brief
            if not brief or not brief.url_path:
                error_msg = f"Cannot export PageContent ID {page_content.pk}: lacks a valid PageBrief or url_path."
                logger.error(error_msg)
                raise ValueError(error_msg)

            # اطمینان از وجود پوشه اصلی خروجی
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # حذف اسلش‌های ابتدا و انتهای آدرس برای جلوگیری از ایجاد پوشه‌های خالی
            # مثال: "/services/honda/" -> "services/honda"
            clean_url_path = brief.url_path.strip("/")
            
            # ایجاد ساختار درختی پوشه‌ها در output/
            page_dir = os.path.join(output_dir, clean_url_path)
            if not os.path.exists(page_dir):
                os.makedirs(page_dir)

            # فایل خروجی را همیشه index.html نامگذاری می‌کنیم
            # تا روی سرور بتوان به صورت آدرس تمیز site.com/services/honda آن را لود کرد
            file_path = os.path.join(page_dir, "index.html")

            try:
                # تولید کد HTML نهایی با ادغام هدر، فوتر (تگ‌های SSI) و بدنه
                final_html = self.generate_static_html(page_content)
                
                # ذخیره فایل روی هارد
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(final_html)
                
                logger.info("Exported static file successfully: %s", file_path)
                return file_path
                
            except Exception as e:
                logger.exception("Failed to export static file for PageContent ID %d: %s", page_content.pk, str(e))
                raise e
            