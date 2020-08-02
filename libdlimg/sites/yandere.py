from .. import lib
import re
import urllib.parse

site = 'yandere'
match = re.compile('https?://yande.re/post\\?tags=.*')
query = True


async def second_and_third(__url, **args):
    img = await lib.single_one_selector(
        {'url': __url, 'selector': '.highres-show', 'attr': 'href'}, **args)
    if img:
        return [img]
    img = await lib.single_one_selector(
        {'url': __url, 'selector': 'img.image', 'attr': 'src'}, **args)
    return [img]


async def collector(**args):
    async def links_fn(page_num, **args):
        if args['query']:
            url = f'https://yande.re/post?tags={urllib.parse.quote(args["query"])}&page={page_num}'
        else:
            url = args['url'] + f'&page={page_num}'
        doc = await lib.fetch_doc(url, **args)
        return list(map(lambda e: 'https://yande.re' + e['href'], doc.select('a.thumb')))

    async for img in lib.parallel_for(
        generator=lib.paged_collector(links_fn=links_fn, ** args),
        async_fn=second_and_third,
        **args
    ):
        yield img


async def info_getter(**args):
    return {
        'title': 'yandere',
        'imgs': collector(**args)
    }
