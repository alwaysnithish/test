from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from django.views.static import serve
from django.views.decorators.csrf import csrf_exempt
from django.contrib.sitemaps.views import sitemap

# IMPORT FIRST, BEFORE USING
from blog.sitemap import BlogPostSitemap

# NOW you can use it in the dictionary
sitemaps = {
    'blog': BlogPostSitemap,
}

from django.contrib.sitemaps.views import sitemap
from blog.sitemap import (
    BlogPostSitemap, 
    BlogCategorySitemap, 
    BlogTagSitemap, 
    BlogStaticSitemap
)

blog_sitemaps = {
    'posts': BlogPostSitemap,
    'categories': BlogCategorySitemap,
    'tags': BlogTagSitemap,
    'static': BlogStaticSitemap,
}


urlpatterns = [
    path('admin/', admin.site.urls),
    path('blog-sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='blog_sitemap'),
    path('blog/sitemap.xml', sitemap, 
         {'sitemaps': blog_sitemaps},
         name='blog_sitemap'),path('blog/sitemap.xml', sitemap, 
         {'sitemaps': blog_sitemaps},
         name='blog_sitemap'),
    path('fileconverter/', include('fileconverter.urls')),    
    path('agecalculator/', views.age_calculator, name='age_calculator'),
    path('api/age-calculate/', views.age_calculate_api, name='age_calculate_api'),
    path('about/', views.about, name='about'),
    path('help/', views.help, name='help'),
    path('privacypolicy/', views.privacypolicy, name='privacypolicy'),
    path('termsandconditions/', views.termsandconditions, name='termsandconditions'),
    path('', views.home, name='home'),
    path('contact/',views.contact,name='contact'),
    path('timecalculator/', views.time_calculator, name='time_calculator'),
    path('time-difference-api/', views.time_difference_api, name='time_difference_api'),
    path('time-add-subtract-api/', views.time_add_subtract_api, name='time_add_subtract_api'),
    path('time-convert-api/', views.time_convert_api, name='time_convert_api'),
    path('unitconverter/', views.unit, name='unit'),
    path('unit-converter-api/', views.unit_converter_api, name='unit_converter_api'),

    path('interestcalculator/', views.interest_calculator, name='interest_calculator'),
    path('api/simple-interest/', views.simple_interest_api, name='simple_interest_api'),
    path('api/compound-interest/', views.compound_interest_api, name='compound_interest_api'),
    path('api/loan-calculator/', views.loan_calculator_api, name='loan_calculator_api'),
    path('api/compare-plans/', views.compare_plans_api, name='compare_plans_api'),
    #path('convert/', include('fileconverter.urls')),
    path('pdftools/', include('pdftools.urls')),
    path('imageresizer/', include('image_resizer.urls')),
    #path('qrscanner/', include('qrscanner.urls')),
    #path('ckeditor/', include('ckeditor_uploader.urls')),
  #  path('fileconverter',include('fileconverter.urls')),
    
    path('blog/', include('blog.urls')),
    
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('', include('shortener.urls')),
    # Serve sitemap and ads.txt files
    re_path(r'^sitemap\.xml$', serve, {
        'document_root': settings.STATIC_ROOT, 
        'path': 'sitemap.xml'
    }),
    re_path(r'^ads\.txt$', serve, {
        'document_root': settings.BASE_DIR, 
        'path': 'ads.txt'
    }),
]

# Static and Media files serving
if settings.DEBUG:
    # During development, serve static and media files
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # In production, you might need to serve static files through Django
    # Only use this if your web server (nginx/apache) isn't handling static files
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', serve, {
            'document_root': settings.STATIC_ROOT,
        }),
        re_path(r'^media/(?P<path>.*)$', serve, {
            'document_root': settings.MEDIA_ROOT,
        }),
    ]

# Custom 404 handler
def custom_page_not_found(request, exception):
    """Custom 404 handler that won't interfere with static files"""
    from django.shortcuts import render
    return render(request, '404.html', status=404)

# Set the custom handler
handler404 = custom_page_not_found
# Custom 500 handler
def custom_server_error(request):
    """Custom 500 handler for database/server errors"""
    from django.shortcuts import render
    return render(request, '500.html', status=503)  # Use 503 instead of 500

# Set the custom handlers

handler500 = custom_server_error  # Add this line
