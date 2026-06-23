from peewee import AutoField, CharField, DateTimeField, ForeignKeyField

from bot.models import db
from bot.models.user import User


class Question(db.Model):
    id = AutoField()
    from_user = ForeignKeyField(User, backref="questions_asked")
    to_speaker = ForeignKeyField(User, backref="questions_received")
    text = CharField(max_length=2000)
    answer = CharField(max_length=2000, null=True)
    created_at = DateTimeField()

    class Meta:
        database = db
