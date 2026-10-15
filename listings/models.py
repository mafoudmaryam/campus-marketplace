from django.conf import settings
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Listing(models.Model):
    class Condition(models.TextChoices):
        NEW = "new", "New"
        LIKE_NEW = "like_new", "Like new"
        GOOD = "good", "Good"
        FAIR = "fair", "Fair"

    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        RESERVED = "reserved", "Reserved"
        SOLD = "sold", "Sold"

    class Campus(models.TextChoices):
        WANGJIANG = "wangjiang", "Wangjiang"
        JIANGAN = "jiangan", "Jiang'an"
        HUAXI = "huaxi", "Huaxi"

    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listings")
    title = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    condition = models.CharField(max_length=10, choices=Condition.choices, default=Condition.GOOD)
    campus = models.CharField(max_length=10, choices=Campus.choices, default=Campus.WANGJIANG)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.AVAILABLE)
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="listing_status_created_idx"),
            models.Index(fields=["campus"], name="listing_campus_idx"),
            models.Index(fields=["title"], name="listing_title_idx"),
        ]

    def __str__(self):
        return self.title


class ListingImage(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="listings/")