from django.contrib import admin
from django.urls import path
from .views import home, download_pdf

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name="home"),
    path('download-pdf/', download_pdf, name="download_pdf"),
]