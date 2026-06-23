from django.db import models


class Event(models.Model):
    speaker = models.ForeignKey(
        "TelegramUser", on_delete=models.CASCADE, related_name="events"
    )
    title = models.CharField(max_length=300)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    class Meta:
        db_table = "events"
