from django.contrib import admin, messages
from core.models import Project
from content.models import Keyword, PageBrief, PageContent, InternalLink
from content.services.pagebrief_sync import sync_project
from generation.services.elementor_publisher import publish_direct_elementor
from generation.services.orchestrator import run_orchestrator_pipeline
from django.utils.html import format_html, mark_safe
from generation.services.wordpress_publisher import publish_to_wordpress

@admin.register(PageBrief)
class PageBriefAdmin(admin.ModelAdmin):
    list_display = ("id", "keyword", "entity", "page_level", "page_type", "status", "updated_at")
    list_filter = ("page_level", "page_type", "status", "is_active", "locked")
    search_fields = ("keyword__text", "entity__name", "url_path")
    autocomplete_fields = ("project", "keyword", "entity", "parent_page")
    readonly_fields = ("created_at", "updated_at", "last_regenerated_at")

    fieldsets = (
        ("Main", {"fields": ("project", "keyword", "entity", "parent_page")}),
        ("URL", {"fields": ("page_level", "page_type", "url_path", "canonical_url")}),
        ("Status", {"fields": ("target_word_count", "status", "content_version", "is_active", "locked")}),
        ("Meta", {"fields": ("created_at", "updated_at", "last_regenerated_at")}),
    )

@admin.action(description="🔄 ریست کامل محتوی (شروع مجدد از صفر مطلق)")
def reset_page_content_pipeline(modeladmin, request, queryset):
    """
    پاک‌سازی کامل تمام فیلدهای خروجی و ساختاری ایجنت‌ها برای رکوردهای انتخابی
    """
    rows_updated = queryset.update(
        slug="",
        seo_title="",
        h1="",
        meta_description="",
        outline_json={},
        blocks_json=[],
        compiled_body="",
        faq_json=[],
        schema_json={},
        generation_status=PageContent.GenerationStatus.PENDING,
        publish_status=PageContent.PublishStatus.DRAFT,
        seo_score=0,
        iterations=0,
        generation_error="",
        generated_at=None
    )
    
    modeladmin.message_user(
        request, 
        f"فرآیند تولید محتوا برای {rows_updated} رکورد انتخابی با موفقیت کاملاً ریست و آماده شروع مجدد شد.", 
        level=messages.SUCCESS
    )

@admin.action(description="🚀 تولید محتوای هوشمند (حداکثر ۵ رکورد انتخابی)")
def generate_ai_content(modeladmin, request, queryset):
    if queryset.count() > 5:
        modeladmin.message_user(request, "لطفاً حداکثر ۵ رکورد را انتخاب کنید.", level=messages.ERROR)
        return

    pending_qs = queryset.exclude(generation_status=PageContent.GenerationStatus.FAILED)
    if not pending_qs.exists():
        modeladmin.message_user(request, "رکوردهای انتخابی قبلاً با موفقیت تکمیل شده‌اند.", level=messages.WARNING)
        return

    results = run_orchestrator_pipeline(pending_qs)
    for title, status in results:
        modeladmin.message_user(request, f"{title}: {status}", level=messages.SUCCESS)

@admin.action(description="🌐 ارسال به وردپرس (حداکثر ۱۰ رکورد)")
def push_to_wp_action(modeladmin, request, queryset):
    if queryset.count() > 10:
        modeladmin.message_user(request, "لطفاً برای جلوگیری از تایم‌اوت، حداکثر ۱۰ رکورد انتخاب کنید.", level=messages.ERROR)
        return

    # فقط مقالاتی که کامل شده‌اند و هنوز منتشر نشده‌اند را می‌گیریم
    ready_qs = queryset.filter(
        generation_status=PageContent.GenerationStatus.COMPLETED
    ).exclude(publish_status=PageContent.PublishStatus.PUBLISHED)

    if not ready_qs.exists():
        modeladmin.message_user(request, "رکوردهای انتخابی یا کامل نشده‌اند یا قبلاً ارسال شده‌اند.", level=messages.WARNING)
        return

    success_count = 0
    for page in ready_qs:
        success, msg = publish_to_wordpress(page)
        if success:
            success_count += 1
            modeladmin.message_user(request, f"{page.page_brief.keyword.text}: {msg}", level=messages.SUCCESS)
        else:
            modeladmin.message_user(request, f"{page.page_brief.keyword.text}: {msg}", level=messages.ERROR)

@admin.action(description="انتشار در وردپرس (با طراحی داینامیک المنتور)")
def publish_to_wp_elementor(self, request, queryset):
    success_count = 0
    error_messages = []
    
    for page in queryset:
        # فقط صفحاتی که نگارش آن‌ها تکمیل شده را منتشر کن
        if page.generation_status == PageContent.GenerationStatus.COMPLETED:
            success, msg = publish_direct_elementor(page)
            if success:
                success_count += 1
            else:
                error_messages.append(f"{page.h1}: {msg}")
        else:
            error_messages.append(f"{page.h1}: محتوا هنوز توسط AI تکمیل نشده است.")
            
    if success_count > 0:
        self.message_user(request, f"{success_count} مقاله با ساختار المنتور در سایت منتشر شد.", messages.SUCCESS)
    if error_messages:
        for err in error_messages:
            self.message_user(request, err, messages.ERROR)

