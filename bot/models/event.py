from django.db import models


class Event(models.Model):
    speaker = models.ForeignKey(
        "TelegramUser", on_delete=models.CASCADE, related_name="events"
    )
    title = models.CharField(max_length=300)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_active = models.BooleanField(default=False)

    class Meta:
        db_table = "events"

    def save(self, *args, **kwargs):
        if self.is_active:
            Event.objects.filter(is_active=True).exclude(pk=self.pk).update(
                is_active=False
            )
            super().save(*args, **kwargs)
