from .database import db
from .models import State


def initialize_state():
    with db.connection_context():
        State.insert_many(
            [
                {"key": "teams_json_hash", "value": None},
            ]
        ).on_conflict_ignore().execute()


def get_state(key: str):
    with db.connection_context():
        state = State.get_or_none(State.key == key)
        return state.value if state else None


def set_state(key: str, value: str):
    with db.connection_context():
        State.insert(
            key=key,
            value=value,
        ).on_conflict(
            conflict_target=[State.key],
            preserve=[State.value],
        ).execute()
