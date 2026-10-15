from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Profile

from .forms import ListingForm
from .models import Category, Listing


SORTS = {
    "newest": ("Newest first", "-created_at"),
    "price_asc": ("Price low to high", "price"),
    "price_desc": ("Price high to low", "-price"),
}


def parse_price(value):
    """Turn a query-string value into a non-negative Decimal, or None if it is empty or invalid."""
    try:
        price = Decimal(value.strip())
    except (InvalidOperation, AttributeError):
        return None
    return price if price.is_finite() and price >= 0 else None


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

    min_price = parse_price(request.GET.get("min_price", ""))
    max_price = parse_price(request.GET.get("max_price", ""))
    if min_price is not None:
        listings = listings.filter(price__gte=min_price)
    if max_price is not None:
        listings = listings.filter(price__lte=max_price)

    sort = request.GET.get("sort", "")
    if sort not in SORTS:
        sort = "newest"
    # pk as a tie-breaker keeps pagination stable
    listings = listings.order_by(SORTS[sort][1], "-pk")

    page = Paginator(listings, 12).get_page(request.GET.get("page"))
    # keep the search and filters in the page links
    params = request.GET.copy()
    params.pop("page", None)

    # category chips keep every other filter but replace the category
    chip_params = params.copy()
    chip_params.pop("category", None)
    chip_base = chip_params.urlencode()
    chips = [{"name": "All", "slug": "", "querystring": chip_base}]
    for item in Category.objects.all():
        chips.append({
            "name": item.name,
            "slug": item.slug,
            "querystring": urlencode({**chip_params.dict(), "category": item.slug}),
        })

    context = {
        "listings": page,
        "page": page,
        "categories": Category.objects.all(),
        "campuses": Listing.Campus.choices,
        "query": query,
        "selected_category": category,
        "selected_campus": campus,
        "chips": chips,
        "min_price": request.GET.get("min_price", "") if min_price is not None else "",
        "max_price": request.GET.get("max_price", "") if max_price is not None else "",
        "sorts": [(key, label) for key, (label, _) in SORTS.items()],
        "selected_sort": sort,
        "querystring": params.urlencode(),
    }
    return render(request, "listings/home.html", context)


def detail(request, pk):
    listing = get_object_or_404(
        Listing.objects.select_related("category", "seller").prefetch_related("images"),
        pk=pk,
    )
    seller_profile, _ = Profile.objects.get_or_create(user=listing.seller)
    return render(request, "listings/detail.html", {"listing": listing, "seller_profile": seller_profile})


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
    profile, _ = Profile.objects.get_or_create(user=request.user)
    context = {
        "form": form,
        "heading": "Sell an item",
        "missing_wechat": not (profile.wechat_id or profile.wechat_qr),
    }
    return render(request, "listings/form.html", context)



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
