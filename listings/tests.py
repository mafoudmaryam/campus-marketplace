import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Category, Listing, ListingImage

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


class EditPhotosTests(ListingTestBase):
    def setUp(self):
        super().setUp()
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.client.login(username="seller", password="pass12345")
        self.url = reverse("listings:edit", args=[self.listing.pk])
        with override_settings(MEDIA_ROOT=self.media):
            self.photos = [
                ListingImage.objects.create(listing=self.listing, image=make_photo(f"old{i}.png"))
                for i in range(4)
            ]

    def post(self, **extra):
        with override_settings(MEDIA_ROOT=self.media):
            return self.client.post(self.url, self.form_data(**extra))

    def test_edit_page_shows_existing_photos_with_remove_checkbox(self):
        with override_settings(MEDIA_ROOT=self.media):
            response = self.client.get(self.url)
        for photo in self.photos:
            self.assertContains(response, f'id="remove-{photo.pk}"')

    def test_selected_photos_are_removed(self):
        self.post(remove_images=[self.photos[0].pk, self.photos[1].pk])
        remaining = set(self.listing.images.values_list("pk", flat=True))
        self.assertEqual(remaining, {self.photos[2].pk, self.photos[3].pk})

    def test_limit_counts_existing_plus_new_photos(self):
        response = self.post(images=[make_photo("a.png"), make_photo("b.png")])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.listing.images.count(), 4)

    def test_removing_photos_makes_room_for_new_ones(self):
        response = self.post(
            remove_images=[self.photos[0].pk, self.photos[1].pk],
            images=[make_photo("a.png"), make_photo("b.png")],
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.listing.images.count(), 4)

    def test_cannot_remove_another_listings_photo(self):
        other_listing = self.make_listing("Other item")
        with override_settings(MEDIA_ROOT=self.media):
            foreign = ListingImage.objects.create(listing=other_listing, image=make_photo("f.png"))
        response = self.post(remove_images=[foreign.pk])
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ListingImage.objects.filter(pk=foreign.pk).exists())


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

    def titles(self, **params):
        response = self.client.get(reverse("listings:home"), params)
        return [listing.title for listing in response.context["listings"]]

    def test_price_range_filter(self):
        self.make_listing("Cheap pen", price=5)
        self.make_listing("Pricey chair", price=100)
        self.assertEqual(set(self.titles(min_price="10", max_price="50")), {"Calculus book"})
        self.assertEqual(set(self.titles(min_price="50")), {"Pricey chair"})
        self.assertEqual(set(self.titles(max_price="5")), {"Cheap pen"})

    def test_invalid_price_is_ignored(self):
        self.assertEqual(self.titles(min_price="abc", max_price="-3"), ["Calculus book"])

    def test_sort_by_price(self):
        self.make_listing("Cheap pen", price=5)
        self.make_listing("Pricey chair", price=100)
        self.assertEqual(self.titles(sort="price_asc"), ["Cheap pen", "Calculus book", "Pricey chair"])
        self.assertEqual(self.titles(sort="price_desc"), ["Pricey chair", "Calculus book", "Cheap pen"])

    def test_default_sort_is_newest_first(self):
        self.make_listing("Newer item")
        self.assertEqual(self.titles(), ["Newer item", "Calculus book"])
        self.assertEqual(self.titles(sort="nonsense"), ["Newer item", "Calculus book"])

    def test_filters_work_together_with_search_and_sort(self):
        self.make_listing("Blue lamp", price=30, campus="huaxi")
        self.make_listing("Red lamp", price=10, campus="huaxi")
        self.make_listing("Green lamp", price=20, campus="jiangan")
        result = self.titles(q="lamp", campus="huaxi", min_price="5", sort="price_asc")
        self.assertEqual(result, ["Red lamp", "Blue lamp"])

    def test_category_chips_are_listed_and_active_one_is_marked(self):
        shoes = Category.objects.create(name="Shoes", slug="shoes")
        response = self.client.get(reverse("listings:home"), {"category": "shoes", "sort": "price_asc"})
        chips = {chip["name"]: chip for chip in response.context["chips"]}
        self.assertEqual(set(chips), {"All", "Books", "Shoes"})
        self.assertContains(response, 'class="chip active"', count=1)
        self.assertIn("sort=price_asc", chips["Books"]["querystring"])
        self.assertIn("category=books", chips["Books"]["querystring"])
        self.assertNotIn("category", chips["All"]["querystring"])

    def test_pagination_links_keep_filters(self):
        for i in range(14):
            self.make_listing(f"Item {i}", price=10 + i)
        response = self.client.get(reverse("listings:home"), {"min_price": "10", "sort": "price_asc"})
        self.assertContains(response, "min_price=10&amp;sort=price_asc&page=2")


