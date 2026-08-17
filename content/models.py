# conten/models.py
from django.db import models

from core.models import Project, IntentType
from taxonomy.models import ServiceType, TaxonomyNode


class Keyword(models.Model):
    class Status(models.TextChoices):
        CLASSIFIED = "classified", "Classified"
        ARCHIVED = "archived", "Archived"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="keywords")
    text = models.CharField(max_length=255, verbose_name="کلمه کلیدی")
    normalized_text = models.CharField(max_length=255, db_index=True, blank=True)
    is_pillar = models.BooleanField(
        default=False, 
        verbose_name="آیا این کلیدواژه پیلار است؟"
    )
    parent_keyword = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_keywords",
        verbose_name="کلیدواژه پیلار والد",
        help_text="اگر این کلاستر است، پیلار والد آن را انتخاب کنید."
    )

    # منطق معنایی اینجا می‌ماند
    service = models.ForeignKey(
        ServiceType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="keywords",
        verbose_name="نوع خدمت",
    )
    intent = models.ForeignKey(
        IntentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="keywords",
        verbose_name="نیت کاربر",
    )

    # کلیدواژه‌های کمکی برای پرامپت ایجنت
    extra_keywords_text = models.TextField(
        blank=True,
        verbose_name="کلیدواژه‌های کمکی",
        help_text="به صورت comma-separated",
    )

    search_volume = models.PositiveIntegerField(default=0)
    keyword_difficulty = models.PositiveIntegerField(default=0)
    cpc = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    priority_score = models.IntegerField(default=0)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CLASSIFIED)
    source = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("project", "text")
        indexes = [
            models.Index(fields=["project", "service", "intent"]),
            models.Index(fields=["project", "status"]),
            models.Index(fields=["project", "normalized_text"]),
        ]

    def save(self, *args, **kwargs):
        if not self.normalized_text:
            self.normalized_text = self.text.strip().lower()
        super().save(*args, **kwargs)

    @property
    def extra_keywords_list(self):
        if not self.extra_keywords_text:
            return []
        return [x.strip() for x in self.extra_keywords_text.split(",") if x.strip()]

    def __str__(self):
        return f"{self.text} ({self.project.name})"

class PageBrief(models.Model):
    class Status(models.TextChoices):
        GENERATED = "generated", "Generated"
        NEEDS_UPDATE = "needs_update", "Needs Update"

    class PageType(models.TextChoices):
        PILLAR = "pillar", "Pillar"
        CLUSTER = "cluster", "Cluster"
        EDUCATIONAL = "educational", "Educational"
        SHOP = "shop", "Shop"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="page_briefs")

    # هر pagebrief از روی یک keyword seed ساخته می‌شود
    keyword = models.ForeignKey(
        Keyword,
        on_delete=models.CASCADE,
        related_name="page_briefs",
        verbose_name="کلیدواژه مبنا",
    )

    # برای صفحات لایه 1/2/3؛ لایه 0 می‌تواند null باشد یا city داشته باشد
    entity = models.ForeignKey(
        TaxonomyNode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="page_briefs",
        verbose_name="موجودیت",
    )

    parent_page = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children_pages",
        verbose_name="صفحه والد",
    )

    page_type = models.CharField(max_length=20, choices=PageType.choices)
    page_level = models.PositiveSmallIntegerField(default=0, verbose_name="سطح صفحه")

    url_path = models.CharField(max_length=500)
    canonical_url = models.URLField(blank=True)

    target_word_count = models.PositiveIntegerField(default=1500)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.GENERATED)
    content_version = models.PositiveIntegerField(default=1)

    is_active = models.BooleanField(default=True)
    locked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_regenerated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("project", "url_path")
        constraints = [
            models.UniqueConstraint(
                fields=["project", "entity", "keyword", "page_level"],
                name="uniq_entity_pagebrief_per_entity_level",
            ),
        ]    

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    @property
    def full_url(self):
        # if self.canonical_url:
        #     return self.canonical_url
        return f"{self.project.base_domain.rstrip('/')}{self.url_path}"

    def __str__(self):
        entity_part = f" - {self.entity}" if self.entity else ""
        return f"{self.keyword.text}{entity_part} (L{self.page_level})"

