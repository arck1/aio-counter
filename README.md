Async counter with decrement after timeout (ttl)


> Python 3.7+

Install
-------
    pip install git+https://github.com/arck1/aio-counter

Examples
-------
```
counter = AioCounter(max_count=10, start_count=0, ttl=1, loop=loop)

# try increment counter or wait
await counter.inc(value=1)

# try increment counter or raise exception
counter.inc_nowait(value=1)

# try decrement counter or raise exception
counter.dec_nowait(value=1)

# try decrement counter or wait
await counter.dec(value=1)

# try increment counter with value 2 which decrement back after 2 seconds or wait
await counter.inc(value=2, ttl=2)

# try increment counter with value 2 which decrement back after 2 seconds or raise exception
counter.inc_nowait(value=2, ttl=2)
```