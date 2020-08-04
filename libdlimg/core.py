import argparse
from libdlimg.error import FATAL, INFO, FILEIO, PROGRESS, report
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


async def archive_downloader(info_getter, **args):
    try:
        start = time.time()

        args['semaphore'] = asyncio.Semaphore(args['limit'])
        args['session'] = aiohttp.ClientSession()

        info = await info_getter(**args)
        title = re.sub('[<>:"/\\|?*]', '', info['title']).strip()
        report(INFO, f'title: {title}', **args)
        imgs = info['imgs']

        bin_path = os.path.join(args['basedir'], args['outdir'] or normarize_path(title))
        os.makedirs(bin_path, exist_ok=True)

        lib.load_map(**args)

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
                report(INFO, f'writing data -> {json_path}', type=FILEIO, **args)
                with open(json_path, 'wt', encoding='utf-8') as fp:
                    json.dump(data, fp)

            # map.jsonの整合性確認
            exists_file = lib.read_map(imgurl, **args)
            if not exists_file:
                exists_file = lib.exists_prefix(bin_path, basename)
                if exists_file:
                    lib.write_map(imgurl, exists_file, **args)

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
                report(INFO, f'skip {imgurl} == {exists_file}', **args)

            if args['count'] != -1 and i+1 >= args['count']:
                break

            i += 1

        downloaded = await asyncio.gather(*tasks)

        lib.save_map(**args)

        total_size = 0
        for e in [e for e in downloaded if e]:
            total_size += e['size']

        if args['archive']:
            report(INFO, f'archiving to {bin_path+".zip"}', type=FILEIO, **args)
            shutil.make_archive(bin_path, 'zip', root_dir=bin_path)
            shutil.rmtree(bin_path)

        await args['session'].close()

        total_time = int((time.time() - start)*10)/10
        total_mib = int(total_size/1024/1024 * 10)/10
        report(FATAL, f'downloaded {len(downloaded)} files in {total_time} s / {total_mib} MiB / {int(total_mib/(total_time + 1e-3)*10)/10} MiB/s', **args)
    except KeyboardInterrupt:
        print('key')

