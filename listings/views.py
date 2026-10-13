from django.shortcuts import get_object_or_404, render

from .models import Listing


def home(request):
    listings = (
        Listing.objects.filter(status=Listing.Status.AVAILABLE)
        .select_related("category", "seller")
        .prefetch_related("images")
    )
    return render(request, "listings/home.html", {"listings": listings})


def detail(request, pk):
    listing = get_object_or_404(
        Listing.objects.select_related("category", "seller").prefetch_related("images"),
        pk=pk,
    )
    return render(request, "listings/detail.html", {"listing": listing})