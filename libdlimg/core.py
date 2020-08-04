import argparse
from libdlimg.list import Mapper
from libdlimg.error import FATAL, INFO, FILEIO, PROGRESS, Reporter, report
from libdlimg.lib import normarize_path, show_progress
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


async def archive_downloader(info_getter, reporter: Reporter = None, **args):
    try:
        start = time.time()

        args['semaphore'] = asyncio.Semaphore(args['limit'])
        args['session'] = aiohttp.ClientSession()

        info = await info_getter(**args)
        title = re.sub('[<>:"/\\|?*]', '', info['title']).strip()
        reporter.report(INFO, f'title: {title}')
        imgs = info['imgs']

        bin_path = os.path.join(args['basedir'], args['outdir'] or normarize_path(title))
        os.makedirs(bin_path, exist_ok=True)

        mapper = Mapper(bin_path, reporter=reporter)

        # sigint handler
        def on_sigint(n, f):
            reporter.reporter.report(FATAL, 'SIGINT')
            mapper.save_map()
            exit(1)

        signal.signal(signal.SIGINT, on_sigint)

        i = args['startnum']
        tasks = []
        # async runnerに参照で渡す
        params = {'progress': 0}
        async for img in imgs:
            if isinstance(img, dict):
                imgurl = img['url']
                data = img['data']
            else:
                imgurl = img
                data = None

            filename = args['name_fn']({
                'number': i,
                'url': imgurl,
                'ext': ''
            }, **args)
            basename, _ = os.path.splitext(filename)
            file_path = os.path.join(bin_path, filename)

            # データあり
            if not args['nodata'] and data:
                json_path = os.path.join(bin_path, basename + '.json')
                reporter.report(INFO, f'writing data -> {json_path}', type=FILEIO)
                with open(json_path, 'wt', encoding='utf-8') as fp:
                    json.dump(data, fp)

            # map.jsonの整合性確認
            exists_file = mapper.read_map(imgurl)
            if not exists_file:
                exists_file = lib.exists_prefix(bin_path, basename)
                if exists_file:
                    mapper.write_map(imgurl, exists_file)

            # ファイルが存在しない場合は非同期ダウンロード
            if not exists_file:
                async def runner(imgurl, file_path):
                    ret: dict = await lib.download_img(imgurl, file_path, **args)
                    params['progress'] += 1
                    show_progress(params['progress'], len(tasks), **args)
                    if ret:
                        ret['size'] = os.stat(ret['path']).st_size
                    return ret

                task = asyncio.ensure_future(runner(imgurl, file_path))
                tasks.append(task)
            else:
                reporter.report(INFO, f'skip {imgurl} == {exists_file}')

            if args['count'] != -1 and i+1 >= args['count']:
                break

            i += 1

        downloaded = await asyncio.gather(*tasks)
        await args['session'].close()

        mapper.save_map()

        total_size = 0
        for e in [e for e in downloaded if e]:
            total_size += e['size']

        if args['archive']:
            reporter.report(INFO, f'archiving to {bin_path+".zip"}', type=FILEIO)
            shutil.make_archive(bin_path, 'zip', root_dir=bin_path)
            shutil.rmtree(bin_path)

        total_time = int((time.time() - start)*10)/10
        total_mib = int(total_size/1024/1024 * 10)/10
        reporter.report(FATAL, f'downloaded {len(downloaded)} files in {total_time} s / {total_mib} MiB / {int(total_mib/(total_time + 1e-3)*10)/10} MiB/s')
    except KeyboardInterrupt:
        print('key')