class PageContent(models.Model):
    class GenerationStatus(models.TextChoices):
        PENDING = "PN", "Pending"
        PLANNING = "PL", "Planning"        # ایجنت‌های پلنر در حال ساخت بریف و آوت‌لاین هستند
        WRITING = "WR", "Writing"          # ایجنت رایتر در حال نگارش بلوک‌هاست
        REVIEWING = "RV", "Reviewing"      # ایجنت سئو در حال ممیزی و لینک‌سازی است
        COMPLETED = "CM", "Completed"
        FAILED = "FL", "Failed"

    class PublishStatus(models.TextChoices):
        DRAFT = "DR", "Draft"
        PUBLISHED = "PB", "Published"
        NEEDS_UPDATE = "NU", "Needs Update"

    page_brief = models.OneToOneField('PageBrief', on_delete=models.CASCADE, related_name="content")

    # خروجی‌های سئویی و متا (تولید شده توسط ایجنت)
    slug = models.SlugField(max_length=255, allow_unicode=True, null=True, blank=True)
    seo_title = models.CharField(max_length=255, blank=True)
    h1 = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=320, blank=True)
    focus_keyword = models.CharField(max_length=128, blank=True, null=True)

    # --------------------------------------------------------
    # معماری محتوای بلوک‌محور (Block-Based Content Architecture)
    # --------------------------------------------------------
    outline_json = models.JSONField(default=dict, blank=True, help_text="ساختار تیترها و لیست بلوک‌های برنامه‌ریزی شده")
    
    # فیلد جدید: ایجنت محتوا را تکه تکه در این فیلد می‌نویسد
    blocks_json = models.JSONField(default=list, blank=True, help_text="آرایه بلوک‌های محتوایی (hero, table, main_section, ...)")
    
    # همان body_content سابق: چسباندن بلوک‌ها برای ارسال به وردپرس
    compiled_body = models.TextField(blank=True, help_text="خروجی نهایی و یکپارچه HTML برای ارسال به سایت")

    # داده‌های ساختاریافته تکمیلی
    faq_json = models.JSONField(default=list, blank=True)
    schema_json = models.JSONField(default=dict, blank=True)
    seo_report = models.JSONField(
        default=dict, blank=True, null=True,
        verbose_name="گزارش تفصیلی ممیزی سئو"
    )
    # --------------------------------------------------------
    # وضعیت و رهگیری ایجنت‌ها
    # --------------------------------------------------------
    generation_status = models.CharField(
        max_length=2,
        choices=GenerationStatus.choices,
        default=GenerationStatus.PENDING,
    )
    publish_status = models.CharField(
        max_length=2,
        choices=PublishStatus.choices,
        default=PublishStatus.DRAFT,
    )

    # فیلدهای جدید برای سیستم Multi-Agent و کنترل کیفیت
    seo_score = models.IntegerField(default=0, help_text="نمره تایید لایه سئو (از 100)")
    iterations = models.PositiveIntegerField(default=0, help_text="تعداد دفعات رد شدن و بازنویسی محتوا")

    target_server_post_id = models.CharField(max_length=50, blank=True, null=True)
    target_url = models.URLField(blank=True, null=True)

    generated_by = models.CharField(max_length=100, blank=True, help_text="مدل استفاده شده (مثلا gpt-4o یا claude-3)")
    generation_error = models.TextField(blank=True)
    
    generated_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.page_brief.keyword.text if self.page_brief else 'No Brief'} - {self.get_publish_status_display()}"
    
class InternalLink(models.Model):
    class RelationType(models.TextChoices):
        VERTICAL = "vertical", "Vertical"
        HORIZONTAL = "horizontal", "Horizontal"
        EDUCATIONAL = "educational", "Educational"
        RELATED = "related", "Related"

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        APPLIED = "applied", "Applied"
        IGNORED = "ignored", "Ignored"
        OBSOLETE = "obsolete", "Obsolete"

    source_page = models.ForeignKey(PageBrief, on_delete=models.CASCADE, related_name="outbound_links")
    target_page = models.ForeignKey(PageBrief, on_delete=models.CASCADE, related_name="inbound_links")
    anchor_text = models.CharField(max_length=150)

    relation_type = models.CharField(max_length=20, choices=RelationType.choices, default=RelationType.RELATED)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)

    confidence = models.PositiveSmallIntegerField(default=0)
    source_reason = models.TextField(blank=True)

    is_applied_on_server = models.BooleanField(default=False)
    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("source_page", "target_page", "anchor_text")
        indexes = [
            models.Index(fields=["source_page", "status"]),
            models.Index(fields=["target_page", "status"]),
            models.Index(fields=["relation_type"]),
        ]

    def __str__(self):
        return f"{self.source_page} -> {self.target_page}"