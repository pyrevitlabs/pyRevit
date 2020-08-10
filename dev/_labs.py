"""Manage pyRevit labs tasks"""
# pylint: disable=invalid-name,broad-except
from typing import Dict

# dev scripts
from scripts import utils
from scripts import configs


def build_labs(_: Dict[str, str]):
    """Build pyRevit labs"""
    # clean
    utils.system(
        [f"msbuild {configs.LABS} ", "-t:Restore ", "-p:Configuration=Release"]
    )
    # build
    utils.system([f"msbuild {configs.LABS} ", "-t:Build ", "-p:Configuration=Release"])

