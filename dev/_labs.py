"""Manage pyRevit labs tasks"""
# pylint: disable=invalid-name,broad-except
import sys
import os.path as op
import logging
from typing import Dict

# dev scripts
from scripts import utils
from scripts import configs


logger = logging.getLogger()


def _abort(message):
    print("Build failed")
    print(message)
    sys.exit(1)


def _build(name: str, sln: str, config: str):
    utils.ensure_windows()

    # clean
    slnpath = op.abspath(sln)
    logger.debug("building %s solution: %s", name, slnpath)
    # clean, restore, build
    print(f"Building {name}...")
    report = utils.system(
        [
            "msbuild",
            slnpath,
            "-t:Clean;Restore;Build",
            f"-p:Configuration={config}",
        ]
    )
    passed, report = utils.parse_msbuild_output(report)
    if not passed:
        _abort(report)
    else:
        print(f"Building {name} completed successfully")


def build_engines(_: Dict[str, str]):
    """Build pyRevit engines"""
    _build("default ironpython engine", configs.LOADERS, "Release")
    _build("ironpython 2.7.* engines", configs.LOADERS, "Release")
    _build("cpython 3.7 engine", configs.CPYTHONRUNTIME, "ReleasePY37")
    _build("cpython 3.8 engine", configs.CPYTHONRUNTIME, "ReleasePY38")


def build_labs(_: Dict[str, str]):
    """Build pyRevit labs"""
    _build("cli and labs", configs.LABS, "Release")
