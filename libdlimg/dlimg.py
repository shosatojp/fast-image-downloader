#!/usr/bin/python3
from asyncio.locks import Semaphore
from libdlimg.list import FileList
import os
import sys
import asyncio

import aiohttp
from libdlimg.lib import Fetcher
from libdlimg.waiter import Waiter, select_waiter
import libdlimg.core
import libdlimg.sites
import libdlimg.lib
import argparse
import signal
from libdlimg.error import FATAL, INFO, Reporter, WARN


parser = argparse.ArgumentParser('fast image downloader')
parser.add_argument('url', action='store', nargs='?', help='URL')
parser.add_argument('--archive', '-a', action='store_true', default=False, help='archive as zip')
parser.add_argument('--selenium', '-d', action='store_true', default=False, help='selenium')
parser.add_argument('--profile', '-P', type=str, default='', help='selenium profile directory')
parser.add_argument('--name', '-n', choices=['keep', 'number', 'random'], default='number', help='how to name the files')
parser.add_argument('--startnum', '-sn', type=int, default=0, help='image number starts from this number when select `number` as name')
parser.add_argument('--namelen', '-nl', type=int, default=-1, help='max length of filename')
parser.add_argument('--pagestart', '-ps', type=int, default=1, help='page start')
parser.add_argument('--pageend', '-pe', type=int, default=-1, help='page end')
parser.add_argument('--filelist', '-F', type=str, default='', help='outputs pagefile')
parser.add_argument('--count', '-c', type=int, default=-1, help='max count')
parser.add_argument('--outdir', '-o', default='', help='output directory name')
parser.add_argument('--basedir', '-b', default='', help='output base directory name')
parser.add_argument('--limit', '-l', default=10, type=int, help='limit of concurrent fetching')
parser.add_argument('--quality', '-q', default=0, type=int, help='image quality. 0 is the highest.')
parser.add_argument('--query', '-s', default='',  help='query for search')
parser.add_argument('--site', '-t', default='',  help='site name')
parser.add_argument('--useragent', '-ua', default='',  help='user agent')
parser.add_argument('--mods', '-m', action='store_true', default=False,  help='show available modules')
parser.add_argument('--wait', '-w', default='', nargs='+', type=str, help='interval for http requests. default is none. `-w 0.5` `-w random 1 2.5`')
parser.add_argument('--waitlist', '-wl', default='', type=str, help='interval list for wait option. prior than `--wait`')
parser.add_argument('--nightshift', '-ns', default=1, type=int, help='night shift')
parser.add_argument('--nodata', default=False, action='store_true', help='')
parser.add_argument('--savefetched', '-S', default=False, action='store_true', help='cache fetched documents (html, json, ...)')
parser.add_argument('--usecache', '-U', default=False, action='store_true', help='use cached documents to reduce requests')
parser.add_argument('--verify', '-V', default=False, action='store_true', help='verify map')
parser.add_argument('--handler', '-H', default='', type=str, help='error handler executable')
parser.add_argument('--handlelevel', '-HL', default=3, type=int, help='log level')
parser.add_argument('--loglevel', '-LL', default=2, type=int, help='log level')
parser.add_argument('--command', '-C', default='', type=str, help='download command')

args = parser.parse_args()

args_dict = vars(args)

# 引数チェック
if args_dict['mods']:
    libdlimg.sites.print_sites_info()
    exit(0)
if not (args_dict['url'] or (args_dict['query'] and args_dict['site'])):
    parser.print_usage()
    exit(1)

args_dict['threading'] = args_dict['selenium']
waiter = Waiter(**args_dict)


reporter = Reporter(args.loglevel, args.handler, args.handlelevel)
semaphore = asyncio.Semaphore(args.limit)
filelist = FileList(
    args.filelist and os.path.join(args.basedir, args.outdir, args.filelist),
    reporter=reporter
)
fetcher = Fetcher(
    semaphore=semaphore,
    waiter=waiter,
    cache=args.savefetched,
    usecache=args.usecache,
    cachedir=os.path.join(args.basedir, args.outdir),
    reporter=reporter,
    useragent=args.useragent,
    filelister=filelist,
    selenium=args.selenium,
    profile=args.profile,
)

collector = libdlimg.sites.collector_selector(**args_dict)(
    reporter=reporter,
    waiter=waiter,
    fetcher=fetcher,
)

reporter.report(WARN, f'start crawling: `{" ".join(sys.argv)}`')


async def main():

    await libdlimg.core.archive_downloader(collector, args.basedir, args.outdir, semaphore,
                                           reporter=reporter,
                                           waiter=waiter,
                                           filelister=filelist,
                                           ** args_dict)
    await fetcher.close()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
