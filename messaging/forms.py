from django import forms

from .models import Message

MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5 MB


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["body", "image"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 1, "placeholder": "Type a message..."}),
            "image": forms.FileInput(attrs={"accept": "image/*"}),
        }
        labels = {"body": "", "image": ""}

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > MAX_PHOTO_SIZE:
            raise forms.ValidationError("Photos can be 5 MB at most.")
        return image

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("body") and not cleaned.get("image") and not self.errors:
            raise forms.ValidationError("Write a message or add a photo.")
        return cleaned
