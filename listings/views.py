from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ListingForm
from .models import Category, Listing


def home(request):
    listings = (
        Listing.objects.filter(status=Listing.Status.AVAILABLE)
        .select_related("category", "seller")
        .prefetch_related("images")
    )

    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    campus = request.GET.get("campus", "")
    if query:
        listings = listings.filter(Q(title__icontains=query) | Q(description__icontains=query))
    if category:
        listings = listings.filter(category__slug=category)
    if campus in Listing.Campus.values:
        listings = listings.filter(campus=campus)

    page = Paginator(listings, 12).get_page(request.GET.get("page"))
    # keep the search and filters in the page links
    params = request.GET.copy()
    params.pop("page", None)
    context = {
        "listings": page,
        "page": page,
        "categories": Category.objects.all(),
        "campuses": Listing.Campus.choices,
        "query": query,
        "selected_category": category,
        "selected_campus": campus,
        "querystring": params.urlencode(),
    }
    return render(request, "listings/home.html", context)


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



def get_own_listing(request, pk):
    """Find a listing and make sure the logged-in user is the seller."""
    listing = get_object_or_404(Listing, pk=pk)
    if listing.seller != request.user:
        raise PermissionDenied
    return listing


@login_required
def edit(request, pk):
    listing = get_own_listing(request, pk)
    if request.method == "POST":
        form = ListingForm(request.POST, request.FILES, instance=listing)
        if form.is_valid():
            form.save()
            return redirect("listings:detail", pk=listing.pk)
    else:
        form = ListingForm(instance=listing)
    return render(request, "listings/form.html", {"form": form, "heading": "Edit your listing"})


@login_required
@require_POST
def delete(request, pk):
    listing = get_own_listing(request, pk)
    listing.delete()
    return redirect("listings:home")


@login_required
@require_POST
def mark_sold(request, pk):
    listing = get_own_listing(request, pk)
    listing.status = Listing.Status.SOLD
    listing.save()
    return redirect("listings:detail", pk=listing.pk)



@login_required
def my_listings(request):
    listings = (
        Listing.objects.filter(seller=request.user)
        .select_related("category")
        .prefetch_related("images")
    )
    return render(request, "listings/my_listings.html", {"listings": listings})
