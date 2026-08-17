# generation/agents/link_injector.py
import re
from typing import List
from pydantic import BaseModel, Field

from langchain_core.prompts import ChatPromptTemplate
from content.models import InternalLink, PageContent
from generation.utils.llm_manager import get_llm

# دیتابیس بومی کلمات کلیدی تخصصی برای لینک‌های خارجی سئو
EXTERNAL_LINKS_MAP = {
    "ایموبلایزر": "https://fa.wikipedia.org/wiki/%D8%A7%DB%8C%D9%85%D9%88%D8%A8%D9%84%D8%A7%DB%8C%D8%B2%D8%B1",
    "Immobilizer": "https://fa.wikipedia.org/wiki/%D8%A7%DB%8C%D9%85%D9%88%D8%A8%D9%84%D8%A7%DB%8C%D8%B2%D8%B1",
    "دیاگ": "https://fa.wikipedia.org/wiki/%D8%AF%DB%8C%D8%A7%DA%AF",
    "برد الکترونیکی" : "https://fa.wikipedia.org/wiki/%D8%A8%D8%B1%D8%AF_%D9%85%D8%AF%D8%A7%D8%B1_%DA%86%D8%A7%D9%BE%DB%8C#:~:text=%D8%A8%D9%8F%D8%B1%D8%AF%20%D9%85%D8%AF%D8%A7%D8%B1%20%DA%86%D8%A7%D9%BE%DB%8C%20%DB%8C%D8%A7%20%D8%A8%D8%B1%D8%AF,%D8%AE%D8%A7%D8%B2%D9%86%D8%8C%20%D8%B3%D9%84%D9%81%D8%8C%20%D8%A2%DB%8C%20%D8%B3%DB%8C%20%D9%88",
}

# ==========================================
# ۱. Pydantic Model
# ==========================================
class SmartLinkInjection(BaseModel):
    updated_content: str = Field(
        description="متن کامل و بدون تغییر HTML بلوک، که لینک‌های تایید شده با حفظ ساختار و تگ‌های اصلی قبلی، درون آن تزریق شده‌اند. شما حق حذف هیچ اطلاعات یا تگی را ندارید."
    )
    injected_urls: List[str] = Field(
        description="لیست دقیق تمام URLهایی (چه داخلی و چه خارجی) که موفق شدید به طور طبیعی در متن این بلوک جایگذاری کنید."
    )


# ==========================================
# ۲. پرامپت حفاظت‌شده ویراستار سئو
# ==========================================
LINK_INJECTOR_PROMPT = """شما یک ویراستار و ممیز ارشد تکنیکال سئو هستید. وظیفه شما تزریق طبیعی لینک‌های داخلی درون متن یک بلوک HTML است.

قوانین بسیار سخت‌گیرانه برای امنیت محتوا (قفل کانتکست):
1. شما تحت هیچ شرایطی حق حذف، خلاصه‌سازی یا بازنویسی کلی متن را ندارید. تمام پاراگراف‌ها، لیست‌ها و اطلاعات باید دقیقاً حفظ شوند.
2. وظیفه شما فقط و فقط جایگذاری کدهای HTML لینک به صورت `<a href="URL">Anchor</a>` در محل‌های مناسب است.
3. در صورت نیاز، مجاز هستید صرفاً ۳ الی ۴ کلمه اطراف محل لینک را تغییر دهید تا جمله‌بندی برای پذیرش انکرتکست طبیعی شود.
4. هشدار: هرگز کلمه کلیدی اصلی که درون تگ <strong> قرار دارد را با لینک قطع نکنید.
5. بسیار مهم: شما موظف هستید دقیقاً از Anchor Text های ارائه شده در لیست زیر استفاده کنید، حتی اگر به نظرتان کمی طولانی یا غیرمعمول بیایند.

متن فعلی بلوک که باید ویرایش شود:
---
{block_content}
---

لیست تمام لینک‌های مجاز و در دسترس (فقط داخلی):
---
{links_data}
---

فقط و فقط خروجی را به فرمت دقیق JSON درخواستی برگردانید.
"""


# ==========================================
# ۳. توابع منطقی و کمکی سیستم
# ==========================================

