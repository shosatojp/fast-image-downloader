import re
import importlib
import os
from . import anysites


def get_modules():
    modules = []
    files = filter(lambda e: not e.startswith('__'), os.listdir(os.path.dirname(__file__)))
    for file in files:
        name = file.replace('.py', '')
        mod = vars(importlib.import_module('libdlimg.sites.'+name))
        modules.append((file, name, mod))
    return modules


def load_site_modules():
    sites = {}
    for file, name, mod in get_modules():
        if all(map(lambda e: e in mod, ['info_getter', 'site', 'match'])):
            sites[name] = mod
    return sites


def info_getter_selector(**args):
    sites = load_site_modules()

    for e in sites.values():
        if (args['url'] and re.match(e['match'], args['url'])) or \
                (args['query'] and ('query' in e) and e['site'] == args['site']):
            return e['info_getter']

    return anysites.info_getter


def print_sites_info():
    print("| {:<20} | {:^5} |".format('site', 'query'))
    print("| {:-<20} | {:-^5} |".format('', ''))
    for file, name, mod in get_modules():
        query = 'query' in mod and mod['query']
        print("| {:<20} | {:^5} |".format(mod['site'], 'O' if query else 'X'))
