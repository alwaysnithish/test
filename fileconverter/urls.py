from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('', views.FileConverterView.as_view(), name='converter'),
    path('batch/', views.BatchConverterView.as_view(), name='batch_convert'),
    path('download/<str:file_id>/', views.FileDownloadView.as_view(), name='download'),
    path('formats/', views.SupportedFormatsView.as_view(), name='formats'),
    path('health/', views.health_check, name='health'),
]+static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)