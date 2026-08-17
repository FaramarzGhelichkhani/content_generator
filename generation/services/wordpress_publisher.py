# generation/services/wordpress_publisher.py
import os
import mimetypes
import requests
import json
from datetime import datetime
from content.models import PageContent

def get_jwt_token(wp_api_url, username, password):
    api_base = wp_api_url.replace('/wp/v2', '').rstrip('/')
    token_url = f"{api_base}/jwt-auth/v1/token"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json',
    }
    try:
        response = requests.post(token_url, data={'username': username, 'password': password}, headers=headers, timeout=15)
        try:
            token_data = response.json()
        except ValueError:
            return None, f"پاسخ سرور JSON نبود: {response.text[:200]}"
            
        if response.status_code == 200:
            return token_data.get('token'), None
        return None, f"خطای توکن ({response.status_code}): {token_data.get('message', response.text)}"
    except Exception as e:
        return None, f"خطای شبکه در درخواست توکن: {str(e)}"

def sync_entity_image_to_wp(entity, wp_api_url, token):
    """
    خواندن تصویر از فولدر لوکال سرور و آپلود آن در رسانه وردپرس.
    """
    # بررسی وجود نام فایل در دیتابیس
    if not entity or not entity.local_image_filename:
        return True, "نام فایل عکسی برای آپلود تنظیم نشده است."

    # اگر عکس قبلاً آپلود شده و آیدی دارد، اسکیپ می‌کنیم
    if entity.wp_attachment_id and entity.wp_image_url:
        return True, "عکس از قبل در وردپرس موجود است."

    # محاسبه مسیر دقیق فایل در سرور بر اساس معماری فولدرها
    image_path = entity.get_actual_image_path()
    
    if not image_path or not os.path.exists(image_path):
        return False, f"فایل تصویر در سرور یافت نشد. مسیر بررسی شده: {image_path}"

    print(f"[*] Uploading new image for entity '{entity.name}' from local folder to WP...")

    api_base = wp_api_url.rstrip('/')
    media_url = f"{api_base}/media"
    
    filename = os.path.basename(image_path)
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "image/jpeg"

    # آماده‌سازی هدرهای وردپرس برای آپلود دیتای باینری
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Disposition': f'attachment; filename="{filename}"',
        'Content-Type': mime_type
    }

    try:
        with open(image_path, 'rb') as f:
            img_data = f.read()

        response = requests.post(media_url, headers=headers, data=img_data, timeout=45)
        
        if response.status_code in [200, 201]:
            data = response.json()
            
            # ذخیره دیتای دریافتی از وردپرس
            entity.wp_attachment_id = data.get('id')
            entity.wp_image_url = data.get('source_url')
            entity.save()
            
            print(f"[+] Image synced successfully! WP ID: {entity.wp_attachment_id}")
            return True, "آپلود تصویر موفقیت‌آمیز بود."
        else:
            return False, f"خطای آپلود در رسانه وردپرس ({response.status_code}): {response.text}"
            
    except Exception as e:
        return False, f"خطای شبکه در زمان خواندن فایل یا آپلود: {str(e)}"
    
def format_as_gutenberg_blocks(blocks_json, faq_json=None, entity=None):
    """رندر نهایی بلوک‌ها شامل استخراج داینامیک تصویر از موجودیت"""
    gutenberg_html = """<style>
    .wp-seo-container-card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 30px; margin-bottom: 25px; direction: rtl; text-align: right; }
    .wp-seo-faq-card { background: #f8fafc; border: 2px dashed #cbd5e1; border-radius: 12px; padding: 35px; margin-top: 30px; direction: rtl; text-align: center; }
    .wp-seo-faq-card .wp-block-heading { text-align: center !important; margin-bottom: 25px; }
    .wp-seo-faq-card details { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin: 12px auto; max-width: 700px; text-align: right; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    .wp-seo-faq-card summary { font-weight: bold; color: #2D4B8C; cursor: pointer; list-style: none; }
    .wp-seo-faq-card summary::-webkit-details-marker { display: none; }
</style>
\n\n"""

    for block in blocks_json:
        block_type = block.get("block_type", "")
        title = (block.get("title") or "").strip()
        content = (block.get("content") or "").strip()
        
        # رندر بلوک تصویر
        if block_type == "image":
            if entity and entity.wp_image_url:
                alt_text = content or f"تصویر {entity.name}"
                wp_id = entity.wp_attachment_id or 0
                
                gutenberg_html += f"""<figure class="wp-block-image size-large wp-seo-entity-image" style="text-align:center; margin: 30px 0;">
    <img src="{entity.wp_image_url}" alt="{alt_text}" class="wp-image-{wp_id}" style="border-radius:10px; max-width:100%; height:auto;"/>
</figure>
\n\n"""
            continue 

        # رندر بلوک‌های متنی
        if not content:
            continue
            
        gutenberg_html += '\n'
        gutenberg_html += '<div class="wp-block-group wp-seo-container-card">\n'
        
        import re
        if title and block_type != "hero":
            has_heading = re.search(r'<h[2-6]\b[^>]*>.*?' + re.escape(title) + r'.*?</h[2-6]>', content, re.IGNORECASE)
            if not has_heading:
                gutenberg_html += f'\n<h2 class="wp-block-heading">{title}</h2>\n\n\n'
        
        gutenberg_html += f'\n{content}\n\n'
        gutenberg_html += '</div>\n\n\n'

    # رندر FAQ
    if faq_json and isinstance(faq_json, list):
        gutenberg_html += '\n'
        gutenberg_html += '<div class="wp-block-group wp-seo-faq-card">\n'
        gutenberg_html += '\n<h2 class="wp-block-heading has-text-align-center">سوالات متداول کاربران</h2>\n\n\n'
        
        for item in faq_json:
            q = item.get("question", "").strip()
            a = item.get("answer", "").strip()
            if q and a:
                gutenberg_html += f'\n'
                gutenberg_html += f'<details class="wp-block-details"><summary>❓ {q}</summary>\n'
                gutenberg_html += f'\n<p>{a}</p>\n\n'
                gutenberg_html += f'</details>\n\n\n'
                
        gutenberg_html += '</div>\n\n\n'

    return gutenberg_html


