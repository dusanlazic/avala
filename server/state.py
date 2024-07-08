from .database import db
from .models import State


class StateManager:
    def __init__(self, db) -> None:
        self.db = db

    def get_state(self, key: str):
        with self.db.connection_context():
            state = State.get_or_none(State.key == key)
            return state.value if state else None

    def set_state(self, key: str, value: str):
        with self.db.connection_context():
            State.insert(
                key=key,
                value=value,
            ).on_conflict(
                conflict_target=[State.key],
                preserve=[State.value],
            ).execute()

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(f"'StateManager' object has no attribute '{name}'")
        return self.get_state(name)

    def __setattr__(self, name, value):
        if name.startswith("_") or name == "db":
            super().__setattr__(name, value)
        else:
            self.set_state(name, value)


state = StateManager(db)
