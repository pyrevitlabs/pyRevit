"""Build all"""
import os
import os.path as op
import shutil
from typing import Dict

from scripts import configs

import _apidocspy as apidocs
import _autocomplete as autoc
import _labs as labs
import _telem as telem


ARTIFACTS = ['bin', 'obj', '.vs', 'TestResults']


def clean_build(_: Dict[str, str]):
    """Clean bin and obj from projects"""
    for dirname, subdirs, _ in os.walk(configs.DEVPATH):
        for subdir in subdirs:
            if any(subdir == x for x in ARTIFACTS):
                shutil.rmtree(op.join(dirname, subdir))


def build_binaries(_: Dict[str, str]):
    """Build all projects under pyRevit dev"""
    apidocs.build_docs(_)
    labs.build_labs(_)
    labs.build_engines(_)
    telem.build_telem(_)
    autoc.build_autocmp(_)
