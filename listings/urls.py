from django.urls import path

from . import views

app_name = "listings"

urlpatterns = [
    path("", views.home, name="home"),
    path("sell/", views.create, name="create"),
    path("listing/<int:pk>/", views.detail, name="detail"),
]