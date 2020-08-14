"""Manage tasks related to the build environment"""
# pylint: disable=invalid-name,broad-except
from collections import namedtuple
from typing import Dict

from scripts import utils

RequiredTool = namedtuple("RequiredTool", ["name", "get", "step"])


REQUIRED_TOOLS = [
    RequiredTool(name="msbuild", get="", step="build"),
    RequiredTool(name="go", get="", step="build"),
    RequiredTool(name="gcc", get="", step="build"),
    RequiredTool(name="signtool", get="", step="release"),
    RequiredTool(name="advancedinstaller.com", get="", step="release"),
]


def install(_: Dict[str, str]):
    """Prepare build environment"""
    print("Preparing build environment")


def check(_: Dict[str, str]):
    """Check build environment"""
    any_failed = False
    # check required tools
    for rtool in REQUIRED_TOOLS:
        has_tool = utils.where(rtool.name)
        if has_tool:
            print(utils.colorize(f"[ <grn>PASS</grn> ]\t{rtool.name} is ready"))
        else:
            any_failed = True
            print(
                utils.colorize(
                    f"[ <red>FAIL</red> ]\t{rtool.name} is "
                    f"required for {rtool.step} step. "
                    f"see --help"
                )
            )
    return any_failed
