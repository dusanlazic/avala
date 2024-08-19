import pickle
from typing import Generator, Any
from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert
from .models import StoredObject
from .database import get_db


@contextmanager
def _use_or_get_db(db: Session | None = None) -> Generator[Session, None, None]:
    """
    A context manager that provides a new database session if one is not provided,
    or reuses the provided session. This context allows using existing sessions
    and minimizes the number of sessions created.

    :param db: Optional existing database session.
    :type db: Session | None, optional
    :yield: Provided or newly created database session.
    :rtype: Generator[Session, None, None]
    """
    if not db:
        with get_db() as new_db:
            yield new_db
    else:
        yield db


class BlobStorage:
    """
    A simple key-value store for storing arbitrary objects in local SQLite database.
    Objects are pickled before storing and unpickled when retrieved.
    """

    def __init__(self) -> None:
        pass

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self.put(key, value, overwrite=True)

    def __delitem__(self, key: str) -> None:
        self.delete(key)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def put(
        self,
        key: str,
        value: Any,
        overwrite: bool = True,
    ) -> Any:
        """
        Stores a key-value pair in the database. The value is pickled before storage.

        If the `overwrite` flag is set to `False`, the method will not overwrite the existing object associated with the given key.

        :param key: Key under which the value will be stored.
        :type key: str
        :param value: Value to store. Must be serializable.
        :type value: Any
        :param overwrite: If True, overwrites the existing value. If False and the key exists,
                          the function does nothing and returns None. Defaults to True.
        :type overwrite: bool, optional
        :raises ValueError: If the provided value is None.
        :return: Stored value, or None if the key already exists and `overwrite` is False.
        :rtype: Any
        """
        if value is None:
            raise ValueError("Cannot store None value.")

        with get_db() as db:
            obj_blob = pickle.dumps(value)

            try:
                if not overwrite and self.get(key, db):
                    return None
            except pickle.UnpicklingError:
                pass

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
    ) -> Any:
        """
        Retrieves and unpickles the value associated with the given key from the database.

        :param key: Key whose associated value is to be retrieved.
        :type key: str
        :param db: Optional database session. If not provided, a new session will be created.
        :type db: Session | None, optional
        :return: The deserialized value associated with the key, or None if the key does not exist.
        :rtype: Any
        """
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
        """
        Deletes the value associated with the given key from the database.

        :param key: Key whose associated entry is to be deleted.
        :type key: str
        :param db: Optional database session. If not provided, a new session will be created.
        :type db: Session | None, optional
        :return: True if the entry was successfully deleted, False if the key was not found.
        :rtype: bool
        """
        with _use_or_get_db(db) as db:
            return db.query(StoredObject).filter(StoredObject.key == key).delete() > 0


storage = BlobStorage()
