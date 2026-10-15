from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ListingForm
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


@login_required
def create(request):
    if request.method == "POST":
        form = ListingForm(request.POST, request.FILES)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.seller = request.user
            listing.status = Listing.Status.AVAILABLE
            listing.save()
            form.save_images()
            return redirect("listings:detail", pk=listing.pk)
    else:
        form = ListingForm()
    return render(request, "listings/form.html", {"form": form, "heading": "Sell an item"})
