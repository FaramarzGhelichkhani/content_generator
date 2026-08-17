# generation/agents/writer.py
import json
from typing import List
from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate
from content.models import PageContent
from generation.utils.llm_manager import get_llm


# ==========================================
# 1. Pydantic Model (خروجی متنی هر بلوک)
# ==========================================
class GeneratedBlock(BaseModel):
    content: str = Field(
        description="محتوای متنی غنی و سئوشده بلوک کاملاً به فرمت HTML (مانند تگ‌های p, ul, ol, strong). از استایل‌های خطی یا کلاس‌های CSS استفاده نکنید. اگر نوع بلوک table است، حتماً تگ table با ساختار درست تولید کنید."
    )
    entity_mentions: List[str] = Field(
        description="لیست تمام موجودیت‌هایی (برند، مدل، قطعه) که در متن این بلوک به آن‌ها اشاره شده است"
    )


# ==========================================
# 2. Prompt Template (پرامپت تخصصی نویسنده سیلور)
# ==========================================
WRITER_PROMPT = """شما یک نویسنده فنی و متخصص ارشد تولید محتوای سئو در حوزه خودرو و کلیدسازی/ریموت هستید.
وظیفه شما نگارش محتوا برای یک بلوک مشخص از صفحه وب است.

مشخصات کل پیج:
- کلمه کلیدی اصلی سایت: {keyword}
- اطلاعات موجودیت هدف (Entity Context): {rich_entity_context}
- نوع صفحه: {page_type}

مشخصات بلوکی که اکنون باید بنویسید:
- نوع بلوک: {block_type}
- تیتر بلوک (در صورت وجود): {block_title}
- هدف این بلوک: {block_purpose}
- کلمات کلیدی اجباری برای این بلوک: {target_keywords}
- تعداد کلمات درخواستی: حدود {word_count_limit} کلمه
{specific_feedback}

سوابق محتوای تولید شده در بلوک‌های قبلی همین صفحه (حافظه لغزان):
---
{previous_context}
---

قوانین سخت‌گیرانه نگارش:
1. لحن محتوا باید کاملاً تخصصی، قابل اعتماد و متناسب با Search Intent باشد.
2. به هیچ وجه محتوای تکراری نسبت به بلوک‌های قبلی (که در بخش سوابق آمده) ننویسید. اطلاعات جدید اضافه کنید.
3. درج دقیق کلمه کلیدی: کلمه کلیدی اصلی ({keyword}) باید دقیقاً و عیناً (بدون شکستن کلمات یا تغییر ساختار) در ۱۰۰ کلمه اول متن شما (به‌خصوص اگر نوع بلوک 'hero' است) استفاده شود.
4. کلمات کلیدی اجباری این بلوک را به صورت کاملاً طبیعی در متن HTML جاگذاری کنید.
5. لینک‌دهی خارجی (External Links): اگر نیاز به لینک دادن کلمات تخصصی به منابع خارجی داشتید، حداکثر از ۱ یا ۲ لینک معتبر و مرتبط فارسی استفاده کنید. لینک دادن به صفحات انگلیسی (مانند en.wikipedia.org) اکیداً ممنوع است.
6. خروجی متن باید کاملاً معتبر به صورت HTML (فقط تگ‌های ساختاری مثل p, ul, table و...) باشد و نیازی به تگ‌های markdown (مثل ```html) ندارد.
7. قانون بسیار حیاتی بلاک FAQ: اگر نوع بلاک جاری (block_type) برابر با "faq" بود، شما نباید متن HTML معمولی بنویسید. بلکه باید محتوای فیلد content را دقیقاً به صورت یک آرایه JSON ساختاریافته (رشته شده) مانند نمونه زیر برگردانید تا سیستم بتواند آن را پارس کند:
دقت کن که اگر داخل متن جواب‌ها از علامت نقل‌قول (") استفاده می‌کنی، حتماً با بک‌اسلش (\\") آن را اسکیپ کن تا فرمت JSON خراب نشود.
[
  {{"question": "سوال اول در مورد موجودیت؟", "answer": "پاسخ کوتاه و تخصصی سوال اول."}},
  {{"question": "سوال دوم؟", "answer": "پاسخ تخصصی دوم."}}
]
8. قانون فوق‌حیاتی بلوک تصویر (image): 
اگر نوع بلوک جاری (block_type) برابر با "image" بود، تو حق نداری هیچ‌گونه متن، پاراگراف، تگ HTML یا توضیحات اضافه‌ای تولید کنی! 
وظیفه تو در این بلوک فقط و فقط تولید یک رشته متنی کوتاه (بین ۵ تا ۱۰ کلمه) به عنوان متن جایگزین (Alt Text) برای سئوی عکس است. 
مثال خروجی صحیح برای فیلد content وقتی بلوک از نوع image است: "ریموت فابریک و اورجینال بنز C200"

9. از کلمه "ارزان" به هیچ وجه استفاده نکن.
9.5 قیمت ابدا نده.
10. قانون فوق‌حیاتی بلوک مشخصات فنی (specs):
اگر block_type برابر با "specs" بود، تو حق نداری هیچ پاراگراف متنی، تگ HTML یا توضیحات اضافه‌ای بنویسی! 
وظیفه تو استخراج اطلاعات فنی ریموت (فرکانس، نوع چیپ ایموبیلایزر، نوع باتری، وجود تیغه اضطراری) بر اساس کانتکست موجودیت است.
خروجی تو باید منحصراً یک ساختار JSON معتبر (بدون بک‌تیک و مارک‌داون) باشد.
برای بدست آوردن این اطلاعات سرچ کن اگه نیاز بود.
مثال خروجی صحیح:
{{"فرکانس کاری": "۴۳۳ مگاهرتز", "نوع چیپ": "ID46 ضدسرقت", "باتری": "CR2032"}}

فقط و فقط ساختار JSON درخواستی را برگردانید.
"""


