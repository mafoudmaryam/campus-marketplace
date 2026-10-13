from django.shortcuts import render

from .models import Listing


def home(request):
    listings = (
        Listing.objects.filter(status=Listing.Status.AVAILABLE)
        .select_related("category", "seller")
        .prefetch_related("images")
    )
    return render(request, "listings/home.html", {"listings": listings})