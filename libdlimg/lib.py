import json
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
import time
import glob
import re
import os
import bs4
import asyncio
import shutil
import urllib
import aiohttp
import random
import string
import aiofiles
import mimetypes
import concurrent.futures
import aiohttp.client_exceptions
import traceback
import sys
from libdlimg.error import ERROR, INFO, report

concurrent_semaphore = asyncio.Semaphore(10)
executor = concurrent.futures.ThreadPoolExecutor(10)
waiter_table = {}
imgmap = None

CACHE_VERSION = 1


async def download_img(__url, __path, **args):
    # waiter
    if 'waiter' in args:
        await args['waiter'].wait(__url)

    try:
        async with concurrent_semaphore:
            async with aiohttp.ClientSession() as session:
                async with session.get(__url) as res:
                    if res.status == 200:
                        _, ext = os.path.splitext(__path)
                        if not ext:
                            __path += mimetypes.guess_extension(res.content_type) or '.jpg'

                        report(INFO, f'downloading {__url} -> {__path}', **args)

                        dirname, filename = os.path.split(__path)
                        tmp_path = f'{dirname}/.{filename}'

                        async with aiofiles.open(tmp_path, 'wb') as fd:
                            while True:
                                chunk = await res.content.read(1024)
                                if not chunk:
                                    break
                                await fd.write(chunk)
                    else:
                        report(ERROR, f'download_img: {res.status} {__url}', **args)
                        return None

        if os.path.exists(tmp_path):
            shutil.move(tmp_path, __path)

        # save mapdata
        if args['imgmap']:
            save_map(__url, filename, **args)

        return {
            'path': __path,
            'tmp_path': tmp_path,
        }
    except Exception as e:
        report(ERROR, f'skip {__url} {e}\n{traceback.format_exc()}', **args)
        return None


def save_map(__url: str, __filename: str, **args):
    global imgmap
    if args['check']:
        if not imgmap:
            imgmap = {}
        imgmap[__url] = __filename
    else:
        mapfile = os.path.join(args['basedir'], args['outdir'], 'map.json')
        with open(mapfile, 'a+t', encoding='utf-8') as f:
            f.seek(0)
            obj = json.loads(f.read() or '{}')
            obj[__url] = __filename
        with open(mapfile, 'wt', encoding='utf-8') as f:
            f.write(json.dumps(obj))


def save_map_asjson(**args):
    mapfile = os.path.join(args['basedir'], args['outdir'], 'map.json')
    with open(mapfile, 'wt', encoding='utf-8') as f:
        json.dump(imgmap, f)


def load_map(__url: str, **args):
    global imgmap
    if args['check']:
        if not imgmap:
            mapfile = os.path.join(args['basedir'], args['outdir'], 'map.json')
            with open(mapfile, 'rt', encoding='utf-8') as f:
                imgmap = json.loads(f.read() or '{}')
        if __url in imgmap and os.path.exists(os.path.join(args['basedir'], args['outdir'], imgmap[__url])):
            return imgmap[__url]
        else:
            return False
    else:
        mapfile = os.path.join(args['basedir'], args['outdir'], 'map.json')
        with open(mapfile, 'a+t', encoding='utf-8') as f:
            f.seek(0)
            obj = json.loads(f.read() or '{}')
            if __url in obj and os.path.exists(os.path.join(args['basedir'], args['outdir'], obj[__url])):
                return obj[__url]
            else:
                return False


def single_selector_collector(__url, __selector, __attr='src', **args):
    async def get_imgs():
        html = await fetch(__url, **args)
        open('hoge.html', 'wt', encoding='utf-8').write(html)
        doc = bs4.BeautifulSoup(html, 'html.parser')
        urls = list(map(lambda e: e[__attr], doc.select(__selector)))
        for url in urls:
            yield url

    return get_imgs


async def single_one_selector(params, **args):
    html = await fetch(params['url'], **args)
    doc = bs4.BeautifulSoup(html, 'html.parser')
    return doc.select_one(params['selector'])[params['attr']]


async def multiple_selector(params, **args):
    html = await fetch(params['url'], **args)
    doc = bs4.BeautifulSoup(html, 'html.parser')
    return list(map(lambda e: e[params['attr']], doc.select(params['selector'])))


async def paged_collector(links_fn, ps=None, pe=None, params=None, ** args):
    page_num = ps if ps != None else (args['pagestart'] if 'pagestart' in args else 1)
    page_end = pe if pe != None else (args['pageend'] if 'pageend' in args else -1)
    while True:
        if params:
            links = await links_fn(page_num, params, **args)
        else:
            links = await links_fn(page_num, **args)

        for link in links:
            yield link
        if len(links) == 0 or (page_end != -1 and page_num >= page_end):
            break
        page_num += 1