# ==========================================
# 3. Agent Execution Logic (منطق حافظه لغزان و لوپ)
# ==========================================
def generate_all_blocks(page_content: PageContent) -> bool:
    brief = page_content.page_brief
    outline = page_content.outline_json  # لیست بلوک‌های برنامه‌ریزی شده توسط پلنر
    
    if not outline:
        print("[-] No outline found to write content.")
        return False

    # اگر فیلد blocks_json خالی بود، آن را با لیست اوت‌لاین مقداردهی اولیه می‌کنیم
    if not page_content.blocks_json:
        page_content.blocks_json = [
            {
                "block_id": b.get("block_id"),
                "block_type": b.get("block_type"),
                "title": b.get("title"),
                "purpose": b.get("purpose"),
                "target_keywords": b.get("target_keywords"),
                "block_word_count": b.get("block_word_count", 200),
                "content": "" # ابتدا کانتنت خالی است
            }
            for b in outline
        ]
        page_content.save()

    # --------------------------------------------------------
    # استخراج هوشمند فیدبک‌های منفی سئو از دورهای قبلی (پارس کردن خطای سئو)
    # --------------------------------------------------------
    failed_blocks_feedback = {}
    if page_content.generation_error:
        try:
            # پارس کردن دیکشنری خطایی که seo_reviewer ذخیره کرده بود
            error_data = json.loads(page_content.generation_error)
            if "failed_blocks" in error_data:
                # تبدیل لیست به دیکشنری {block_id: feedback_text} برای دسترسی سریع در لوپ
                failed_blocks_feedback = {
                    item["block_id"]: item["feedback"] 
                    for item in error_data["failed_blocks"]
                }
        except Exception:
            # اگر فرمت خطا جی‌سان نبود (مثلا خطای شبکه)، نادیده می‌گیریم
            pass

    # فراخوانی مدل پرو برای نگارش عمیق محتوا
    llm = get_llm(temperature=0.5)
    structured_llm = llm.with_structured_output(GeneratedBlock)
    prompt_template = ChatPromptTemplate.from_template(WRITER_PROMPT)
    writer_chain = prompt_template | structured_llm

    # آماده‌سازی کانکست عمومی موجودیت
    if brief.entity:
        entity = brief.entity
        rich_entity_context = f"نوع: {entity.kind} | نام: {entity.name}"
        if entity.kind == "model" and entity.parent:
            rich_entity_context += f" | برند مادر: {entity.parent.name}"
    else:
        rich_entity_context = "عمومی"

    blocks = page_content.blocks_json
    
    # شروع لوپ روی تک‌تک بلوک‌های صفحه با استفاده از enumerate برای داشتن ایندکس موقعیت (idx)
    for idx, block in enumerate(blocks):
        block_id = block.get("block_id")
        block_type = block.get("block_type")
        
        # استخراج کانتنت موجود
        current_content = (block.get("content") or "").strip()
        
        # بررسی فیدبک سئو
        is_failed_in_seo = block_id in failed_blocks_feedback if block_id else False

        # مکانیسم ازسرگیری هوشمند
        if current_content and not is_failed_in_seo:
            print(f"[+] Block {block_id or idx} ({block_type}) already generated and healthy. Resuming safely...")
            continue

        specific_feedback_str = ""
        if is_failed_in_seo:
            print(f"[!] Block {block_id} ({block_type}) failed SEO audit. Forcing Rewrite...")
            specific_feedback_str = f"\n⚠️ خطای ناظر سئو در دور قبل برای این بلوک:\n{failed_blocks_feedback[block_id]}\nلطفاً محتوای جدید را دقیقاً با اصلاح این ایراد بنویسید."
        else:
            print(f"[*] [{idx + 1}/{len(blocks)}] Generating Block: {block_type} -> {block.get('title') or 'بدون تیتر'}")

        # --------------------------------------------------------
        # اصلاح ریشه‌ای با Slicing پایتون: استخراج بلوک‌های قبلی به صورت ۱۰۰٪ ایمن
        # --------------------------------------------------------
        previous_context = ""
        # blocks[:idx] دقیقاً تمام بلوک‌هایی که قبل از این ایندکس نوشته شده‌اند را کات میکند
        for prev_b in blocks[:idx]:
            if prev_b.get("content"):
                previous_context += f"[{prev_b.get('title') or prev_b.get('block_type')}]:\n{prev_b.get('content')}\n\n"

        # --------------------------------------------------------
        # اجرای فراخوانی هوش مصنوعی با مکانیسم Micro-Retry (مقاوم در برابر هذیان و قطعی)
        # --------------------------------------------------------
        max_api_retries = 3
        attempt = 0
        success = False
        
        while attempt < max_api_retries and not success:
            try:
                response = writer_chain.invoke({
                    "keyword": brief.keyword.text,
                    "rich_entity_context": rich_entity_context,
                    "page_type": brief.page_type,
                    "block_type": block_type,
                    "block_title": block.get("title") or "بدون تیتر",
                    "block_purpose": block.get("purpose", ""),
                    "target_keywords": ", ".join(block.get("target_keywords", [])),
                    "word_count_limit": block.get("block_word_count", 200),
                    "specific_feedback": specific_feedback_str,
                    "previous_context": previous_context
                })
                
                # بررسی ایمنی خروجی: آیا مدل دیتای پوچ یا None برگردانده؟
                if not response or not response.content or response.content.strip() == "":
                    raise ValueError("هوش مصنوعی محتوای خالی (None/Empty) برگرداند.")
                
                # اگر موفق بود، ذخیره کن و از حلقه ریترای خارج شو
                if block_type == "specs":
                    try:
                        clean_json = response.content.replace('```json', '').replace(' ```', '').strip()
                        block["meta_specs"] = json.loads(clean_json)
                        block["content"] = ""
                    except Exception as e:
                        print(f"[-] Error parsing specs JSON: {e}")
                        block["meta_specs"] = {"خطا": "داده فنی استخراج نشد"}
                else:
                    block["content"] = response.content
                
                page_content.blocks_json = blocks
                page_content.save()
                success = True

            except Exception as e:
                attempt += 1
                print(f"[-] Writer API Error on block '{block.get('title')}' (Attempt {attempt}/{max_api_retries}): {e}")
                
                if attempt >= max_api_retries:
                    print(f"[-] Critical Error: Max retries reached for this block. Aborting pipeline.")
                    return False # فقط در صورتی متوقف می‌شود که ۳ بار پشت سر هم خطا بدهد
        
    return True
