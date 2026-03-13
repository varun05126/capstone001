from django.contrib import admin
from django.urls import path
from .views import home, download_pdf, profile, signup, login_view, logout_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("download-pdf/", download_pdf, name="download_pdf"),
    path("profile/", profile, name="profile"),
    path("signup/", signup, name="signup"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
]