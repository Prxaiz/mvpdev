from django.contrib import admin

from .models import Business, GeneratedContent, Lead, Website


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("name", "service", "city", "user", "slug")
    search_fields = ("name", "city", "service", "slug")


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("name", "business", "status", "source", "phone", "created_at")
    list_filter = ("status", "source")
    search_fields = ("name", "email", "phone")


@admin.register(GeneratedContent)
class GeneratedContentAdmin(admin.ModelAdmin):
    list_display = ("business", "kind", "created_at")
    search_fields = ("business__name",)


@admin.register(Website)
class WebsiteAdmin(admin.ModelAdmin):
    list_display = ("business", "generated_at")
