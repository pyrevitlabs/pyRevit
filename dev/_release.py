"""Manage pyRevit release tasks"""
# pylint: disable=invalid-name,broad-except
from typing import Dict

import _buildall as buildall
import _setprop as setprop


def create_release(args: Dict[str, str]):
    """Create pyRevit release (build, test, publish)"""
    # update copyright notice
    setprop.update_copyright(args)
    # prepare required arg for setprop.update_versions
    args["<version>"] = args["<tag>"]
    setprop.update_versions(args)

    # now build all projects
    buildall.build_all(args)
