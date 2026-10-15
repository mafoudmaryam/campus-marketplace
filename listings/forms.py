from django import forms

from .models import Listing, ListingImage

MAX_PHOTOS = 5
MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5 MB


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    """An image field that accepts several files at once."""

    widget = MultipleFileInput

    def clean(self, data, initial=None):
        if not data:
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        return [super(MultipleImageField, self).clean(item, initial) for item in data]


class ListingForm(forms.ModelForm):
    # Declared before "images" so it is cleaned first and clean_images can use it.
    remove_images = forms.ModelMultipleChoiceField(
        queryset=ListingImage.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Remove photos",
    )
    images = MultipleImageField(
        required=False,
        label="Photos",
        help_text="Up to 5 photos, 5 MB each.",
    )

    class Meta:
        model = Listing
        # seller and status are not here on purpose: the view sets them.
        fields = ["title", "description", "price", "category", "condition", "campus"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxSelectMultiple):
                continue
            css = "form-select" if isinstance(widget, forms.Select) else "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()
        if self.instance.pk:
            # Only this listing's own photos can be removed.
            self.fields["remove_images"].queryset = self.instance.images.all()
        self.fields["images"].widget.attrs["accept"] = "image/*"

    def clean_price(self):
        price = self.cleaned_data["price"]
        if price < 0:
            raise forms.ValidationError("Price cannot be negative.")
        return price

    def clean_images(self):
        images = self.cleaned_data.get("images") or []
        already_saved = self.instance.images.count() if self.instance.pk else 0
        already_saved -= len(self.cleaned_data.get("remove_images") or [])
        if already_saved + len(images) > MAX_PHOTOS:
            raise forms.ValidationError(f"A listing can have at most {MAX_PHOTOS} photos.")
        for image in images:
            if image.size > MAX_PHOTO_SIZE:
                raise forms.ValidationError(f"{image.name} is bigger than 5 MB.")
        return images

    def save(self, commit=True):
        listing = super().save(commit=commit)
        if commit:
            self.save_images()
        return listing

    def save_images(self):
        for photo in self.cleaned_data.get("remove_images") or []:
            photo.delete()
        for image in self.cleaned_data.get("images", []):
            ListingImage.objects.create(listing=self.instance, image=image)
