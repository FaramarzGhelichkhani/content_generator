# generation/agents/seo_reviewer.py
import json 
from typing import List
from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate
from content.models import PageContent
from generation.utils.llm_manager import get_llm


# ==========================================
# 1. Pydantic Models
# ==========================================
class BlockFeedback(BaseModel):
    block_id: int = Field(description="شناسه یا همان block_id بلوکی که ایراد دارد")
    feedback: str = Field(description="دلیل دقیق رد شدن بلوک و راهنمایی کاملاً شفاف فنی به ایجنت نویسنده برای اصلاح آن")

class SEOAuditResult(BaseModel):
    score: int = Field(description="نمره کل سئوی معنایی و ساختاری صفحه از 0 تا 100")
    is_approved: bool = Field(description="آیا سئوی صفحه مورد تایید است؟")
    failed_blocks: List[BlockFeedback] = Field(description="لیست بلوک‌هایی که استانداردهای سئو را پاس نکرده‌اند")
    missing_entities: List[str] = Field(description="موجودیت‌های کلیدی LSI که در متن غایب هستند")
    summary_report: str = Field(description="گزارش نهایی و تحلیل کلی از وضعیت سئوی معنایی صفحه")


# ==========================================
# 2. Prompt Template (ارتقایافته با درک بازار ایران و باکس‌های گرافیکی)
# ==========================================
SEO_REVIEWER_PROMPT = """شما یک ممیز ارشد و سرسخت سئوی تکنیکال و معنایی (Semantic SEO) در حوزه قفل و کلیدسازی خودرو هستید.
وظیفه شما آنالیز دقیق ساختار لندینگ پیج تولید شده و انطباق آن با اصول گراف موضوعی (Topic Graph) است.

مشخصات استراتژیک صفحه:
- کلمه کلیدی اصلی (Focus Keyword): {focus_keyword}
- کلمات کلیدی همگرا و LSI: {extra_keywords}
- موجودیت هدف و اطلاعات فنی (Context & Specs): {rich_entity_context}
- نوع صفحه و سطح سیلو: {page_type} 

محتوای ساختاریافته بلوک‌محور صفحه برای ممیزی:
---
{compiled_content_with_ids}
---

چک‌لیست ممیزی سخت‌گیرانه:
1. آنالیز توزیع فوکوس کیورد: کلمه کلیدی اصلی حتماً باید در ۳۰٪ ابتدایی بلوک هیرو/مقدمه به صورت طبیعی درج شده باشد.
2. ممیزی چگالی معنایی (TF-IDF): کلمات کلیدی کمکی و ال‌اس‌آی (LSI) باید در بدنه متون پخش شده باشند. 
3. تبصره اطلاعات فنی (Technical Specs): اطلاعات دقیق فنی مانند فرکانس، نوع باتری و چیپ ایموبیلایزر که در بخش (Context & Specs) به تو داده شده، در یک باکس گرافیکی مجزا در سایت رندر می‌شوند. بنابراین اگر این کلمات مستقیماً در متن پاراگراف‌ها تکرار نشده بودند، نباید نمره منفی بدهی.
4. تبصره جداول قیمت (Pricing Policy): به دلیل نوسانات بازار ایران، استفاده از عباراتی نظیر "استعلام تلفنی"، "تماس بگیرید" یا "بر اساس مدل" در جداول قیمت کاملاً استاندارد و مورد تایید است. به هیچ وجه برای نبود عدد دقیق قیمت نمره منفی نده.
5. عدم تکرار در تایتل‌ها: تایتل‌ها نباید درون کانتنت تکرار شوند.

اگر بلوکی معیارهای بالا را نقض کرده، شناسه دقیق آن (block_id) را در فیلد failed_blocks قرار داده و یک راهنمای صریح برای نویسنده بنویسید.
خروجی شما باید منحصراً یک ساختار JSON معتبر باشد.
"""

