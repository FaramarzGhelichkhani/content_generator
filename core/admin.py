# core/admin.py
from django.contrib import admin
from .models import Project, IntentType

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_domain', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'base_domain')
    ordering = ('-created_at',)

@admin.register(IntentType)
class IntentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)