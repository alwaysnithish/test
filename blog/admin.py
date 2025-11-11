# blog/admin.py - Complete file

from django.contrib import admin
from .models import BlogPost, Category, Tag, AuthorProfile, NewsletterSubscriber


# ==================== CATEGORY ADMIN ====================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)


# ==================== TAG ADMIN ====================
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)


# ==================== BLOG POST ADMIN ====================
@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'status', 'published_at', 'created_at')
    list_filter = ('status', 'category', 'created_at', 'published_at')
    search_fields = ('title', 'content', 'excerpt')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('tags',)
    date_hierarchy = 'published_at'
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'slug', 'content', 'excerpt', 'thumbnail')
        }),
        ('Classification', {
            'fields': ('category', 'tags')
        }),
        ('Publishing', {
            'fields': ('author', 'status', 'published_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)


# ==================== AUTHOR PROFILE ADMIN ====================
@admin.register(AuthorProfile)
class AuthorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'job_title', 'location', 'created_at')
    search_fields = ('user__username', 'user__email', 'bio', 'job_title')
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User Info', {
            'fields': ('user', 'job_title', 'location', 'bio')
        }),
        ('Profile Picture', {
            'fields': ('profile_picture',)
        }),
        ('Social Links', {
            'fields': ('website', 'twitter', 'facebook', 'linkedin', 'instagram')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ==================== NEWSLETTER SUBSCRIBER ADMIN ====================
@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'confirmed', 'is_active', 'subscribed_at')
    list_filter = ('confirmed', 'is_active', 'subscribed_at')
    search_fields = ('email',)
    readonly_fields = ('subscribed_at', 'confirmation_token')
    date_hierarchy = 'subscribed_at'
    
    actions = ['activate_subscribers', 'deactivate_subscribers']
    
    def activate_subscribers(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} subscriber(s) activated.')
    activate_subscribers.short_description = "Activate selected subscribers"
    
    def deactivate_subscribers(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} subscriber(s) deactivated.')
    deactivate_subscribers.short_description = "Deactivate selected subscribers"
    
    fieldsets = (
        ('Subscriber Info', {
            'fields': ('email', 'confirmed', 'is_active')
        }),
        ('Token', {
            'fields': ('confirmation_token',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('subscribed_at',),
            'classes': ('collapse',)
        }),
    )


# Optional: Customize Django Admin site header
admin.site.site_header = "21K Tools Blog Administration"
admin.site.site_title = "21K Tools Blog Admin"
admin.site.index_title = "Welcome to 21K Tools Blog Admin Panel"
