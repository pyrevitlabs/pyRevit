"""Manage Host data file tasks"""
# pylint: disable=invalid-name,broad-except
import sys
import re
import signal
from typing import Dict
import json
from collections import namedtuple

from scripts import configs
from scripts import utils


PyRevitHostMeta = namedtuple("PyRevitHostMeta", "schema,source")
PyRevitHost = namedtuple(
    "PyRevitHost", "meta,product,release,version,build,target,notes"
)


def _handle_break(signum, stack):  # pylint: disable=unused-argument
    print("\nCancelled new host entry")
    sys.exit(0)


def _abort(message):
    print(message)
    sys.exit(1)


def _load_host(d):
    if "schema" in d:
        return PyRevitHostMeta(**d)
    else:
        return PyRevitHost(**d)


def _valid_release(release):
    return re.match(r"^\d{4}(.\d{1})?$", release)


def _valid_version(version):
    return re.match(r"^\d{2}\.\d+\.\d+\.\d+$", version)


def _valid_build(build):
    return re.match(r"^\d{8}_\d{4}$", build)


def _input(name, title, validator, hdata):
    data = ""
    while not validator(data):
        if data:
            print(utils.colorize(f"<red>Invalid {name} format</red>"))
        data = input(utils.colorize(f"<f>Enter {title}:</f>\n"))
        if any(x for x in hdata if getattr(x, name) == data):
            _abort(f"Host already exists with {name}={data}")
    return data


def add_hostdata(_: Dict[str, str]):
    """Add new Revit version to host data"""
    hdata = []
    with open(configs.PYREVIT_HOSTS_DATAFILE, "r") as dfile:
        hdata = json.load(dfile, object_hook=_load_host)

    signal.signal(signal.SIGINT, _handle_break)

    release = _input(
        "release", "Release Name (e.g. 2021.1)", _valid_release, hdata
    )
    version = _input(
        "version", "Version (e.g. 21.1.0.108)", _valid_version, hdata
    )
    build = _input(
        "build", "Build Number (e.g. 20200708_1515)", _valid_build, hdata
    )
    meta_source = input("Enter Release Notes URL:\n")
    if not meta_source:
        _abort("You must provide a source for this information")
    notes = input("Enter Any Notes:\n")

    hdata.append(
        PyRevitHost(
            meta=PyRevitHostMeta(schema="1.0", source=meta_source),
            product="Autodesk Revit",
            release=release,
            version=version,
            build=build,
            target="x64",
            notes=notes,
        ),
    )

    with open(configs.PYREVIT_HOSTS_DATAFILE, "w") as dfile:
        json.dump([x._asdict() for x in hdata], dfile, indent=True)
