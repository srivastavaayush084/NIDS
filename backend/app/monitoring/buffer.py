import asyncio
import collections
import logging
import threading
from typing import Any, List, Literal, Optional

logger = logging.getLogger(__name__)

OverflowPolicy = Literal["drop_oldest", "drop_newest", "backpressure"]


class MonitoringBuffer:
    """
    Bounded thread-safe and async-compatible buffer for decoupling packet/flow ingestion
    from the downstream ML detection and database persistence pipeline.
    """

    def __init__(
        self,
        max_size: int = 10000,
        overflow_policy: OverflowPolicy = "drop_oldest",
    ):
        self.max_size = max_size
        self.overflow_policy = overflow_policy
        self._deque: collections.deque = collections.deque()
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)
        self._async_event = asyncio.Event()

        self.total_pushed: int = 0
        self.total_popped: int = 0
        self.total_dropped: int = 0

    def size(self) -> int:
        with self._lock:
            return len(self._deque)

    def is_full(self) -> bool:
        with self._lock:
            return len(self._deque) >= self.max_size

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._deque) == 0

    def push(self, item: Any) -> bool:
        """
        Synchronously push an item into the buffer respecting overflow policy.
        Returns True if item was added, False if dropped.
        """
        with self._lock:
            if len(self._deque) >= self.max_size:
                if self.overflow_policy == "drop_newest":
                    self.total_dropped += 1
                    return False
                elif self.overflow_policy == "drop_oldest":
                    self._deque.popleft()
                    self.total_dropped += 1
                elif self.overflow_policy == "backpressure":
                    # For sync push under backpressure, wait if lock allows
                    while len(self._deque) >= self.max_size:
                        self._not_full.wait(timeout=0.1)
                        if len(self._deque) >= self.max_size:
                            self.total_dropped += 1
                            return False

            self._deque.append(item)
            self.total_pushed += 1
            self._not_empty.notify()
            self._async_event.set()
            return True

    async def async_push(self, item: Any) -> bool:
        """
        Asynchronously push an item into the buffer.
        """
        if self.overflow_policy == "backpressure" and self.is_full():
            while self.is_full():
                await asyncio.sleep(0.01)
        return self.push(item)

    def pop(self, timeout: Optional[float] = None) -> Optional[Any]:
        """
        Synchronously pop a single item from the buffer with optional timeout.
        """
        with self._lock:
            if not self._deque:
                if timeout is not None and timeout > 0:
                    self._not_empty.wait(timeout=timeout)
                if not self._deque:
                    return None

            item = self._deque.popleft()
            self.total_popped += 1
            self._not_full.notify()
            if not self._deque:
                self._async_event.clear()
            return item

    async def async_pop(self, timeout: Optional[float] = None) -> Optional[Any]:
        """
        Asynchronously pop a single item from the buffer.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.pop, timeout)

    def pop_batch(self, batch_size: int, timeout: Optional[float] = None) -> List[Any]:
        """
        Synchronously pop up to batch_size items from the buffer.
        """
        items: List[Any] = []
        with self._lock:
            if not self._deque and timeout is not None and timeout > 0:
                self._not_empty.wait(timeout=timeout)

            while self._deque and len(items) < batch_size:
                items.append(self._deque.popleft())
                self.total_popped += 1

            if items:
                self._not_full.notify_all()
            if not self._deque:
                self._async_event.clear()

        return items

    async def async_pop_batch(self, batch_size: int, timeout: Optional[float] = None) -> List[Any]:
        """
        Asynchronously pop up to batch_size items from the buffer.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.pop_batch, batch_size, timeout)

    def clear(self) -> None:
        """Clear all items in the buffer."""
        with self._lock:
            self._deque.clear()
            self._async_event.clear()
            self._not_full.notify_all()
