from logging import FATAL
from libdlimg.error import ERROR, report
import re
from .. import lib
import urllib.parse

site = 'bing'
match = re.compile('https?://www.bing.com/images/search\\?q=.*')
query = True


async def collector(**args):
    async def links_fn(page_num, **args):
        if args['query']:
            url = f'https://www.bing.com/images/search?q={urllib.parse.quote(args["query"])}&first={28*(page_num-1)+1}&count={28}'
        else:
            url = args['url'] + f'&first={28*(page_num-1)+1}&count={28}'
        doc = await lib.fetch_doc(url, **args)

        if args['quality'] == 0:
            return list(map(lambda e: e['href'], doc.select('a.thumb')))
        elif args['quality'] == 1:
            return list(map(lambda e: e['src'], doc.select('a.thumb img')))
        else:
            report(FATAL, 'no such quality for bing (0-1)', **args)
            exit(1)

    async for img in lib.paged_collector(links_fn=links_fn, ** args):
        async with lib.concurrent_semaphore:
            yield img


async def info_getter(**args):
    return {
        'title': 'bing',
        'imgs': collector(**args)
    }
