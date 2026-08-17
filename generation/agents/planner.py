# generation/agents/planner.py
import json
from typing import List, Optional
from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate
from content.models import PageContent
from generation.utils.llm_manager import get_llm


# ==========================================
# 1. Pydantic Models 
# ==========================================
class BlockPlan(BaseModel):
    block_type: str = Field(
        description="یکی از این مقادیر: hero, introduction, main_section, image, comparison, step_by_step, table, faq, cta, related_content, conclusion, specs"
    )
    title: Optional[str] = Field(description="تیتر بلوک (برای hero خالی بگذارید، برای بقیه H2 یا H3)")
    purpose: str = Field(description="هدف روانشناختی، سئویی یا کاربردی این بلوک چیست؟")
    target_keywords: List[str] = Field(description="حداکثر ۳ کلمه کلیدی LSI که باید در این بلوک استفاده شوند")
    block_word_count: int = Field(description="بودجه تعداد کلمات این بلوک (مثلاً 200 یا 300 کلمه)")

class PageOutline(BaseModel):
    seo_title: str = Field(description="تایتل سئو صفحه (حداکثر 60 کاراکتر)")
    meta_description: str = Field(description="متا دیسکریپشن (حداکثر 150 کاراکتر)")
    h1_title: str = Field(description="تیتر اصلی H1")
    focus_keyword: str = Field(description="کلمه کلیدی که براساس کلمه کلید اصلی و موجودیت هدف باید بسازی بعدا جهت بررسی سئواستفاده خواهد شد.")
    blocks: List[BlockPlan] = Field(description="لیست بلوک‌هایی که ساختار صفحه را شکل می‌دهند")


# ==========================================
# 2. Prompt Templates (معماری سئو و ضد هم‌خواری)
# ==========================================

STANDARD_PLANNER_PROMPT = """شما یک استراتژیست ارشد سئو و معمار محتوای سایت‌های خدماتی ریموت خودرو هستید.
وظیفه شما طراحی ساختار بلوک‌محور (Block-Based Outline) برای یک صفحه وب است.

مشخصات صفحه:
- کلمه کلیدی اصلی: {keyword}
- نوع صفحه: {page_type}
- اطلاعات موجودیت هدف (Entity): {rich_entity_context}
- نیت کاربر: {intent_name} - {intent_desc}
- کلمات کلیدی هم‌خانواده و LSI: {extra_keywords}

استراتژی محتوایی:
این صفحه یک هاب جامع (Resource Center) یا صفحه مستقل است. باید بلوک‌های کلی داشته باشد که تمام جنبه‌های سرویس را پوشش دهد. از بلوک‌های 'introduction', 'main_section', 'comparison', 'related_content' (برای هدایت به کلاسترها) استفاده کنید.

قوانین ثابت چیدمان:
1. اولین بلوک باید 'hero' باشد.
2. آخرین بلوک‌ها باید 'faq' و سپس 'conclusion' باشند.
3. کلمات کلیدی LSI را به صورت توزیع‌شده در فیلد 'target_keywords' بلوک‌ها پخش کنید تا چگالی سئو رعایت شود.
4. تعداد کلمات درخواستی کل این مقاله {total_word_count} کلمه است. این بودجه را منطقی و متناسب با اهمیت هر بلوک، در فیلد block_word_count بین بلوک‌ها تقسیم کنید.
5. در صورت وجود اطلاعات موجودیت، "seo_title" و "h1_title" به هیچ عنوان نباید عمومی باشند. نام دقیق موجودیت هدف را درون آن‌ها بگنجانید.
6. قانون درج تصویر صنعتی: یک بلوک با block_type برابر با "image" طراحی کنید و فقط یک جمله توصیفی کوتاه برای ویژگی Alt در فیلد title/purpose بنویسید.

قانون بلوک مشخصات فنی (Specs):
اگر نیت کاربر (Intent) شامل 'Commercial & Buying' یا 'Emergency & Local' بود، دقیقاً یک بلوک "specs" با عنوان "مشخصات فنی و ساختاری ریموت" بسازید. در غیر این صورت به هیچ وجه بلوک "specs" نسازید.

ساختار را فقط به فرمت JSON تولید کن.
"""

