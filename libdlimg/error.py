import subprocess

PROGRESS = 0
DEBUG = 1
INFO = 2
WARN = 3
ERROR = 4
FATAL = 5

# リアルタイムで通知したいので同期的に


NETWORK = '>'
FILEIO = '.'


def report(level: int, message: str, end='\n', type=' ', ** args):
    if level == PROGRESS or level >= args['loglevel']:
        print(type*level, message, end=end)

    if level >= args['handlelevel'] and args['handler']:
        subprocess.run([args['handler'], str(level), message])
