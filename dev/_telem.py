"""Configure and start the telemetry server"""
import os
import os.path as op
import signal
import sys
from typing import Dict

from scripts import configs
from scripts import utils


# TODO: ask docker to setup supported servers
def _ensure_db(_: Dict[str, str]):
    pass


def _get_test_bin():
    bin_fname = "ts"
    if sys.platform == "win32":
        bin_fname = "ts.exe"
    return op.join(configs.TELEMETRYSERVERPATH, bin_fname)


def _handle_break(signum, stack):   #pylint: disable=unused-argument
    os.remove(_get_test_bin())
    print("\nStopped telemetry test server")
    sys.exit(0)


def build_telem(args: Dict[str, str]):
    """Build pyRevit telemetry server"""
    # get telemetry dependencies
    # configure git globally for `go get`
    utils.system(
        [
            "git",
            "config",
            "--global",
            "http.https://pkg.re.followRedirects",
            "true",
        ]
    )

    print("Updating telemetry server dependencies...")
    report = utils.system(
        ["go", "get", r"./..."],
        cwd=op.abspath(configs.TELEMETRYSERVERPATH),
        dump_stdout=True
    )
    print("Telemetry server dependencies successfully updated")

    print("Building telemetry server...")
    output_bin = (
        args["<output>"]
        if "<output>" in args
        else op.abspath(configs.TELEMETRYSERVERBIN)
    )
    report = utils.system(
        ["go", "build", "-o", output_bin, op.abspath(configs.TELEMETRYSERVER)],
        cwd=op.abspath(configs.TELEMETRYSERVERPATH),
    )
    print("Building telemetry server completed successfully")


def start_telem(_: Dict[str, str]):
    """Start a telemetry test server"""
    # make sure db is available
    _ensure_db(_)

    test_bin = _get_test_bin()
    # build a server binary for testing
    build_telem({"<output>": op.basename(test_bin)})

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
