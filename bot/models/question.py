from django.db import models


class Question(models.Model):
    from_user = models.ForeignKey(
        "TelegramUser", on_delete=models.CASCADE, related_name="questions_asked"
    )
    to_speaker = models.ForeignKey(
        "TelegramUser", on_delete=models.CASCADE, related_name="questions_received"
    )
    text = models.CharField(max_length=2000)
    answer = models.CharField(max_length=2000, null=True, blank=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "questions"
