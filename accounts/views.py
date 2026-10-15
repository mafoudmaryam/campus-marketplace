from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import get_object_or_404, redirect, render

from listings.models import Listing

from .forms import ProfileForm
from .models import Profile


def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("listings:home")
    else:
        form = UserCreationForm()
    return render(request, "accounts/signup.html", {"form": form})


def profile(request, username):
    owner = get_object_or_404(get_user_model(), username=username)
    profile, _ = Profile.objects.get_or_create(user=owner)
    listings = (
        Listing.objects.filter(seller=owner, status=Listing.Status.AVAILABLE)
        .select_related("category")
        .prefetch_related("images")
    )
    return render(
        request,
        "accounts/profile.html",
        {"owner": owner, "profile": profile, "listings": listings},
    )


@login_required
def edit_profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("accounts:profile", username=request.user.username)
    else:
        form = ProfileForm(instance=profile)
    # a small checklist that nudges people to finish their profile
    steps = [
        ("Add a profile photo", bool(profile.avatar)),
        ("Add your display name", bool(profile.display_name)),
        ("Choose your campus", bool(profile.campus)),
        ("Add your WeChat ID or QR code", bool(profile.wechat_id or profile.wechat_qr)),
    ]
    done = sum(1 for _, ok in steps if ok)
    context = {
        "form": form,
        "profile": profile,
        "steps": steps,
        "percent": round(done * 100 / len(steps)),
    }
    return render(request, "accounts/edit_profile.html", context)