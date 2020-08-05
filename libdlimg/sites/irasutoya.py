from asyncio.locks import Semaphore
from libdlimg.lib import Fetcher
from libdlimg.waiter import Waiter
from logging import FATAL
from libdlimg.error import ERROR, Reporter
from .. import lib
import re
import urllib
import urllib.parse

site = 'irasutoya'
match = re.compile('https?://www.irasutoya.com/search\\?q=.*')
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
        self.title = 'irasutoya'

    async def gettitle(self, url: str):
        return self.title

    async def second_and_third(self, __url, **args):
        imgs = await lib.multiple_selector(
            {'url': __url, 'selector': '.entry a', 'attr': 'href'}, fetcher=self.fetcher, **args)
        for i, img in enumerate(imgs):
            parsed = urllib.parse.urlparse(img)
            imgs[i] = parsed._replace(scheme=parsed.scheme or 'https').geturl()
        return imgs

    async def collector(self, **args):
        async def links_fn(page_num, **args):
            if args['query']:
                url = f'https://www.irasutoya.com/search?q={urllib.parse.quote(args["query"])}&start={20*(page_num-1)}'
            else:
                url = args['url'] + f'&start={20*(page_num-1)}'
            doc = await self.fetcher.fetch_doc(url)
            return list(map(lambda e: e['href'], doc.select('.boxim a')))

        async for page in lib.parallel_for(
            generator=lib.paged_collector(links_fn, args['pagestart'], args['pageend'], ** args),
            async_fn=self.second_and_third,
            **args
        ):
            yield page
