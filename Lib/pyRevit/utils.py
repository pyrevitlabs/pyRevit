import os
import os.path as op
import subprocess as sp
import time


def assert_folder(folder):
    if not op.exists(folder):
        try:
            os.makedirs(folder)
        except OSError:
            return False
    return True


def get_parent_directory(path):
    return op.dirname(path)


def run_process(proc, cwd=''):
    return sp.Popen(proc, stdout=sp.PIPE, stderr=sp.PIPE, cwd=cwd, shell=True)


class Timer:
    """Timer class using python native time module."""
    def __init__(self):
        self.start = time.time()

    def restart(self):
        self.start = time.time()

    def get_time_hhmmss(self):
        return "%02.2f seconds" % (time.time() - self.start)
