from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from listings.models import Category, Listing

from .models import Conversation, Message

User = get_user_model()


class MessagingTests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user("seller", password="pass12345")
        self.buyer = User.objects.create_user("buyer", password="pass12345")
        self.stranger = User.objects.create_user("stranger", password="pass12345")
        category = Category.objects.create(name="Books", slug="books")
        self.listing = Listing.objects.create(
            seller=self.seller, title="Calculus book", description="x", category=category
        )

    def start_conversation(self):
        self.client.login(username="buyer", password="pass12345")
        self.client.post(reverse("messaging:start", args=[self.listing.pk]))
        return Conversation.objects.get(listing=self.listing, buyer=self.buyer)

    def test_buyer_can_start_conversation_once(self):
        self.start_conversation()
        self.client.post(reverse("messaging:start", args=[self.listing.pk]))
        self.assertEqual(Conversation.objects.count(), 1)

    def test_seller_cannot_message_own_listing(self):
        self.client.login(username="seller", password="pass12345")
        self.client.post(reverse("messaging:start", args=[self.listing.pk]))
        self.assertEqual(Conversation.objects.count(), 0)

    def test_stranger_gets_403(self):
        convo = self.start_conversation()
        self.client.logout()
        self.client.login(username="stranger", password="pass12345")
        response = self.client.get(reverse("messaging:conversation", args=[convo.pk]))
        self.assertEqual(response.status_code, 403)

    def test_send_message_and_unread_badge(self):
        convo = self.start_conversation()
        self.client.post(reverse("messaging:conversation", args=[convo.pk]), {"body": "Is it free?"})
        self.assertEqual(Message.objects.count(), 1)

        # the seller sees 1 unread message in the navbar
        self.client.logout()
        self.client.login(username="seller", password="pass12345")
        response = self.client.get(reverse("messaging:inbox"))
        self.assertEqual(response.context["unread_count"], 1)

        # opening the conversation marks it as read
        self.client.get(reverse("messaging:conversation", args=[convo.pk]))
        response = self.client.get(reverse("messaging:inbox"))
        self.assertEqual(response.context["unread_count"], 0)
