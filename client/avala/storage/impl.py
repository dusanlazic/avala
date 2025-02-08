import base64
import pickle
from typing import Any

from ..api_client.schemas import FlagsEnqueueBody
from .base import HashRedisStorage, SetRedisStorage


class BlobStorage(HashRedisStorage[Any]):
    """
    Simple Redis key-value store for storing arbitrary objects.
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
    Simple Redis set store for storing obtained flag ID hashes.
    """

    def _encode(self, value: str) -> bytes:
        if not isinstance(value, str):
            raise TypeError("Value must be a string.")
        return value.encode("utf-8")

    def _decode(self, value: bytes) -> str:
        return value.decode("utf-8")


class UnsentFlagStorage(SetRedisStorage[FlagsEnqueueBody]):
    """
    Simple Redis set store for storing unsent flags.
    """

    def _encode(self, value: FlagsEnqueueBody) -> bytes:
        if not isinstance(value, FlagsEnqueueBody):
            raise TypeError("Value must be of type EnqueueBody.")
        return value.model_dump_json().encode("utf-8")

    def _decode(self, value: bytes) -> FlagsEnqueueBody:
        return FlagsEnqueueBody.model_validate_json(value.decode("utf-8"))