def get_varied_anchor(cluster_url_path, pillar_kw_text, entity_name):
    """
    تولید انکرتکست‌های متنوع (LSI و طولانی) برای جلوگیری از Over-Optimization در سئو
    """
    exact_match = f"{pillar_kw_text} {entity_name}".strip()

    formats = [
        "{exact}",
        "{exact}",
        "مرکز تخصصی {exact}",
        "خدمات حرفه‌ای {exact}",
        "اطلاعات کامل درباره {exact}",
        "تعمیرات و خدمات {exact}",
        "نمایندگی خدمات {exact}",
        "سوئیچ و {exact}",
        "سیستم قفل و {exact}",
        "برای خدمات {entity} کلیک کنید",
        "بیشتر بخوانید: صفحه اختصاصی {entity}",
    ]

    # با هش کردن URL، برای هر صفحه خاص همیشه یک انکرتکست ثابت تولید می‌شود
    idx = abs(hash(cluster_url_path)) % len(formats)
    return formats[idx].format(exact=exact_match, entity=entity_name)


def create_dedicated_link_block(leftover_internal: list, next_block_id: int) -> dict:
    html_lines = ['<p><strong>خدمات و صفحات مرتبط:</strong></p>\n<ul class="seo-internal-links">']
    for lk in leftover_internal:
        html_lines.append(f'  <li><a href="{lk["url"]}">{lk["anchor"]}</a></li>')
    html_lines.append('</ul>')
    
    joined_lines = "\n".join(html_lines)
    
    html_content = f'<div class="allocated-related-contents-block">\n{joined_lines}\n</div>'
    
    return {
        "block_id": next_block_id,
        "block_type": "internal_link",
        "title": "مقالات و خدمات مرتبط",
        "purpose": "هدایت کاربر به کلاسترهای مرتبط",
        "target_keywords": [],
        "content": html_content.strip(),
        "metadata": {"auto_generated": True}
    }


