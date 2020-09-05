from asyncio.locks import Semaphore
from importlib.resources import path
import json
from random import Random

from aiohttp.client import ClientSession
from libdlimg.waiter import Waiter
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
import aiohttp.client_exceptions
import traceback
import sys
from libdlimg.error import ERROR, INFO, NETWORK, PROGRESS, FILEIO, Reporter, WARN

import subprocess


class CommandDownloader():
    def __init__(self,
                 reporter: Reporter = None,
                 command: str = '',
                 **others):
        self.reporter = reporter
        self.command = command

    async def download_img(self, __url, __path, **args):
        process = subprocess.run([self.command, __url, __path])
        if not process.returncode:
            self.reporter.report(INFO, f'download with command {__url} -> {__path}', type=NETWORK)
        else:
            self.reporter.report(ERROR, f'download command failed {__url} -> {__path}', type=NETWORK)


class ImageDownloader():
    def __init__(self,
                 reporter: Reporter = None,
                 waiter: Waiter = None,
                 semaphore: Semaphore = None,
                 **others):
        self.reporter = reporter
        self.waiter = waiter
        self.semaphore = semaphore

    async def download_img(self, __url, __path, **args):
        # waiter
        if self.waiter:
            await self.waiter.wait(__url)

        try:
            async with self.semaphore:
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
                 useragent: str = '',
                 selenium: bool = False,
                 profile: str = '',
                 ) -> None:
        self.session = ClientSession()
        self.semaphore = semaphore
        self.reporter = reporter
        self.waiter = waiter
        self.cachedir = cachedir
        self.cache = cache
        self.usecache = usecache
        self.useragent = useragent
        self.selenium = selenium
        self.profile = profile
        self.CACHE_VERSION = 1

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

        if self.selenium:
            return await self.fetch_by_browser(__url)

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
            if 'cache_version' in obj and obj['cache_version'] == self.CACHE_VERSION:
                obj['body'] = html
                return obj
            else:
                return None
        else:
            return None

    def save_fetched(self, __url: str, __body: str, __obj):
        filename = urllib.parse.quote(__url, '')
        tmpname = '.' + filename
        htmlpath = os.path.join(self.cachedir, filename+'.html')
        jsonpath = os.path.join(self.cachedir, filename+'.json')
        tmphtmlpath = os.path.join(self.cachedir, tmpname+'.html')
        tmpjsonpath = os.path.join(self.cachedir, tmpname+'.json')
        __obj['cache_version'] = self.CACHE_VERSION

        with open(tmpjsonpath, 'wt', encoding='utf-8') as f:
            self.reporter.report(INFO, f'writing {jsonpath}', type=FILEIO,)
            json.dump(__obj, f)
        shutil.move(tmpjsonpath, jsonpath)

        with open(tmphtmlpath, 'wt', encoding='utf-8') as f:
            self.reporter.report(INFO, f'writing {htmlpath}', type=FILEIO)
            f.write(__body)
        shutil.move(tmphtmlpath, htmlpath)

    async def fetch_doc(self, __url: str, ret={}):
        html = await self.fetch(__url, ret)
        return html and bs4.BeautifulSoup(html, 'lxml')

    async def fetch_by_browser(self, __url: str):
        from selenium.webdriver.firefox.options import Options
        from selenium import webdriver

        def get():
            opt = Options()
            opt.add_argument("--headless")
            profile = webdriver.FirefoxProfile(self.profile)
            print(self.profile, profile.profile_dir)
            # opt.add_argument('--profile')
            # opt.add_argument(self.profile)
            driver = webdriver.Firefox(profile, options=opt)

            print(driver.profile.path)
            driver.get(__url)

            while True:
                state = driver.execute_script('return document.readyState')
                if state == 'complete':
                    break
                time.sleep(0.1)

            html = driver.find_element_by_tag_name('html').get_attribute('innerHTML')
            # driver.quit()
            # driver.binary.kill()
            if self.cache:
                self.save_fetched(__url, html, {
                    'realurl': str(__url)  # リダイレクト後のURL取れる？
                })
            return html

        self.reporter.report(INFO, f'fetched {__url}', type=NETWORK)
        return get()


