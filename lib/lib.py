from concurrent.futures import ThreadPoolExecutor
import threading
import time
import glob
import re
import os
import bs4
import asyncio
import shutil
import urllib
import aiohttp
import sys
import random
import string
import aiofiles
import mimetypes
import concurrent.futures
import aiohttp.client_exceptions

concurrent_semaphore = asyncio.Semaphore(10)
executor = concurrent.futures.ThreadPoolExecutor(10)
waiter_table = {}


async def download_img(__url, __path, **args):
    # waiter
    if 'waiter' in args:
        await args['waiter'].wait(__url)

    try:
        async with concurrent_semaphore:
            async with aiohttp.ClientSession() as session:
                async with session.get(__url) as res:
                    _, ext = os.path.splitext(__path)
                    if not ext:
                        __path += mimetypes.guess_extension(res.content_type) or '.jpg'

                    print(f'downloading {__url} -> {__path}')

                    dirname, filename = os.path.split(__path)
                    tmp_path = f'{dirname}/.{filename}'

                    async with aiofiles.open(tmp_path, 'wb') as fd:
                        while True:
                            chunk = await res.content.read(1024)
                            if not chunk:
                                break
                            await fd.write(chunk)

        if os.path.exists(tmp_path):
            shutil.move(tmp_path, __path)

        return {
            'path': __path,
            'tmp_path': tmp_path,
        }
    except aiohttp.client_exceptions.TooManyRedirects as e:
        print(f'TooManyRedirects: skip {__url}')
    except:
        print(f'unknown error: skip {__url}')


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


async def paged_collector(links_fn, ** args):
    page_num = args['pagestart'] if 'pagestart' in args else 1
    page_end = args['pageend'] if 'pageend' in args else -1
    while True:
        links = await links_fn(page_num)
        for link in links:
            yield link
        if len(links) == 0 or (page_end != -1 and page_num >= page_end):
            break
        page_num += 1


async def fetch(__url: str, ret={}, **args):
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
                ret['realurl'] = res.url
                print('fetched', __url)
                return await res.text()
    except:
        print(f'unknown error: skip {__url}')


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

    print('fetched', __url)
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
    return len(files) != 0


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
