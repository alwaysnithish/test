from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from django.views.static import serve
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('admin/', admin.site.urls),
   
    path('agecalculator/', views.age, name='age'),
    path('about/', views.about, name='about'),
    path('help/', views.help, name='help'),
    path('privacypolicy/', views.privacypolicy, name='privacypolicy'),
    path('termsandconditions/', views.termsandconditions, name='termsandconditions'),
    path('', views.home, name='home'),
    path('timecalculator/', views.time, name='time'),
    path('unitconverter/', views.unit, name='unit'),
    path('interestcalculator/', views.interest, name='interest'),
    #path('convert/', include('fileconverter.urls')),
    path('pdftools/', include('pdftools.urls')),
    path('', include('shortener.urls')),
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
        'document_root': settings.STATIC_ROOT, 
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
