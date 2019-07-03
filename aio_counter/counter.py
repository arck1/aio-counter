import asyncio
import collections
import uuid
from typing import Optional, Union

from .exceptions import AioCounterException


class AioCounter:
    _MAX_COUNT = 100
    _TTL = 5

    def __init__(self, max_count: Optional[int] = None, start_count: int = 0, ttl: Optional[int] = _TTL,
                 loop=None):
        """
        Control request rate per period
        :param max_count:
        :param start_count:
        :param ttl:
        :param loop:
        """
        if max_count is None:
            max_count = self._MAX_COUNT

        if max_count is None or max_count <= 0:
            raise ValueError(f"max_count: int should be positive integer value, not {str(max_count)}")

        if loop is None:
            loop = asyncio.get_event_loop()

        self._loop = loop
        self._count = start_count
        self._max_count = max_count or AioCounter._MAX_COUNT
        self._ttl = ttl or AioCounter._TTL

        # Futures.
        self._incs = collections.deque()
        # Futures.
        self._decs = collections.deque()

        self._handlers = {}

    @property
    def count(self) -> int:
        """
        Return AioCounter current value
        :return:
        """
        return self._count

    @property
    def max_count(self) -> int:
        """
        Return AioCounter  max_count value
        :return:
        """
        return self._max_count

    def _wakeup_next(self, waiters: collections.deque):
        """
        Wake up the next waiter (if any) that isn't cancelled.
        :param waiters:
        :return:
        """
        while waiters:
            waiter = waiters.popleft()
            if not waiter.done():
                waiter.set_result(None)
                break

    def normalize(self):
        """
        If counter not initialize or broken
        :return:
        """
        if self._count is None:
            self._count = 0

        """
        Check if self._count between 0 and self._max_count
        """
        self._count = max(
            min(self._count, self._max_count),
            0
        )

    def empty(self) -> bool:
        self.normalize()
        return self.count <= 0

    def full(self) -> bool:
        self.normalize()
        return self.count >= self._max_count

    def can_dec(self, value: int = 1) -> bool:
        return self.count >= max(0, value)

    def can_inc(self, value: int = 1) -> bool:
        return self.count + max(0, value) <= self._max_count

    def get_key(self) -> str:
        """
        Return key for callback
        :return:
        """
        return uuid.uuid4().hex

    def cancel(self):
        """
        Graceful shutdown and close handlers
        :return:
        """
        for key, handler in self._handlers.items():
            try:
                handler.cancel()
            except:
                pass

    def close(self):
        self.cancel()

    def inc_nowait(self, ttl: Optional[int] = None, value: int = 1) -> int:
        """
        Direct synchronous increment counter
        :param ttl: Optional[int] - time to live in seconds, if None ttl = INF
        :param value: int
        :return:
        """
        if self.full():
            raise AioCounterException("Counter is full")

        if value is None:
            value = 1

        if self._count + value > self._max_count:
            raise AioCounterException(f"New counter value = {self._count + value} "
                                      f"greater than max_count = {self._max_count}")
        self._count += value

        self._wakeup_next(self._decs)

        ttl = ttl or self._ttl

        if ttl is not None and ttl > 0:
            key = self.get_key()
            self._handlers[key] = self._loop.call_later(ttl, self.__dec_callback, key, value)
        return self.count

    def dec_nowait(self, value: int = 1) -> int:
        """
        Direct synchronous decrement counter
        :param value:
        :return:
        :raise AioCounterException if can't dec counter
        """
        if self.empty():
            raise AioCounterException("Counter is empty")

        if value is None:
            value = 1

        if self._count - value < 0:
            raise AioCounterException(f"New counter value = {self._count + value} "
                                      f"less than Zero)")
        self._count -= value
        self._wakeup_next(self._incs)
        return self.count

    def __dec_callback(self, key, value: int = 1) -> int:
        """
        Callback wrapper for dec counter after ttl
        :param key:
        :param value:
        :return:
        """
        try:
            self.dec_nowait(value=value)
        except:
            pass
        else:
            handler = self._handlers.pop(key, None)
            if handler is not None:
                handler.cancel()
            return 1
        return 0

    async def inc(self, ttl: Optional[int] = None, value: int = 1) -> int:
        """
        Async increment of counter
        If Counter is full(), wait free slots
        :param ttl: seconds
        :param value:
        :return:
        """
        while not self.can_inc(value=value):
            incer = self._loop.create_future()
            self._incs.append(incer)
            try:
                await incer
            except:
                incer.cancel()  # Just in case incer is not done yet.
                try:
                    # Clean self._incs from canceled incer.
                    self._incs.remove(incer)
                except ValueError:
                    # The incer could be removed from self._incs by a
                    # previous inc_nowait call.
                    pass
                if not self.full() and not incer.cancelled():
                    # We were woken up by inc_nowait(), but can't take
                    # the call.  Wake up the next in line.
                    self._wakeup_next(self._incs)
                raise
        return self.inc_nowait(ttl=ttl, value=value)

    async def dec(self, value: int = 1) -> int:
        """
        Async decrement of counter
        if counter is empty(), wait any increment
        :param value:
        :return:
        """
        while not self.can_dec(value=value):
            decer = self._loop.create_future()
            self._decs.append(decer)
            try:
                await decer
            except:
                decer.cancel()  # Just in case decer is not done yet.
                try:
                    # Clean self._decs from canceled decer.
                    self._decs.remove(decer)
                except ValueError:
                    # The decer could be removed from self._decs by a
                    # previous dec_nowait call.
                    pass
                if not self.empty() and not decer.cancelled():
                    # We were woken up by dec_nowait(), but can't take
                    # the call.  Wake up the next in line.
                    self._wakeup_next(self._decs)
                raise
        return self.dec_nowait(value=value)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.cancel()