CLUSTER_PLANNER_PROMPT = """شما یک استراتژیست ارشد سئو و معمار محتوای سایت‌های خدماتی ریموت خودرو هستید.
وظیفه شما طراحی ساختار بلوک‌محور برای یک صفحه کلاستر (Cluster) به شدت تخصصی (Deep Dive) است.

مشخصات صفحه کلاستر فعلی:
- کلمه کلیدی اصلی: {keyword}
- اطلاعات موجودیت هدف (Entity): {rich_entity_context}
- نیت کاربر: {intent_name} - {intent_desc}
- کلمات کلیدی هم‌خانواده و LSI (جهت تمایز معنایی): {extra_keywords}

⚠️ هشدار حیاتی سئو: جلوگیری از Keyword Cannibalization ⚠️
این صفحه یک کلاستر است که زیرمجموعه صفحه والد (Pillar) زیر می‌باشد:
- کلمه کلیدی صفحه والد: {parent_keyword}
- فوکوس کیورد صفحه والد: {parent_focus_keyword}
- ساختار تیترهای استفاده شده در صفحه والد (Outline):
{parent_outline}

ماموریت و خطوط قرمز شما:
۱. به هیچ عنوان موضوعات، تیترها و مفاهیم کلی که در ساختار والد بالا آمده است را در این صفحه تکرار نکنید. والد برای معرفی و کلیات است، این کلاستر برای حل یک مشکل ریز و تخصصی است (مثلاً فقط تعمیرات، یا فقط تعویض قاب، یا پروگرامینگ مجدد).
۲. حتماً از کلمات کمکی ({extra_keywords}) برای ساختن تیترهای H2 و H3 به شدت نیچ و متمایز استفاده کنید تا گوگل تفاوت معنایی این صفحه با والد را درک کند.
۳. "seo_title" و "h1_title" باید کاملاً یونیک بوده و سیگنال تخصصی بودن (مثل تعمیر، حل مشکل، آموزش) را به کاربر بدهند.
۴. در کلاسترها از بلوک‌های عملیاتی مثل 'step_by_step' (آموزش مراحل)، 'table' (لیست ارورها یا هزینه‌ها) و 'cta' (دعوت به اقدام فوری) بیشتر استفاده کنید.

قوانین ثابت چیدمان:
1. اولین بلوک باید 'hero' باشد.
2. آخرین بلوک‌ها باید 'faq' (فقط سوالات مربوط به همین کلاستر، نه والد) و سپس 'conclusion' باشند.
3. بودجه کلمات کل این مقاله {total_word_count} کلمه است که باید در block_word_count تقسیم شود.
4. قانون تصویر صنعتی: یک بلوک از نوع "image" با Alt مرتبط به مشکل تخصصی ایجاد کنید.
5. قانون مشخصات فنی: اگر نیت کاربر پتانسیل خرید یا امداد دارد ('Commercial & Buying' یا 'Emergency & Local') یک بلوک "specs" قرار دهید، در غیر این صورت اکیداً ممنوع است.

ساختار را فقط به فرمت JSON تولید کن.
"""


