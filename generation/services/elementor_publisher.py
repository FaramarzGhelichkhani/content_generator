# generation/services/elementor_publisher.py
import random
import re
import json
import uuid
import requests
import mimetypes
import os
import urllib.parse
from datetime import datetime
from content.models import PageContent
from generation.services.schema_generator import generate_advanced_schema

def generate_elementor_id():
    """تولید آیدی ۷ کاراکتری منحصر‌به‌فرد برای المان‌های المنتور"""
    return uuid.uuid4().hex[:7] if 'uuid' in globals() else __import__('uuid').uuid4().hex[:7]

# ==========================================
# توابع ساخت ابزارک‌های بومی المنتور (Widgets)
# ==========================================

def create_heading_widget(text, color="#000000", align="right", size_tag="h2"):
    return {
        "id": generate_elementor_id(),
        "elType": "widget",
        "isInner": False,
        "settings": {
            "title": text,
            "align": align,
            "title_color": color,
            "header_size": size_tag,
            "typography_typography": "custom",
            "typography_font_weight": "bold"
        },
        "widgetType": "heading"
    }

def create_text_widget(content_html, align="right"):
    return {
        "id": generate_elementor_id(),
        "elType": "widget",
        "isInner": False,
        "settings": {
            "editor": f"<div class='dynamic-text-inner' style='text-align: {align}; direction: rtl;'>{content_html}</div>",
        },
        "widgetType": "text-editor"
    }

def create_image_widget(image_url, attachment_id=0, alt_text=""):
    return {
        "id": generate_elementor_id(),
        "elType": "widget",
        "isInner": False,
        "settings": {
            "image": {
                "url": image_url,
                "id": attachment_id
            },
            "alt": alt_text,
            "align": "center",
            "image_border_radius": {"unit": "px", "top": "10", "right": "10", "bottom": "10", "left": "10", "isLinked": True}
        },
        "widgetType": "image"
    }

def create_button_widget(text, url, align="center"):
    return {
        "id": generate_elementor_id(),
        "elType": "widget",
        "isInner": False,
        "settings": {
            "text": text,
            "link": {"url": url, "is_external": "true", "nofollow": "false"},
            "align": align,
            "button_background_color": "#2D4B8C",
            "typography_typography": "custom",
            "typography_font_weight": "bold",
            "border_radius": {"unit": "px", "top": "8", "right": "8", "bottom": "8", "left": "8", "isLinked": True},
            "padding": {"unit": "px", "top": "15", "right": "30", "bottom": "15", "left": "30", "isLinked": False}
        },
        "widgetType": "button"
    }

def wrap_in_elementor_card(elements, bg_color="#ffffff"):
    """قرار دادن ابزارک‌ها داخل کانتینر با استایل کارت سایه‌دار و کلاس واکنش‌گرا"""
    return {
        "id": generate_elementor_id(),
        "elType": "section",
        "isInner": False,
        "settings": {
            "background_background": "classic",
            "background_color": bg_color,
            "_css_classes": "dynamic-seo-card", # کلاس کمکی برای اعمال مدیا کوئری‌های ریسپانسیو
            "padding": {"unit": "px", "top": "40", "right": "30", "bottom": "40", "left": "30", "isLinked": False},
            "margin": {"unit": "px", "top": "0", "right": "0", "bottom": "25", "left": "0", "isLinked": False},
            "border_radius": {"unit": "px", "top": "12", "right": "12", "bottom": "12", "left": "12", "isLinked": True},
            "box_shadow_box_shadow_type": "yes",
            "box_shadow_box_shadow": {"horizontal": 0, "vertical": 4, "blur": 10, "spread": -3, "color": "rgba(0,0,0,0.07)"}
        },
        "elements": [
            {
                "id": generate_elementor_id(),
                "elType": "column",
                "isInner": False,
                "settings": {"_column_size": 100},
                "elements": elements
            }
        ]
    }

# ==========================================
# توابع کمکی شبکه و همگام‌سازی
# ==========================================

