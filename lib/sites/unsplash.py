from .. import lib
import re
import asyncio
import urllib
import json
import urllib.parse


site = 'unsplash'
match = re.compile('https?://unsplash.com/napi/search/photos\\?query=.*')
query = True


async def collector(**args):

    qualities = ['raw', 'full', 'regular', 'small', 'thumb']

    async def links_fn(page_num, **args):
        if args['query']:
            url = f'https://unsplash.com/napi/search/photos?query={urllib.parse.quote(args["query"])}&page={page_num}'
        else:
            url = args['url'] + f'&page={page_num}'
        src = await lib.fetch(url, **args)
        data = json.loads(src)
        return list(map(lambda e: e['urls'][qualities[args['quality']]], data['results']))

    async for img in lib.paged_collector(links_fn=links_fn, ** args):
        async with lib.concurrent_semaphore:
            yield img
            await asyncio.sleep(0.1)


async def info_getter(**args):
    return {
        'title': 'unsplash',
        'imgs': collector(**args)
    }
