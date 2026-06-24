from django.db import models


class TelegramUser(models.Model):
    ROLE_CHOICES = [
        ("guest", "Гость"),
        ("speaker", "Спикер"),
        ("organizer", "Организатор"),
    ]
    user_id = models.IntegerField(primary_key=True)
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default="guest"
    )
    full_name = models.CharField(max_length=200, default="")

    class Meta:
        db_table = "users"
