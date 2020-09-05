import argparse
from asyncio.locks import Semaphore

from aiohttp.client import ClientSession
from libdlimg.waiter import Waiter
from libdlimg.sites.wear import Collector
from libdlimg.list import FileList, Mapper
from libdlimg.error import FATAL, INFO, FILEIO, PROGRESS, Reporter
from libdlimg.lib import CommandDownloader, Fetcher, ImageDownloader, normarize_path, register_rmap, select_namer
import sys
import aiohttp
import urllib
import shutil
import asyncio
import bs4
import os
import re
from . import lib
from . import sites
import time
import json
import stat
import signal


def show_progress(reporter: Reporter, __progress: int, __total: int):
    reporter.report(PROGRESS, f'  {__progress}/{__total}  {int(__progress/__total*1000)/10}%', end='\r')


async def archive_downloader(
        collector: Collector,
        base_directory: str,
        out_directory: str,
        semaphore: Semaphore,
        reporter: Reporter,
        waiter: Waiter,
        archive=False,
        count: int = -1,
        nodata: bool = False,
        noimage: bool = False,
        startnum=0,
        **args):
    try:
        start = time.time()

        title = re.sub('[<>:"/\\|?*]', '', await collector.gettitle(args['url'])).strip()
        reporter.report(INFO, f'title: {title}')

        bin_path = os.path.join(base_directory, out_directory or normarize_path(title))
        os.makedirs(bin_path, exist_ok=True)

        if args['command']:
            image_downloader = CommandDownloader(
                reporter=reporter,
                command=args['command'],
            )
        else:
            image_downloader = ImageDownloader(
                reporter=reporter,
                waiter=waiter,
                semaphore=semaphore,
            )

        # sigint handler
        def on_sigint(n, f):
            reporter.report(FATAL, 'SIGINT')
            exit(1)

        signal.signal(signal.SIGINT, on_sigint)

        namer = select_namer(args['name'], args['namelen'])

        i = startnum
        tasks = []
        # async runnerに参照で渡す
        params = {'progress': 0}
        async for img in collector.collector(**args):
            if isinstance(img, dict):
                imgurl = img['url']
                data = img['data']
            else:
                imgurl = img
                data = None

            filename = namer.getname(url=imgurl, ext='', number=i)
            basename, _ = os.path.splitext(filename)
            file_path = os.path.join(bin_path, filename)

            # データあり
            if not nodata and data:
                json_path = os.path.join(bin_path, filename + '.json')
                reporter.report(INFO, f'writing data -> {json_path}', type=FILEIO)
                with open(json_path, 'wt', encoding='utf-8') as fp:
                    json.dump(data, fp)

            # ファイル存在確認
            exists_file = lib.exists_prefix(bin_path, basename)

            # ファイルが存在しない場合は非同期ダウンロード
            if not exists_file:
                async def runner(imgurl, file_path):
                    ret: dict = await image_downloader.download_img(imgurl, file_path)
                    params['progress'] += 1
                    show_progress(reporter, params['progress'], len(tasks))
                    if ret:
                        register_rmap(ret['path'])
                        ret['size'] = os.stat(ret['path']).st_size
                    return ret

                if not noimage:
                    task = asyncio.ensure_future(runner(imgurl, file_path))
                    tasks.append(task)
            else:
                reporter.report(INFO, f'skip {imgurl} == {exists_file}')

            if count != -1 and i+1 >= count:
                break

            i += 1

        downloaded = await asyncio.gather(*tasks)

        total_size = 0
        for e in [e for e in downloaded if e]:
            total_size += e['size']

        if archive:
            reporter.report(INFO, f'archiving to {bin_path+".zip"}', type=FILEIO)
            shutil.make_archive(bin_path, 'zip', root_dir=bin_path)
            shutil.rmtree(bin_path)

        total_time = int((time.time() - start)*10)/10
        total_mib = int(total_size/1024/1024 * 10)/10
        reporter.report(FATAL, f'downloaded {len(downloaded)} files in {total_time} s / {total_mib} MiB / {int(total_mib/(total_time + 1e-3)*10)/10} MiB/s')
    except KeyboardInterrupt:
        print('key')
