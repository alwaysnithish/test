# image_resizer/urls.py

from django.urls import path
from . import views

app_name = 'image_resizer'

urlpatterns = [
    path('', views.image_resizer_view, name='resizer'),
    path('process/', views.process_image, name='process'),
    path('preview/', views.preview_image, name='preview'),
]