def inject_links_and_references(page_content: PageContent, base_domain: str):
    blocks = page_content.blocks_json
    brief = page_content.page_brief
    
    if not blocks:
        return False

    # ==========================================
    # فاز اول: تزریق لینک‌های داخلی برنامه‌ریزی شده با هوش مصنوعی
    # ==========================================
    planned_links = InternalLink.objects.filter(
        source_page=brief,
    ).select_related('target_page', 'target_page__entity', 'target_page__keyword')

    target_links_pool = []
    
    # لاجیک جدید: اگر انکرتکست‌ها قبلاً یکسان تولید شده‌اند، در اینجا تنوع ایجاد می‌کنیم
    for link in planned_links:
        target_url = link.target_page.url_path
        
        # استخراج نام موجودیت و کلمه کلیدی پیلار از صفحه هدف
        entity_name = link.target_page.entity.name if link.target_page.entity else ""
        target_kw_text = link.target_page.keyword.text if link.target_page.keyword else ""
        
        # اگر اطلاعات برای ساخت انکر متنوع کافی بود، تابع را صدا می‌زنیم
        if entity_name and target_kw_text:
             varied_anchor = get_varied_anchor(target_url, target_kw_text, entity_name)
        else:
             varied_anchor = link.anchor_text # فال‌بک به انکر اورجینال
             
        # آپدیت انکرتکست در دیتابیس برای هماهنگی گزارشات سئو
        if link.anchor_text != varied_anchor:
             link.anchor_text = varied_anchor
             link.save(update_fields=['anchor_text'])

        target_links_pool.append({
            "id": link.id,
            "anchor": varied_anchor,
            "url": f"{base_domain.rstrip('/')}{target_url}"
        })

    if target_links_pool:
        main_text_blocks = [b for b in blocks if b.get("block_type") in ["main_section", "introduction"]]
        target_block = max(main_text_blocks, key=lambda b: len(b.get("content", ""))) if main_text_blocks else max(blocks, key=lambda b: len(b.get("content", "")))
        target_block_index = blocks.index(target_block)

        try:
            llm = get_llm(temperature=0.2)
            structured_llm = llm.with_structured_output(SmartLinkInjection)
            prompt = ChatPromptTemplate.from_template(LINK_INJECTOR_PROMPT)
            chain = prompt | structured_llm

            links_data_str = "\n".join([f"ID: {l['id']} | Anchor: {l['anchor']} | URL: {l['url']}" for l in target_links_pool])
            result: SmartLinkInjection = chain.invoke({
                "block_content": target_block.get("content", ""),
                "links_data": links_data_str
            })

            blocks[target_block_index]["content"] = result.updated_content
            successfully_injected_urls = result.injected_urls

            leftover_internal = [l for l in target_links_pool if l["url"] not in successfully_injected_urls]
            
            if leftover_internal:
                next_block_id = max([int(b.get("block_id")) if isinstance(b.get("block_id"), (int, str)) and str(b.get("block_id")).isdigit() else 0 for b in blocks], default=0) + 1
                allocated_block = create_dedicated_link_block(leftover_internal, next_block_id)
                blocks.append(allocated_block)

            applied_internal_ids = [l["id"] for l in target_links_pool]
            InternalLink.objects.filter(id__in=applied_internal_ids).update(status=InternalLink.Status.APPLIED)

        except Exception as e:
            print(f"[-] AI Internal Link Injector error: {e}")
            next_block_id = max([int(b.get("block_id")) if isinstance(b.get("block_id"), (int, str)) and str(b.get("block_id")).isdigit() else 0 for b in blocks], default=0) + 1
            fallback_block = create_dedicated_link_block(target_links_pool, next_block_id)
            blocks.append(fallback_block)
            InternalLink.objects.filter(id__in=[l["id"] for l in target_links_pool]).update(status=InternalLink.Status.APPLIED)


    # ==========================================
    # فاز دوم: تزریق لینک‌های خارجی (ویکی‌پدیا) با پایتون خالص و ایمن
    # ==========================================
    for ext_kw, ext_url in EXTERNAL_LINKS_MAP.items():
        
        flexible_kw_pattern = ext_kw.replace("‌", r"[\s\u200c]?").replace(" ", r"[\s\u200c]?")
        
        # الگو محافظتی
        pattern = re.compile(
            r'(<a\b[^>]*>.*?</a>)' + 
            r'|(<h[1-6]\b[^>]*>.*?</h[1-6]>|<strong\b[^>]*>.*?</strong>)' + 
            r'|(' + flexible_kw_pattern + r')', 
            re.IGNORECASE
        )
        
        keyword_injected = False 
        
        for block in blocks:
            content = block.get("content", "")
            if not content:
                continue
            
            if block.get("block_type") == "faq":
                continue

            def replace_func(match):
                nonlocal keyword_injected
                
                # اگر تگ a از قبل موجود بود، بهش دست نزن
                if match.group(1):
                    return match.group(1)
                
                # اگر کلمه داخل تگ H یا Strong بود (یعنی مهم است)، بهش دست نزن
                if match.group(2):
                    return match.group(2)
                
                # اگر کلمه آزاد بود و هنوز در صفحه لینک نشده بود، لینکش کن
                elif match.group(3) and not keyword_injected:
                    keyword_injected = True
                    return f'<a href="{ext_url}" target="_blank" rel="nofollow noopener noreferrer">{match.group(3)}</a>'
                
                # در غیر این صورت، خودش رو برگردون
                else:
                    return match.group(3) if match.group(3) else match.group(0)

            # اعمال تابع جایگزینی روی متن بلوک
            new_content = pattern.sub(replace_func, content)
            
            # اگر لینک با موفقیت تزریق شد، آپدیت کن و برو سراغ کلمه خارجی بعدی
            if keyword_injected:
                block["content"] = new_content
                break


    # ==========================================
    # فاز نهایی: کامپایل خروجی و ذخیره
    # ==========================================
    page_content.blocks_json = blocks
    
    full_html = ""
    for b in blocks: 
        
        content = (b.get("content") or "").strip()
        title = (b.get("title") or "").strip()
        
        # جلوگیری از تولید H2 تکراری
        if title and b.get("block_type") != "hero":
            if f"<h2>{title}" not in content and f"<h2> {title}" not in content and f"<h2" not in content[:15]:
                full_html += f"<h2>{title}</h2>\n"
         
        if b.get("block_type") == "specs":  # تغییر "spec" به "specs" برای همخوانی با کدهای قبلی
            # استخراج محتوای specs از meta_specs
            meta_specs = b.get("meta_specs", {})
            if isinstance(meta_specs, dict) and meta_specs:
                full_html += "<table class='specs-table'><tbody>"
                for key, val in meta_specs.items():
                    full_html += f"<tr><td><strong>{key}</strong></td><td>{val}</td></tr>"
                full_html += "</tbody></table>\n"
                
        full_html += f"{content}\n\n"
        
    page_content.compiled_body = full_html
    page_content.save()
    
    return True
