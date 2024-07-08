import json
from collections import namedtuple
from shared.logs import logger
from datetime import datetime
from peewee import Model, CharField, TextField, DateTimeField, IntegerField, Check
from .database import db


class BaseModel(Model):
    class Meta:
        database = db


class Flag(BaseModel):
    value = CharField(unique=True)
    exploit = CharField()
    player = CharField()
    tick = IntegerField()
    target = CharField()
    timestamp = DateTimeField(default=datetime.now)
    status = CharField(
        constraints=[Check("status IN ('queued', 'accepted', 'rejected')")]
    )
    response = CharField(null=True)


class FlagResponse(namedtuple("FlagResponse", "value status response")):
    def to_json(self):
        return json.dumps(self._asdict())

    @staticmethod
    def from_json(response):
        return FlagResponse(**json.loads(response))


class State(BaseModel):
    key = CharField(unique=True)
    value = TextField(null=True)


def create_tables():
    db.create_tables([Flag, State])
    Flag.add_index(Flag.value)

    logger.info("Created tables and indexes.")