# ==========================================
# 3. Agent Execution Logic
# ==========================================
def review_page_seo(page_content: PageContent):
    brief = page_content.page_brief
    blocks = page_content.blocks_json

    if not blocks:
        return False

    keyword_text = brief.keyword.text
    extra_kws = brief.keyword.extra_keywords_text
    page_type = brief.page_type

    # ----------------------------------------------------
    # غنی‌سازی کانتکست با اطلاعات موجودیت و استخراج هوشمند Specs
    # ----------------------------------------------------
    rich_entity_context = ""
    if brief.entity:
        entity = brief.entity
        rich_entity_context = f"نوع موجودیت: {entity.kind} | نام موجودیت: {entity.name}"
        if entity.kind == "model" and entity.parent:
            rich_entity_context += f" | برند اصلی: {entity.parent.name}"
    else:
        rich_entity_context = "موضوع عمومی"

    # پیدا کردن بلوک Specs و اضافه کردن محتوای آن به صورت متن ساده (نه JSON) به کانتکست
    extracted_specs_text = ""
    for b in blocks:
        if b.get("block_type") in ["specs", "specs_block"]:
            raw_specs = b.get("meta_specs", {})
            if isinstance(raw_specs, str):
                try:
                    raw_specs = json.loads(raw_specs)
                except:
                    raw_specs = {}
            if raw_specs:
                extracted_specs_text = " | ".join([f"{k}: {v}" for k, v in raw_specs.items()])
            break

    if extracted_specs_text:
        rich_entity_context += f"\n[اطلاعات فنی موجود در گرافیک صفحه (از این موارد آگاه باش اما عدم حضورشان در متن را جریمه نکن): {extracted_specs_text}]"

    # ----------------------------------------------------
    # فیلتر و آماده‌سازی محتوای متنی برای ممیزی
    # ----------------------------------------------------
    formatted_content = ""
    for b in blocks:
        b_type = b.get('block_type', 'N/A')
        
        # حذف بلوک‌های تصویری و فنی از ورودی برای جلوگیری از خطای پارس مدل
        if b_type in ['image', 'specs', 'specs_block', 'faq']:
            continue
            
        block_id = b.get('block_id', 'N/A')
        title = b.get('title', '')
        content_body = b.get('content', '').strip()
        
        if content_body:
            formatted_content += f"=== BLOCK_ID: {block_id} | TYPE: {b_type} | TITLE: {title} ===\n{content_body}\n\n"

    if not formatted_content.strip():
        page_content.seo_score = 100
        page_content.generation_status = PageContent.GenerationStatus.COMPLETED
        page_content.save()
        return True

    # ----------------------------------------------------
    # فراخوانی مدل ارزیاب سئو
    # ----------------------------------------------------
    try:
        llm = get_llm(temperature=0.1)
        structured_llm = llm.with_structured_output(SEOAuditResult)
        prompt = ChatPromptTemplate.from_template(SEO_REVIEWER_PROMPT)
        reviewer_chain = prompt | structured_llm

        result: SEOAuditResult = reviewer_chain.invoke({
            "focus_keyword": page_content.focus_keyword,
            "extra_keywords": extra_kws,
            "rich_entity_context": rich_entity_context, 
            "page_type": page_type,
            "compiled_content_with_ids": formatted_content
        })

        # ذخیره کامل گزارش برای مانیتورینگ
        page_content.seo_report = {
            "score": result.score,
            "is_approved": result.is_approved,
            "failed_blocks": [fb.model_dump() for fb in result.failed_blocks],
            "missing_entities": result.missing_entities,
            "summary": result.summary_report
        }
        
        page_content.seo_score = result.score

        if result.is_approved:
            page_content.generation_status = PageContent.GenerationStatus.COMPLETED
            page_content.generation_error = "تایید شد: سئو پاس شد."
        else:
            page_content.iterations += 1
            page_content.generation_status = PageContent.GenerationStatus.WRITING
            page_content.generation_error = f"رد شده در لوپ {page_content.iterations} - نمره: {result.score} - در حال بازنویسی..."

        page_content.save()
        return result.is_approved
        
    except Exception as e:
        print(f"[-] SEO Reviewer Error: {e}")
        return False
    