async def fetch(__url: str, ret={}, **args):
    if args['usecache']:
        obj = load_cache(__url, **args)
        if obj:
            report(INFO, f'use cached {__url}', **args)
            ret['realurl'] = obj['realurl']
            return obj['body']

    # waiter
    if 'waiter' in args:
        await args['waiter'].wait(__url)

    if args['threading']:
        return await fetch_by_browser2(__url, **args)

    headers = {}
    if 'useragent' in args:
        headers['user-agent'] = args['useragent']

    try:
        async with args['semaphore']:
            session: aiohttp.client.ClientSession = args['session']
            async with session.get(__url, headers=headers) as res:
                if res.status == 200:
                    ret['realurl'] = res.url
                    text = await res.text()
                    if args['savefetched']:
                        save_fetched(__url, {
                            'body': text,
                            'realurl': str(res.url)
                        }, **args)
                    report(INFO, f'fetched: {__url}', **args)
                    return text
                else:
                    report(ERROR, f'fetch(): {__url}', **args)
                    return None
    except Exception as e:
        report(ERROR, f'skip {__url} {e}', file=sys.stderr, **args)


def load_cache(__url: str, **args):
    filename = urllib.parse.quote(__url, '')
    fullpath = os.path.join(args['basedir'], args['outdir'], filename+'.json')
    if os.path.exists(fullpath):
        with open(fullpath, 'rt', encoding='utf-8') as f:
            obj = json.load(f)
            if 'cache_version' in obj and obj['cache_version'] == CACHE_VERSION:
                return obj
            else:
                return None
    else:
        return None


def save_fetched(__url: str, __obj, **args):
    filename = urllib.parse.quote(__url, '')
    fullpath = os.path.join(args['basedir'], args['outdir'], filename+'.json')
    __obj['cache_version'] = CACHE_VERSION
    with open(fullpath, 'wt', encoding='utf-8') as f:
        json.dump(__obj, f)


async def fetch_by_browser2(__url: str, **args):
    from selenium.webdriver.chrome.options import Options
    from selenium import webdriver

    def get():
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(__url)

        while True:
            state = driver.execute_script('return document.readyState')
            if state == 'complete':
                break
            time.sleep(0.1)

        html = driver.find_element_by_tag_name('html').get_attribute('innerHTML')
        driver.quit()
        return html

    report(INFO, f'fetched {__url}', **args)
    return get()


async def fetch_by_browser(__url: str, **args):
    from selenium.webdriver.chrome.options import Options
    from selenium import webdriver

    def get():
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(__url)

        while True:
            state = driver.execute_script('return document.readyState')
            if state == 'complete':
                break
            time.sleep(0.1)

        html = driver.find_element_by_tag_name('html').get_attribute('innerHTML')
        driver.quit()
        return html

    async def async_get():
        future = executor.submit(get)
        return future.result()

    async with args['semaphore']:
        print('start')
        task = asyncio.ensure_future(async_get())
        result = (await asyncio.gather(task))[0]
        print('fetched', __url)
        return result


async def fetch_doc(__url: str, ret={}, **args):
    html = await fetch(__url, ret, **args)
    return bs4.BeautifulSoup(html, 'html.parser')


def name_keep(params, **args):
    filename = os.path.split(params['url'])[1]
    name, ext = os.path.splitext(filename)
    if args['namelen'] > 0:
        name = name[:args['namelen']]
    return name + (ext or params['ext'])


def name_number(params, **args):
    namelen = args['namelen'] if args['namelen'] > 0 else 5
    return str(params['number']).zfill(namelen) + params['ext']


def name_random(params, **args):
    namelen = args['namelen'] if args['namelen'] > 0 else 5
    rand = [random.choice(string.ascii_letters + string.digits) for i in range(namelen)]
    return ''.join(rand) + params['ext']


def select_name(src):
    return {
        'keep': name_keep,
        'number': name_number,
        'random': name_random,
    }[src]


def exists_prefix(rootdir, prefix):
    pattern = os.path.join(rootdir, prefix) + '.*'
    files = glob.glob(pattern)
    files = list(filter(lambda e: not e.endswith('.json'), files))
    if len(files) > 0:
        return os.path.basename(files[0])
    else:
        return False
    # return len(files) != 0


async def parallel_for(generator, async_fn, **args):
    if args['threading']:
        def run_in_new_loop(async_fn, *args, **kwargs):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(async_fn(*args, **kwargs))
            return result[0]

        tpe = ThreadPoolExecutor(args['limit'])
        fs = []
        async for page in generator:
            fs.append(tpe.submit(run_in_new_loop, async_fn, page, **args))

        for f in fs:
            yield f.result()
    else:
        pending = []

        # semaphoreで調整しながら並列化する
        async for page in generator:
            async with concurrent_semaphore:
                pending.append(asyncio.ensure_future(async_fn(page, **args)))

        # 並列化したやつを非同期的に待ち直列化する
        while len(pending):
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for t in done:
                for img in t.result():
                    yield img


def normarize_path(__path: str) -> str:
    return re.sub('[ ]', '_', __path)
