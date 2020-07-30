import urllib.parse
import time
import asyncio
import random

lock = asyncio.Lock()


class DefaultWaiter():
    def __init__(self):
        self.table = {}

    async def wait(self, url: str):
        return

    async def _wait(self, url: str, sec: int):
        parsed_url = urllib.parse.urlparse(url)
        host = parsed_url.hostname
        await lock.acquire()
        now = time.time()
        if host in self.table:
            if now > self.table[host] + sec:
                self.table[host] = now
            else:
                ws = self.table[host] + sec - now
                await asyncio.sleep(ws)
                self.table[host] = time.time()
        else:
            self.table[host] = now
        lock.release()


class ConstWaiter(DefaultWaiter):
    def __init__(self, sec: int):
        super(ConstWaiter, self).__init__()
        self.sec = sec

    async def wait(self, url: str):
        await self._wait(url, self.sec)


class RandomWaiter(DefaultWaiter):
    def __init__(self, min: int, max: int):
        super(RandomWaiter, self).__init__()
        self.min = min
        self.max = max

    async def wait(self, url: str):
        await self._wait(url, random.randrange(self.min, self.max))


def select_waiter(wargs: list):
    if (len(wargs) == 1):
        return ConstWaiter(float(wargs[0]))
    elif (len(wargs) == 2 and wargs[0] == 'const'):
        return ConstWaiter(float(wargs[1]))
    elif len(wargs) == 3 and wargs[0] == 'random':
        return RandomWaiter(float(wargs[1]), float(wargs[2]))
    else:
        return DefaultWaiter()
