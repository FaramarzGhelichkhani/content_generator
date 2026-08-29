from django.contrib import admin, messages
from core.models import Project
from content.models import Keyword, PageBrief, PageContent, InternalLink
from generation.services.schema_generator import generate_advanced_schema
from generation.services.elementor_publisher import publish_direct_elementor
from django.utils.html import format_html, mark_safe
from generation.services.orchestrator import ContentOrchestratorService
import json
import re
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from generation.agents.prompt_manager import PromptManager, WriterOutput
from generation.utils.llm_manager import get_llm
import traceback

import logging
from django.db.models import QuerySet
from django.http import HttpRequest

from .models import PageContent
from .services.content_compiler import PageContentCompiler
from .services.deployer import FTPDeployer
from django import forms

logger = logging.getLogger(__name__)

@admin.register(PageBrief)
class PageBriefAdmin(admin.ModelAdmin):
    list_display = ("id", "keyword", "entity", "service_type__name", "location__name" ,"page_level", "page_type", "status", "updated_at")
    list_filter = ("page_level", "page_type", "status", "is_active", "locked")
    search_fields = ("keyword__text", "entity__name", "url_path")
    autocomplete_fields = ("project", "keyword", "entity", "parent_page")
    readonly_fields = ("created_at", "updated_at", "last_regenerated_at")

    fieldsets = (
        ("Main", {"fields": ("project", "keyword", "entity","service_type", "parent_page")}),
        ("URL", {"fields": ("page_level", "page_type", "url_path", "canonical_url")}),
        ("Status", {"fields": ("target_word_count", "status", "content_version", "is_active", "locked")}),
        ("Meta", {"fields": ("created_at", "updated_at", "last_regenerated_at")}),
    )

# @admin.action(description="🔄 ریست کامل محتوی (شروع مجدد از صفر مطلق)")
# def reset_page_content_pipeline(modeladmin, request, queryset):
#     """
#     پاک‌سازی کامل تمام فیلدهای خروجی و ساختاری ایجنت‌ها برای رکوردهای انتخابی
#     """
#     rows_updated = queryset.update(
#         slug="",
#         seo_title="",
#         h1="",
#         meta_description="",
#         outline_json={},
#         blocks_json=[],
#         compiled_body="",
#         faq_json=[],
#         schema_json={},
#         generation_status=PageContent.GenerationStatus.PENDING,
#         publish_status=PageContent.PublishStatus.DRAFT,
#         seo_score=0,
#         iterations=0,
#         generation_error="",
#         generated_at=None
#     )
    
#     modeladmin.message_user(
#         request, 
#         f"فرآیند تولید محتوا برای {rows_updated} رکورد انتخابی با موفقیت کاملاً ریست و آماده شروع مجدد شد.", 
#         level=messages.SUCCESS
#     )

# @admin.action(description="🚀 تولید محتوای هوشمند (حداکثر ۵ رکورد انتخابی)")
# def generate_ai_content(modeladmin, request, queryset):
#     if queryset.count() > 5:
#         modeladmin.message_user(request, "لطفاً حداکثر ۵ رکورد را انتخاب کنید.", level=messages.ERROR)
#         return

#     pending_qs = queryset.exclude(generation_status=PageContent.GenerationStatus.FAILED)
#     if not pending_qs.exists():
#         modeladmin.message_user(request, "رکوردهای انتخابی قبلاً با موفقیت تکمیل شده‌اند.", level=messages.WARNING)
#         return

#     results = run_orchestrator_pipeline(pending_qs)
#     for title, status in results:
#         modeladmin.message_user(request, f"{title}: {status}", level=messages.SUCCESS)

# @admin.action(description="🌐 ارسال به وردپرس (حداکثر ۱۰ رکورد)")
# def push_to_wp_action(modeladmin, request, queryset):
#     if queryset.count() > 10:
#         modeladmin.message_user(request, "لطفاً برای جلوگیری از تایم‌اوت، حداکثر ۱۰ رکورد انتخاب کنید.", level=messages.ERROR)
#         return

