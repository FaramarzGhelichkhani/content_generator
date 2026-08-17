# taxonomy/models.py
from django.db import models
from core.models import Project
from seoengine.settings import MEDIA_ROOT
import os 

class ServiceType(models.Model):
    class Code(models.TextChoices):
        CREATE_REMOTE = "create_remote", "ساخت ریموت/سوییچ/کلید"
        COPY_REMOTE = "copy_remote", "کپی ریموت (یدک)"
        REPAIR_REMOTE = "repair_remote", "تعمیر ریموت"
        CAR_UNLOCK = "car_unlock", "بازکردن درب خودرو"
        SELL_REMOTE = "sell_remote", "فروش ریموت"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="services")
    code = models.CharField(max_length=50, choices=Code.choices)
    name = models.CharField(max_length=100)
    slug = models.SlugField(allow_unicode=True)
    root_keyword = models.CharField(max_length=255, blank=True, verbose_name="کلیدواژه ریشه")
    description = models.TextField(blank=True)
    modifier_keywords = models.JSONField(default=list, blank=True, verbose_name="مودیفایرها")
    is_active = models.BooleanField(default=True)
    is_ecommerce = models.BooleanField(default=False)

    class Meta:
        unique_together = ("project", "slug")
        indexes = [
            models.Index(fields=["project", "code"]),
            models.Index(fields=["project", "slug"]),
        ]

    def __str__(self):
        return self.name
    
class TaxonomyNode(models.Model):
    class Kind(models.TextChoices):
        BRAND = "brand", "Brand"
        MODEL = "model", "Model"
        CITY = "city", "City"
        EDUCATIONAL = "educational", "Educational"
        OTHER = "other", "Other"

    project = models.ForeignKey('core.Project', on_delete=models.CASCADE, related_name="taxonomy_nodes")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, allow_unicode=True)
    is_pillar_eligible = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    meta = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("project", "kind", "parent", "slug")
        indexes = [
            models.Index(fields=["project", "kind"]),
            models.Index(fields=["project", "parent"]),
            models.Index(fields=["project", "slug"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.kind})"
    
    # متدهای کمکی برای دریافت راحت تصاویر
    def get_product_image(self):
        return self.images.filter(image_type=TaxonomyImage.ImageType.PRODUCT).first()

    def get_poster_image(self):
        return self.images.filter(image_type=TaxonomyImage.ImageType.POSTER).first()

class TaxonomyImage(models.Model):
    """مدل جدید برای مدیریت تصاویر چندگانه موجودیت‌ها"""
    class ImageType(models.TextChoices):
        PRODUCT = "product", "تصویر محصول (فروشگاهی)"
        POSTER = "poster", "پوستر (مقالات و کلاسترها)"

    taxonomy = models.ForeignKey(
        'TaxonomyNode', # فرض بر این است که مدل TaxonomyNode وجود دارد
        on_delete=models.CASCADE, 
        related_name="images"
    )
    image_type = models.CharField(max_length=20, choices=ImageType.choices)
    
    image = models.ImageField(
        upload_to='taxonomy_images/', 
        null=True, 
        blank=True,
        verbose_name="تصویر",
        help_text="تصویر خود را از اینجا آپلود کنید."
    )

    wp_attachment_id = models.PositiveIntegerField(
        null=True, blank=True, 
        verbose_name="آیدی تصویر در وردپرس (خودکار)"
    )
    wp_image_url = models.URLField(
        max_length=500, null=True, blank=True,
        verbose_name="لینک وردپرس تصویر (خودکار)"
    )

    class Meta:
        # جلوگیری از آپلود دو تصویر هم‌نوع برای یک موجودیت
        unique_together = ("taxonomy", "image_type")

    def __str__(self):
        return f"{self.taxonomy.name} - {self.get_image_type_display()}"

    def reset_wp_image_sync(self):
        self.wp_attachment_id = None
        self.wp_image_url = None
        self.save()
