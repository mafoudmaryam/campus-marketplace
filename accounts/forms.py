from django import forms
from django.core.files.uploadedfile import UploadedFile

from .models import Profile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["display_name", "campus", "wechat_id", "wechat_qr", "avatar"]
        labels = {"wechat_qr": "WeChat QR code"}
        help_texts = {
            "wechat_qr": "Open WeChat > Me > tap your QR code > Save image, then upload it here",
        }

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if isinstance(avatar, UploadedFile) and avatar.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Please upload an image smaller than 5 MB.")
        return avatar

    def clean_wechat_qr(self):
        qr = self.cleaned_data.get("wechat_qr")
        if isinstance(qr, UploadedFile) and qr.size > 2 * 1024 * 1024:
            raise forms.ValidationError("Please upload an image smaller than 2 MB.")
        return qr