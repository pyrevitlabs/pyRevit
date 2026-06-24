"""Build all"""
import os
import os.path as op
import shutil
from typing import Dict

from scripts import configs

# import _apidocspy as apidocs # not used by new documentation workflow
import _autocomplete as autoc
import _labs as labs

import shutil

ARTIFACTS = ['bin', 'obj', '.vs', 'TestResults']


def clean_build(_: Dict[str, str]):
    """Clean bin and obj from projects"""
    for dirname, subdirs, _ in os.walk(configs.DEVPATH):
        for subdir in subdirs:
            if any(subdir == x for x in ARTIFACTS):
                shutil.rmtree(op.join(dirname, subdir))


def build_binaries(_: Dict[str, str]):
    """Build all projects under pyRevit dev.

    Note: vendored dependencies under dev/libs/{netfx,netcore} (MahApps.Metro,
    NLog, Newtonsoft.Json, Python.Net, ...) are NOT rebuilt here. They are
    committed to git and consumed by the labs/runtime projects via HintPath.
    To refresh them, run `pipenv run pyrevit build deps` locally; that step
    still requires the .NET Core 3.1 SDK (for the MahApps.Metro netcore TFM)
    and is intended for maintainers bumping a submodule under dev/modules/.
    """
    # apidocs.build_docs(_)
    labs.build_labs(_)
    labs.build_engines(_)
    labs.build_runtime(_)
    autoc.build_autocmp(_)
