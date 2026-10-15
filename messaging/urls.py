from django.urls import path

from . import views

app_name = "messaging"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("start/<int:listing_pk>/", views.start, name="start"),
    path("<int:pk>/", views.conversation, name="conversation"),
    path("<int:pk>/archive/", views.archive, name="archive"),
]
