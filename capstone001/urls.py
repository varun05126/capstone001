from django.contrib import admin
from django.urls import path
from aiapp.views import home, download_pdf

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("download/", download_pdf, name="download_pdf"),
]
