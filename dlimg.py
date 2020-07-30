#!/usr/bin/python3
import asyncio
from lib.waiter import select_waiter
import lib.core
import lib.sites
import lib.lib
import argparse
import signal

signal.signal(signal.SIGINT, lambda n, f: exit(1))

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
parser.add_argument('--basedir', '-b', default='bin', help='output base directory name')
parser.add_argument('--limit', '-l', default=10, type=int, help='limit of concurrent fetching')
parser.add_argument('--quality', '-q', default=0, type=int, help='image quality. 0 is the highest.')
parser.add_argument('--query', '-s', default='',  help='query for search')
parser.add_argument('--site', '-t', default='',  help='site name')
parser.add_argument('--useragent', '-ua', default='',  help='user agent')
parser.add_argument('--mods', '-m', action='store_true', default=False,  help='show available modules')
parser.add_argument('--wait', '-w', default='', nargs='+', type=str, help='interval for http requests. default is none. `-w 0.5` `-w random 1 2.5`')

args = parser.parse_args()

args_dict = vars(args)

# 引数チェック
if args_dict['mods']:
    lib.sites.print_sites_info()
    exit(0)
if not (args_dict['url'] or (args_dict['query'] and args_dict['site'])):
    parser.print_usage()
    exit(1)

args_dict['name_fn'] = lib.lib.select_name(args_dict['name'])
args_dict['threading'] = args_dict['selenium']
args_dict['waiter'] = select_waiter(args_dict['wait'])

info_getter = lib.sites.info_getter_selector(**args_dict)
loop = asyncio.get_event_loop()
loop.run_until_complete(
    lib.core.archive_downloader(info_getter,
                                **args_dict)
)
