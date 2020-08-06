from asyncio.locks import Semaphore
from libdlimg.lib import Fetcher
from libdlimg.waiter import Waiter
from logging import FATAL
from libdlimg.error import ERROR, Reporter
from .. import lib
import re
import urllib.parse

site = 'yandere'
match = re.compile('https?://yande.re/post\\?tags=.*')
query = True


class Collector():
    def __init__(self,
                 reporter: Reporter = None,
                 waiter: Waiter = None,
                 fetcher: Fetcher = None):
        self.reporter = reporter
        self.waiter = waiter
        self.fetcher = fetcher
        self.semaphore = Semaphore(10)
        self.title = 'yandere'

    async def gettitle(self, url: str):
        return self.title

    async def second_and_third(self, __url, **args):
        img = await lib.single_one_selector(
            {'url': __url, 'selector': '.highres-show', 'attr': 'href'}, fetcher=self.fetcher, **args)
        if img:
            return [img]
        img = await lib.single_one_selector(
            {'url': __url, 'selector': 'img.image', 'attr': 'src'}, fetcher=self.fetcher ** args)
        return [img]

    async def collector(self, **args):
        async def links_fn(page_num, **args):
            if args['query']:
                url = f'https://yande.re/post?tags={urllib.parse.quote(args["query"])}&page={page_num}'
            else:
                url = args['url'] + f'&page={page_num}'
            doc = await self.fetcher.fetch_doc(url)
            return list(map(lambda e: 'https://yande.re' + e['href'], doc.select('a.thumb')))

        async for img in lib.parallel_for(
            generator=lib.paged_collector(links_fn, args['pagestart'], args['pageend'], ** args),
            async_fn=self.second_and_third,
            **args
        ):
            yield img
