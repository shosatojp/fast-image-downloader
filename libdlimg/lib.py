from asyncio.locks import Semaphore
from functools import cached_property
import json
from os import stat_result

from aiohttp.client import ClientSession
from libdlimg.waiter import Waiter
from libdlimg.list import Mapper
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
from libdlimg.error import ERROR, INFO, NETWORK, PROGRESS, FILEIO, Reporter

concurrent_semaphore = asyncio.Semaphore(10)
# executor = concurrent.futures.ThreadPoolExecutor(10)
waiter_table = {}
# imgmap = None

CACHE_VERSION = 1


class ImageDownloader():
    def __init__(self,
                 reporter: Reporter = None,
                 mapper: Mapper = None,
                 waiter: Waiter = None):
        self.reporter = reporter
        self.mapper = mapper
        self.waiter = waiter

    async def download_img(self, __url, __path, **args):
        # waiter
        if self.waiter:
            await self.waiter.wait(__url)

        try:
            async with concurrent_semaphore:
                async with aiohttp.ClientSession() as session:
                    async with session.get(__url) as res:
                        if res.status == 200:
                            _, ext = os.path.splitext(__path)
                            if not ext:
                                __path += mimetypes.guess_extension(res.content_type) or '.jpg'

                            self.reporter.report(INFO, f'downloading {__url} -> {__path}', type=NETWORK)

                            dirname, filename = os.path.split(__path)
                            tmp_path = f'{dirname}/.{filename}'

                            async with aiofiles.open(tmp_path, 'wb') as fd:
                                while True:
                                    chunk = await res.content.read(1024)
                                    if not chunk:
                                        break
                                    await fd.write(chunk)
                        else:
                            self.reporter.report(ERROR, f'download_img: {res.status} {__url}', type=NETWORK)
                            return None

            if os.path.exists(tmp_path):
                shutil.move(tmp_path, __path)

            # save mapdata
            self.mapper.write_map(__url, filename)

            return {
                'path': __path,
                'tmp_path': tmp_path,
            }
        except Exception as e:
            self.reporter.report(ERROR, f'skip {__url} {e}\n{traceback.format_exc()}', type=NETWORK)
            return None


class Fetcher():
    def __init__(self,
                 semaphore: Semaphore,
                 reporter: Reporter = None,
                 waiter: Waiter = None,
                 cachedir: str = '',
                 cache: bool = True,
                 usecache: bool = True,
                 useragent: str = ''
                 ) -> None:
        self.session = ClientSession()
        self.semaphore = semaphore
        self.reporter = reporter
        self.waiter = waiter
        self.cachedir = cachedir
        self.cache = cache
        self.usecache = usecache
        self.useragent = useragent

    async def close(self):
        await self.session.close()

    async def fetch(self, __url: str, ret={}):
        if self.usecache:
            obj = self.load_cache(__url)
            if obj:
                ret['realurl'] = obj['realurl']
                return obj['body']

        # waiter
        if self.waiter:
            await self.waiter.wait(__url)

        # if args['threading']:
        #     return await fetch_by_browser2(__url, **args)

        headers = {}
        if self.useragent:
            headers['user-agent'] = self.useragent

        try:
            async with self.semaphore:
                session: aiohttp.client.ClientSession = self.session
                self.reporter.report(INFO, f'fetching {__url}', type=NETWORK)
                async with session.get(__url, headers=headers) as res:
                    if res.status == 200:
                        ret['realurl'] = res.url
                        text = await res.text()
                        if self.cache:
                            self.save_fetched(__url, text, {
                                'realurl': str(res.url)
                            })
                        return text
                    else:
                        self.reporter.report(ERROR, f'error response {res.status} {__url}', type=NETWORK)
                        return None
        except Exception as e:
            self.reporter.report(ERROR, f'skip {__url} {e}', file=sys.stderr, type=NETWORK)

    def load_cache(self, __url: str):
        filename = urllib.parse.quote(__url, '')
        htmlpath = os.path.join(self.cachedir, filename+'.html')
        jsonpath = os.path.join(self.cachedir, filename+'.json')

        html = None

        if os.path.exists(htmlpath):
            with open(htmlpath, 'rt', encoding='utf-8') as f:
                self.reporter.report(INFO, f'reading {htmlpath}', type=FILEIO)
                html = f.read()

        if os.path.exists(jsonpath):
            with open(jsonpath, 'rt', encoding='utf-8') as f:
                self.reporter.report(INFO, f'reading {jsonpath}', type=FILEIO)
                obj = json.load(f)
            if 'cache_version' in obj and obj['cache_version'] == CACHE_VERSION:

                # json内にhtml置くのやめる
                if 'body' in obj:
                    html = obj['body']
                    with open(htmlpath, 'wt', encoding='utf-8') as f:
                        self.reporter.report(INFO, f'writing {htmlpath}', type=FILEIO)
                        f.write(obj['body'])
                    del obj['body']
                    with open(jsonpath, 'wt', encoding='utf-8') as f:
                        self.reporter.report(INFO, f'writing {jsonpath}', type=FILEIO)
                        json.dump(obj, f)
                ###############################

                obj['body'] = html

                return obj
            else:
                return None
        else:
            return None

    def save_fetched(self, __url: str, __body: str, __obj):
        filename = urllib.parse.quote(__url, '')
        htmlpath = os.path.join(self.cachedir, filename+'.html')
        jsonpath = os.path.join(self.cachedir, filename+'.json')
        __obj['cache_version'] = CACHE_VERSION
        with open(jsonpath, 'wt', encoding='utf-8') as f:
            self.reporter.report(INFO, f'writing {jsonpath}', type=FILEIO,)
            json.dump(__obj, f)
        with open(htmlpath, 'wt', encoding='utf-8') as f:
            self.reporter.report(INFO, f'writing {htmlpath}', type=FILEIO)
            f.write(__body)

    async def fetch_doc(self, __url: str, ret={}):
        html = await self.fetch(__url, ret)
        return html and bs4.BeautifulSoup(html, 'lxml')


def name_keep(params, **args):
    parsed = urllib.parse.urlparse(params['url'])
    filename = os.path.split(parsed.path)[1]
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


def single_selector_collector(__url, __selector, __attr='src', fetcher: Fetcher = None, **args):
    async def get_imgs():
        doc = await fetcher.fetch_doc(__url)
        urls = list(map(lambda e: e[__attr], doc.select(__selector)))
        for url in urls:
            yield url

    return get_imgs


async def single_one_selector(params, fetcher: Fetcher = None):
    doc = await fetcher.fetch_doc(params['url'])
    return doc.select_one(params['selector'])[params['attr']]


async def multiple_selector(params, fetcher: Fetcher = None):
    doc = await fetcher.fetch_doc(params['url'])
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
