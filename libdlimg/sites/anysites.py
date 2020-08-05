from libdlimg.lib import Fetcher
from libdlimg.waiter import Waiter
from libdlimg.error import Reporter
from .. import lib

site = 'anysite'
query = False


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

    async def gettitle(self, url: str):
        doc = await self.fetcher.fetch_doc(url)
        return doc.select_one('title').text

    async def collector(self, **args):
        async for e in lib.single_selector_collector(
            args['url'],
            'img',
            'src',
            **args
        )():
            yield e
