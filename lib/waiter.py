import urllib.parse
import time
import asyncio
import random
import json

lock = asyncio.Lock()


class DefaultWaiter():
    def __init__(self, **args):
        if 'waitlist' in args and args['waitlist']:
            with open(args['waitlist'], 'rt', encoding='utf-8') as f:
                self.waitlist = json.load(f)
        else:
            self.waitlist = {}
        self.nightshift = 'nightshift' in args and args['nightshift']
        self.table = {}

    async def wait(self, url: str):
        await self._wait(url, 0)

    async def _wait(self, url: str, sec: int):
        parsed_url = urllib.parse.urlparse(url)
        host = parsed_url.hostname

        # overwrite sec with waitlist
        _sec = self.waitlist[host] if host in self.waitlist else sec

        # night shift
        hour = time.localtime().tm_hour
        if self.nightshift and 1 <= hour <= 6:
            _sec /= self.nightshift

        await lock.acquire()
        now = time.time()
        if host in self.table:
            if now > self.table[host] + _sec:
                self.table[host] = now
            else:
                ws = self.table[host] + _sec - now
                await asyncio.sleep(ws)
                self.table[host] = time.time()
        else:
            self.table[host] = now
        lock.release()


class ConstWaiter(DefaultWaiter):
    def __init__(self, sec: int, **args):
        super(ConstWaiter, self).__init__(**args)
        self.sec = sec

    async def wait(self, url: str):
        await self._wait(url, self.sec)


class RandomWaiter(DefaultWaiter):
    def __init__(self, min: int, max: int, **args):
        super(RandomWaiter, self).__init__(**args)
        self.min = min
        self.max = max

    async def wait(self, url: str):
        await self._wait(url, random.randrange(self.min, self.max))


def select_waiter(wargs: list, **args):
    if (len(wargs) == 1):
        return ConstWaiter(float(wargs[0]), **args)
    elif (len(wargs) == 2 and wargs[0] == 'const'):
        return ConstWaiter(float(wargs[1]), **args)
    elif len(wargs) == 3 and wargs[0] == 'random':
        return RandomWaiter(float(wargs[1]), float(wargs[2]), **args)
    else:
        return DefaultWaiter(**args)
