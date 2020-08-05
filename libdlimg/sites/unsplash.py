from asyncio.locks import Semaphore
from libdlimg.lib import Fetcher
from libdlimg.waiter import Waiter
from logging import FATAL
from libdlimg.error import ERROR, Reporter
from .. import lib
import re
import asyncio
import urllib
import json
import urllib.parse


site = 'unsplash'
match = re.compile('https?://unsplash.com/napi/search/photos\\?query=.*')
query = True


class Collector():
    def __init__(self,
                 reporter: Reporter = None,
                 waiter: Waiter = None,
                 fetcher: Fetcher = None,
                 **others):
        self.reporter = reporter
        self.waiter = waiter
        self.fetcher = fetcher
        self.semaphore = Semaphore(10)
        self.title = 'unsplash'

    async def gettitle(self, url: str):
        return self.title

    async def collector(self, **args):

        qualities = ['raw', 'full', 'regular', 'small', 'thumb']

        async def links_fn(page_num, **args):
            if args['query']:
                url = f'https://unsplash.com/napi/search/photos?query={urllib.parse.quote(args["query"])}&page={page_num}'
            else:
                url = args['url'] + f'&page={page_num}'
            src = await self.fetcher.fetch(url)
            data = json.loads(src)
            return list(map(lambda e: e['urls'][qualities[args['quality']]], data['results']))

        async for img in lib.paged_collector(links_fn=links_fn, ** args):
            yield img
            await asyncio.sleep(0.1)
