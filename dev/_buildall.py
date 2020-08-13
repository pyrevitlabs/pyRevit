"""Build all"""
import os
import os.path as op
import shutil
from typing import Dict

from scripts import configs

import _autocomplete as autocomp
import _build as build


ARTIFACTS = ['bin', 'obj', '.vs', 'TestResults']

def build_clean(_: Dict[str, str]):
    """Clean bin and obj from projects"""
    for dirname, subdirs, _ in os.walk(configs.DEVPATH):
        for subdir in subdirs:
            if any(subdir == x for x in ARTIFACTS):
                shutil.rmtree(op.join(dirname, subdir))


def build_all(_: Dict[str, str]):
    """Build all projects under pyRevit dev"""
    build.build_labs(_)
    build.build_engines(_)
    build.build_telemetry(_)
    autocomp.build_autocomplete(_)
