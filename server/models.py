import json
from sqlalchemy import Column, Text, Integer, String, DateTime, func
from sqlalchemy.schema import CheckConstraint
from collections import namedtuple
from shared.logs import logger
from .database import Base, engine


class Flag(Base):
    __tablename__ = "flags"

    id = Column(Integer, primary_key=True)  # Add an explicit primary key column
    value = Column(String, unique=True, index=True)
    exploit = Column(String)
    player = Column(String)
    tick = Column(Integer)
    target = Column(String)
    timestamp = Column(DateTime, default=func.now())
    status = Column(String, nullable=False)
    response = Column(String, nullable=True)

    __table_args__ = (CheckConstraint("status IN ('queued', 'accepted', 'rejected')"),)


class State(Base):
    __tablename__ = "states"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)


class FlagResponse(namedtuple("FlagResponse", "value status response")):
    def to_json(self):
        return json.dumps(self._asdict())

    @staticmethod
    def from_json(response):
        return FlagResponse(**json.loads(response))
