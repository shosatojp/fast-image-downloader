import multiprocessing as mp
import glob
from concurrent.futures.process import ProcessPoolExecutor
import shutil
import time
import requests
import bs4
import urllib.parse
import os
import argparse
import signal
import fcntl


class Cacher():
    def __init__(self, cache_dir: str = 'cache') -> None:
        if not os.path.exists(cache_dir):
            os.mkdir(cache_dir)
        self.cache_dir = cache_dir

    def get(self, filename: str):
        path = os.path.join(self.cache_dir, filename)
        if os.path.exists(path):
            with open(path, 'rt', encoding='utf-8') as f:
                return f.read()

    def set(self, filename: str, content, info):
        tmppath = os.path.join(self.cache_dir, '.' + filename)
        path = os.path.join(self.cache_dir, filename)
        with open(tmppath, 'wt', encoding='utf-8') as f:
            f.write(content)
        shutil.move(tmppath, path)
