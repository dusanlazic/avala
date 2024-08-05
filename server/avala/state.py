from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from .models import State


class StateManager:
    def __init__(self, db: Session) -> None:
        self.db: Session = db

    def get_state(self, key: str):
        state = self.db.query(State).filter(State.key == key).first()
        return state.value if state else None

    def set_state(self, key: str, value: str):
        self.db.execute(
            insert(State)
            .values(key=key, value=value)
            .on_conflict_do_update(
                index_elements=[State.key],
                set_={"value": value},
            )
        )

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(f"'StateManager' object has no attribute '{name}'")
        return self.get_state(name)

    def __setattr__(self, name, value):
        if name.startswith("_") or name == "db":
            super().__setattr__(name, value)
        else:
            self.set_state(name, value)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db = None