class Namer():
    def __init__(self, namelen: int) -> None:
        self.namelen = namelen
        self._count = 0

    def getname(self, url: str = '', ext: str = '', number: int = 0) -> str:
        pass

    def getnameext(self, url: str):
        parsed = urllib.parse.urlparse(url)
        filename = os.path.split(parsed.path)[1]
        return os.path.splitext(filename)

    def get_unique_prefix(self):
        self._count += 1
        return str(int(time.time() * 1000)) + '_'\
            + str(self._count).zfill(3) + '_'\
            + ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(3)])


class KeepedNamer(Namer):
    def __init__(self, namelen) -> None:
        super(KeepedNamer, self).__init__(namelen)

    def getname(self, url: str = '', ext: str = '', number: int = 0):
        name, _ext = self.getnameext(url)
        if self.namelen > 0:
            name = name[:self.namelen]
        return name + (_ext or ext)


class NumberddNamer(Namer):
    def __init__(self, namelen) -> None:
        super(NumberddNamer, self).__init__(namelen)

    def getname(self, url: str = '', ext: str = '', number: int = 0):
        name, _ext = self.getnameext(url)
        namelen = self.namelen if self.namelen > 0 else 5
        return str(number).zfill(namelen) + (_ext or ext)


class RandomNamer(Namer):
    def __init__(self, namelen) -> None:
        super(RandomNamer, self).__init__(namelen)

    def getname(self, url: str = '', ext: str = '', number: int = 0):
        name, _ext = self.getnameext(url)
        namelen = self.namelen if self.namelen > 0 else 5
        rand = [random.choice(string.ascii_letters + string.digits) for i in range(namelen)]
        return self.get_unique_prefix() + '.' + ''.join(rand) + (_ext or ext)


class UrlNamer(Namer):
    def __init__(self, namelen) -> None:
        super(UrlNamer, self).__init__(namelen)

    def getname(self, url: str = '', ext: str = '', number: int = 0):
        name, _ext = os.path.splitext(url)
        return urllib.parse.quote(name, '') + (_ext or ext)


def select_namer(src: str, namelen: int) -> Namer:
    return {
        'keep': KeepedNamer,
        'number': NumberddNamer,
        'random': RandomNamer,
        'url': UrlNamer,
    }[src](namelen)


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


def register_rmap(path):
    _, filename = os.path.split(path)
    basename, ext = os.path.splitext(filename)
    rmap[basename] = ext


async def parallel_for(generator, async_fn, parallel: int = 10, **args):
    if args['threading']:
        def run_in_new_loop(async_fn, *args, **kwargs):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(async_fn(*args, **kwargs))
            return result[0]

        tpe = ThreadPoolExecutor(args['limit'])
        pending = set()
        async for page in generator:
            if len(pending) <= parallel:
                pending.add(tpe.submit(run_in_new_loop, async_fn, page, **args))
            else:
                _pending = []
                for f in pending:
                    if f.done():
                        yield f.result()
                    else:
                        _pending.append(f)
                pending = _pending
    else:
        pending = set()
        async for page in generator:

            if len(pending) <= parallel:
                pending.add(asyncio.ensure_future(async_fn(page, **args)))

            else:
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


async def single_one_selector(params, fetcher: Fetcher, **args):
    doc = await fetcher.fetch_doc(params['url'])
    return doc.select_one(params['selector'])[params['attr']]


async def multiple_selector(params, fetcher: Fetcher, **args):
    doc = await fetcher.fetch_doc(params['url'])
    return list(map(lambda e: e[params['attr']], doc.select(params['selector'])))


async def paged_collector(links_fn, ps: int, pe: int, params=None, ** args):
    while True:
        if params:
            links = await links_fn(ps, params, **args)
        else:
            links = await links_fn(ps, **args)

        for link in links:
            yield link
        if len(links) == 0 or (pe != -1 and ps >= pe):
            break
        ps += 1
