from peewee import CharField, IntegerField

from bot.models import db


class User(db.Model):
    user_id = IntegerField(primary_key=True)  # Telegram ID
    role = CharField(default="guest")  # guest | speaker | organizer
    full_name = CharField(max_length=200, default="")

    class Meta:
        database = db
