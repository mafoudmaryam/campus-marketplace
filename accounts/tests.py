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
