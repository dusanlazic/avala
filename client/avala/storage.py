import pickle
from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert
from .models import StoredObject
from .database import get_db
from .shared.logs import logger


@contextmanager
def _use_or_get_db(db: Session | None = None):
    if db is None:
        with get_db() as new_db:
            yield new_db
    else:
        yield db


def store(
    key: str,
    value: any,
    overwrite: bool = True,
    db: Session | None = None,
):
    obj_blob = pickle.dumps(value)

    if not overwrite and exists(key, db):
        return None

    with _use_or_get_db(db) as db:
        db.execute(
            insert(StoredObject)
            .values(key=key, value=obj_blob)
            .on_conflict_do_update(
                index_elements=["key"],
                set_={"value": obj_blob},
            )
        )


def exists(
    key: str,
    db: Session | None = None,
):
    with _use_or_get_db(db) as db:
        return db.query(StoredObject).filter(StoredObject.key == key).count() > 0


def retrieve(
    key: str,
    db: Session | None = None,
):
    with _use_or_get_db(db) as db:
        stored_obj = (
            db.query(StoredObject.value).filter(StoredObject.key == key).first()
        )

        if stored_obj is None:
            return None

        try:
            obj = pickle.loads(stored_obj.value)
        except pickle.UnpicklingError:
            logger.error("Failed to unpickle stored object for key %s" % key)
            return None

        return obj