def get_jwt_token(wp_api_url, username, password):
    api_base = wp_api_url.replace('/wp/v2', '').rstrip('/')
    token_url = f"{api_base}/jwt-auth/v1/token"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
    try:
        response = requests.post(token_url, data={'username': username, 'password': password}, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.json().get('token'), None
        return None, f"خطای توکن ({response.status_code})"
    except Exception as e:
        return None, str(e)


def sync_entity_image_to_wp(entity_image, wp_api_url, token):
    # ۱. اصلاح شرط اول: به جای local_image_filename فقط خود فیلد image را چک می‌کنیم
    if not entity_image or not entity_image.image:
        return True, "عکسی تنظیم نشده است."
        
    if entity_image.wp_attachment_id and entity_image.wp_image_url:
        return True, "عکس از قبل موجود است."
    
    # چون در شرط بالا چک کردیم که image وجود دارد، اینجا با خیال راحت path را می‌گیریم
    image_path = entity_image.image.path

    if not image_path or not os.path.exists(image_path):
        return False, f"فایل یافت نشد: {image_path}"
    
    filename = os.path.basename(image_path)
    
    # ۲. اصلاح باگ MimeType
    guessed_type, _ = mimetypes.guess_type(image_path)
    mime_type = guessed_type or "image/jpeg"
    
    headers = {
        'Authorization': f'Bearer {token}', 
        'Content-Disposition': f'attachment; filename="{filename}"', 
        'Content-Type': mime_type,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        'Accept': '*/*'
    }
    
    try:
        with open(image_path, 'rb') as f:
            img_data = f.read()
            
        response = requests.post(
            f"{wp_api_url.rstrip('/')}/media", 
            headers=headers, 
            data=img_data, 
            timeout=45
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            entity_image.wp_attachment_id = data.get('id')
            entity_image.wp_image_url = data.get('source_url')
            entity_image.save()
            return True, "موفق"
            
        return False, f"خطای وردپرس: {response.text}"
        
    except Exception as e:
        return False, f"خطای سیستمی: {str(e)}"
    
# ==========================================
# استایل‌های سراسری (CSS Grid و اکشن‌بار)
# ==========================================
GLOBAL_RESPONSIVE_CSS = """<style>
.dynamic-seo-card { padding: 35px 25px !important; transition: all 0.3s ease; }
.responsive-table-container { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; margin: 20px 0; border: 1px solid #e2e8f0; border-radius: 8px; }
.responsive-table-container table { width: 100% !important; border-collapse: collapse; min-width: 550px; }
.responsive-table-container th, .responsive-table-container td { padding: 12px 15px !important; text-align: right; border-bottom: 1px solid #e2e8f0; font-size: 14px; }
.responsive-table-container th { background-color: #f8fafc; color: #2D4B8C; font-weight: bold; }
.dynamic-text-inner p { line-height: 1.85; color: #333333; font-size: 15px; margin-bottom: 15px; text-align: justify; }

/* --- استایل‌های هدر فروشگاهی (گرید داینامیک و هم‌ارتفاع) --- */
.shop-hero-container { display: grid; grid-template-columns: 1fr 1.5fr; gap: 20px; direction: rtl; align-items: stretch; margin-bottom: 20px; }
.shop-hero-image { background: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; display: flex; align-items: center; justify-content: center; }
.shop-hero-image img { max-height: 250px; width: auto; object-fit: contain; border-radius: 8px; }
.shop-hero-specs { background: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; }

/* --- استایل نوار اکشن (ستاره‌ها و باکس قیمت) --- */
.action-bar-wrapper { display: flex; justify-content: space-between; align-items: center; background: #f8fafc; border: 1px solid #cbd5e1; padding: 12px 20px; border-radius: 10px; margin-bottom: 20px; flex-wrap: wrap; gap: 15px; direction: rtl; }
.stars-box { display: flex; align-items: center; gap: 6px; color: #dd6b20; font-size: 13px; letter-spacing: -2px; }
.price-box { background: #fee2e2; border: 1px solid #fca5a5; padding: 8px 15px; border-radius: 6px; color: #b91c1c; font-weight: bold; font-size: 15px; }

@media (max-width: 767px) {
    .dynamic-seo-card { padding: 20px 15px !important; margin-bottom: 15px !important; border-radius: 8px !important; }
    .shop-hero-container { grid-template-columns: 1fr; }
    .action-bar-wrapper { flex-direction: column; text-align: center; justify-content: center; }
}
</style>"""

# ==========================================
# تابع اصلی انتشار در المنتور
# ==========================================
def publish_direct_elementor(page_content: PageContent):
    brief = page_content.page_brief
    project = brief.project
    entity = brief.entity
    
    if not all([project.wp_api_url, project.wp_username, project.wp_app_password]):
        return False, "اطلاعات اتصال وردپرس ناقص است."

    token, error_msg = get_jwt_token(project.wp_api_url, project.wp_username, project.wp_app_password)
    if not token:
        return False, error_msg

    # ۱. واکشی تصاویر از دیتابیس جدید
    product_img_obj = entity.get_product_image() if entity else None
    poster_img_obj = entity.get_poster_image() if entity else None

    # ۲. همگام‌سازی تصاویر با رسانه وردپرس
    if product_img_obj:
        sync_entity_image_to_wp(product_img_obj, project.wp_api_url, token)
    if poster_img_obj:
        sync_entity_image_to_wp(poster_img_obj, project.wp_api_url, token)

    blocks = page_content.blocks_json
    if not blocks:
        return False, "بلوک‌های متنی یافت نشد."

    elementor_data = []
    is_shop_rendered = False

    # --------------------------------------------------------
    # ۳. استخراج متای ویژگی‌های فنی (Specs)
    # --------------------------------------------------------
    specs_dict = {}
    for b in blocks:
        if b.get("block_type") == "specs":
            # هندل کردن حالتی که متا به صورت دیکشنری یا استرینگ جیسون ذخیره شده باشد
            raw_specs = b.get("meta_specs", {})
            if isinstance(raw_specs, str):
                try:
                    specs_dict = json.loads(raw_specs)
                except:
                    specs_dict = {}
            else:
                specs_dict = raw_specs
            break

    if specs_dict:
        specs_dict["نحوه ارسال"] = "اینترنتی و حضوری"
        specs_dict["کیفیت کالا"] = "اصلی / اورجینال"

    # --------------------------------------------------------
    # ۴. ساخت هدر فروشگاهی (عکس راست، ویژگی‌ها چپ + اکشن‌بار)
    # --------------------------------------------------------
    if brief.page_level == 2 and brief.page_type == "pillar" and brief.keyword.text == 'ریموت' and entity:
        if product_img_obj and product_img_obj.wp_image_url:
            stock_count = random.randint(1, 10)
            
            specs_rows_html = ""
            for k, v in specs_dict.items():
                if v:
                    specs_rows_html += f"""
                    <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px dashed #e2e8f0; padding: 8px 0; margin-bottom: 4px;">
                        <span style="color:#718096; font-size: 13px; font-weight: bold;">{k}</span>
                        <span style="color:#2D4B8C; font-weight: bold; font-size: 14px;">{v}</span>
                    </div>
                    """

            shop_html = f"""
            {GLOBAL_RESPONSIVE_CSS}
            <div class="shop-hero-container">
                <div class="shop-hero-image">
                    <img src="{product_img_obj.wp_image_url}" alt="ریموت  {entity.name}">
                </div>
                
                <div class="shop-hero-specs">
                    <h2 style="color: #000; font-size: 18px; margin-top: 0; margin-bottom: 15px; border-bottom: 2px solid #2D4B8C; padding-bottom: 8px; display: inline-block;">
                        مشخصات ریموت {entity.name}
                    </h2>
                    <div style="display: flex; flex-direction: column;">
                        {specs_rows_html}
                    </div>
                </div>
            </div>
            
            <div class="action-bar-wrapper">
                <div class="stars-box">
                    ⭐⭐⭐⭐⭐ <span style="font-size: 12px; color:#64748b; letter-spacing: 0;">موجودی: {stock_count} عدد</span>
                </div>
                <div class="price-box">
                    قیمت: <span>برای قیمت تماس بگیرید</span>
                </div>
            </div>
            """

            shop_elements = [
                create_text_widget(shop_html, align="right"),
                create_heading_widget("🚚 ارسال سریع به سراسر ایران", color="#2D4B8C", align="center", size_tag="h4"),
                create_button_widget("🛒 درخواست خرید و مشاوره فوری", "tel:+98910868078", align="center")
            ]
            shop_section = wrap_in_elementor_card(shop_elements, bg_color="#ffffff")
            elementor_data.append(shop_section)
            is_shop_rendered = True

    # --------------------------------------------------------
    # ۵. پردازش بلوک‌های متنی تولید شده
    # --------------------------------------------------------
    for index, block in enumerate(blocks):
        b_type = block.get("block_type", "")
        title = block.get("title", "")
        content = block.get("content", "").strip()
        
        # اسکیپ بلوک‌های خاص که جداگانه هندل شده‌اند
        if b_type in ["faq", "specs", "specs_block"]:
            continue

        block_elements = []

        if b_type == "image":
            if is_shop_rendered:
                continue
            
            # در مقالات و کلاسترها، از پوستر استفاده می‌کنیم
            if poster_img_obj and poster_img_obj.wp_image_url:
                alt_text = content or f"خدمات تخصصی ریموت {entity.name}"
                block_elements.append(create_image_widget(poster_img_obj.wp_image_url, poster_img_obj.wp_attachment_id, alt_text))
            else:
                continue
        else:
            if title and b_type != "hero":
                block_elements.append(create_heading_widget(title, color="#000000", align="right"))
                content = re.sub(r'<h[2-6]\b[^>]*>.*?' + re.escape(title) + r'.*?</h[2-6]>', '', content, flags=re.IGNORECASE).strip()
            
            if content:
                if "<table" in content.lower():
                    content = re.sub(r'(<table\b[^>]*>.*?</table>)', r'<div class="responsive-table-container">\1</div>', content, flags=re.DOTALL | re.IGNORECASE)
                
                if len(elementor_data) == 0 and not is_shop_rendered:
                    content = GLOBAL_RESPONSIVE_CSS + content

                block_elements.append(create_text_widget(content, align="right"))

        if block_elements:
            bg_color = "#ffffff" if index % 2 == 0 else "#f8fafc"
            card_section = wrap_in_elementor_card(block_elements, bg_color=bg_color)
            elementor_data.append(card_section)

    # --------------------------------------------------------
    # ۶. رندر آکاردئون سوالات متداول
    # --------------------------------------------------------
    if page_content.faq_json and isinstance(page_content.faq_json, list):
        faq_elements = [create_heading_widget("سوالات متداول کاربران", color="#000000", align="center")]
        faq_html = "<div style='max-width: 750px; margin: 0 auto; text-align: center;'>"
        for item in page_content.faq_json:
            q = item.get("question", "").strip()
            a = item.get("answer", "").strip()
            if q and a:
                faq_html += f"""
                <details style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin-bottom: 12px; text-align: right; box-shadow: 0 2px 4px rgba(0,0,0,0.01);">
                    <summary style="font-weight: bold; color: #2D4B8C; cursor: pointer; direction: rtl; list-style: none;">❓ {q}</summary>
                    <p style="margin-top: 10px; color: #4a5568; line-height: 1.7; padding-right: 15px; margin-bottom:0;">{a}</p>
                </details>"""
        faq_html += "</div>"
        faq_elements.append(create_text_widget(faq_html, align="center"))
        faq_card = wrap_in_elementor_card(faq_elements, bg_color="#f1f5f9")
        elementor_data.append(faq_card)

    # --------------------------------------------------------
    # ۷. تزریق پکیج اسکیماها به انتهای صفحه
    # --------------------------------------------------------
    # generated_schemas = generate_advanced_schema(brief, page_content)
    generated_schemas = page_content.schema_json
    if generated_schemas:
        schema_html = ""
        for schema in generated_schemas:
            schema_html += f'\n<script type="application/ld+json">\n{json.dumps(schema, ensure_ascii=False)}\n</script>'
        
        elementor_data.append({
            "id": __import__('uuid').uuid4().hex[:7],
            "elType": "widget",
            "isInner": False,
            "settings": {"editor": schema_html},
            "widgetType": "text-editor"
        })

    # --------------------------------------------------------
    # ۸. پکیج کردن و ارسال نهایی به وردپرس
    # --------------------------------------------------------
    elementor_json_str = json.dumps(elementor_data, separators=(',', ':'), ensure_ascii=False)

    focus_keywords = brief.keyword.text + " " + (entity.name if entity else "")
    if brief.keyword.extra_keywords_text:
        extra_clean = brief.keyword.extra_keywords_text.replace('\r', '').replace('\n', ',')
        focus_keywords += f",{extra_clean}"

    wp_meta_data = {
        "rank_math_title": page_content.seo_title,
        "rank_math_description": page_content.meta_description,
        "rank_math_focus_keyword": focus_keywords,
        "_elementor_edit_mode": "builder",
        "_elementor_template_type": "wp-post",
        "_elementor_data": elementor_json_str
    }
    
    clean_slug = brief.url_path.strip('/') if brief.url_path else ""
    safe_slug = urllib.parse.quote(clean_slug)
    if brief.url_path:
        wp_meta_data["custom_permalink"] = safe_slug

    # if hasattr(brief, 'canonical_url') and brief.canonical_url:
    #     wp_meta_data["rank_math_canonical_url"] = brief.canonical_url

    wp_payload = {
        "title": page_content.h1,
        "content": "",
        "slug": clean_slug.split('/')[-1], 
        "meta": wp_meta_data,
        "status": "publish", #if page_content.publish_status == "published" else "draft",
        "modified": datetime.now().isoformat()
    }

    if poster_img_obj and poster_img_obj.wp_attachment_id:
        wp_payload["featured_media"] = poster_img_obj.wp_attachment_id
    elif product_img_obj and product_img_obj.wp_attachment_id:
        wp_payload["featured_media"] = product_img_obj.wp_attachment_id

    wp_payload["categories"] = [11] if brief.page_type == "educational" else [12, 18] # luxremote
    wp_payload["tags"] = [27] # کلاستر مدل

    headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Accept': 'application/json'
    }

    url = f"{project.wp_api_url.rstrip('/')}/posts/{page_content.target_server_post_id}" if page_content.target_server_post_id else f"{project.wp_api_url.rstrip('/')}/posts"
    
    try:
        response = requests.post(url, json=wp_payload, headers=headers, timeout=20)
        if response.status_code in [200, 201]:
            data = response.json()
            page_content.publish_status = PageContent.PublishStatus.PUBLISHED
            page_content.target_server_post_id = data.get('id')
            page_content.save()
            return True, f"لندینگ پیج با موفقیت مستقر شد. (ID: {data.get('id')})"
        return False, f"خطای وردپرس: {response.text}"
    except Exception as e:
        return False, str(e)
    