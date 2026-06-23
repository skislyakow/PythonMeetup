from django.contrib import admin
from .telegram_user import TelegramUser
from .event import Event
from .question import Question


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ("user_id", "full_name", "role")
    list_filter = ("role",)
    search_fields = ("full_name", "user_id")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "speaker", "start_time", "end_time")
    list_filter = ("start_time",)
    search_fields = ("title",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("from_user", "to_speaker", "text", "created_at")
    list_filter = ("created_at",)
