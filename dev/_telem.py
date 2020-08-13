"""Configure and start the telemetry server"""
import os
import os.path as op
import signal
import sys
from typing import Dict

from scripts import configs
from scripts import utils

import _build as build


# TODO: ask docker to setup supported servers
def _ensure_db(_: Dict[str, str]):
    pass


def _get_test_bin():
    bin_fname = "ts"
    if sys.platform == "win32":
        bin_fname = "ts.exe"
    return configs.TELEMETRYSERVERPATH + bin_fname


def _handle_break(signum, stack):   #pylint: disable=unused-argument
    os.remove(_get_test_bin())
    print("\nStopped telemetry test server")
    sys.exit(0)


def start_telemserver(_: Dict[str, str]):
    """Start a telemetry test server"""
    # make sure db is available
    _ensure_db(_)

    test_bin = _get_test_bin()
    # build a server binary for testing
    build.build_telemetry({"<output>": op.basename(test_bin)})

    # listen for CTRL+C
    signal.signal(signal.SIGINT, _handle_break)

    # run it
    utils.system(
        [
            test_bin,
            "mongodb://pyrevit:pyrevit@localhost:27017/pyrevit",
            "--scripts=scripts",
            "--events=events",
            "--port=8090",
        ],
        dump_stdout=True
    )
