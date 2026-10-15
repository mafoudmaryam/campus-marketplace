import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Category, Listing

User = get_user_model()


def make_photo(name="photo.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class ListingTestBase(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user("seller", password="pass12345")
        self.other = User.objects.create_user("other", password="pass12345")
        self.category = Category.objects.create(name="Books", slug="books")
        self.listing = self.make_listing("Calculus book")

    def make_listing(self, title, **extra):
        data = {
            "seller": self.seller,
            "title": title,
            "description": "Nice",
            "price": 20,
            "category": self.category,
        }
        data.update(extra)
        return Listing.objects.create(**data)

    def form_data(self, **extra):
        data = {
            "title": "Desk lamp",
            "description": "Works well",
            "price": "15.00",
            "category": self.category.pk,
            "condition": "good",
            "campus": "wangjiang",
        }
        data.update(extra)
        return data


class CreateListingTests(ListingTestBase):
    def setUp(self):
        super().setUp()
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)

    def test_anonymous_user_is_sent_to_login(self):
        response = self.client.get(reverse("listings:create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_create_sets_seller_and_status(self):
        self.client.login(username="seller", password="pass12345")
        with override_settings(MEDIA_ROOT=self.media):
            response = self.client.post(reverse("listings:create"), self.form_data(images=[make_photo()]))
        listing = Listing.objects.get(title="Desk lamp")
        self.assertRedirects(response, reverse("listings:detail", args=[listing.pk]))
        self.assertEqual(listing.seller, self.seller)
        self.assertEqual(listing.status, Listing.Status.AVAILABLE)
        self.assertEqual(listing.images.count(), 1)

    def test_more_than_five_photos_is_rejected(self):
        self.client.login(username="seller", password="pass12345")
        photos = [make_photo(f"p{i}.png") for i in range(6)]
        with override_settings(MEDIA_ROOT=self.media):
            response = self.client.post(reverse("listings:create"), self.form_data(images=photos))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Listing.objects.filter(title="Desk lamp").exists())


class OwnerOnlyTests(ListingTestBase):
    def test_other_user_gets_403_on_edit_delete_and_sold(self):
        self.client.login(username="other", password="pass12345")
        self.assertEqual(self.client.get(reverse("listings:edit", args=[self.listing.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("listings:delete", args=[self.listing.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("listings:mark_sold", args=[self.listing.pk])).status_code, 403)
        self.assertTrue(Listing.objects.filter(pk=self.listing.pk).exists())

    def test_owner_can_edit(self):
        self.client.login(username="seller", password="pass12345")
        self.client.post(reverse("listings:edit", args=[self.listing.pk]), self.form_data(title="New title"))
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.title, "New title")

    def test_owner_can_mark_sold(self):
        self.client.login(username="seller", password="pass12345")
        self.client.post(reverse("listings:mark_sold", args=[self.listing.pk]))
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.Status.SOLD)

    def test_my_listings_shows_only_own_items(self):
        Listing.objects.create(
            seller=self.other, title="Other thing", description="x", category=self.category
        )
        self.client.login(username="seller", password="pass12345")
        response = self.client.get(reverse("listings:my_listings"))
        self.assertContains(response, "Calculus book")
        self.assertNotContains(response, "Other thing")


class BrowseTests(ListingTestBase):
    def test_search_finds_matching_title(self):
        self.make_listing("Rice cooker")
        response = self.client.get(reverse("listings:home"), {"q": "rice"})
        self.assertContains(response, "Rice cooker")
        self.assertNotContains(response, "Calculus book")

    def test_campus_filter(self):
        self.make_listing("Huaxi chair", campus="huaxi")
        response = self.client.get(reverse("listings:home"), {"campus": "huaxi"})
        self.assertContains(response, "Huaxi chair")
        self.assertNotContains(response, "Calculus book")

    def test_category_filter(self):
        shoes = Category.objects.create(name="Shoes", slug="shoes")
        self.make_listing("Running shoes", category=shoes)
        response = self.client.get(reverse("listings:home"), {"category": "shoes"})
        self.assertContains(response, "Running shoes")
        self.assertNotContains(response, "Calculus book")

    def test_home_is_paginated(self):
        for i in range(14):
            self.make_listing(f"Item {i}")
        response = self.client.get(reverse("listings:home"))
        self.assertEqual(len(response.context["listings"]), 12)
        second = self.client.get(reverse("listings:home"), {"page": 2})
        self.assertEqual(len(second.context["listings"]), 3)
