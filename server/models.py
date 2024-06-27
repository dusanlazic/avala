import json
from collections import namedtuple
from shared.logs import logger
from datetime import datetime
from peewee import Model, CharField, DateTimeField, IntegerField, Check
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
    def serialize(self):
        return json.dumps(self._asdict())

    def deserialize(response):
        return FlagResponse(**json.loads(response))


def create_tables():
    db.create_tables([Flag])
    Flag.add_index(Flag.value)

    logger.info("Created tables and indexes.")