#     # فقط مقالاتی که کامل شده‌اند و هنوز منتشر نشده‌اند را می‌گیریم
#     ready_qs = queryset.filter(
#         generation_status=PageContent.GenerationStatus.COMPLETED
#     ).exclude(publish_status=PageContent.PublishStatus.PUBLISHED)

#     if not ready_qs.exists():
#         modeladmin.message_user(request, "رکوردهای انتخابی یا کامل نشده‌اند یا قبلاً ارسال شده‌اند.", level=messages.WARNING)
#         return

#     success_count = 0
#     for page in ready_qs:
#         success, msg = publish_to_wordpress(page)
#         if success:
#             success_count += 1
#             modeladmin.message_user(request, f"{page.page_brief.keyword.text}: {msg}", level=messages.SUCCESS)
#         else:
#             modeladmin.message_user(request, f"{page.page_brief.keyword.text}: {msg}", level=messages.ERROR)

# @admin.action(description="انتشار در وردپرس (با طراحی داینامیک المنتور)")
# def publish_to_wp_elementor(self, request, queryset):
#     success_count = 0
#     error_messages = []
    
#     for page in queryset:
#         # فقط صفحاتی که نگارش آن‌ها تکمیل شده را منتشر کن
#         if page.generation_status == PageContent.GenerationStatus.COMPLETED:
#             success, msg = publish_direct_elementor(page)
#             if success:
#                 success_count += 1
#             else:
#                 error_messages.append(f"{page.h1}: {msg}")
#         else:
#             error_messages.append(f"{page.h1}: محتوا هنوز توسط AI تکمیل نشده است.")
            
#     if success_count > 0:
#         self.message_user(request, f"{success_count} مقاله با ساختار المنتور در سایت منتشر شد.", messages.SUCCESS)
#     if error_messages:
#         for err in error_messages:
#             self.message_user(request, err, messages.ERROR)


class PageContentAdminForm(forms.ModelForm):
    class Meta:
        model = PageContent
        fields = '__all__'
        widgets = {
            # تغییر ویجت به Textarea و تنظیم ابعاد باکس (تعداد سطر و ستون)
            'seo_title': forms.Textarea(attrs={'rows': 2, 'cols': 90}),
            'h1': forms.Textarea(attrs={'rows': 2, 'cols': 90}),
            'meta_description': forms.Textarea(attrs={'rows': 4, 'cols': 90}),
        }

