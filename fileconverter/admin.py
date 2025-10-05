from django.contrib import admin
from .models import Conversion

@admin.register(Conversion)
class ConversionAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'original_format', 'target_format', 'success', 'created_at']
    list_filter = ['success', 'original_format', 'target_format', 'created_at']
    search_fields = ['original_filename', 'converted_filename']
