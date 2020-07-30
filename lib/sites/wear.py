import bs4
import re
from .. import lib
import urllib.parse

site = 'wear'
match = re.compile('https?://wear.jp/.*')
query = True


async def collector(**args):

    async def links_fn(page_num):
        url = args['url'] + f'?pageno={page_num}'
        ret = {}
        doc = await lib.fetch_doc(url, ret, **args)
        # 終了条件
        if page_num >= 2 and str(ret['realurl']).count('?pageno') == 0:
            return []
        else:
            links = []
            for e in doc.select('.like_mark'):
                link = 'https:' + e.select_one('.img img')['data-originalretina']
                data = {
                    'snapid': e['data-snapid'],
                    'saves': int(e.select_one('.btn_save span').text.strip()),
                    'likes': int(e.select_one('.btn_like span').text.strip()),
                    'link': e.select_one('.over')['href']
                }

                # first name if exists
                elem_first_name = e.select_one('.namefirst')
                if elem_first_name:
                    data['first_name'] = elem_first_name.text.strip()

                # height if exists
                elem_height = e.select_one('.height')
                if elem_height:
                    data['height'] = elem_height.text.strip()

                links.append({
                    'url': link,
                    'data': data,
                })
            return links

    async for img in lib.paged_collector(links_fn=links_fn, ** args):
        async with lib.concurrent_semaphore:
            yield img


async def info_getter(**args):
    return {
        'title': 'wear',
        'imgs': collector(**args)
    }
