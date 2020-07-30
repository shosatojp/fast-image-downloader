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
        async for img in imgs:
            filename = args['name_fn']({
                'number': i,
                'url': img,
                'ext': ''
            }, **args)
            basename, _ = os.path.splitext(filename)
            file_path = os.path.join(bin_path, filename)

            if not lib.exists_prefix(bin_path, basename):
                task = asyncio.ensure_future(lib.download_img(img, file_path))
                tasks.append(task)

            if args['count'] != -1 and i+1 >= args['count']:
                break

            i += 1

        downloaded = await asyncio.gather(*tasks)

        total_size = 0
        for e in [e for e in downloaded if e]:
            total_size += os.stat(e['path']).st_size

        if args['archive']:
            print('archiving to ', bin_path+'.zip')
            shutil.make_archive(bin_path, 'zip', root_dir=bin_path)
            shutil.rmtree(bin_path)

        await args['session'].close()

        total_time = int((time.time() - start)*10)/10
        total_mib = int(total_size/1024/1024 * 10)/10
        print(f'downloaded {len(downloaded)} files in {total_time} s / {total_mib} MiB / {int(total_mib/total_time*10)/10} MiB/s')
    except KeyboardInterrupt:
        print('key')
