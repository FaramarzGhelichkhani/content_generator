# generation/services/orchestrator.py
import json
import re
from django.utils import timezone
from content.models import PageContent

# ایمپورت بازوهای اجرایی خط تولید
from generation.agents.planner import generate_page_plan
from generation.agents.writer import generate_all_blocks
from generation.agents.link_injector import inject_links_and_references
from generation.agents.seo_reviewer import review_page_seo
from generation.services.schema_generator import generate_advanced_schema


def run_orchestrator_pipeline(queryset):
    """
    ارکستراتور ارشد و هماهنگ‌کننده خط تولید محتوای خودترمیمی.
    """
    contents = list(queryset)[:5]
    results = []

    for page_content in contents:
        brief = page_content.page_brief
        base_domain = brief.project.base_domain
        
        print(f"\n========================================")
        print(f"[*] Orchestrating Content Pipeline for: {brief.keyword.text}")
        print(f"========================================")

        # --------------------------------------------------------
        # پیش‌پردازش: بررسی وابستگی‌های کلاستر به پیلار
        # --------------------------------------------------------
        parent_context = None
        if brief.page_type == "cluster" and brief.parent_page:
            print(f"[*] Cluster Page Detected. Fetching Parent (Pillar) Data: {brief.parent_page.keyword.text}")
            
            # بررسی اینکه آیا صفحه والد محتوایی تولید شده دارد یا خیر
            if hasattr(brief.parent_page, 'content') and brief.parent_page.content:
                parent_content_obj = brief.parent_page.content
                parent_context = {
                    "parent_keyword": brief.parent_page.keyword.text,
                    "parent_url": brief.parent_page.url_path,
                    "parent_outline": parent_content_obj.outline_json, # ارسال ساختار برای جلوگیری از تکرار تیتر
                    "parent_focus_keyword": parent_content_obj.focus_keyword,
                }
                print(f"[+] Parent outline successfully loaded to prevent cannibalization.")
            else:
                print(f"[-] Warning: Parent Pillar page '{brief.parent_page.keyword.text}' does not have generated content yet.")

        # --------------------------------------------------------
        # مرحله ۱: لایه برنامه‌ریزی ساختار (Planner Agent)
        # --------------------------------------------------------
        # پارامتر parent_context را به پلنر پاس می‌دهیم
        if not generate_page_plan(page_content, parent_context=parent_context):
            page_content.generation_status = PageContent.GenerationStatus.FAILED if hasattr(PageContent.GenerationStatus, 'FAILED') else PageContent.GenerationStatus.PENDING
            page_content.generation_error = "توقف خط تولید: خطا در فاز برنامه‌ریزی (Planner)"
            page_content.save()
            results.append((brief.keyword.text, "خطا در فاز برنامه‌ریزی ساختار"))
            continue

        seo_approved = False
        max_loops = 3
        local_failsafe_counter = 0
        
        if page_content.generation_status == PageContent.GenerationStatus.COMPLETED:
            seo_approved = True

        # --------------------------------------------------------
        # مرحله ۲: حلقه هوشمند خودترمیمی (Writer <-> SEO Reviewer)
        # --------------------------------------------------------
        writer_aborted = False
        while not seo_approved and page_content.iterations < max_loops and local_failsafe_counter < max_loops:
            local_failsafe_counter += 1
            page_content.refresh_from_db()
            
            print(f"\n[*] [Loop {local_failsafe_counter}/{max_loops}] Invoking Resumable Writer Agent...")
            if not generate_all_blocks(page_content):
                print(f"[-] Writer Agent critical interruption.")
                writer_aborted = True
                break

            print(f"[*] [Loop {local_failsafe_counter}/{max_loops}] Invoking Smart Link Injector...")
            inject_links_and_references(page_content, base_domain)

            print(f"[*] [Loop {local_failsafe_counter}/{max_loops}] Executing SEO Semantic Audit...")
            seo_approved = review_page_seo(page_content)
            
            page_content.refresh_from_db()

        # اگر در لوپ رایتر خطای مهلک رخ داد، کلاً متوقف شود
        if writer_aborted:
            page_content.generation_error = "توقف خط تولید: خطای غیرقابل بازیابی در مرحله نگارش (Writer)"
            page_content.save()
            results.append((brief.keyword.text, "ناموفق در چرخه نگارش"))
            continue

        # --------------------------------------------------------
        # مرحله ۳: پس‌پردازش و غنی‌سازی نهایی
        # --------------------------------------------------------
        page_content.refresh_from_db()
        
        if seo_approved or page_content.iterations >= max_loops or local_failsafe_counter >= max_loops:
            
            # ثبت وضعیت نهایی و دلیل توقف در دیتابیس
            if not seo_approved:
                print(f"[!] Circuit Breaker: SEO hit max iterations ({max_loops}). Forcing compilation step...")
                page_content.generation_error = f"پایان اجباری: اتمام سقف {max_loops} بار اصلاح. نمره سئو نهایی: {page_content.seo_score}"
            else:
                page_content.generation_error = f"پایان موفق: سئو با نمره {page_content.seo_score} تایید شد."

            print(f"[*] Extracting FAQ data directly from generated blocks...")
            
            blocks = page_content.blocks_json or []
            
            for b in blocks:
                if b.get("block_type") == "faq":
                    raw_faq_output = b.get("content", "").strip()
                    try:
                        clean_json = raw_faq_output.strip()
                        if clean_json.startswith("```json"):
                            clean_json = clean_json[7:]
                        elif clean_json.startswith("```"):
                            clean_json = clean_json[3:]
                        if clean_json.endswith("```"):
                            clean_json = clean_json[:-3]
                        clean_json = clean_json.strip()

                        # فیلتر جادویی Regex برای حل مشکل HTML در JSON
                        clean_json = re.sub(r'([a-zA-Z0-9-]+)="([^"]*)"', r"\1='\2'", clean_json)

                        faq_data = json.loads(clean_json)
                        page_content.faq_json = faq_data

                    except json.JSONDecodeError as e:
                        print(f"[-] Critical JSON Parse Error in FAQ: {e}")
                        page_content.faq_json = []

            # ساخت اسکیمای سئو (JSON-LD)
            generated_schemas = generate_advanced_schema(brief, page_content)
            page_content.schema_json = generated_schemas
            
            # ذخیره تمامی آپدیت‌ها در دیتابیس
            page_content.generation_status = PageContent.GenerationStatus.COMPLETED
            page_content.generated_at = timezone.now()
            page_content.generated_by = "Gemini Self-Correction Pipeline"
            page_content.save()
            
            final_status = "تکمیل شد" if seo_approved else f"تکمیل شد (سقف اصلاح - نمره {page_content.seo_score})"
            results.append((brief.keyword.text, final_status))
            
    return results
