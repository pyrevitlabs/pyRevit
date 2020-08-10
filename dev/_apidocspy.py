"""Manage python api documentation tasks"""
# pylint: disable=invalid-name,broad-except
import shutil
import os.path as op
from typing import Dict

# dev scripts
from scripts import utils
from scripts import configs


def build_docs(_: Dict[str, str]):
    """Build the python docs"""
    report = utils.system(
        [
            "pipenv",
            "run",
            "sphinx-build",
            "-b",
            "html",
            configs.DOCS_DIR,
            configs.DOCS_BUILD,
        ],
        cwd=configs.DOCS_DIR,
    )
    print(report)


def open_docs(_: Dict[str, str]):
    """Open the local python docs in browser"""
    if op.exists(configs.DOCS_INDEX):
        if sys.platform == "darwin":
            runargs = ["open", configs.DOCS_INDEX]
        else:
            runargs = ["start", configs.DOCS_INDEX]
        utils.system(runargs)
    else:
        raise Exception("Docs are not built yet")


def clean_docs(_: Dict[str, str]):
    """Clean the local python docs build folder"""
    shutil.rmtree(configs.DOCS_BUILD)
    print("Removed docs build directory")
