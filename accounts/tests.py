import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

User = get_user_model()


def make_qr(size_bytes=0, name="qr.png"):
    """A valid PNG, padded with trailing bytes to reach roughly size_bytes."""
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), "black").save(buffer, format="PNG")
    data = buffer.getvalue()
    data += b"\0" * max(0, size_bytes - len(data))
    return SimpleUploadedFile(name, data, content_type="image/png")


class WechatQrUploadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("alice", password="pass12345")
        self.client.login(username="alice", password="pass12345")
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)

    def post(self, qr):
        data = {"display_name": "Alice", "campus": "wangjiang", "wechat_id": "alice_wx", "wechat_qr": qr}
        with override_settings(MEDIA_ROOT=self.media):
            return self.client.post(reverse("accounts:edit_profile"), data)

    def test_edit_form_shows_help_text(self):
        response = self.client.get(reverse("accounts:edit_profile"))
        self.assertContains(response, "Open WeChat > Me > tap your QR code > Save image, then upload it here")

    def test_small_qr_is_saved(self):
        response = self.post(make_qr())
        self.assertEqual(response.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.wechat_qr)

    def test_qr_over_2_mb_is_rejected(self):
        response = self.post(make_qr(2 * 1024 * 1024 + 1))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "smaller than 2 MB")
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.wechat_qr)


class ProfileWechatTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("bob", password="pass12345")
        User.objects.create_user("viewer", password="pass12345")
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        profile = self.owner.profile
        profile.wechat_id = "bob_wx"
        with override_settings(MEDIA_ROOT=self.media):
            profile.wechat_qr = make_qr()
            profile.save()
        self.url = reverse("accounts:profile", args=["bob"])

    def get(self):
        with override_settings(MEDIA_ROOT=self.media):
            return self.client.get(self.url)

    def test_anonymous_user_does_not_see_wechat(self):
        response = self.get()
        self.assertNotContains(response, "bob_wx")
        self.assertNotContains(response, "wechat_qr/")
        self.assertContains(response, "to see contact details")

    def test_logged_in_user_sees_id_and_qr(self):
        self.client.login(username="viewer", password="pass12345")
        response = self.get()
        self.assertContains(response, "bob_wx")
        self.assertContains(response, "Chat on WeChat")
        self.assertContains(response, "Scan with WeChat")

    def test_owner_does_not_see_bar_on_own_profile(self):
        self.client.login(username="bob", password="pass12345")
        self.assertNotContains(self.get(), "Chat on WeChat")


class WechatFormLabelTests(TestCase):
    def test_wechat_id_label_and_example(self):
        User.objects.create_user("carol", password="pass12345")
        self.client.login(username="carol", password="pass12345")
        response = self.client.get(reverse("accounts:edit_profile"))
        self.assertContains(response, "WeChat ID (for buyers to add you)")
        self.assertContains(response, "Find it in WeChat > Me > your name > WeChat ID")


class EditProfilePageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("dana", password="pass12345")
        self.client.login(username="dana", password="pass12345")
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.url = reverse("accounts:edit_profile")

    def post(self, **extra):
        data = {"display_name": "Dana", "campus": "huaxi", "wechat_id": ""}
        data.update(extra)
        with override_settings(MEDIA_ROOT=self.media):
            return self.client.post(self.url, data)

    def test_progress_starts_at_a_quarter(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context["percent"], 25)
        self.assertContains(response, "Add your WeChat ID or QR code")

    def test_campus_is_picked_with_cards(self):
        self.post()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.campus, "huaxi")
        response = self.client.get(self.url)
        self.assertContains(response, 'value="huaxi" checked')

    def test_photo_can_be_added_and_removed(self):
        self.post(avatar=make_qr(name="me.png"))
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.avatar)
        self.assertEqual(self.client.get(self.url).context["percent"], 75)
        self.post(**{"avatar-clear": "on"})
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.profile.avatar)
