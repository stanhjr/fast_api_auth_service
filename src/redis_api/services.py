import json
import os
from typing import Optional, Union

import redis

REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")


class RedisCacheService:
    """
    Redis cache service for storing and retrieving data from Redis.
    """

    def __init__(self, db_number: int = 0, data_ttl: int = 30):
        """
        Initialize the RedisCacheService with a Redis connection.
        """
        self.redis_session = redis.StrictRedis(
            host="redis",
            port=6379,
            password=REDIS_PASSWORD,
            db=db_number
        )
        self.data_ttl = data_ttl

    def clear_cache(self) -> None:
        """
        Clear the entire Redis cache by flushing the database.
        """
        self.redis_session.flushdb()

    def set_ttl(self, ttl: int) -> int:
        self.data_ttl = ttl
        return self.data_ttl

    def set_requests_number(self, device_id: str):
        ...

    def get_cache_data(self, key: str) -> Optional[Union[dict, list]]:
        """
        Retrieve cached data from Redis based on the specified key.

        Args:
            key (str): The key to retrieve cached data for.

        Returns:
            Optional[Union[dict, list]]: The cached data as a dictionary or list, or None if not found.
        """
        data = self.redis_session.get(key)
        if data:
            return json.loads(data)

    def set_cache_data(self, key: str, data: Union[dict, list]) -> None:
        """
        Set cached data in Redis with the specified key and TTL.

        Args:
            key (str): The key to set cached data for.
            data (Union[dict, list]): The data to be cached, either a dictionary or a list.
        """
        json_data = json.dumps(data)
        self.redis_session.set(key, json_data)
        self.redis_session.expire(key, self.data_ttl)

    def delete_keys(self, keys: list) -> None:
        """
        Delete the specified keys from Redis.

        Args:
            keys (list): A list of keys to be deleted.
        """
        self.redis_session.delete(*keys)
