from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from listings.models import Listing

from .forms import MessageForm
from .models import Conversation


@login_required
@require_POST
def start(request, listing_pk):
    listing = get_object_or_404(Listing, pk=listing_pk)
    if listing.seller == request.user:
        messages.error(request, "You cannot message yourself about your own listing.")
        return redirect("listings:detail", pk=listing.pk)
    conversation, _ = Conversation.objects.get_or_create(listing=listing, buyer=request.user)
    return redirect("messaging:conversation", pk=conversation.pk)


@login_required
def inbox(request):
    conversations = (
        Conversation.objects.filter(Q(buyer=request.user) | Q(listing__seller=request.user))
        .select_related("listing", "listing__seller", "buyer")
        .annotate(
            unread=Count(
                "messages",
                filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user),
            )
        )
    )
    return render(request, "messaging/inbox.html", {"conversations": conversations})


@login_required
def conversation(request, pk):
    convo = get_object_or_404(
        Conversation.objects.select_related("listing", "listing__seller", "buyer"), pk=pk
    )
    if not convo.has_member(request.user):
        raise PermissionDenied

    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = convo
            message.sender = request.user
            message.save()
            convo.save()  # moves this conversation to the top of the inbox
            return redirect("messaging:conversation", pk=convo.pk)
    else:
        form = MessageForm()

    convo.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    return render(
        request,
        "messaging/conversation.html",
        {
            "conversation": convo,
            "other": convo.other_person(request.user),
            "chat": convo.messages.select_related("sender"),
            "form": form,
        },
    )
