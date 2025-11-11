from django.urls import path
from . import views

app_name = 'fileconverter'

urlpatterns = [
    path('', views.index, name='index'),
    path('upload/', views.upload_file, name='upload'),
    path('convert/', views.convert_file, name='convert'),
    path('download/<str:filename>/', views.download_file, name='download'),
    path('options/<str:from_format>/', views.get_conversion_options, name='options'),
    path('formats/', views.get_supported_formats, name='formats'),
]
