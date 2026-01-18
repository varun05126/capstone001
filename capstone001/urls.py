from django.contrib import admin
from django.urls import path
from aiapp.views import home, download_pdf
from django.http import HttpResponse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# ---- Files for Google & SEO ----

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


# ---- URL patterns ----

urlpatterns = [
    path("admin/", admin.site.urls),

    # SEO / Google files
    path("robots.txt", robots_txt),
    path("sitemap.xml", sitemap_xml),
    path("googleb5949ab1058f2676.html", google_verify),

    # App routes
    path("", home, name="home"),
    path("download/", download_pdf, name="download_pdf"),
]
