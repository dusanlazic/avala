from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import RedisDsn
from redis import Redis

T = TypeVar("T")


class BaseRedisStorage(ABC, Generic[T]):
    """
    Abstract base class for Redis-based stores.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379", name: str = "storage") -> None:
        """
        Initializes the storage with connection to a Redis instance.

        :param redis_url: Redis connection URL, defaults to "redis://localhost:6379"
        :type redis_url: str, optional
        :param name: Name of the Redis storage, defaults to "storage"
        :type name: str, optional
        """
        redis_dsn = RedisDsn(redis_url)

        self._redis = Redis(
            host=redis_dsn.host,
            port=redis_dsn.port,
            password=redis_dsn.password,
            decode_responses=False,
        )
        self._name = name

    @abstractmethod
    def _encode(self, value: T) -> bytes:
        """
        Encodes a value for storage in Redis.

        :param value: The value to encode.
        :type value: T
        :return: The encoded value.
        :rtype: bytes
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


class HashRedisStorage(BaseRedisStorage[T]):
    """
    Key-value store implemented as a Redis hash.
    """

    def put(self, key: str, value: T, overwrite: bool = True) -> None:
        """
        Stores a key-value pair in Redis hash.

        :param key: The key under which the value will be stored.
        :type key: str
        :param value: The value to store.
        :type value: T
        :param overwrite: Whether to overwrite the existing value. Defaults to True.
        :type overwrite: bool, optional
        """
        if value is None:
            raise ValueError("Cannot store None value.")

        if not overwrite and self._redis.hget(self._name, key) is not None:
            raise KeyError(f"Key '{key}' already exists and overwrite is set to False.")

        encoded_value = self._encode(value)
        self._redis.hset(self._name, key, encoded_value)  # type: ignore

    def get(self, key: str) -> T:
        """
        Retrieves a value associated with the given key from Redis hash.

        :param key: The key to retrieve.
        :type key: str
        :raises KeyError: If the key does not exist.
        :return: The value associated with the key.
        :rtype: T
        """
        value: bytes | None = self._redis.hget(self._name, key)  # type: ignore
        if value is None:
            raise KeyError(f"Key '{key}' not found.")
        return self._decode(value)

    def delete(self, key: str) -> bool:
        """
        Deletes the value associated with the given key from Redis hash.

        :param key: The key to delete.
        :type key: str
        :return: True if the value was deleted, False otherwise.
        :rtype: bool
        """
        if self._redis.hdel(self._name, key):
            return True
        raise KeyError(f"Key '{key}' not found.")

    def contains(self, key: str) -> bool:
        """
        Checks if the given key exists in the Redis hash.

        :param key: The key to check.
        :type key: str
        :return: True if the key exists, False otherwise.
        :rtype: bool
        """
        return self._redis.hexists(self._name, key)  # type: ignore

    def size(self) -> int:
        """
        Returns the size of the Redis hash.

        :return: Size of the hash.
        :rtype: int
        """
        return self._redis.hlen(self._name)  # type: ignore[return-value]

    def __getitem__(self, key: str) -> T:
        return self.get(key)

    def __setitem__(self, key: str, value: T) -> None:
        self.put(key, value)

    def __delitem__(self, key: str) -> None:
        self.delete(key)

    def __contains__(self, key: str) -> bool:
        return self.contains(key)


class SetRedisStorage(BaseRedisStorage[T]):
    """
    Storage for managing a Redis set.
    """

    def add(self, *values: T) -> None:
        """
        Stores one or more values in a Redis set.

        :param values: Values to store.
        :type values: T
        """
        encoded_values = [self._encode(value) for value in values]
        self._redis.sadd(self._name, *encoded_values)

    def remove(self, *values: T) -> None:
        """
        Removes one or more values from a Redis set.

        :param values: Values to remove.
        :type values: T
        """
        encoded_values = [self._encode(value) for value in values]
        self._redis.srem(self._name, *encoded_values)

    def pop(self) -> T | None:
        """
        Retrieves and removes a random value from the Redis set.

        :return: Popped value.
        :rtype: T
        """
        raw_value: bytes | None = self._redis.spop(self._name)  # type: ignore
        return self._decode(raw_value) if raw_value is not None else None

    def contains(self, value: T) -> bool:
        """
        Checks if a value exists in the Redis set.

        :param value: The value to check.
        :type value: T
        :return: True if the value exists, False otherwise.
        :rtype: bool
        """
        encoded_value = self._encode(value)
        return self._redis.sismember(self._name, encoded_value) == 1  # type: ignore

    def size(self) -> int:
        """
        Returns the size of the Redis set.

        :return: Size of the set.
        :rtype: int
        """
        return self._redis.scard(self._name)  # type: ignore[return-value]

    def __contains__(self, value: T) -> bool:
        return self.contains(value)
