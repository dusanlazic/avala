import pickle
from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert
from .models import StoredObject
from .database import get_db


@contextmanager
def _use_or_get_db(db: Session | None = None):
    if not db:
        with get_db() as new_db:
            yield new_db
    else:
        yield db


class BlobStorage:
    def __init__(self) -> None:
        pass

    def __getitem__(self, key: str) -> any:
        return self.get(key)

    def __setitem__(self, key: str, value: any) -> None:
        self.put(key, value, overwrite=True)

    def __delitem__(self, key: str) -> None:
        self.delete(key)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def put(
        self,
        key: str,
        value: any,
        overwrite: bool = True,
    ) -> any:
        if value is None:
            raise ValueError("Cannot store None value.")

        obj_blob = pickle.dumps(value)

        try:
            if not overwrite and self.get(key):
                return None
        except pickle.UnpicklingError:
            pass

        with get_db() as db:
            db.execute(
                insert(StoredObject)
                .values(key=key, value=obj_blob)
                .on_conflict_do_update(
                    index_elements=["key"],
                    set_={"value": obj_blob},
                )
            )

        return value

    def get(
        self,
        key: str,
        db: Session | None = None,
    ) -> any:
        with _use_or_get_db(db) as db:
            stored_obj = db.query(StoredObject).filter(StoredObject.key == key).first()

            if stored_obj is None:
                return None

            return pickle.loads(stored_obj.value)

    def delete(
        self,
        key: str,
        db: Session | None = None,
    ) -> bool:
        with _use_or_get_db(db) as db:
            return db.query(StoredObject).filter(StoredObject.key == key).delete() > 0


storage = BlobStorage()
