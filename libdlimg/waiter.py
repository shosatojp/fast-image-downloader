import urllib.parse
import time
import asyncio
import random
import json

lock = asyncio.Lock()


class Waiter():
    def __init__(self, wait, waitlist, **args):
        self.waitlist = {}
        if waitlist:
            with open(waitlist, 'rt', encoding='utf-8') as f:
                obj: dict = json.load(f)
                for key, item in obj.items():
                    wargs = list(map(lambda e: e.strip(), str(item).split(' ')))
                    self.waitlist[key] = select_waiter(wargs, **args)

        if '*' not in self.waitlist:
            if wait:
                self.waitlist['*'] = select_waiter(wait, **args)
            else:
                self.waitlist['*'] = DefaultWaiter(**args)

    async def wait(self, url: str):
        parsed_url = urllib.parse.urlparse(url)
        host = parsed_url.hostname

        if host in self.waitlist:
            waiter: DefaultWaiter = self.waitlist[host]
        else:
            waiter: DefaultWaiter = self.waitlist['*']

        await waiter.wait(url)


class DefaultWaiter():
    def __init__(self, **args):
        self.nightshift = 'nightshift' in args and args['nightshift']
        self.table = {}

    async def wait(self, url: str):
        await self._wait(url, 0)

    async def _wait(self, url: str, sec: int):
        parsed_url = urllib.parse.urlparse(url)
        host = parsed_url.hostname

        # night shift
        hour = time.localtime().tm_hour
        if self.nightshift and 1 <= hour < 6:
            sec /= self.nightshift

        if host in self.table:
            await self.table[host]['lock'].acquire()
            now = time.time()
            if now > self.table[host]['time'] + sec:
                self.table[host]['time'] = now
            else:
                ws = max(sec - (now - self.table[host]['time']), 0)
                await asyncio.sleep(ws)
                self.table[host]['time'] = time.time()
            self.table[host]['lock'].release()
        else:
            self.table[host] = {
                'lock': asyncio.Lock(),
                'time': time.time()
            }


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
