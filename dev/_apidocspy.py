"""Manage python api documentation tasks"""
# pylint: disable=invalid-name,broad-except
import sys
import shutil
import os.path as op
from typing import Dict

# dev scripts
from scripts import utils
from scripts import configs


def _abort(message):
    print("Building python docs has errors")
    print(message)
    sys.exit(1)


def build_docs(_: Dict[str, str]):
    """Build the python docs"""
    if sys.platform == 'win32':
        print(
            "Skipping building the docs on Windows\n"
            " Some packages fail install due to end of life python 2.7"
            )
        return

    print("Building python docs...")
    report = utils.system(["pipenv", "install"], cwd=configs.DOCS_DIR)
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
    if not report:
        _abort("Sphinx is not configured to build the docs")
    if any(x in report.lower() for x in ['warning', 'failed']):
        _abort(report)
    print("Building python docs completed successfully")


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
