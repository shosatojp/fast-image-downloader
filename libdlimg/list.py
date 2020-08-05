from libdlimg.error import INFO, FILEIO, Reporter
import os
import json


class FileList():
    def __init__(self, listfile: str, max=100, reporter: Reporter = None):
        self.listfile = listfile
        self.list = []
        self.max = max
        self.reporter = reporter
        if self.listfile:
            with open(self.listfile, 'wt', encoding='utf-8') as f:
                f.write('')

    def add(self, path: str):
        self.list.append(path)

        if len(path) == self.max:
            self.write()
            self.list = []

    def write(self):
        if self.listfile:
            with open(self.listfile, 'wt', encoding='utf-8') as f:
                self.reporter.report(INFO, f'writing {self.listfile}', type=FILEIO)
                f.write('\n'.join(self.list)+'\n')


class Mapper():
    def __init__(self, outdir: str, reporter: Reporter = None):
        self.outdir = outdir
        self.mapfile = os.path.join(outdir, 'map.json')

        self.WRITE_MAP_COUNT = 0
        self.SAVE_MAP_PER = 1000
        self.imgmap = {}

        self.reporter = reporter

        self.load_map()

    def write_map(self, __url: str, __filename: str):
        self.imgmap[__url] = __filename

        self.WRITE_MAP_COUNT += 1
        if self.WRITE_MAP_COUNT % self.SAVE_MAP_PER == 0:
            self.save_map()

    def save_map(self):
        with open(self.mapfile, 'wt', encoding='utf-8') as f:
            self.reporter.report(INFO, f'writing {self.mapfile}', type=FILEIO)
            json.dump(self.imgmap, f)

    def load_map(self):
        if os.path.exists(self.mapfile):
            with open(self.mapfile, 'rt', encoding='utf-8') as f:
                self.reporter.report(INFO, f'reading {self.mapfile}', type=FILEIO)
                self.imgmap = json.loads(f.read() or '{}')
        else:
            self.imgmap = {}

    def read_map(self, __url: str):
        if __url in self.imgmap and os.path.exists(os.path.join(self.outdir, self.imgmap[__url])):
            return self.imgmap[__url]
        else:
            return False
