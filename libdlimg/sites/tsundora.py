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


async def second_and_third(__url, **args):
    if args['quality'] == 0:
        third_page = await lib.single_one_selector(
            {'url': __url, 'selector': '.post-img > a', 'attr': 'href'}, **args)
        img = await lib.single_one_selector(
            {'url': third_page, 'selector': 'img', 'attr': 'src'}, **args)
        return [img]

    elif args['quality'] == 1:
        img = await lib.single_one_selector(
            {'url': __url, 'selector': '.post-img img', 'attr': 'src'}, **args)
        return [img]


async def collector(**args):
    if args['query']:
        __url_format = f'https://tsundora.com/page/{{page}}?s={urllib.parse.quote(args["query"])}'
    else:
        __url_format = args['url'] + '/page/{page}'

    async def links_fn(page_num, **args):
        url = __url_format.replace('{page}', str(page_num))
        doc = await lib.fetch_doc(url, **args)
        if args['quality'] == 0 or args['quality'] == 1:
            return list(map(lambda e: e['href'], doc.select('.home-img > a')))
        elif args['quality'] == 2:
            return list(map(lambda e: e['src'], doc.select('.home-img > a > img')))

    if args['quality'] == 0 or args['quality'] == 1:
        async for img in lib.parallel_for(
            generator=lib.paged_collector(links_fn=links_fn, ** args),
            async_fn=second_and_third,
            **args
        ):
            yield img

    elif args['quality'] == 2:
        async for second_page in lib.paged_collector(links_fn=links_fn, ** args):
            async with lib.concurrent_semaphore:
                yield second_page
    else:
        print('no such quality for tsundora')
        exit(1)


async def info_getter(**args):
    return {
        'title': 'tsundora',
        'imgs': collector(**args)
    }
