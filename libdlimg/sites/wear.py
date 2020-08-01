import bs4
import re
from .. import lib
import urllib.parse

site = 'wear'
match = re.compile('https?://wear.jp/.*')


async def user_links_fn(page_num, **args):
    url = args['url'] + f'?pageno={page_num}'
    ret = {}
    doc = await lib.fetch_doc(url, ret, **args)
    # 終了条件
    if page_num >= 2 and str(ret['realurl']).count('?pageno') == 0:
        return []
    else:
        links = []
        for e in doc.select('#list_1column li.list'):
            link = 'https://wear.jp' + e.select_one('.over')['href']
            type_e = e.select_one('h3.name span')
            if not type_e:
                user_type = 'normal'
            elif 'wearista' in type_e['class']:
                user_type = 'wearista'
            elif 'shopstaff' in type_e['class']:
                user_type = 'shopstaff'
            else:
                user_type = ''

            shopname_e = e.select_one('.shopname')
            if not shopname_e:
                shopname = ''
            else:
                shopname = shopname_e.text.strip()

            data = {
                'userid': e.select_one('.over')['href'].replace('/', ''),
                'name': e.select_one('h3.name').text.strip(),
                'info': list(map(lambda li: li.text.strip(), e.select('ul.info li'))),
                'meta': list(map(lambda li: li.text.strip(), e.select('ul.meta li'))),
                'brands': list(map(lambda li: li.text.strip(), e.select('.fav_brand ul li'))),
                'user_type': user_type,
                'shopname': shopname,
            }
            links.append({
                'url': link,
                'data': data,
            })
        return links


async def user_collector(**args):
    async for user in lib.paged_collector(links_fn=user_links_fn, ** args):
        async for img in lib.paged_collector(links_fn=gallery_links_fn, ps=1, pe=-1, params=user, ** args):
            async with lib.concurrent_semaphore:
                yield img


async def gallery_links_fn(page_num, params=None, **args):
    _url = params['url'] if params and 'url' in params else args['url']
    url = _url + f'?pageno={page_num}'
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

            # データが渡されたときはつける
            if params and 'data' in params:
                data['user'] = params['data']

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


async def gallery_collector(**args):
    async for img in lib.paged_collector(links_fn=gallery_links_fn, ** args):
        async with lib.concurrent_semaphore:
            yield img

async def collector(**args):
    if re.match('https?://wear.jp/user/.*', args['url']):
        async for e in user_collector(**args):
            yield e
    else:
        async for e in gallery_collector(**args):
            yield e


async def info_getter(**args):
    return {
        'title': 'wear',
        'imgs': collector(**args)
    }
