from django.urls import path

from . import views

app_name = "listings"

urlpatterns = [
    path("", views.home, name="home"),
    path("sell/", views.create, name="create"),
    path("my-listings/", views.my_listings, name="my_listings"),
    path("listing/<int:pk>/", views.detail, name="detail"),
    path("listing/<int:pk>/edit/", views.edit, name="edit"),
    path("listing/<int:pk>/delete/", views.delete, name="delete"),
    path("listing/<int:pk>/sold/", views.mark_sold, name="mark_sold"),
]