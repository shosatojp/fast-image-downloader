import re
from .. import lib
import urllib.parse

site = 'google'
match = re.compile('https?://www.google.com/search\\?.*')
query = True


async def collector(**args):

    async def links_fn(page_num, **args):
        if args['query']:
            url = f'https://www.google.com/search?tbm=isch&q={urllib.parse.quote(args["query"])}&start={20*(page_num-1)}'
        else:
            url = args['url'] + f'&start={20*(page_num-1)}'
        doc = await lib.fetch_doc(url, **args)
        return list(map(lambda e: e['src'], doc.select('img.t0fcAb')))

    async for img in lib.paged_collector(links_fn=links_fn, ** args):
        async with lib.concurrent_semaphore:
            yield img


async def info_getter(**args):
    args['useragent'] = 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)'
    return {
        'title': 'google',
        'imgs': collector(**args)
    }
