import os
import os.path as op
import subprocess as sp


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
