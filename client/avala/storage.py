import pickle
from base64 import b64decode, b64encode
from typing import Any

import redis


class BlobStorage:
    """
    A simple key-value store for storing arbitrary objects in Redis.
    Objects are pickled before storing and unpickled when retrieved.
    All keys are tracked in a Redis hash named 'blobs'.
    """

    def __init__(self, host: str = "localhost", port: int = 6379, password: str | None = None) -> None:
        """
        Initializes the BlobStorage with a connection to Redis.

        :param host: Host to Redis, defaults to "localhost"
        :type host: str, optional
        :param port: Port to Redis, defaults to 6379
        :type port: int, optional
        :param password: Password to Redis, defaults to None
        :type password: str | None, optional
        """
        self._redis = redis.Redis(host=host, port=port, password=password, decode_responses=False)
        self._blob_hash = "blobs"

    def __getitem__(self, key: str) -> Any:
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self.put(key, value, overwrite=True)

    def __delitem__(self, key: str) -> None:
        self.delete(key)

    def __contains__(self, key: str) -> bool:
        return self.contains(key)

    def get(self, key: str) -> Any:
        """
        Retrieves and unpickles the value associated with the given key from Redis.

        :param key: Key whose associated value is to be retrieved.
        :type key: str
        :raises KeyError: If the key does not exist.
        :return: The deserialized value associated with the key, or None if the key does not exist.
        :rtype: Any
        """
        b64_obj_blob: str | None = self._redis.hget(self._blob_hash, key)  # type: ignore
        if not b64_obj_blob:
            raise KeyError(f"Key '{key}' not found.")

        return self.decode_and_unpickle(b64_obj_blob)

    def put(self, key: str, value: Any, overwrite: bool = True) -> Any:
        """
        Stores a key-value pair in the Redis hash. The value is pickled before storage.

        If the `overwrite` flag is set to `False`, the method will not overwrite the existing object associated with the
        given key and will raise a ValueError instead.

        :param key: Key under which the value will be stored.
        :type key: str
        :param value: Value to store. Must be serializable.
        :type value: Any
        :param overwrite: If True, overwrites the existing value. If False and the key exists,
                          the function does nothing and returns None. Defaults to True.
        :type overwrite: bool, optional
        :raises ValueError: If the provided value is None, or if the key already exists and `overwrite` is False.
        :return: Stored value, or None if the key already exists and `overwrite` is False.
        :rtype: Any
        """
        if value is None:
            raise ValueError("Cannot store None value.")

        if not overwrite and self._redis.hget(self._blob_hash, key) is not None:
            raise KeyError(f"Key '{key}' already exists and overwrite is set to False.")

        b64_obj_blob = self.pickle_and_encode(value)
        self._redis.hset(self._blob_hash, key, b64_obj_blob)
        return value

    def delete(self, key: str) -> bool:
        """
        Deletes the value associated with the given key from Redis and removes the key from the 'blobs' set.

        :param key: Key whose associated entry is to be deleted.
        :type key: str
        :raises KeyError: If the key does not exist.
        :return: True if the entry was successfully deleted, False if the key was not found.
        :rtype: bool
        """
        if self._redis.hdel(self._blob_hash, key) == 1:
            return True
        raise KeyError(f"Key '{key}' not found.")

    def contains(self, key: str) -> bool:
        """
        Checks if the key exists in the Redis hash.

        :param key: Key to check.
        :type key: str
        :return: True if the key exists, False otherwise.
        :rtype: bool
        """
        return self._redis.hexists(self._blob_hash, key)  # type: ignore

    @staticmethod
    def pickle_and_encode(value: Any) -> str:
        """
        Encodes a value using base64 encoding.

        :param value: Value to encode.
        :type value: Any
        :return: Encoded value.
        :rtype: str
        """
        return b64encode(pickle.dumps(value)).decode("utf-8")

    @staticmethod
    def decode_and_unpickle(value: str) -> Any:
        """
        Decodes a value using base64 encoding.

        :param value: Value to decode.
        :type value: str
        :return: Decoded value.
        :rtype: Any
        """
        return pickle.loads(b64decode(value))
