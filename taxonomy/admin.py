from django.contrib import admin, messages
from core.models import Project
from taxonomy.models import TaxonomyImage, TaxonomyNode, ServiceType
from content.services.pagebrief_sync import sync_project


@admin.action(description="Sync selected entities to page briefs + page contents + links")
def sync_entities_action(modeladmin, request, queryset):
    project_ids = queryset.values_list("project", flat=True).distinct()
    total = 0
    for pid in project_ids:
        project = Project.objects.get(id=pid)
        ids = list(queryset.filter(project=project).values_list("id", flat=True))
        result = sync_project(project, entity_ids=ids, rebuild_links=True)
        total += len(result["root_pages"]) + len(result["entity_pages"]) + len(result["keyword_pages"])
    modeladmin.message_user(request, f"{total} page briefs processed.", level=messages.SUCCESS)

class TaxonomyImageInline(admin.TabularInline):
    model = TaxonomyImage
    extra = 1  # تعداد سطرهای خالی پیش‌فرض برای اضافه کردن عکس جدید
    max_num = 2  # چون کلا دو نوع عکس (Product و Poster) داریم
    
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
    actions = [sync_entities_action]

@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ("project", "name", "slug", "description", "root_keyword","is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
