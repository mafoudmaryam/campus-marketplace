import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from listings.models import Category, Listing
from listings.tests import make_photo

from .models import Conversation, Message

User = get_user_model()


class MessagingBase(TestCase):
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


class MessagingTests(MessagingBase):
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


class ChatFeatureTests(MessagingBase):
    def setUp(self):
        super().setUp()
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.convo = self.start_conversation()
        self.url = reverse("messaging:conversation", args=[self.convo.pk])

    def send(self, **data):
        with override_settings(MEDIA_ROOT=self.media):
            return self.client.post(self.url, data)

    def as_seller(self):
        self.client.logout()
        self.client.login(username="seller", password="pass12345")

    def test_empty_conversation_shows_quick_replies_to_buyer(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Start the conversation")
        self.assertContains(response, "Is the price negotiable?")
        self.assertContains(response, "Send message")

    def test_empty_message_is_not_saved(self):
        self.send(body="   ")
        self.assertEqual(Message.objects.count(), 0)

    def test_photo_can_be_sent_without_text(self):
        self.send(image=make_photo())
        message = Message.objects.get()
        self.assertTrue(message.image.name.startswith("messages/"))
        self.assertEqual(message.body, "")

    def test_read_tick_after_the_other_person_opens_the_chat(self):
        self.send(body="Hello")
        self.assertContains(self.client.get(self.url), 'aria-label="Sent"')
        self.as_seller()
        self.client.get(self.url)
        self.client.logout()
        self.client.login(username="buyer", password="pass12345")
        self.assertContains(self.client.get(self.url), 'aria-label="Read"')

    def test_inbox_lists_conversation_and_opens_newest_chat(self):
        self.send(body="Is it free?")
        self.as_seller()
        response = self.client.get(reverse("messaging:inbox"))
        self.assertContains(response, "Is it free?")
        self.assertEqual(response.context["conversation"], self.convo)
        # shown but not opened yet, so it still counts as unread
        self.assertEqual(response.context["counts"], {"all": 1, "unread": 1, "archived": 0})

    def test_unread_tab_shows_only_unread_conversations(self):
        self.send(body="Is it free?")
        self.as_seller()
        response = self.client.get(reverse("messaging:inbox") + "?tab=unread")
        self.assertEqual(len(response.context["conversations"]), 1)
        # opening it marks it read, so the unread tab is empty afterwards
        self.client.get(reverse("messaging:inbox") + f"?c={self.convo.pk}")
        response = self.client.get(reverse("messaging:inbox") + "?tab=unread")
        self.assertEqual(len(response.context["conversations"]), 0)

    def test_archive_moves_conversation_and_new_message_brings_it_back(self):
        self.client.post(reverse("messaging:archive", args=[self.convo.pk]))
        response = self.client.get(reverse("messaging:inbox"))
        self.assertEqual(response.context["counts"]["archived"], 1)
        self.assertEqual(len(response.context["conversations"]), 0)
        self.send(body="Still there?")
        response = self.client.get(reverse("messaging:inbox"))
        self.assertEqual(response.context["counts"]["archived"], 0)

    def test_sending_from_inbox_returns_to_inbox(self):
        response = self.send(body="Hi", next="inbox")
        self.assertRedirects(response, reverse("messaging:inbox") + f"?c={self.convo.pk}")

    def test_stranger_cannot_archive(self):
        self.client.logout()
        self.client.login(username="stranger", password="pass12345")
        response = self.client.post(reverse("messaging:archive", args=[self.convo.pk]))
        self.assertEqual(response.status_code, 403)
