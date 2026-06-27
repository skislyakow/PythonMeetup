from django.db import models


class TelegramUser(models.Model):
    ROLE_CHOICES = [
        ("guest", "Гость"),
        ("speaker", "Спикер"),
        ("organizer", "Организатор"),
    ]
    user_id = models.IntegerField(primary_key=True)
    username = models.CharField(max_length=100, default="", blank=True)
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default="guest"
    )
    full_name = models.CharField(max_length=200, default="")
    is_organizer = models.BooleanField(default=False)
    is_speaker = models.BooleanField(default=False) 
    class Meta:
        db_table = "users"
