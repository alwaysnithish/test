"""
QR Tools URLs - Professional Routing Configuration
"""

from django.urls import path
from . import views

app_name = 'qrtools'

urlpatterns = [
    # Main page
    path('', views.qr_main_view, name='qr_main'),
    
    # QR Generation APIs
    path('api/upload-file/', views.upload_file_to_cloudinary, name='upload_file'),
    path('api/generate/', views.generate_qr_api, name='generate_qr'),
    path('api/profile-card/create/', views.create_profile_card_api, name='create_profile_card'),
    path('api/bulk-generate/', views.bulk_generate_api, name='bulk_generate'),
    path('api/templates/', views.get_templates_api, name='get_templates'),
    
    # Dynamic QR Management
    path('api/dynamic/<str:code>/update/', views.update_dynamic_qr_api, name='update_dynamic_qr'),
    
    # QR Redirect (for tracking)
    path('qr/<str:code>/', views.qr_redirect, name='qr_redirect'),
    
    # Analytics Dashboard
    path('analytics/<str:key>/', views.analytics_dashboard, name='analytics'),
    path('api/update/<str:code>/', views.update_dynamic_qr_api, name='update_dynamic_qr'),
    # Profile Card Landing Page
    #path('profile/<str:code>/', views.profile_card_view, name='profile_card'),
    path('api/bulk-download/', views.bulk_download_api, name='bulk_download'),
    path('api/bulk-download/folder/', views.bulk_download_by_folder_api, name='bulk_download_folder'),
    path('api/bulk-download/batch/<uuid:batch_id>/', views.bulk_download_batch_api, name='bulk_download_batch'),

]

