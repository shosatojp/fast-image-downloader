from .. import lib
import re
import urllib
import urllib.parse

site = 'irasutoya'
match = re.compile('https?://www.irasutoya.com/search\\?q=.*')
query = True


async def second_and_third(__url, **args):
    imgs = await lib.multiple_selector(
        {'url': __url, 'selector': '.entry a', 'attr': 'href'}, **args)
    for i, img in enumerate(imgs):
        parsed = urllib.parse.urlparse(img)
        imgs[i] = parsed._replace(scheme=parsed.scheme or 'https').geturl()
    return imgs


async def collector(**args):
    async def links_fn(page_num, **args):
        if args['query']:
            url = f'https://www.irasutoya.com/search?q={urllib.parse.quote(args["query"])}&start={20*(page_num-1)}'
        else:
            url = args['url'] + f'&start={20*(page_num-1)}'
        doc = await lib.fetch_doc(url, **args)
        return list(map(lambda e: e['href'], doc.select('.boxim a')))

    async for page in lib.parallel_for(
        generator=lib.paged_collector(links_fn=links_fn, ** args),
        async_fn=second_and_third,
        **args
    ):
        yield page


async def info_getter(**args):
    return {
        'title': 'irasutoya',
        'imgs': collector(**args)
    }