@admin.register(PageContent)
class PageContentAdmin(admin.ModelAdmin):
    form = PageContentAdminForm
    list_display = ('id','view_generated_page','page_brief__keyword__text','page_brief__entity__name', 'page_brief__location__name',
                    'page_brief__page_type', 'page_brief__page_level',
                    'generation_status', 'publish_status', 'seo_score', 'iterations')
    list_filter = ('generation_status', 'publish_status', 'page_brief__entity__kind', 'page_brief__page_level')
    search_fields = ('page_brief__entity__parent__name','page_brief__entity__name')
    actions = ['run_ai_orchestrator', 'reset_to_pending', 'regenerate_hero_only' ,'reset_schema' ,'compile_content_to_html']
    
    # اضافه کردن فیلد پیش‌نمایش به فرم ادمین
    readonly_fields = ('html_preview', 'view_generated_page',)
    
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
            'classes': ('collapse',)
        }),
        (' خروجی', {"fields":('compiled_body',), 'classes': ('collapse',)})
        ,('دیتای خام سیستمی', {
            'fields': ('outline_json', 'blocks_json', 'faq_json', 'schema_json', 'seo_report','generation_error'),
            'classes': ('collapse',) # این بخش را به صورت کشویی می‌بندیم تا شلوغ نشود
        }),
        ('اطلاعات صفحه', {
            'fields': ('target_server_post_id', 'target_url', ),
            'classes': ('collapse',)
        }),
        
    )

    def get_keyword(self, obj):
            return obj.page_brief.keyword.text if obj.page_brief and obj.page_brief.keyword else "No Keyword"
    get_keyword.short_description = "کلمه کلیدی"
    
    @admin.action(description='🚀 اجرای ارکستراتور AI (تولید کامل محتوا)')
    def run_ai_orchestrator(self, request, queryset):
        success_count = 0
        failed_count = 0
        
        for content_obj in queryset:
            # فقط صفحاتی که Completed نشده‌اند را ران می‌کنیم
            if content_obj.generation_status != PageContent.GenerationStatus.COMPLETED:
                service = ContentOrchestratorService(content_obj)
                is_success = service.run()
                
                if is_success:
                    success_count += 1
                else:
                    failed_count += 1

        self.message_user(
            request, 
            f"عملیات پایان یافت: {success_count} صفحه موفق، {failed_count} صفحه خطا/رد شده.",
            level=messages.SUCCESS if failed_count == 0 else messages.WARNING
        )
    
    @admin.action(description='🔄 بازنشانی وضعیت به PENDING (جهت تولید مجدد)')
    def reset_to_pending(self, request, queryset):
        queryset.update(
            generation_status=PageContent.GenerationStatus.PENDING,
            compiled_body="",
            blocks_json=[],
            outline_json={},
            seo_score=0,
            iterations=0,
            generation_error=""
        )
        self.message_user(request, "صفحات انتخاب شده ریست شدند.", level=messages.SUCCESS)

    @admin.action(description='✍️ بازنویسی اختصاصی بلوک مقدمه (Hero) با کپی‌رایتر')
    def regenerate_hero_only(self, request, queryset):
        # استفاده از دمای 0.6 برای افزایش خلاقیت و لحن تبلیغاتی کپی‌رایتر
        hero_llm = get_llm(model_name="gemini-3.5-flash-lite", temperature=0.6).with_structured_output(WriterOutput)
        
        success_count = 0
        failed_count = 0
        
        for obj in queryset:
            try:
                # ۱. پیدا کردن دیتای خام هیرو در outline_json (برای گرفتن تارگت کیوردها و طول کلمات)
                outline_blocks = obj.outline_json.get('blocks', []) if isinstance(obj.outline_json, dict) else []
                hero_outline_data = None
                
                for b in outline_blocks:
                    if b.get("block_type") == "hero":
                        hero_outline_data = b
                        break
                
                if not hero_outline_data:
                    failed_count += 1
                    continue
                
                # ۲. ساخت پرامپت مخصوص هیرو با دیتای خام
                pm = PromptManager(obj.page_brief)
                prompt = pm.get_hero_writer_prompt(current_block=hero_outline_data, focus_keyword=obj.focus_keyword)
                
                # ۳. فراخوانی ایجنت کپی‌رایتر
                hero_out = hero_llm.invoke(prompt.to_messages())
                new_hero_content = hero_out.content
                
                # ۴. جایگذاری محتوای جدید در blocks_json
                blocks = obj.blocks_json
                hero_updated = False
                
                for block in blocks:
                    if block.get("block_type") == "hero":
                        block["content"] = new_hero_content
                        hero_updated = True
                        break
                
                # ۵. ذخیره نهایی در دیتابیس
                if hero_updated:
                    obj.blocks_json = blocks
                    obj.save()
                    success_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                print(f"Error regenerating hero for Page {obj.id}: {traceback.format_exc()}")
                failed_count += 1
                
        self.message_user(
            request, 
            f"عملیات بازنویسی هیرو پایان یافت: {success_count} صفحه با موفقیت آپدیت شد. ({failed_count} صفحه ناموفق)",
            level=messages.SUCCESS if failed_count == 0 else messages.WARNING
        )

    @admin.action(description="رندر کدهای HTML، ساخت فایل استاتیک و ارسال به سایت")
    def compile_content_to_html(self, request: HttpRequest, queryset: QuerySet) -> None:
        
        compiler = PageContentCompiler()
        deployer = FTPDeployer() # نمونه‌سازی از کلاس آپلودر
        
        success_count = 0
        failed_count = 0

        for page in queryset:
            try:
                # ۱. رندر و ذخیره در دیتابیس
                is_compiled = compiler.compile_and_save(page)
                
                if is_compiled:
                    page.refresh_from_db()
                    
                    # ۲. تولید فایل استاتیک روی هارد لوکال (مسیر فایل برگردانده می‌شود)
                    local_file_path = compiler.export_to_static_files(page)
                    
                    # ۳. استخراج مسیر پوشه روی سرور (مثل honda/click)
                    remote_dir = page.page_brief.url_path.strip("/")
                    
                    # ۴. ارسال فایل به دایرکت‌ادمین عبر FTP
                    is_uploaded = deployer.upload_file(local_file_path, remote_dir)
                    
                    if is_uploaded:
                        # ۵. تغییر وضعیت به منتشر شده
                        page.publish_status = PageContent.PublishStatus.PUBLISHED
                        page.save(update_fields=['publish_status', 'updated_at'])
                        success_count += 1
                    else:
                        # اگر آپلود فیل شد، وضعیت منتشر شده نمی‌گیرد
                        logger.error("Failed to FTP upload PageContent ID %d", page.pk)
                        failed_count += 1
                else:
                    failed_count += 1

            except ValueError as ve:
                logger.error("Validation error for PageContent ID %d: %s", page.pk, ve)
                failed_count += 1
            except Exception as e:
                logger.error("Critical error for PageContent ID %d: %s", page.pk, e)
                failed_count += 1

        if success_count > 0:
            self.message_user(
                request,
                f"پروسه موفق: {success_count} صفحه رندر و با موفقیت روی سرور سایت آپلود شدند.",
                level=messages.SUCCESS
            )
            
        if failed_count > 0:
            self.message_user(
                request,
                f"عملیات برای {failed_count} صفحه با خطا مواجه شد. (مشکل در رندر یا خطای اتصال FTP)",
                level=messages.ERROR
            )

    def html_preview(self, obj):
        # بررسی اینکه blocks_json وجود داشته باشد و خالی نباشد
        if obj.blocks_json and isinstance(obj.blocks_json, list) and len(obj.blocks_json) > 0:
            html_content = ""
            
            # ۱. استخراج و ساخت HTML تصاویر از موجودیت متصل
            images_html = ""
            try:
                if obj.page_brief and obj.page_brief.entity:
                    images = obj.page_brief.entity.images.all()
                    for img in images:
                        if img.image:
                            images_html += f"""
                            <div style="text-align: center; margin: 25px 0;">
                                <img src="{img.image.url}" alt="{img.get_image_type_display()}" style="max-width: 100%; height: auto; border-radius: 8px; border: 1px solid #ddd; box-shadow: 0 4px 6px rgba(0,0,0,0.05);" />
                                <div style="color: #888; font-size: 13px; margin-top: 5px;">{img.get_image_type_display()}</div>
                            </div>
                            """
            except AttributeError:
                pass 

            image_injected = False

            # ۲. پیمایش بلوک‌های تایید شده و ساخت HTML نهایی
            for block in obj.blocks_json:
                b_type = block.get("block_type", "")
                b_content = block.get("content", "")
                
                # بلوک تصویر
                if b_type == "image":
                    if images_html:
                        html_content += images_html
                        image_injected = True
                    else:
                        # استخراج alt از محتوا (حذف تگ‌های احتمالی که لینک‌ساز اضافه کرده)
                        clean_alt = re.sub(r'<[^>]+>', '', b_content).strip()
                        html_content += f'<div style="text-align:center; padding:20px; background:#f5f5f5; border:1px dashed #ccc; margin:20px 0; color:#666;">[جایگاه تصویر: {clean_alt}]</div>'
                
                # بلوک سوالات متداول (تبدیل JSON به HTML برای پیش‌نمایش)
                elif b_type == "faq":
                    try:
                        # حذف تگ div احتمالی که ایجنت لینک‌ساز دور آن انداخته است
                        clean_json_str = re.sub(r'^<div[^>]*>|</div>$', '', b_content.strip(), flags=re.IGNORECASE).strip()
                        faq_data = json.loads(clean_json_str)
                        
                        html_content += "<div class='faq-preview-section'><h3>❓ سوالات متداول</h3>"
                        for item in faq_data:
                            html_content += f"<div style='margin-bottom: 15px; background: #fff; padding: 15px; border-radius: 5px; border: 1px solid #eee;'><strong>{item.get('question', '')}</strong><p style='margin-top: 8px; margin-bottom:0;'>{item.get('answer', '')}</p></div>"
                        html_content += "</div>"
                    except (json.JSONDecodeError, TypeError):
                        html_content += b_content # اگر پارس نشد، خام رندر کن
                
                # بلوک مشخصات فنی (تبدیل JSON به Table)
                elif b_type == "specs":
                    try:
                        clean_json_str = re.sub(r'^<div[^>]*>|</div>$', '', b_content.strip(), flags=re.IGNORECASE).strip()
                        specs_data = json.loads(clean_json_str)
                        
                        html_content += "<div class='specs-preview-section'><h3>⚙️ مشخصات فنی</h3><table><tbody>"
                        for k, v in specs_data.items():
                            html_content += f"<tr><th>{k}</th><td>{v}</td></tr>"
                        html_content += "</tbody></table></div>"
                    except (json.JSONDecodeError, TypeError):
                        html_content += b_content
                
                # بلوک‌های متنی معمولی (hero, introduction, conclusion, ...)
                else:
                    html_content += b_content + "\n"

            # ۳. تزریق تصاویر اگر بلوک image توسط پلنر ساخته نشده بود اما عکس داشتیم (Fallback)
            if images_html and not image_injected:
                html_content = images_html + html_content

            # ۴. استایل‌های اختصاصی برای رندر بی‌نقص و راست‌چین در پنل ادمین
            style = """
            <style>
                .seo-preview-box { 
                    direction: rtl; 
                    text-align: right; 
                    background: #fcfcfc; 
                    padding: 30px; 
                    border-radius: 8px; 
                    border: 1px solid #e0e0e0; 
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
                .seo-preview-box table { width: 100%; border-collapse: collapse; margin: 20px 0; background: #fff; }
                .seo-preview-box th, .seo-preview-box td { border: 1px solid #ddd; padding: 12px; text-align: right; }
                .seo-preview-box th { background: #f7f7f7; width: 30%; }
            </style>
            """
            return format_html('{style}<div class="seo-preview-box">{body}</div>', style=mark_safe(style), body=mark_safe(html_content))
            
        return format_html('<span style="color: red;">محتوایی برای پیش‌نمایش وجود ندارد. (بلوک‌ها تولید نشده‌اند)</span>')

    html_preview.short_description = "پیش‌نمایش زنده مقاله"

    @admin.display(description='لینک مشاهده')
    def view_generated_page(self, obj: PageContent) -> str:
        """
        Generates a clickable HTML button to view the page on the frontend
        using the url_path defined in the associated PageBrief.
        """
        if not obj.page_brief or not obj.page_brief.url_path:
            return format_html('<span style="color: gray;">آدرس تنظیم نشده</span>')

        # اطمینان از وجود اسلش در ابتدای آدرس
        url = obj.page_brief.url_path
        if not url.startswith('/'):
            url = f'/{url}'

        if not obj.compiled_body:
            return format_html(
                '<span style="color: #ba1a1a;" title="ابتدا باید صفحه رندر شود">رندر نشده</span>'
            )

        return format_html(
            '<a href="{}" target="_blank" '
            'style="background: #006970; color: white; padding: 5px 5px; '
            'border-radius: 4px; text-decoration: none; font-size: 8px; font-weight: bold;">'
            'مشاهده صفحه'
            '</a>',
            url
        )

    @admin.action(description="ریستارت اسکیما")
    def reset_schema( self, request: HttpRequest, queryset: QuerySet) -> None:
        success_count = 0
        failed_count = 0
        
        for page in queryset:
            try:
                schemas_list = generate_advanced_schema(page.page_brief, page)
                page.schema_json = json.dumps(schemas_list, ensure_ascii=False)
                success_count =+ 1
                page.save()
            except ValueError as ve:
                logger.error("Validation error for PageContent ID %d: %s", page.pk, ve)
                failed_count += 1
            except Exception as e:
                logger.error("Critical error for PageContent ID %d: %s", page.pk, e)
                failed_count += 1
        if success_count > 0:
                    self.message_user(
                        request,
                        f"پروسه موفق: {success_count} صفحه اسکیما ریستارت شدند.",
                        level=messages.SUCCESS
                    )


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ("text", "intent","parent_keyword", "is_pillar", "priority_score")
    list_filter = ("intent", "status")
    search_fields = ("text", "extra_keywords_text")


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
