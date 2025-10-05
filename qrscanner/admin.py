from django.contrib import admin
from .models import QRCodeScan, ScanEvent

@admin.register(QRCodeScan)
class QRCodeScanAdmin(admin.ModelAdmin):
    list_display = ['scan_id', 'decoded_text_preview', 'views_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['scan_id', 'decoded_text', 'secret_code']
    readonly_fields = ['scan_id', 'secret_code', 'created_at', 'views_count']
    
    def decoded_text_preview(self, obj):
        return obj.decoded_text[:50] + '...' if len(obj.decoded_text) > 50 else obj.decoded_text
    decoded_text_preview.short_description = 'Decoded Text'

@admin.register(ScanEvent)
class ScanEventAdmin(admin.ModelAdmin):
    list_display = ['scan', 'timestamp', 'ip_address', 'user_agent_preview']
    list_filter = ['timestamp']
    search_fields = ['scan__scan_id', 'ip_address']
    readonly_fields = ['scan', 'timestamp', 'ip_address', 'user_agent', 'referrer']
    
    def user_agent_preview(self, obj):
        return obj.user_agent[:50] + '...' if len(obj.user_agent) > 50 else obj.user_agent
    user_agent_preview.short_description = 'User Agent'
