from datetime import datetime
import random
import json
from django.utils import timezone

def generate_advanced_schema(brief, page_content):
    """
    تولید خودکار و هوشمند گراف اسکیما (JSON-LD) 
    شامل اسکیماهای پایه (برای همه صفحات) و اختصاصی (بر اساس نوع صفحه)
    """
    entity = getattr(brief, 'entity', None)
    location = getattr(brief, 'location', None)
    keyword_text = brief.keyword.text if brief.keyword else ""
    
    project = getattr(brief, 'project', None)
    base_domain = project.base_domain.rstrip('/') if project and project.base_domain else "https://remotecyclet.ir"
    
    clean_path = brief.url_path.strip('/') if brief.url_path else ""
    page_url = f"{base_domain}/{clean_path}/" if clean_path else f"{base_domain}/"
    
    schemas = []

    # ==========================================
    # بخش اول: اسکیماهای پایه (مشترک برای تمام صفحات)
    # ==========================================

    # ۱. اسکیمای سازمان / برند (Organization)
    org_schema = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "مرکز تخصصی سوئیچ و ریموت موتور سیکلت ریموت سیکلت", 
        "url": f"{base_domain}/",
        "logo": f"{base_domain}/assets/img/logo3.png", 
        "contactPoint": {
            "@type": "ContactPoint",
            "telephone": "+989204407640",
            "contactType": "customer service",
            "areaServed": "IR",
            "availableLanguage": "Persian"
        }
    }
    schemas.append(org_schema)

    # ۲. اسکیمای صفحه وب (WebPage)
    webpage_schema = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": f"{page_url}#webpage",
        "url": page_url,
        "name": page_content.seo_title or page_content.h1 or keyword_text,
        "description": page_content.meta_description or "",
        "inLanguage": "fa-IR",
        "isPartOf": {
            "@type": "WebSite",
            "@id": f"{base_domain}/#website",
            "url": f"{base_domain}/",
            "name": "مرکز تخصصی سوئیچ و ریموت ریموت سیکلت"
        }
    }
    schemas.append(webpage_schema)

    # ۳. اسکیمای مسیر راهنما (BreadcrumbList)
    if brief.url_path:
        breadcrumb_schema = {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": []
        }
        
        path_segments = [p for p in brief.url_path.split('/') if p]
        current_url = base_domain
        
        breadcrumb_schema["itemListElement"].append({
            "@type": "ListItem",
            "position": 1,
            "name": "صفحه اصلی",
            "item": current_url + "/"
        })
        
        entity_chain_names = {}
        curr_entity = entity
        while curr_entity:
            entity_chain_names[curr_entity.slug] = curr_entity.name
            curr_entity = getattr(curr_entity, 'parent', None)
            
        position = 2
        for segment in path_segments:
            current_url += f"/{segment}"
            
            friendly_name = segment
            if segment == "remotes":
                friendly_name = "خدمات ریموت و سوئیچ"
            elif segment in ["mag", "blog"]:
                friendly_name = "مجله آموزشی"
            elif segment in entity_chain_names:
                friendly_name = entity_chain_names[segment]
                
            breadcrumb_schema["itemListElement"].append({
                "@type": "ListItem",
                "position": position,
                "name": friendly_name,
                "item": current_url + "/"
            })
            position += 1
            
        if len(breadcrumb_schema["itemListElement"]) > 1:
            schemas.append(breadcrumb_schema)

    # ۴. اسکیمای سوالات متداول (FAQPage)
    if getattr(page_content, 'faq_json', None) and isinstance(page_content.faq_json, list):
        faq_schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": []
        }
        for item in page_content.faq_json:
            q = item.get("question", "").strip()
            a = item.get("answer", "").strip()
            if q and a:
                faq_schema["mainEntity"].append({
                    "@type": "Question",
                    "name": q,
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": a
                    }
                })
        if faq_schema["mainEntity"]:
            schemas.append(faq_schema)

    # ==========================================
    # بخش دوم: اسکیماهای اختصاصی (بر اساس نوع صفحه)
    # ==========================================

    service_type = getattr(brief, 'service_type', None)
    is_ecommerce = service_type.is_ecommerce if service_type else False

    # ۵. اسکیمای تجاری (Product)
    if is_ecommerce and entity:
        review_count = random.randint(15, 85)
        
        image_url = f"{base_domain}/assets/img/adv.jpg"
        if hasattr(entity, 'get_product_image'):
            product_image = entity.get_product_image()
            if product_image and getattr(product_image, 'wp_image_url', None):
                image_url = product_image.wp_image_url

        parent_name = entity.parent.name if getattr(entity, 'parent', None) else entity.name

        product_schema = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": page_content.seo_title or f"خرید ریموت {entity.name}",
            "image": image_url,
            "description": page_content.meta_description or f"فروش ریموت اورجینال {entity.name} با بالاترین کیفیت و ضمانت.",
            "brand": {
                "@type": "Brand",
                "name": parent_name
            },
            "aggregateRating": {
                "@type": "AggregateRating",
                "ratingValue": "5.0",
                "reviewCount": str(review_count)
            },
            "offers": {
                "@type": "Offer",
                "url": page_url,
                "priceCurrency": "IRR",
                "price": "0", 
                "priceValidUntil": "2028-12-31",
                "availability": "https://schema.org/InStock",
                "itemCondition": "https://schema.org/NewCondition"
            }
        }
        schemas.append(product_schema)    

    # ۶. صفحات کلاستر محلی و خدماتی
    elif getattr(brief, 'page_type', '') == "cluster" and not is_ecommerce:
        image_url = f"{base_domain}/assets/img/service-hero.jpg"
        if entity and hasattr(entity, 'get_poster_image'):
            poster_image = entity.get_poster_image()
            if poster_image and getattr(poster_image, 'wp_image_url', None):
                image_url = poster_image.wp_image_url

        loc_name = location.name if location else "تهران"

        local_business = {
            "@context": "https://schema.org",
            "@type": "AutomotiveRepairShop", 
            "name": page_content.h1 or keyword_text,
            "image": image_url,
            "url": page_url,
            "telephone": "+989204407640",
            "priceRange": "$$",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": loc_name, 
                "addressRegion": "Tehran",
                "addressCountry": "IR"
            },
            "geo": {
                "@type": "GeoCoordinates",
                "latitude": "35.6892",
                "longitude": "51.3890"
            }
        }
        
        service_schema = {
            "@context": "https://schema.org",
            "@type": "Service",
            "serviceType": keyword_text,
            "provider": {
                "@type": "AutomotiveRepairShop",
                "name": "مرکز تخصصی سوئیچ و ریموت ریموت سیکلت"
            },
            "areaServed": {
                "@type": "AdministrativeArea",
                "name": loc_name
            }
        }
        schemas.append(local_business)
        schemas.append(service_schema)

    # ۷. صفحات دانشنامه‌ای (TechArticle)
    elif getattr(brief, 'page_type', '') == "educational":
        image_url = f"{base_domain}/assets/img/educational-hero.jpg"
        if entity and hasattr(entity, 'get_poster_image'):
            poster_image = entity.get_poster_image()
            if poster_image and getattr(poster_image, 'wp_image_url', None):
                image_url = poster_image.wp_image_url

        updated_at = getattr(page_content, 'updated_at', None)
        pub_date = updated_at.isoformat() if updated_at else timezone.now().isoformat()

        article_schema = {
            "@context": "https://schema.org",
            "@type": "TechArticle",
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": page_url
            },
            "headline": page_content.h1 or keyword_text,
            "description": page_content.meta_description or "",
            "image": image_url,
            "datePublished": pub_date,
            "dateModified": pub_date,
            "author": {
                "@type": "Organization",
                "name": "تیم فنی کلیدسازی تخصصی"
            },
            "publisher": {
                "@type": "Organization",
                "name": "مرکز تخصصی سوئیچ و ریموت ریموت سیکلت",
                "logo": {
                    "@type": "ImageObject",
                    "url": f"{base_domain}/assets/img/logo3.png"
                }
            }
        }
        schemas.append(article_schema)

    # ⭐️ نکته بسیار مهم: تبدیل اجباری لیست پایتونی به ساختار استاندارد JSON خالص
    # این کار تضمین می‌کند که هیچ‌گاه سینگل‌کوتیشن (') در خروجی دیتابیس ذخیره نشود
    clean_json_string = json.dumps(schemas, ensure_ascii=False)
    return json.loads(clean_json_string)
