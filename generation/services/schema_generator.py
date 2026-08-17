# generation/services/schema_generator.py
from datetime import datetime
import random

def generate_advanced_schema(brief, page_content):
    """
    تولید خودکار و هوشمند گراف اسکیما (JSON-LD) 
    شامل اسکیماهای پایه (برای همه صفحات) و اختصاصی (بر اساس نوع صفحه)
    """
    entity = brief.entity
    keyword_text = brief.keyword.text
    base_domain = brief.project.base_domain.rstrip('/')
    
    # ساخت URL ایمن
    clean_path = brief.url_path.strip('/') if brief.url_path else ""
    page_url = f"{base_domain}/{clean_path}/" if clean_path else f"{base_domain}/"
    
    schemas = []

    # ==========================================
    # بخش اول: اسکیماهای پایه (مشترک برای تمام صفحات)
    # ==========================================

    # ۱. اسکیمای سازمان / برند (Organization) - برای شناساندن هویت سایت به گوگل
    org_schema = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "مرکز تخصصی سوئیچ و ریموت خودرو و موتور سیکلت لوکس ریموت", # می‌توانید این را از تنظیمات پروژه هم بگیرید
        "url": base_domain,
        "logo": f"{base_domain}/wp-content/uploads/2026/07/logo-scaled.webp", # مسیر لوگوی سایت شما
        "contactPoint": {
            "@type": "ContactPoint",
            "telephone": "+989204407640",
            "contactType": "customer service",
            "areaServed": "IR",
            "availableLanguage": "Persian"
        }
    }
    schemas.append(org_schema)

    # ۲. اسکیمای صفحه وب (WebPage) - متصل به سازمان
    webpage_schema = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": f"{page_url}#webpage",
        "url": page_url,
        "name": page_content.seo_title or page_content.h1 or keyword_text,
        "description": page_content.meta_description,
        "inLanguage": "fa-IR",
        "isPartOf": {
            "@type": "WebSite",
            "@id": f"{base_domain}/#website",
            "url": base_domain,
            "name": "مرکز تخصصی سوئیچ و ریموت لوکس ریموت"
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
            curr_entity = curr_entity.parent
            
        position = 2
        for segment in path_segments:
            current_url += f"/{segment}"
            
            friendly_name = segment
            if segment == "remotes":
                friendly_name = "خدمات ریموت و سوئیچ"
            elif segment == "mag":
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
    if page_content.faq_json and isinstance(page_content.faq_json, list):
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

    # ۵. اسکیمای تجاری (Product + ستاره‌ها) برای کلاسترهای فروشگاهی/خدماتی اصلی
    if brief.page_level == 2 and brief.page_type == "pillar" and keyword_text == "ریموت" and entity:
        review_count = random.randint(15, 85)
        
        product_image = entity.get_product_image()
        image_url = product_image.wp_image_url if product_image else f"{base_domain}/wp-content/uploads/default-product.jpg"

        product_schema = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": f"ریموت {entity.name}",
            "image": image_url,
            "description": page_content.meta_description or f"خدمات ساخت، تعریف و کپی ریموت اورجینال {entity.name} با بالاترین کیفیت.",
            "brand": {
                "@type": "Brand",
                "name": entity.parent.name if entity.parent else entity.name
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

    # ۶. صفحات کلاستر محلی و خدماتی -> LocalBusiness + Service
    elif brief.page_type == "cluster" and entity:
        poster_image = entity.get_poster_image()
        image_url = poster_image.wp_image_url if poster_image else f"{base_domain}/wp-content/uploads/default-service.jpg"

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
                "addressLocality": entity.name, 
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
                "name": "مرکز تخصصی سوئیچ و ریموت خودرو لوکس ریموت"
            },
            "areaServed": {
                "@type": "AdministrativeArea",
                "name": entity.name
            }
        }
        schemas.append(local_business)
        schemas.append(service_schema)

    # ۷. صفحات دانشنامه‌ای (Educational) -> Article / TechArticle
    elif brief.page_type == "educational":
        poster_image = entity.get_poster_image() if entity else None
        image_url = poster_image.wp_image_url if poster_image else f"{base_domain}/wp-content/uploads/default-article.jpg"

        article_schema = {
            "@context": "https://schema.org",
            "@type": "TechArticle",
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": page_url
            },
            "headline": page_content.h1 or keyword_text,
            "description": page_content.meta_description,
            "image": image_url,
            "datePublished": datetime.now().isoformat() if 'datetime' in locals() else page_content.updated_at.isoformat(),
            "dateModified": page_content.updated_at.isoformat(),
            "author": {
                "@type": "Organization",
                "name": "تیم فنی کلیدسازی تخصصی"
            },
            "publisher": {
                "@type": "Organization",
                "name": "مرکز تخصصی سوئیچ و ریموت خودرو لوکس ریموت",
                "logo": {
                    "@type": "ImageObject",
                    "url": f"{base_domain}/wp-content/uploads/2026/07/logo-scaled.webp"
                }
            }
        }
        schemas.append(article_schema)

    return schemas
