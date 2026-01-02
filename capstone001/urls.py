from django.urls import path
from aiapp.views import home, download_pdf

urlpatterns = [
    path("", home),
    path("download-pdf/", download_pdf),
]
