from asyncio.locks import Semaphore
from libdlimg.lib import Fetcher
from libdlimg.waiter import Waiter
from libdlimg.error import Reporter
import re
from .. import lib
import urllib.parse

site = 'google'
match = re.compile('https?://www.google.com/search\\?.*')
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
        self.fetcher.useragent = 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)'
        self.title = 'google'

    async def gettitle(self, url: str):
        return self.title

    async def collector(self, **args):
        async def links_fn(page_num, **args):
            if args['query']:
                url = f'https://www.google.com/search?tbm=isch&q={urllib.parse.quote(args["query"])}&start={20*(page_num-1)}'
            else:
                url = args['url'] + f'&start={20*(page_num-1)}'
            doc = await self.fetcher.fetch_doc(url)
            return list(map(lambda e: e['src'], doc.select('img.t0fcAb'))) if doc else []

        async for img in lib.paged_collector(links_fn=links_fn, ** args):
            yield img