class WechatContactTests(ListingTestBase):
    def setUp(self):
        super().setUp()
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.url = reverse("listings:detail", args=[self.listing.pk])

    def set_wechat(self, wechat_id="seller_wx", qr=False):
        profile = self.seller.profile
        profile.wechat_id = wechat_id
        if qr:
            with override_settings(MEDIA_ROOT=self.media):
                profile.wechat_qr = make_photo("qr.png")
                profile.save()
        else:
            profile.save()

    def get(self):
        with override_settings(MEDIA_ROOT=self.media):
            return self.client.get(self.url)

    def test_anonymous_user_sees_login_prompt_not_wechat_id(self):
        self.set_wechat()
        response = self.get()
        self.assertContains(response, "Log in</a> to chat with the seller on WeChat")
        self.assertNotContains(response, "seller_wx")
        self.assertNotContains(response, "Chat on WeChat")

    def test_logged_in_user_sees_wechat_card(self):
        self.set_wechat()
        self.client.login(username="other", password="pass12345")
        response = self.get()
        self.assertContains(response, "Chat on WeChat")
        self.assertContains(response, "seller_wx")
        self.assertContains(response, 'data-wechat-id="seller_wx"')
        self.assertContains(response, "Message seller")
        self.assertNotContains(response, "Scan with WeChat")

    def test_qr_code_is_shown_when_uploaded(self):
        self.set_wechat(wechat_id="", qr=True)
        self.client.login(username="other", password="pass12345")
        response = self.get()
        self.assertContains(response, "Scan with WeChat")
        self.assertContains(response, "wechat_qr/")
        self.assertNotContains(response, "seller_wx")

    def test_card_hidden_when_seller_has_no_wechat_info(self):
        self.client.login(username="other", password="pass12345")
        response = self.get()
        self.assertNotContains(response, "Chat on WeChat")
        self.assertContains(response, "Message seller")

    def test_sell_page_nudges_seller_without_wechat(self):
        self.client.login(username="seller", password="pass12345")
        response = self.client.get(reverse("listings:create"))
        self.assertContains(response, "Add your WeChat so buyers can contact you")
        self.assertContains(response, reverse("accounts:edit_profile"))

    def test_sell_page_has_no_nudge_once_wechat_is_set(self):
        self.set_wechat()
        self.client.login(username="seller", password="pass12345")
        response = self.client.get(reverse("listings:create"))
        self.assertNotContains(response, "Add your WeChat so buyers can contact you")

    def test_edit_page_has_no_nudge(self):
        self.client.login(username="seller", password="pass12345")
        response = self.client.get(reverse("listings:edit", args=[self.listing.pk]))
        self.assertNotContains(response, "Add your WeChat so buyers can contact you")


    def test_bar_is_green_sticky_and_has_app_link_and_copy_script(self):
        self.set_wechat()
        self.client.login(username="other", password="pass12345")
        response = self.get()
        self.assertContains(response, "wechat-action wechat-action-sticky")
        self.assertContains(response, "ID copied! Paste it in WeChat > Contacts > Add Contacts")
        self.assertContains(response, "weixin://")

    def test_seller_does_not_see_bar_on_own_listing(self):
        self.set_wechat()
        self.client.login(username="seller", password="pass12345")
        self.assertNotContains(self.get(), "Chat on WeChat")

    def test_seller_card_message_button_and_safety_note(self):
        self.seller.profile.display_name = "Sally"
        self.seller.profile.save()
        self.set_wechat()
        self.client.login(username="other", password="pass12345")
        response = self.get()
        self.assertContains(response, "Sally")
        self.assertContains(response, "Wangjiang campus")
        self.assertContains(response, "Usually replies on WeChat")
        self.assertContains(response, 'class="btn-message"')
        self.assertContains(response, "Message seller")
        self.assertContains(response, "Meet on campus and check the item before you pay.")

    def test_popup_has_copy_button_and_numbered_steps(self):
        self.set_wechat(qr=True)
        self.client.login(username="other", password="pass12345")
        response = self.get()
        self.assertContains(response, 'id="wechat-close"')
        self.assertContains(response, "Copy ID")
        self.assertContains(response, "Copied!")
        self.assertContains(response, "Scan with WeChat")
        self.assertContains(response, "<li>Open WeChat</li>", html=True)
        self.assertContains(response, "<li>Contacts &gt; Add Contacts</li>", html=True)
        self.assertContains(response, "<li>Paste the ID</li>", html=True)

    def test_anonymous_user_gets_no_seller_card(self):
        self.set_wechat()
        response = self.get()
        self.assertNotContains(response, "Usually replies on WeChat")


class ViewCountTests(ListingTestBase):
    def views(self):
        self.listing.refresh_from_db()
        return self.listing.views

    def test_each_visit_by_a_non_seller_counts(self):
        url = reverse("listings:detail", args=[self.listing.pk])
        self.client.get(url)
        self.client.get(url)
        self.client.login(username="other", password="pass12345")
        self.client.get(url)
        self.assertEqual(self.views(), 3)

    def test_seller_visits_do_not_count(self):
        self.client.login(username="seller", password="pass12345")
        self.client.get(reverse("listings:detail", args=[self.listing.pk]))
        self.assertEqual(self.views(), 0)
