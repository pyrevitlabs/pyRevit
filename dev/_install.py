"""Manage tasks related to the build environment"""
# pylint: disable=invalid-name,broad-except
from typing import Dict


def install(_: Dict[str, str]):
    """Prepare build environment"""
    print("running install")
