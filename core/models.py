# core/models.py
from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=100, verbose_name="نام پروژه")
    base_domain = models.URLField(verbose_name="دامنه اصلی")
    locale = models.CharField(max_length=20, default="fa-IR", verbose_name="زبان/لوکال")
    wp_api_url = models.URLField(blank=True, null=True, help_text="مثال: https://luxremote.com/wp-json/wp/v2")
    wp_username = models.CharField(max_length=100, blank=True, null=True, help_text="نام کاربری ادمین وردپرس")
    wp_app_password = models.CharField(max_length=100, blank=True, null=True, help_text="Application Password وردپرس")
    is_active = models.BooleanField(default=True)
    graph_version = models.PositiveIntegerField(default=1, verbose_name="نسخه گراف لینک")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class IntentType(models.Model):
    class Code(models.TextChoices):
        TRANSACTIONAL = "transactional", "Transactional"
        INFORMATIONAL = "informational", "Informational"
        COMMERCIAL = "commercial", "Commercial"
        LOCAL = "local", "Local"

    code = models.CharField(max_length=30, choices=Code.choices, unique=True)
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name