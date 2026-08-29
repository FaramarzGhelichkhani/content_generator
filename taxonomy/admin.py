from django.contrib import admin, messages
from content.services.model_page_generator import ModelPageGeneratorService
from taxonomy.models import TaxonomyImage, TaxonomyNode, ServiceType, Location




class TaxonomyImageInline(admin.TabularInline):
    model = TaxonomyImage
    extra = 1  # تعداد سطرهای خالی پیش‌فرض برای اضافه کردن عکس جدید
    max_num = 4  # چون کلا دو نوع عکس (Product و Poster) داریم
    
    # فیلدهایی که توسط ربات پر می‌شوند را فقط‌خواندنی می‌کنیم
    readonly_fields = ('wp_attachment_id', 'wp_image_url')
    
    # کلمه local_image_filename حذف شد و image جایگزین آن شد
    fields = ('image_type', 'image', 'wp_attachment_id', 'wp_image_url')

@admin.register(TaxonomyNode)
class TaxonomyNodeAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "project", "parent", "is_active", "sort_order")
    list_filter = ("kind", "project", "is_active")
    search_fields = ("name", "slug")
    inlines = [TaxonomyImageInline]
    actions = ['generate_selected_model_pages']

    @admin.action(description='تولید صفحات و کلاسترها برای مدل‌های انتخاب‌شده')
    def generate_selected_model_pages(self, request, queryset):
        # فیلتر کردن تا اکشن فقط روی رکوردهایی که از نوع MODEL هستند اعمال شود
        model_nodes = queryset.filter(kind=TaxonomyNode.Kind.MODEL)
        
        if not model_nodes.exists():
            self.message_user(request, "هیچ مدلی (Model) در موارد انتخاب شده یافت نشد.", level=messages.WARNING)
            return
        try:
            # فراخوانی سرویس برای مدل‌های تیک‌خورده
            service = ModelPageGeneratorService(project_id=1)
            stats = service.process_models(model_nodes)
            
            self.message_user(
                request, 
                f'موفقیت‌آمیز: {stats["pages_created"]} صفحه جدید، {stats["pages_updated"]} آپدیت و {stats["links_created"]} لینک ایجاد شد.', 
                level=messages.SUCCESS
            )
        except Exception as e:
            self.message_user(request, f'خطا در تولید صفحات: {str(e)}', level=messages.ERROR)

@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ("project", "name", "slug", "description", "root_keyword","is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("project", "name", "slug", "parent")
    search_fields = ("name", "slug")
