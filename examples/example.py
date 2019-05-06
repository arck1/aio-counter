import asyncio
import time

from aio_counter import AioCounter


async def with_ttl(loop):
    counter = AioCounter(max_count=10, start_count=2, ttl=1, loop=loop)

    print(counter.count)

    print(time.monotonic())
    for _ in range(100):
        await counter.inc(value=1)
        print(time.monotonic())


async def without_ttl(loop):
    counter = AioCounter(max_count=10, start_count=2, ttl=None, loop=loop)

    # try increment counter or wait
    await counter.inc(value=1)

    # try increment counter or raise exception
    counter.inc_nowait(value=1)

    # try decrement counter or raise exception
    counter.dec_nowait(value=1)

    # try decrement counter or wait
    await counter.dec(value=1)


async def main(loop):
    await with_ttl(loop)
    await without_ttl(loop)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))

