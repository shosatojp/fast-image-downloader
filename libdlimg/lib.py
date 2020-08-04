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
from libdlimg.error import ERROR, INFO, NETWORK, PROGRESS, FILEIO, report

concurrent_semaphore = asyncio.Semaphore(10)
executor = concurrent.futures.ThreadPoolExecutor(10)
waiter_table = {}
imgmap = None

CACHE_VERSION = 1


def show_progress(__progress: int, __total: int, **args):
    report(PROGRESS, f'  {__progress}/{__total}  {int(__progress/__total*1000)/10}%', end='\r', **args)


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

                        report(INFO, f'downloading {__url} -> {__path}', type=NETWORK, **args)

                        dirname, filename = os.path.split(__path)
                        tmp_path = f'{dirname}/.{filename}'

                        async with aiofiles.open(tmp_path, 'wb') as fd:
                            while True:
                                chunk = await res.content.read(1024)
                                if not chunk:
                                    break
                                await fd.write(chunk)
                    else:
                        report(ERROR, f'download_img: {res.status} {__url}', type=NETWORK, **args)
                        return None

        if os.path.exists(tmp_path):
            shutil.move(tmp_path, __path)

        # save mapdata
        write_map(__url, filename, **args)

        return {
            'path': __path,
            'tmp_path': tmp_path,
        }
    except Exception as e:
        report(ERROR, f'skip {__url} {e}\n{traceback.format_exc()}', type=NETWORK, **args)
        return None

WRITE_MAP_COUNT = 0
SAVE_MAP_PER = 1000


def write_map(__url: str, __filename: str, **args):
    global imgmap
    global WRITE_MAP_COUNT
    imgmap[__url] = __filename

    WRITE_MAP_COUNT += 1
    if WRITE_MAP_COUNT % SAVE_MAP_PER == 0:
        save_map(**args)


def save_map(**args):
    mapfile = os.path.join(args['basedir'], args['outdir'], 'map.json')
    with open(mapfile, 'wt', encoding='utf-8') as f:
        report(INFO, f'writing {mapfile}', type=FILEIO, **args)
        json.dump(imgmap, f)


def load_map(**args):
    global imgmap
    directory = os.path.join(args['basedir'], args['outdir'])
    mapfile = os.path.join(directory, 'map.json')
    if os.path.exists(mapfile):
        with open(mapfile, 'rt', encoding='utf-8') as f:
            report(INFO, f'reading {mapfile}', type=FILEIO, ** args)
            imgmap = json.loads(f.read() or '{}')
    else:
        imgmap = {}


def read_map(__url: str, **args):
    global imgmap

    if __url in imgmap and os.path.exists(os.path.join(args['basedir'], args['outdir'], imgmap[__url])):
        return imgmap[__url]
    else:
        return False


def single_selector_collector(__url, __selector, __attr='src', **args):
    async def get_imgs():
        doc = await fetch_doc(__url, **args)
        urls = list(map(lambda e: e[__attr], doc.select(__selector)))
        for url in urls:
            yield url

    return get_imgs


async def single_one_selector(params, **args):
    doc = await fetch_doc(params['url'], **args)
    return doc.select_one(params['selector'])[params['attr']]


async def multiple_selector(params, **args):
    doc = await fetch_doc(params['url'], **args)
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
            report(INFO, f'fetching {__url}', type=NETWORK, **args)
            async with session.get(__url, headers=headers) as res:
                if res.status == 200:
                    ret['realurl'] = res.url
                    text = await res.text()
                    if args['savefetched']:
                        save_fetched(__url, text, {
                            'realurl': str(res.url)
                        }, **args)
                    return text
                else:
                    report(ERROR, f'fetch(): {__url}', type=NETWORK, **args)
                    return None
    except Exception as e:
        report(ERROR, f'skip {__url} {e}', file=sys.stderr, type=NETWORK, **args)


def load_cache(__url: str, **args):
    filename = urllib.parse.quote(__url, '')
    htmlpath = os.path.join(args['basedir'], args['outdir'], filename+'.html')
    jsonpath = os.path.join(args['basedir'], args['outdir'], filename+'.json')

    html = None

    if os.path.exists(htmlpath):
        with open(htmlpath, 'rt', encoding='utf-8') as f:
            report(INFO, f'reading {htmlpath}', type=FILEIO, **args)
            html = f.read()

    if os.path.exists(jsonpath):
        with open(jsonpath, 'rt', encoding='utf-8') as f:
            report(INFO, f'reading {jsonpath}', type=FILEIO, **args)
            obj = json.load(f)
        if 'cache_version' in obj and obj['cache_version'] == CACHE_VERSION:

            # json内にhtml置くのやめる
            if 'body' in obj:
                html = obj['body']
                with open(htmlpath, 'wt', encoding='utf-8') as f:
                    report(INFO, f'writing {htmlpath}', type=FILEIO, **args)
                    f.write(obj['body'])
                del obj['body']
                with open(jsonpath, 'wt', encoding='utf-8') as f:
                    report(INFO, f'writing {jsonpath}', type=FILEIO, **args)
                    json.dump(obj, f)
            ###############################

            obj['body'] = html

            return obj
        else:
            return None
    else:
        return None


def save_fetched(__url: str, __body: str, __obj, **args):
    filename = urllib.parse.quote(__url, '')
    htmlpath = os.path.join(args['basedir'], args['outdir'], filename+'.html')
    jsonpath = os.path.join(args['basedir'], args['outdir'], filename+'.json')
    __obj['cache_version'] = CACHE_VERSION
    with open(jsonpath, 'wt', encoding='utf-8') as f:
        report(INFO, f'writing {jsonpath}', type=FILEIO,  **args)
        json.dump(__obj, f)
    with open(htmlpath, 'wt', encoding='utf-8') as f:
        report(INFO, f'writing {htmlpath}', type=FILEIO, **args)
        f.write(__body)


async def fetch_by_browser2(__url: str, **args):
    from selenium.webdriver.firefox.options import Options
    from selenium import webdriver

    def get():
        firefox_options = Options()
        firefox_options.add_argument("--headless")
        driver = webdriver.Firefox(options=firefox_options)
        driver.get(__url)

        while True:
            state = driver.execute_script('return document.readyState')
            if state == 'complete':
                break
            time.sleep(0.1)

        html = driver.find_element_by_tag_name('html').get_attribute('innerHTML')
        driver.quit()
        return html

    report(INFO, f'fetched {__url}', type=NETWORK, **args)
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
    return bs4.BeautifulSoup(html, 'lxml')


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


rmap = {}


def exists_prefix(rootdir, prefix):
    global rmap
    if not rmap:
        files = glob.glob(os.path.join(rootdir, '*'))
        for e in files:
            _, basename = os.path.split(e)
            name, ext = os.path.splitext(basename)
            rmap[name] = ext

    if prefix in rmap and rmap[prefix] != '.json':
        return prefix + rmap[prefix]
    else:
        return False


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
