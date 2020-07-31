from lib.lib import normarize_path
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
        print('title', title)
        imgs = info['imgs']

        bin_path = os.path.join(args['basedir'], args['outdir'] or normarize_path(title))
        os.makedirs(bin_path, exist_ok=True)

        i = args['startnum']
        tasks = []
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

            exists_file = lib.load_map(imgurl, **args) if args['imgmap'] else not lib.exists_prefix(bin_path, basename)
            if not exists_file:
                async def runner(imgurl, file_path):
                    await lib.download_img(imgurl, file_path, **args)
                    params['progress'] += 1
                    show_progress(params['progress'], len(tasks))

                # データあり
                if not args['nodata'] and data:
                    json_path = os.path.join(bin_path, basename + '.json')
                    print(f'writing data -> {json_path}')
                    with open(json_path, 'wt', encoding='utf-8') as fp:
                        json.dump(data, fp)

                task = asyncio.ensure_future(runner(imgurl, file_path))
                tasks.append(task)
            else:
                print(f'skip: {imgurl} -> {exists_file}')

            if args['count'] != -1 and i+1 >= args['count']:
                break

            i += 1

        downloaded = await asyncio.gather(*tasks)

        if args['check']:
            lib.save_map_asjson(**args)

        total_size = 0
        for e in [e for e in downloaded if e]:
            total_size += os.stat(e['path']).st_size

        if args['archive']:
            print('archiving to ', bin_path+'.zip')
            shutil.make_archive(bin_path, 'zip', root_dir=bin_path)
            shutil.rmtree(bin_path)

        await args['session'].close()

        total_time = int((time.time() - start)*10)/10 + 1e-3
        total_mib = int(total_size/1024/1024 * 10)/10
        print(f'downloaded {len(downloaded)} files in {total_time} s / {total_mib} MiB / {int(total_mib/total_time*10)/10} MiB/s')
    except KeyboardInterrupt:
        print('key')


def show_progress(__progress: int, __total: int):
    print(f'  {__progress}/{__total}  {int(__progress/__total*1000)/10}%', end='\r')
