#!/usr/bin/python3
import sys
import asyncio
from libdlimg.waiter import Waiter, select_waiter
import libdlimg.core
import libdlimg.sites
import libdlimg.lib
import argparse
import signal
from libdlimg.error import FATAL, INFO, WARN, report


parser = argparse.ArgumentParser('fast image downloader')
parser.add_argument('url', action='store', nargs='?', help='URL')
parser.add_argument('--archive', '-a', action='store_true', default=False, help='archive as zip')
parser.add_argument('--selenium', '-d', action='store_true', default=False, help='selenium')
parser.add_argument('--name', '-n', choices=['keep', 'number', 'random'], default='number', help='how to name the files')
parser.add_argument('--startnum', '-sn', type=int, default=0, help='image number starts from this number when select `number` as name')
parser.add_argument('--namelen', '-nl', type=int, default=-1, help='max length of filename')
parser.add_argument('--pagestart', '-ps', type=int, default=1, help='page start')
parser.add_argument('--pageend', '-pe', type=int, default=-1, help='page end')
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

args = parser.parse_args()

args_dict = vars(args)

# 引数チェック
if args_dict['mods']:
    libdlimg.sites.print_sites_info()
    exit(0)
if not (args_dict['url'] or (args_dict['query'] and args_dict['site'])):
    parser.print_usage()
    exit(1)

args_dict['name_fn'] = libdlimg.lib.select_name(args_dict['name'])
args_dict['threading'] = args_dict['selenium']
args_dict['waiter'] = Waiter(**args_dict)

signal.signal(signal.SIGINT, lambda n, f: report(FATAL, 'SIGINT', **args_dict) or exit(1))

info_getter = libdlimg.sites.info_getter_selector(**args_dict)
loop = asyncio.get_event_loop()

report(WARN, f'start crawling: `{" ".join(sys.argv)}`', **args_dict)
loop.run_until_complete(
    libdlimg.core.archive_downloader(info_getter,
                                     **args_dict)
)
