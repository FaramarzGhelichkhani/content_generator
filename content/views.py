# content_engine/views.py

import logging
from django.http import HttpRequest, HttpResponse, Http404
from django.db.models import Q

from taxonomy.models import ServiceType, TaxonomyNode
from .models import PageContent
from django.shortcuts import render
from django.template.loader import render_to_string
from django.core.paginator import Paginator

logger = logging.getLogger(__name__)

def blog_list_view(request):
    """
    ویو اختصاصی برای نمایش لیست مقالات و آموزش‌ها (/blog/)
    """
    articles_qs = PageContent.objects.filter(
        generation_status=PageContent.GenerationStatus.COMPLETED,
        page_brief__keyword__intent__code='informational', # فیلتر بر اساس نیت آموزشی
    ).select_related(
        'page_brief', 
        'page_brief__keyword', 
        'page_brief__entity'
    ).order_by('-updated_at')  # مرتب‌سازی بر اساس جدیدترین آپدیت
    print("Fuck")
    # ۲. استخراج دسته‌بندی‌ها (دینامیک از متای کیوردها)
    # از آنجا که دسته بندی در Keyword.meta ذخیره می‌شود، تمام مقادیر یکتای category را پیدا می‌کنیم
    # توجه: اگر دیتابیس شما بزرگ است، بهتر است دسته‌بندی‌ها را به صورت استاتیک یا از یک جدول مجزا بخوانید
    all_categories = set()
    print(articles_qs)
    for article in articles_qs:
        print("me : ",article.id)
        meta = article.page_brief.keyword.meta
        if isinstance(meta, dict) and meta.get('category'):
            all_categories.add(meta.get('category'))
    
    categories_list = list(all_categories)
    if not categories_list:
        categories_list = ["برنامه‌ریزی ریموت", "امنیت موتورسیکلت", "نگهداری و تعمیرات", "اخبار تکنولوژی"]

    category_query = request.GET.get('category')
    if category_query:
        articles_qs = articles_qs.filter(page_brief__keyword__meta__category=category_query)

    clean_articles = []
    for article in articles_qs:
        
        brief = article.page_brief
        keyword_meta = brief.keyword.meta if isinstance(brief.keyword.meta, dict) else {}
        
        # پیدا کردن عکس (از متای کیورد)
        image_url = keyword_meta.get('image_url', '/assets/img/default-article.jpg')
        
        # پیدا کردن دسته‌بندی
        category = keyword_meta.get('category', 'آموزشی')
        
        # محاسبه زمان مطالعه بر اساس target_word_count (هر 200 کلمه = 1 دقیقه)
        reading_time = max(1, brief.target_word_count // 200)

        clean_articles.append({
            'slug': article.slug or brief.url_path.strip('/'),
            'h1': article.h1 or brief.keyword.text,
            'excerpt': article.meta_description or f"مقاله تخصصی در مورد {brief.keyword.text}",
            'image_url': image_url,
            'category': category,
            'reading_time': reading_time,
            'updated_at': article.updated_at,
        })

    # ۵. صفحه‌بندی (Pagination) - نمایش ۹ مقاله در هر صفحه
    paginator = Paginator(clean_articles, 9)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    all_brands = TaxonomyNode.objects.filter(
            kind=TaxonomyNode.Kind.BRAND, 
            is_active=True
        ).order_by('id')
        
    all_services = ServiceType.objects.filter(is_active=True).order_by('id')

    # ۶. ارسال به کانتکست (Context)
    context = {
        'all_brands': all_brands,
        'all_services': all_services,
        'articles': page_obj.object_list, # لیست مقالات صفحه فعلی
        'page_obj': page_obj,
        'has_next_page': page_obj.has_next(),
        'categories': categories_list,
        'current_category': category_query,
        'is_export': request.GET.get('export') == 'true',
    }
    
    return render(request, 'articles_list.html', context)

def build_full_html_page(page_content: PageContent, is_export: bool = False) -> str:
    """
    Assembles the pre-compiled body with the master layout (Header/Footer).
    
    Args:
        page_content (PageContent): آبجکت محتوای صفحه که فیلد compiled_body آن قبلاً پر شده است.
        is_export (bool): 
            - اگر False باشد (حالت پیش‌نمایش در جنگو): هدر و فوتر به صورت زنده رندر شده و کامل به بدنه می‌چسبند.
            - اگر True باشد (حالت ارسال به سایت): هدر و فوتر پردازش نمی‌شوند و فقط تگِ SSI برای سرور نهایی 
              در کد HTML قرار می‌گیرد تا سایت استاتیک شما سبک و ماژولار بماند.
              
    Returns:
        str: رشته متنی شامل کدهای کامل و نهایی HTML صفحه.
    """
    # بررسی اینکه آیا صفحه اصلاً کامپایل شده است یا خیر
    if not page_content.compiled_body:
        logger.error("PageContent ID %d is not compiled yet.", page_content.pk)
        return ""

    # (اختیاری) کوئری گرفتن برای آیتم‌های منوی هدر و فوتر
    all_brands = TaxonomyNode.objects.filter(kind='brand', is_active=True).order_by('id')
    all_services = ServiceType.objects.filter(is_active=True)

    # کانتکست مورد نیاز برای قالب master_layout.html
    context = {
        "page": page_content,
        "brief": page_content.page_brief,
        "is_export": is_export, 
        "all_brands": all_brands,
        "all_services": all_services,
    }

    try:
        # رندر کردن قالب اصلی و پاس دادن کانتکست به آن
        full_html = render_to_string("master_layout.html", context)
        return full_html
        
    except Exception as e:
        logger.exception("Error rendering master_layout for PageContent ID %d: %s", page_content.pk, str(e))
        return ""
    

def render_dynamic_page(request: HttpRequest, url_path: str) -> HttpResponse:
    """
    Catches dynamic URLs, retrieves the pre-compiled content blocks,
    and assembles them with the master layout for previewing.
    
    Args:
        request (HttpRequest): The HTTP request object.
        url_path (str): The captured path from the URL router.
        
    Returns:
        HttpResponse: The fully assembled HTML page for preview.
    """
    try:
        # نرمال‌سازی مسیر برای پوشش دادن اسلش‌های ابتدا و انتها
        normalized_path = url_path.strip("/")
        
        # جستجو در دیتابیس با در نظر گرفتن حالت‌های مختلف ثبت URL
        page_content = PageContent.objects.select_related('page_brief').filter(
            Q(page_brief__url_path=normalized_path) |
            Q(page_brief__url_path=f"/{normalized_path}") |
            Q(page_brief__url_path=f"/{normalized_path}/") |
            Q(page_brief__url_path=f"{normalized_path}/")
        ).first()

        if not page_content:
            logger.warning("No PageContent found for url_path: %s", url_path)
            raise Http404("صفحه‌ای با این آدرس یافت نشد.")

        # بررسی اینکه آیا صفحه قبلاً کامپایل شده است یا خیر
        if not page_content.compiled_body:
            logger.info("PageContent ID %d has empty compiled_body.", page_content.pk)
            return HttpResponse(
                "<div style='text-align:center; padding:50px; font-family:tahoma;'>"
                "<h2>محتوا یافت نشد</h2>"
                "<p>این صفحه هنوز رندر نشده است. لطفاً از پنل ادمین، اکشن «رندر کدهای HTML» را اجرا کنید.</p>"
                "</div>",
                status=404
            )

        # استفاده از سرویس مونتاژ صفحه برای پیش‌نمایش در ادمین
        # از آنجا که is_export ارسال نشده است (پیش‌فرض False است)،
        # جنگو فایل‌های header و footer را به صورت زنده در کدهای HTML قرار می‌دهد
        # تا شما ظاهر نهایی سایت را به طور کامل مشاهده کنید.
        final_html = build_full_html_page(page_content)
        
        return HttpResponse(final_html)

    except Http404:
        raise
    except Exception as e:
        logger.exception("Error serving dynamic page for path %s: %s", url_path, str(e))
        return HttpResponse(
            "<div style='text-align:center; padding:50px; font-family:tahoma; color:red;'>"
            "<h2>خطای سرور ۵۰۰</h2>"
            "<p>مشکلی در پردازش و نمایش پیش‌نمایش صفحه رخ داد. لطفاً لاگ‌ها را بررسی کنید.</p>"
            "</div>",
            status=500
        )


def home_page_view(request):
    """
    ویو اختصاصی برای نمایش صفحه اصلی (Landing Page)
    """
    # گرفتن تمام برندها برای دراپ‌داون هدر و فوتر
    all_brands = TaxonomyNode.objects.filter(
        kind=TaxonomyNode.Kind.BRAND, 
        is_active=True
    ).order_by('id')
    
    all_services = ServiceType.objects.filter(is_active=True).order_by('id')
    
    context = {
        'all_brands': all_brands,
        'featured_brands': all_brands, # برای سکشن برندهای منتخب در صفحه اصلی
        'all_services': all_services,
        # 'is_export': False, # برای اینکه در پیش‌نمایش جنگو، هدر و فوتر زنده رندر شوند
        'is_export': request.GET.get('export') == 'true',
    }
    
    return render(request, 'landing.html', context)