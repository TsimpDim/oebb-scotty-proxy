import threading
import time
from typing import Any, Callable


class TTLCache:
    """A minimal thread-safe cache with time-based expiry."""

    def __init__(self, ttl: float):
        self._ttl = ttl
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires_at, value = item
            if time.monotonic() < expires_at:
                return value
            self._data.pop(key, None)
            return None

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = (time.monotonic() + self._ttl, value)

    def get_or_set(self, key: str, factory: Callable[[], Any]) -> Any:
        value = self.get(key)
        if value is None:
            value = factory()
            self.set(key, value)
        return value