def publish_to_wordpress(page_content: PageContent):
    brief = page_content.page_brief
    project = brief.project
    
    if not all([project.wp_api_url, project.wp_username, project.wp_app_password]):
        return False, "اطلاعات اتصال وردپرس ناقص است."

    # ۱. دریافت توکن
    token, error_msg = get_jwt_token(project.wp_api_url, project.wp_username, project.wp_app_password)
    if not token:
        return False, error_msg

    # ۲. پیش‌نیاز: همگام‌سازی تصویر موجودیت با رسانه وردپرس (Pre-flight Upload)
    if brief.entity:
        img_success, img_msg = sync_entity_image_to_wp(brief.entity, project.wp_api_url, token)
        if not img_success:
            print(f"[-] Warning: Image upload failed, continuing without image. Reason: {img_msg}")

    # ۳. آماده‌سازی محتوا
    blocks = page_content.blocks_json
    if not blocks:
        return False, "بلوک‌های متنی یافت نشد."
        
    gutenberg_content = format_as_gutenberg_blocks(blocks, faq_json=page_content.faq_json, entity=brief.entity)
    
    if page_content.schema_json:
        schema_str = json.dumps(page_content.schema_json, ensure_ascii=False)
        gutenberg_content += f'\n\n<script type="application/ld+json">\n{schema_str}\n</script>\n'

    # focus_keywords = brief.keyword.text + " " + brief.entity.name
    focus_keywords = page_content.focus_keyword
    if brief.keyword.extra_keywords_text:
        extra_clean = brief.keyword.extra_keywords_text.replace('\r', '').replace('\n', ',')
        focus_keywords += f",{extra_clean}"

    wp_meta_data = {
        "rank_math_title": page_content.seo_title,
        "rank_math_description": page_content.meta_description,
        "rank_math_focus_keyword": focus_keywords,
        "elementor-template id":5759,
        "custom_elementor_template_id": 5759
    }
    
    if hasattr(brief, 'canonical_url') and brief.canonical_url:
        wp_meta_data["rank_math_canonical_url"] = brief.canonical_url
        
    clean_slug = brief.url_path.strip('/') if brief.url_path else ""
    if brief.url_path:
        wp_meta_data["custom_permalink"] = clean_slug

    # ۵. چیدمان پی‌لود و ارسال پست
    wp_payload = {
        "title": page_content.h1,
        "content": gutenberg_content,
        "slug": clean_slug.split('/')[-1], 
        "meta": wp_meta_data,
        "modified": datetime.now().isoformat()
    }

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    if page_content.target_server_post_id:
        url = f"{project.wp_api_url.rstrip('/')}/posts/{page_content.target_server_post_id}"
    else:
        url = f"{project.wp_api_url.rstrip('/')}/posts"
        wp_payload["status"] = "draft"
    
    try:
        response = requests.post(url, json=wp_payload, headers=headers, timeout=15)
        
        if response.status_code in [200, 201]:
            response_data = response.json()
            
            page_content.publish_status = PageContent.PublishStatus.PUBLISHED
            page_content.target_server_post_id = response_data.get('id')
            
            if hasattr(page_content, 'target_url'):
                page_content.target_url = response_data.get('link')
                
            page_content.save()
            return True, f"با موفقیت همگام‌سازی شد (Post ID: {response_data.get('id')})"
        else:
            return False, f"خطای سرور وردپرس: {response.status_code} - {response.text}"
            
    except Exception as e:
        return False, f"خطای ارتباط با سرور وردپرس: {str(e)}"
    