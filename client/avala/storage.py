import base64
import pickle
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from redis import Redis

T = TypeVar("T")


class BaseRedisStorage(ABC, Generic[T]):
    """
    Abstract base class for Redis-based stores.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: str | None = None,
        hash_name: str = "storage",
    ) -> None:
        """
        Initializes the storage with connection to a Redis instance.

        :param host: Host to Redis, defaults to "localhost"
        :type host: str, optional
        :param port: Port to Redis, defaults to 6379
        :type port: int, optional
        :param password: Password to Redis, defaults to None
        :type password: str | None, optional
        :param hash_name: Name of the Redis hash to use, defaults to "storage"
        :type hash_name: str, optional
        """
        self._redis = Redis(host=host, port=port, password=password, decode_responses=False)
        self._hash = hash_name

    @abstractmethod
    def _encode(self, value: T) -> bytes:
        """
        Encodes a value for storage in Redis.

        :param value: The value to encode.
        :type value: T
        :return: The encoded value.
        :rtype: str
        """
        pass

    @abstractmethod
    def _decode(self, value: bytes) -> T:
        """
        Decodes a value retrieved from Redis.

        :param value: The value to decode.
        :type value: bytes
        :return: The decoded value.
        :rtype: T
        """
        pass

    def __getitem__(self, key: str) -> T:
        """
        Retrieves a value associated with the given key.

        :param key: The key to retrieve.
        :type key: str
        :return: The value associated with the key.
        :rtype: T
        """
        return self.get(key)

    def __setitem__(self, key: str, value: T) -> None:
        """
        Sets a value for the given key.

        :param key: The key to set.
        :type key: str
        :param value: The value to set.
        :type value: T
        """
        self.put(key, value, overwrite=True)

    def __delitem__(self, key: str) -> None:
        """
        Deletes the value associated with the given key.

        :param key: The key to delete.
        :type key: str
        """
        self.delete(key)

    def __contains__(self, key: str) -> bool:
        """
        Checks if the given key exists in the storage.

        :param key: The key to check.
        :type key: str
        :return: True if the key exists, False otherwise.
        :rtype: bool
        """
        return self.contains(key)

    def put(self, key: str, value: T, overwrite: bool = True) -> None:
        """
        Stores a key-value pair in Redis.

        :param key: The key under which the value will be stored.
        :type key: str
        :param value: The value to store.
        :type value: T
        :param overwrite: Whether to overwrite the existing value. Defaults to True.
        :type overwrite: bool, optional
        :raises ValueError: If the value is None.
        :raises KeyError: If the key exists and overwrite is set to False.
        :return: The stored value.
        :rtype: T
        """
        if value is None:
            raise ValueError("Cannot store None value.")

        if not overwrite and self._redis.hget(self._hash, key) is not None:
            raise KeyError(f"Key '{key}' already exists and overwrite is set to False.")

        encoded_value = self._encode(value)
        self._redis.hset(self._hash, key, encoded_value)  # type: ignore

    def get(self, key: str) -> T:
        """
        Retrieves a value associated with the given key from Redis.

        :param key: The key to retrieve.
        :type key: str
        :raises KeyError: If the key does not exist.
        :return: The value associated with the key.
        :rtype: T
        """
        value: bytes | None = self._redis.hget(self._hash, key)  # type: ignore
        if value is None:
            raise KeyError(f"Key '{key}' not found.")

        return self._decode(value)

    def delete(self, key: str) -> bool:
        """
        Deletes the value associated with the given key from Redis.

        :param key: The key to delete.
        :type key: str
        :raises KeyError: If the key does not exist.
        :return: True if the value was deleted, False otherwise.
        :rtype: bool
        """
        if self._redis.hdel(self._hash, key):
            return True
        raise KeyError(f"Key '{key}' not found.")

    def contains(self, key: str) -> bool:
        """
        Checks if the key exists in Redis.

        :param key: The key to check.
        :type key: str
        :return: True if the key exists, False otherwise.
        :rtype: bool
        """
        return self._redis.hexists(self._hash, key)  # type: ignore


class BlobStorage(BaseRedisStorage[Any]):
    """
    Simple key-value store for storing arbitrary objects in Redis.
    Objects are pickled before storing and unpickled when retrieved.
    """

    def _encode(self, value: Any) -> bytes:
        """
        Encodes the value using pickle and base64 encoding.

        :param value: The value to encode.
        :type value: Any
        :return: The encoded value.
        :rtype: bytes
        """
        obj_blob = pickle.dumps(value)
        return base64.b64encode(obj_blob)

    def _decode(self, value: bytes) -> Any:
        """
        Decodes the value using base64 decoding and pickle.

        :param value: The value to decode.
        :type value: str
        :return: The decoded value.
        :rtype: Any
        """
        obj_blob = base64.b64decode(value)
        return pickle.loads(obj_blob)


class StringStorage(BaseRedisStorage[str]):
    """
    Simple key-value store for storing strings in Redis.
    Strings are utf-8 encoded before storing and decoded when retrieved.
    """

    def _encode(self, value: str) -> bytes:
        """
        Encodes the string value.

        :param value: The string to encode.
        :type value: str
        :return: The encoded string.
        :rtype: bytes
        """
        if not isinstance(value, str):
            raise TypeError("Value must be a string.")
        return value.encode("utf-8")

    def _decode(self, value: bytes) -> str:
        """
        Decodes the string value.

        :param value: The string to decode.
        :type value: bytes
        :return: The decoded string.
        :rtype: str
        """
        return value.decode("utf-8")
