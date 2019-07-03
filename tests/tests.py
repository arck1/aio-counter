import unittest
from asyncio import sleep

from async_unittest import TestCase

from aio_counter import AioCounter
from aio_counter.exceptions import AioCounterException


class TestAioCounter(TestCase):
    TIK = float(0.3)
    TAK = float(0.6)
    TTL = int(1)

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.counter = AioCounter(loop=cls.loop)

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        cls.counter.close()

    def setUp(self) -> None:
        self.counter._count = 0
        self.counter._incs.clear()
        self.counter._decs.clear()

        # close all handlers
        self.counter.close()

        self.counter._handlers.clear()

    def tearDown(self) -> None:
        self.counter.close()

    async def test_dec(self):
        assert self.counter.empty()
        self.counter._loop.call_later(self.TIK, self.counter.inc_nowait)

        assert self.counter.count == 0

        # wait until delayed inc_nowait increment counter
        count = await self.counter.dec()

        assert count == 0

    async def test_inc(self):
        assert self.counter.empty()

        # fill counter
        self.counter._count = self.counter.max_count

        assert self.counter.count == self.counter.max_count

        self.counter._loop.call_later(self.TIK, self.counter.dec_nowait)

        assert self.counter.count == self.counter.max_count

        # wait until delayed dec_nowait decrement counter
        count = await self.counter.inc()

        assert count == self.counter.max_count

    def test_dec_nowait(self):
        assert self.counter.empty()

        try:
            self.counter.dec_nowait()
        except AioCounterException as e:
            assert e
        else:
            assert False

        count = self.counter.inc_nowait()

        assert count == 1
        assert self.counter.count == 1

        count = self.counter.dec_nowait()

        assert count == 0
        assert self.counter.count == 0

    def test_inc_nowait(self):
        assert self.counter.empty()

        count = self.counter.inc_nowait()

        assert count == 1
        assert self.counter.count == 1

        # fill counter
        self.counter._count = self.counter.max_count

        try:
            self.counter.inc_nowait()
        except AioCounterException as e:
            assert e
        else:
            assert False

    async def test_ttl_inc(self):
        assert self.counter.empty()

        # inc with ttl = TTL
        await self.counter.inc(self.TTL)
        assert self.counter.count == 1

        # sleep and inc() should run in one loop
        await sleep(self.TTL, loop=self.loop)

        # check if count was dec
        assert self.counter.count == 0

    async def test_bulk_inc(self):
        """
        inc() with value > 1 should success only if counter changed to <value > 1> in one moment
        :return:
        """
        assert self.counter.empty()

        # fill counter
        self.counter._count = self.counter.max_count - 1
        assert self.counter.count == self.counter.max_count - 1

        def delayed_check(counter):
            assert counter.count == counter.max_count - 1

        self.counter._loop.call_later(self.TIK, delayed_check, self.counter)

        self.counter._loop.call_later(self.TTL, self.counter.dec_nowait)

        assert self.counter.count == self.counter.max_count - 1

        await self.counter.inc(value=2)

        assert self.counter.count == self.counter.max_count

    async def test_bulk_dec(self):
        """
        dec() with value > 1 should success only if counter changed to <value > 1> in one moment
        :return:
        """
        assert self.counter.empty()

        await self.counter.inc()
        assert self.counter.count == 1

        def delayed_check(counter):
            assert counter.count == 1

        self.counter._loop.call_later(self.TIK, delayed_check, self.counter)
        self.counter._loop.call_later(self.TTL, self.counter.inc_nowait)

        assert self.counter.count == 1

        await self.counter.dec(value=2)

        assert self.counter.empty()

    async def test_ttl_after_dec(self):
        assert self.counter.empty()

        await self.counter.inc(self.TTL)
        assert self.counter.count == 1

        count = self.counter.dec_nowait()
        assert count == 0
        assert self.counter.count == 0

        await sleep(self.TTL, loop=self.loop)


if __name__ == '__main__':
    unittest.main()
