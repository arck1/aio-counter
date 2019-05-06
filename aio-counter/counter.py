import asyncio
import collections
import uuid
from .exceptions import AioCounterException


class AioCounter:

    _MAX_COUNT = 100
    _TTL = 5

    def __init__(self, max_count: int, start_count: int = 0, ttl: int = None, loop=None):
        """
        Control request rate per period
        :param max_count:
        :param start_count:
        :param ttl:
        :param loop:
        """
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

    def _wakeup_next(self, waiters):
        # Wake up the next waiter (if any) that isn't cancelled.
        while waiters:
            waiter = waiters.popleft()
            if not waiter.done():
                waiter.set_result(None)
                break

    def normalize(self):
        if self._count is None:
            self._count = 0

    def empty(self):
        self.normalize()
        return self._count == 0

    def full(self):
        self.normalize()
        return self._count == self._max_count

    def get_key(self):
        return uuid.uuid4().hex

    def cancel(self):
        for key, handler in self._handlers.items():
            try:
                handler.cancel()
            except:
                pass

    def inc_nowait(self, ttl: int = None, value: int = 1):

        if self.full():
            raise AioCounterException("Counter is full")

        if value is None:
            value = 1

        if self._count + value > self._max_count:
            raise AioCounterException(f"New counter value = {self._count + value} "
                                      f"greater than max_count = {self._max_count}")
        self._count += value

        self._wakeup_next(self._incs)

        ttl = ttl or self._ttl

        if ttl is not None and ttl > 0:
            key = self.get_key()
            self._handlers[key] = self._loop.call_later(ttl, self.__dec_callback, key, value)
        return self._count

    def dec_nowait(self, value: int = 1):
        if self.empty():
            raise AioCounterException("Counter is empty")

        if value is None:
            value = 1

        if self._count - value < 0:
            raise AioCounterException(f"New counter value = {self._count + value} "
                                      f"less than Zero)")
        self._count -= value
        self._wakeup_next(self._decs)
        return self._count

    def __dec_callback(self, key, value):
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

    async def inc(self, ttl: int = None, value: int = 1):
        while self.full():
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

    async def dec(self, value: int = 1):
        while self.empty():
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
