from datetime import datetime
from playhouse.postgres_ext import JSONField
from peewee import (
    CharField,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    UUIDField,
    BooleanField,
    Check,
    SQL,
)
from .database import BaseModel


class Client(BaseModel):
    id = UUIDField(primary_key=True)
    ip = CharField()
    alias = CharField()
    note = CharField(null=True)
    last_seen = DateTimeField()


class Exploit(BaseModel):
    id = UUIDField(primary_key=True)
    alias = CharField()
    maintainer = CharField()
    config = JSONField()
    client = ForeignKeyField(Client, to_field="id", backref="exploits")


class Flag(BaseModel):
    value = CharField(unique=True)
    exploit = ForeignKeyField(Exploit, to_field="id", backref="flags")
    tick = IntegerField()
    target = CharField()
    timestamp = DateTimeField(default=datetime.now)
    status = CharField(
        constraints=[Check("status IN ('queued', 'accepted', 'rejected')")]
    )
    response = CharField(null=True)
