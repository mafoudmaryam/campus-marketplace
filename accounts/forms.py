from django import forms
from django.core.files.uploadedfile import UploadedFile

from .models import Profile


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["display_name", "campus", "wechat_id", "avatar"]

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if isinstance(avatar, UploadedFile) and avatar.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Please upload an image smaller than 5 MB.")
        return avatar