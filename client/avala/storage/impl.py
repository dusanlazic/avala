import base64
import pickle
from typing import Any

from .base import HashRedisStorage, SetRedisStorage


class BlobStorage(HashRedisStorage[Any]):
    """
    Simple key-value store for storing arbitrary objects in Redis.
    Objects are pickled before storing and unpickled when retrieved.
    """

    def _encode(self, value: Any) -> bytes:
        obj_blob = pickle.dumps(value)
        return base64.b64encode(obj_blob)

    def _decode(self, value: bytes) -> Any:
        obj_blob = base64.b64decode(value)
        return pickle.loads(obj_blob)


class FlagIdsHashStorage(SetRedisStorage[str]):
    """
    Simple hash store for storing obtained flag ID hashes in Redis.
    """

    def _encode(self, value: str) -> bytes:
        if not isinstance(value, str):
            raise TypeError("Value must be a string.")
        return value.encode("utf-8")

    def _decode(self, value: bytes) -> str:
        return value.decode("utf-8")
