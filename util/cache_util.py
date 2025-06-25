from datetime import datetime, timedelta
from typing import Any, Dict, Tuple, Optional

class InMemoryCache:
    def __init__(self, default_ttl_seconds: int = 3600): # Default to 1 hour
        self._cache: Dict[str, Tuple[Any, datetime]] = {} # {key: (value, expiration_datetime)}
        self.default_ttl_seconds = default_ttl_seconds

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """
        Stores a value in the cache with an optional TTL.
        If ttl_seconds is None, uses the default_ttl_seconds.
        """
        if ttl_seconds is None:
            ttl_seconds = self.default_ttl_seconds
            
        expiration_time = datetime.now() + timedelta(seconds=ttl_seconds)
        self._cache[key] = (value, expiration_time)
        print(f"Cache: Set '{key}', expires at {expiration_time.strftime('%Y-%m-%d %H:%M:%S')}")

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieves a value from the cache. Returns None if key not found or expired.
        Automatically cleans up expired items on access.
        """
        if key not in self._cache:
            print(f"Cache: '{key}' not found.")
            return None

        value, expiration_time = self._cache[key]
        
        if datetime.now() < expiration_time:
            print(f"Cache: Hit for '{key}'. Valid until {expiration_time.strftime('%Y-%m-%d %H:%M:%S')}")
            return value
        else:
            print(f"Cache: '{key}' found but expired. Expired at {expiration_time.strftime('%Y-%m-%d %H:%M:%S')}. Removing.")
            del self._cache[key] # Remove expired item
            return None

    def invalidate(self, key: str):
        """
        Manually invalidates/removes a specific key from the cache.
        """
        if key in self._cache:
            del self._cache[key]
            print(f"Cache: Manually invalidated '{key}'.")
        else:
            print(f"Cache: '{key}' not found for invalidation.")

    def clear_all(self):
        """
        Clears all entries from the cache.
        """
        self._cache.clear()
        print("Cache: All entries cleared.")

    def get_status(self):
        """
        Returns the current number of items in the cache and their keys.
        """
        return {
            "count": len(self._cache),
            "keys": list(self._cache.keys()),
            "details": {k: v[1].strftime('%Y-%m-%d %H:%M:%S') for k, v in self._cache.items()}
        }