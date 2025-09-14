from django.contrib import admin
from .models import DownloadLog

@admin.register(DownloadLog)
class DownloadLogAdmin(admin.ModelAdmin):
    list_display = ('platform', 'status', 'created_at', 'ip_address')
    list_filter = ('platform', 'status')
    search_fields = ('url', 'ip_address')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

# Register your models here.