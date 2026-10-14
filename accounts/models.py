from django.conf import settings
from django.db import models


class Profile(models.Model):
    class Campus(models.TextChoices):
        WANGJIANG = "wangjiang", "Wangjiang"
        JIANGAN = "jiangan", "Jiang'an"
        HUAXI = "huaxi", "Huaxi"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=50, blank=True)
    campus = models.CharField(max_length=10, choices=Campus.choices, default=Campus.WANGJIANG)
    wechat_id = models.CharField(max_length=50, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True)

    def __str__(self):
        return self.display_name or self.user.username