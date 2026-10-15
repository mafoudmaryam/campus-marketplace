from django.db.models import Q

from .models import Message


def unread_count(request):
    """Number of unread messages for the logged-in user, shown in the navbar."""
    if not request.user.is_authenticated:
        return {}
    count = (
        Message.objects.filter(is_read=False)
        .filter(Q(conversation__buyer=request.user) | Q(conversation__listing__seller=request.user))
        .exclude(sender=request.user)
        .count()
    )
    return {"unread_count": count}
