from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Exists, OuterRef, Q, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from listings.models import Listing

from .forms import MessageForm
from .models import Conversation, Message

TABS = ["all", "unread", "archived"]


def user_conversations(user):
    """All conversations of a user, with the last message, unread count and archive flag."""
    last = Message.objects.filter(conversation=OuterRef("pk")).order_by("-created_at")
    archived = Conversation.archived_by.through.objects.filter(conversation=OuterRef("pk"), user=user)
    return (
        Conversation.objects.filter(Q(buyer=user) | Q(listing__seller=user))
        .select_related("listing", "listing__seller", "listing__seller__profile", "buyer", "buyer__profile")
        .prefetch_related("listing__images")
        .annotate(
            unread=Count("messages", filter=Q(messages__is_read=False) & ~Q(messages__sender=user)),
            last_body=Subquery(last.values("body")[:1]),
            last_image=Subquery(last.values("image")[:1]),
            last_at=Subquery(last.values("created_at")[:1]),
            is_archived=Exists(archived),
        )
    )


def chat_context(request, convo, mark_read=True):
    """What the chat panel needs: the other person, the messages and the reply form."""
    other = convo.other_person(request.user)
    if mark_read:
        convo.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    return {
        "conversation": convo,
        "other": other,
        "other_items_count": Listing.objects.filter(seller=other, status=Listing.Status.AVAILABLE).count(),
        "is_buyer": request.user == convo.buyer,
        "chat": convo.messages.select_related("sender", "sender__profile"),
        "form": MessageForm(),
    }


def get_own_conversation(request, pk):
    convo = get_object_or_404(
        Conversation.objects.select_related(
            "listing", "listing__seller", "listing__seller__profile", "buyer", "buyer__profile"
        ).prefetch_related("listing__images"),
        pk=pk,
    )
    if not convo.has_member(request.user):
        raise PermissionDenied
    return convo


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
    tab = request.GET.get("tab", "all")
    if tab not in TABS:
        tab = "all"
    conversations = list(user_conversations(request.user))
    active = [c for c in conversations if not c.is_archived]
    counts = {
        "all": len(active),
        "unread": sum(1 for c in active if c.unread),
        "archived": sum(1 for c in conversations if c.is_archived),
    }
    if tab == "archived":
        shown = [c for c in conversations if c.is_archived]
    elif tab == "unread":
        shown = [c for c in active if c.unread]
    else:
        shown = active

    # the open chat: the one picked in the list, or the newest one on big screens
    picked = request.GET.get("c", "")
    selected = next((c for c in conversations if str(c.pk) == picked), None)
    if selected is None and shown:
        selected = shown[0]
    context = {"conversations": shown, "tab": tab, "counts": counts, "picked": bool(picked)}
    if selected:
        # a chat only counts as read once the person picks it
        context.update(chat_context(request, selected, mark_read=bool(picked)))
        if picked and selected.unread:
            if not selected.is_archived:
                counts["unread"] -= 1
            selected.unread = 0
    return render(request, "messaging/inbox.html", context)


@login_required
def conversation(request, pk):
    convo = get_own_conversation(request, pk)
    from_inbox = request.POST.get("next") == "inbox"

    if request.method == "POST":
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = convo
            message.sender = request.user
            message.save()
            convo.save()  # moves this conversation to the top of the inbox
            convo.archived_by.clear()  # a new message brings it back for both people
            if from_inbox:
                return redirect(f"{reverse('messaging:inbox')}?c={convo.pk}")
            return redirect("messaging:conversation", pk=convo.pk)
        for error in form.non_field_errors() + form.errors.get("image", []):
            messages.error(request, error)
        if from_inbox:
            return redirect(f"{reverse('messaging:inbox')}?c={convo.pk}")

    context = chat_context(request, convo)
    if request.method == "POST":
        context["form"] = form
    return render(request, "messaging/conversation.html", context)


@login_required
@require_POST
def archive(request, pk):
    convo = get_own_conversation(request, pk)
    if convo.archived_by.filter(pk=request.user.pk).exists():
        convo.archived_by.remove(request.user)
        return redirect(f"{reverse('messaging:inbox')}?c={convo.pk}")
    convo.archived_by.add(request.user)
    return redirect(f"{reverse('messaging:inbox')}?tab=archived&c={convo.pk}")
