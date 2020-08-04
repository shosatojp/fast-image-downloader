from libdlimg.lib import Fetcher
from libdlimg.waiter import Waiter
from logging import FATAL
from libdlimg.error import ERROR, Reporter
import re
from .. import lib
import urllib.parse

site = 'bing'
match = re.compile('https?://www.bing.com/images/search\\?q=.*')
query = True


class Collector():
    def __init__(self,
                 reporter: Reporter = None,
                 waiter: Waiter = None,
                 fetcher: Fetcher = None):
        self.reporter = reporter
        self.waiter = waiter
        self.fetcher = fetcher
        self.title = 'bing'

    async def collector(self, **args):
        async def links_fn(page_num, **args):
            if args['query']:
                url = f'https://www.bing.com/images/search?q={urllib.parse.quote(args["query"])}&first={28*(page_num-1)+1}&count={28}'
            else:
                url = args['url'] + f'&first={28*(page_num-1)+1}&count={28}'
            doc = await self.fetcher.fetch_doc(url)

            if args['quality'] == 0:
                return list(map(lambda e: e['href'], doc.select('a.thumb')))
            elif args['quality'] == 1:
                return list(map(lambda e: e['src'], doc.select('a.thumb img')))
            else:
                self.reporter.report(FATAL, 'no such quality for bing (0-1)')
                exit(1)

        async for img in lib.paged_collector(links_fn=links_fn, ** args):
            async with lib.concurrent_semaphore:
                yield img
