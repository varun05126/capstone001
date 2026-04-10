from django.contrib import admin
from django.urls import path
from django.http import HttpResponse
from pathlib import Path

from aiapp.views import home, download_pdf

BASE_DIR = Path(__file__).resolve().parent.parent


# ------------------ STATIC FILE HANDLERS ------------------

def robots_txt(request):
    return HttpResponse(
        (BASE_DIR / "robots.txt").read_text(),
        content_type="text/plain"
    )


def sitemap_xml(request):
    return HttpResponse(
        (BASE_DIR / "sitemap.xml").read_text(),
        content_type="application/xml"
    )


def google_verify(request):
    return HttpResponse(
        (BASE_DIR / "googleb5949ab1058f2676.html").read_text(),
        content_type="text/html"
    )


# ------------------ URL PATTERNS ------------------

urlpatterns = [

    # Admin
    path("admin/", admin.site.urls),

    # SEO / Verification
    path("robots.txt", robots_txt),
    path("sitemap.xml", sitemap_xml),
    path("googleb5949ab1058f2676.html", google_verify),

    # Main App
    path("", home, name="home"),
    path("download/", download_pdf, name="download_pdf"),
]