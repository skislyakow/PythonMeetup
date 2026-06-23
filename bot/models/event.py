from peewee import AutoField, CharField, DateTimeField, ForeignKeyField

from bot.models import db
from bot.models.user import User


class Event(db.Model):
    id = AutoField()
    speaker = ForeignKeyField(User, backref="events")
    title = CharField(max_length=300)
    start_time = DateTimeField()
    end_time = DateTimeField()

    class Meta:
        database = db
