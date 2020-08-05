from asyncio.locks import Semaphore
from libdlimg.lib import Fetcher
from libdlimg.waiter import Waiter
from libdlimg.error import Reporter
from .. import lib
import re
import os
import bs4
import asyncio
import shutil
import urllib
import aiohttp
import sys
import urllib.parse

site = 'tsundora'
match = re.compile('https?://tsundora.com/.*')
query = True  # ready for query


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
        self.title = 'tsundora'

    async def gettitle(self, url: str):
        return self.title

    async def second_and_third(self, __url, **args):
        if args['quality'] == 0:
            third_page = await lib.single_one_selector(
                {'url': __url, 'selector': '.post-img > a', 'attr': 'href'}, fetcher=self.fetcher, **args)
            img = await lib.single_one_selector(
                {'url': third_page, 'selector': 'img', 'attr': 'src'}, fetcher=self.fetcher, **args)
            return [img]

        elif args['quality'] == 1:
            img = await lib.single_one_selector(
                {'url': __url, 'selector': '.post-img img', 'attr': 'src'}, fetcher=self.fetcher, **args)
            return [img]

    async def collector(self, **args):
        if args['query']:
            __url_format = f'https://tsundora.com/page/{{page}}?s={urllib.parse.quote(args["query"])}'
        else:
            __url_format = args['url'] + '/page/{page}'

        async def links_fn(page_num, **args):
            url = __url_format.replace('{page}', str(page_num))
            doc = await self.fetcher.fetch_doc(url)
            if doc:
                if args['quality'] == 0 or args['quality'] == 1:
                    return list(map(lambda e: e['href'], doc.select('.home-img > a')))
                elif args['quality'] == 2:
                    return list(map(lambda e: e['src'], doc.select('.home-img > a > img')))
            else:
                return []

        if args['quality'] == 0 or args['quality'] == 1:
            async for img in lib.parallel_for(
                generator=lib.paged_collector(links_fn, args['pagestart'], args['pageend'], ** args),
                async_fn=self.second_and_third,
                ** args
            ):
                yield img

        elif args['quality'] == 2:
            async for second_page in lib.paged_collector(links_fn, args['pagestart'], args['pageend'], ** args):
                yield second_page
        else:
            print('no such quality for tsundora')
            exit(1)
