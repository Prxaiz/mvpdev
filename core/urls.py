from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("setup/", views.setup, name="setup"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("content/", views.content_tool, name="content_tool"),
    path("website/", views.website_tool, name="website_tool"),
    path("site/<slug:slug>/", views.public_site, name="public_site"),
    path("site/<slug:slug>/contact/", views.public_lead_capture, name="public_lead_capture"),
]