@admin.register(PageContent)
class PageContentAdmin(admin.ModelAdmin):
    list_display = ('page_brief', 'generation_status', 'publish_status', 'seo_score', 'iterations')
    list_filter = ('generation_status', 'publish_status', 'page_brief__entity__kind')
    search_fields = ('page_brief__entity__parent__name','page_brief__entity__name')
    actions = [generate_ai_content, reset_page_content_pipeline, push_to_wp_action, publish_to_wp_elementor]
    
    # اضافه کردن فیلد پیش‌نمایش به فرم ادمین
    readonly_fields = ('html_preview',)
    
    # فیلدبندی برای نمایش زیباتر در صفحه ویرایش
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('page_brief', 'generation_status', 'publish_status', 'seo_score', 'iterations')
        }),
        ('دیتای سئو', {
            'fields': ('slug', 'seo_title', 'h1', 'meta_description', 'focus_keyword')
        }),
        ('پیش‌نمایش محتوای تولید شده', {
            'fields': ('html_preview',),
            'classes': ('wide',)
        }),
        ('دیتای خام سیستمی', {
            'fields': ('outline_json', 'blocks_json', 'faq_json', 'schema_json','compiled_body', 'seo_report','generation_error'),
            'classes': ('collapse',) # این بخش را به صورت کشویی می‌بندیم تا شلوغ نشود
        }),
        ('اطلاعات صفحه', {
            'fields': ('target_server_post_id', 'target_url', ),
            'classes': ('collapse',)
        }),
    )

    def html_preview(self, obj):
            if obj.compiled_body:
                html_content = obj.compiled_body
                
                # ۱. استخراج و ساخت HTML تصاویر از موجودیت متصل
                images_html = ""
                try:
                    # فرض بر این است که brief با املای درست page_brief در مدل شما وجود دارد
                    if obj.page_brief and obj.page_brief.entity:
                        # فراخوانی تمام تصاویر متصل به این موجودیت
                        images = obj.page_brief.entity.images.all()
                        
                        for img in images:
                            if img.image: # اطمینان از اینکه فیلد عکس خالی نیست
                                images_html += f"""
                                <div style="text-align: center; margin: 25px 0;">
                                    <img src="{img.image.url}" alt="{img.image_type}" style="max-width: 100%; height: auto; border-radius: 8px; border: 1px solid #ddd; box-shadow: 0 4px 6px rgba(0,0,0,0.05);" />
                                    <div style="color: #888; font-size: 13px; margin-top: 5px;">{img.get_image_type_display()}</div>
                                </div>
                                """
                except AttributeError:
                    pass # اگر به هر دلیلی ریلیشن‌ها خالی بودند خطایی ندهد

                # ۲. تزریق تصاویر به داخل محتوا
                # اگر در محتوای شما جایگاه عکس با یک عبارت خاص مثل [IMAGE_BLOCK] مشخص شده باشد:
                placeholder = "[IMAGE_BLOCK]"
                if placeholder in html_content:
                    html_content = html_content.replace(placeholder, images_html)
                elif images_html:
                    # اگر پلیس‌هولدری نبود اما عکس وجود داشت، عکس‌ها را می‌اندازیم اول محتوا
                    html_content = images_html + html_content

                # ۳. استایل‌های اختصاصی برای رندر بی‌نقص و راست‌چین در پنل ادمین
                style = """
                <style>
                    .seo-preview-box { 
                        direction: rtl; 
                        text-align: right; 
                        background: #fdfdfd; 
                        padding: 30px; 
                        border-radius: 8px; 
                        border: 1px solid #ddd; 
                        font-family: Tahoma, Arial, sans-serif; 
                        line-height: 2; 
                        color: #222; 
                    }
                    .seo-preview-box h2 { 
                        color: #2D4B8C; 
                        border-bottom: 2px solid #eee; 
                        padding-bottom: 8px; 
                        margin-top: 35px; 
                    }
                    .seo-preview-box h3 { color: #444; margin-top: 25px; }
                    .seo-preview-box a { 
                        color: #e63946; 
                        text-decoration: underline; 
                        font-weight: bold; 
                        padding: 0 4px; 
                    }
                    .seo-preview-box ul, .seo-preview-box ol { margin-right: 20px; }
                    .seo-preview-box table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                    .seo-preview-box th, .seo-preview-box td { border: 1px solid #ddd; padding: 10px; text-align: right; }
                </style>
                """
                return format_html('{style}<div class="seo-preview-box">{body}</div>', style=mark_safe(style), body=mark_safe(html_content))
                
            return format_html('<span style="color: red;">محتوایی برای پیش‌نمایش وجود ندارد.</span>')

    html_preview.short_description = "پیش‌نمایش زنده مقاله"


@admin.action(description="Sync selected keywords to page briefs + page contents + links")
def sync_keywords_action(modeladmin, request, queryset):
    project_ids = queryset.values_list("project", flat=True).distinct()
    total = 0
    for pid in project_ids:
        project = Project.objects.get(id=pid)
        ids = list(queryset.filter(project=project).values_list("id", flat=True))
        result = sync_project(project, keyword_ids=ids, rebuild_links=True)
        total += len(result["root_pages"]) + len(result["entity_pages"]) + len(result["keyword_pages"])
    modeladmin.message_user(request, f"{total} page briefs processed.", level=messages.SUCCESS)


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ("text", "service", "intent","parent_keyword", "is_pillar", "priority_score")
    list_filter = ("service", "intent", "status")
    search_fields = ("text", "extra_keywords_text")
    actions = [sync_keywords_action]


@admin.register(InternalLink)
class InternalLinkAdmin(admin.ModelAdmin):

    list_display = (
        "source_page",
        "target_page",
        "relation_type",
        "is_applied_on_server",
    )

    list_filter = (
        "relation_type",
        "is_applied_on_server",
    )

    search_fields = (
        "anchor_text",
        'source_page__entity__parent__name','source_page__entity__name',
        'target_page__entity__parent__name','target_page__entity__name'
    )
