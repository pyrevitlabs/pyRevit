"""Manage pyRevit labs tasks"""
# pylint: disable=invalid-name,broad-except
import sys
import os.path as op
import logging
from typing import Dict, Optional

# dev scripts
from scripts import utils
from scripts import configs

import _install as install


logger = logging.getLogger()


def _abort(message):
    print("Build failed")
    print(message)
    sys.exit(1)


def _build(name: str, sln: str, config: str, publish_dir: str = None, print_output: Optional[bool] = False):
    utils.ensure_windows()

    # clean
    slnpath = op.abspath(sln)
    logger.debug("building %s solution: %s", name, slnpath)
    # clean, restore, build
    if publish_dir is None:
        print(f"Building {name}...")
        report = utils.system(
            [
                install.get_tool("dotnet"),
                "build",
                slnpath,
                "-c",
                f"{config}",
            ],
            dump_stdout=print_output
        )
    else:
        print(f"Publish {name}...")
        report = utils.system(
            [
                install.get_tool("dotnet"),
                "publish",
                slnpath,
                "-c",
                f"{config}",
                "-o",
                f"{publish_dir}",
            ],
            dump_stdout=print_output
        )

    passed, report = utils.parse_dotnet_build_output(report)
    if not passed:
        _abort(report)
    else:
        print(f"Building {name} completed successfully")


def build_engines(_: Dict[str, str]):
    """Build pyRevit engines"""
    _build("ironpython engines", configs.LOADERS, "Release")
    _build("cpython 3.7 engine", configs.CPYTHONRUNTIME, "ReleasePY37")
    _build("cpython 3.8 engine", configs.CPYTHONRUNTIME, "ReleasePY38")


def build_labs(_: Dict[str, str]):
    """Build pyRevit labs"""
    _build("labs", configs.LABS, "Release")
    _build("cli", configs.LABS_CLI, "Release", configs.BINPATH)
    _build("doctor", configs.LABS_DOCTOR, "Release", configs.BINPATH)


def build_runtime(_: Dict[str, str]):
    """Build pyRevit runtime"""
    _build("runtime", configs.RUNTIME, "Release")
