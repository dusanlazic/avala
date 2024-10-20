from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .models import State


class StateManager:
    """
    A simple key-value store for storing string values in the database.
    """

    def __init__(self, db: Session) -> None:
        self.db: Session = db

    def get(self, key: str):
        state = self.db.query(State).filter(State.key == key).first()
        return state.value if state else None

    def put(self, key: str, value: str):
        if not isinstance(value, str):
            raise TypeError("Stored state value must be a string.")

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
        return self.get(name)

    def __setattr__(self, name, value):
        if name.startswith("_") or name == "db":
            super().__setattr__(name, value)
        else:
            self.put(name, value)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