# ==========================================
# 3. Agent Execution Logic
# ==========================================
def generate_page_plan(page_content: PageContent, parent_context: dict = None) -> bool:
    brief = page_content.page_brief
    
    # اگر آوت‌لاین از قبل موجود بود (مثلاً در یک ران نیمه‌کاره قبلی)، برای حفظ دیتا اسکیپ می‌کنیم
    if page_content.outline_json:
        print(f"[+] Outline already exists for {brief.keyword.text}. Resuming planning state...")
        return True
        
    keyword_text = brief.keyword.text
    # استفاده از لیست کلمات کلیدی اکسترا و تبدیل به رشته برای پرامپت
    extra_keywords_list = brief.keyword.extra_keywords_list
    extra_keywords = "، ".join(extra_keywords_list) if extra_keywords_list else "موردی ثبت نشده است"
    
    page_type = brief.page_type
    intent_name = brief.keyword.intent.name if brief.keyword.intent else "نامشخص"
    intent_desc = brief.keyword.intent.description if brief.keyword.intent else ""

    # روشن کردن تایپ و جزئیات دقیق موجودیت (برند/مدل/شهر)
    if brief.entity:
        entity = brief.entity
        rich_entity_context = f"نوع موجودیت: {entity.kind} | نام موجودیت: {entity.name}"
        if entity.kind == "model" and hasattr(entity, 'parent') and entity.parent:
            rich_entity_context += f" | برند مادر این خودرو: {entity.parent.name}"
    else:
        rich_entity_context = "عمومی (بدون موجودیت خودرویی یا مکانی خاص)"

    try:
        llm = get_llm(temperature=0.2)
        structured_llm = llm.with_structured_output(PageOutline)
        
        # انتخاب هوشمندانه پرامپت بر اساس نوع صفحه و وجود اطلاعات والد
        if page_type.lower() == "cluster" and parent_context:
            print(f"[*] Planning CLUSTER page with Anti-Cannibalization logic for: {keyword_text}")
            
            # تبدیل آوت‌لاین والد به فرمت خوانا برای LLM
            parent_outline_str = "اطلاعات ساختار والد موجود نیست."
            if parent_context.get("parent_outline"):
                # استخراج فقط تیترها و انواع بلوک برای خلوت شدن پرامپت
                simplified_outline = [
                    f"- {b.get('block_type', 'block')}: {b.get('title', 'بدون تیتر')} (هدف: {b.get('purpose', '')})" 
                    for b in parent_context["parent_outline"]
                ]
                parent_outline_str = "\n".join(simplified_outline)
            
            prompt = ChatPromptTemplate.from_template(CLUSTER_PLANNER_PROMPT)
            invoke_args = {
                "keyword": keyword_text,
                "rich_entity_context": rich_entity_context,
                "intent_name": intent_name,
                "intent_desc": intent_desc,
                "extra_keywords": extra_keywords,
                "total_word_count": brief.target_word_count,
                "parent_keyword": parent_context.get("parent_keyword", "نامشخص"),
                "parent_focus_keyword": parent_context.get("parent_focus_keyword", "نامشخص"),
                "parent_outline": parent_outline_str
            }
        else:
            print(f"[*] Planning STANDARD/PILLAR page for: {keyword_text}")
            prompt = ChatPromptTemplate.from_template(STANDARD_PLANNER_PROMPT)
            invoke_args = {
                "keyword": keyword_text,
                "page_type": page_type,
                "rich_entity_context": rich_entity_context,
                "intent_name": intent_name,
                "intent_desc": intent_desc,
                "extra_keywords": extra_keywords,
                "total_word_count": brief.target_word_count
            }

        planner_chain = prompt | structured_llm

        page_content.generation_status = PageContent.GenerationStatus.PLANNING
        page_content.save()

        result: PageOutline = planner_chain.invoke(invoke_args)

        page_content.seo_title = result.seo_title
        page_content.meta_description = result.meta_description
        page_content.h1 = result.h1_title
        page_content.focus_keyword = result.focus_keyword
        page_content.outline_json = [block.model_dump() for block in result.blocks]
        page_content.save()
        return True
        
    except Exception as e:
        print(f"[-] Planner Error: {e}")
        page_content.generation_status = PageContent.GenerationStatus.FAILED
        page_content.generation_error = str(e)
        page_content.save()
        return False
    