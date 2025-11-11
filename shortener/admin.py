from django.contrib import admin
from .models import ShortURL, ClickEvent

@admin.register(ShortURL)
class ShortURLAdmin(admin.ModelAdmin):
    list_display = ['short_code', 'original_url', 'clicks', 'created_at']
    list_filter = ['created_at']
    search_fields = ['short_code', 'original_url']
    readonly_fields = ['short_code', 'secret_code', 'created_at', 'clicks']

@admin.register(ClickEvent)
class ClickEventAdmin(admin.ModelAdmin):
    list_display = ['short_url', 'ip_address', 'timestamp']
    list_filter = ['timestamp']
    readonly_fields = ['timestamp']

