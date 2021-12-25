"""Manage pyRevit release tasks"""
# pylint: disable=invalid-name,broad-except
import sys
import os
import os.path as op
import uuid
import json
import re
import logging
from typing import Dict, List
from collections import namedtuple

from scripts import configs
from scripts import utils

import _install as install
import _build as build
import _props as props


logger = logging.getLogger()


PyRevitProduct = namedtuple("PyRevitProduct", "product,release,version,key")


def _abort(message):
    print("Release failed")
    print(message)
    sys.exit(1)


def _installer_set_uuid(installer_files: List[str]) -> List[str]:
    product_code = str(uuid.uuid4())
    uuid_finder = re.compile(
        r"^#define MyAppUUID \"(\w{8}-\w{4}-\w{4}-\w{4}-\w{12})\""
    )
    for installer_file in installer_files:
        contents = []
        file_changed = False
        with open(installer_file, "r") as instfile:
            logger.debug(
                "Setting uuid in file %s to %s", installer_file, product_code
            )
            for cline in instfile.readlines():
                if uuid_finder.match(cline):
                    newcline = uuid_finder.sub(
                        f'#define MyAppUUID "{product_code}"', cline
                    )
                    if cline != newcline:
                        file_changed = True
                    contents.append(newcline)
                else:
                    contents.append(cline)
        if file_changed:
            with open(installer_file, "w") as instfile:
                instfile.writelines(contents)
    return product_code


def _update_product_data_file(ver, key, cli=False):
    pdata = []
    with open(configs.PYREVIT_PRODUCTS_DATAFILE, "r") as dfile:
        pdata = json.load(dfile, object_hook=lambda d: PyRevitProduct(**d))

    if cli:
        if any(x for x in pdata if "CLI" in x.product and x.version == ver):
            _abort(f"pyRevit CLI product already exists with {ver=}")

        first_cli = next(x for x in pdata if x.product == "pyRevit CLI")
        index = pdata.index(first_cli)
        pdata.insert(
            index,
            PyRevitProduct(
                product="pyRevit CLI", release=ver, version=ver, key=key
            ),
        )

    else:
        if any(x for x in pdata if x.product == "pyRevit" and x.version == ver):
            _abort(f"pyRevit product already exists with {ver=}")

        pdata.insert(
            0,
            PyRevitProduct(
                product="pyRevit", release=ver, version=ver, key=key
            ),
        )

    with open(configs.PYREVIT_PRODUCTS_DATAFILE, "w") as dfile:
        json.dump([x._asdict() for x in pdata], dfile, indent=True)


def set_product_data(_: Dict[str, str]):
    """Set new product uuid on installers and product uuid database """
    pyrevit_pc = _installer_set_uuid(configs.PYREVIT_INSTALLER_FILES)
    pyrevitcli_pc = _installer_set_uuid(configs.PYREVIT_CLI_INSTALLER_FILES)
    release_ver = props.get_version()
    _update_product_data_file(release_ver, pyrevit_pc)
    _update_product_data_file(release_ver, pyrevitcli_pc, cli=True)


def _get_binaries():
    for dirname, _, files in os.walk(configs.BINPATH):
        for fn in files:
            bf = fn.lower()
            if bf.startswith("pyrevit") and any(
                bf.endswith(x) for x in [".exe", ".dll"]
            ):
                yield op.join(dirname, fn)


def sign_binaries(_: Dict[str, str]):
    """Sign binaries with certificate (must be installed on machine)"""
    print("digitally signing binaries...")
    for bin_file in _get_binaries():
        utils.system(
            [
                "signtool",
                "sign",
                "/n",
                "Ehsan Iran Nejad",
                "/t",
                "http://timestamp.digicert.com",
                "/fd",
                "sha256",
                f"{bin_file}",
            ]
        )


def _ensure_clean_tree():
    res = utils.system(["git", "status"])
    if "nothing to commit" not in res:
        print("You have uncommited changes in working tree. Commit those first")
        sys.exit(1)


def build_installers(_: Dict[str, str]):
    """Build pyRevit and CLI installers"""
    installer = "iscc.exe"
    for script in configs.INSTALLER_FILES:
        print(f"Building installer {script}")
        utils.system(
            [
                installer,
                op.abspath(script),
            ]
        )


def sign_installers(_: Dict[str, str]):
    """Sign installers with certificate (must be installed on machine)"""
    print("digitally signing installers...")
    build_version = props.get_version()
    for installer_exe_fmt in configs.INSTALLER_EXES:
        installer_exe = installer_exe_fmt.format(version=build_version)
        utils.system(
            [
                "signtool",
                "sign",
                "/n",
                "Ehsan Iran Nejad",
                "/t",
                "http://timestamp.digicert.com",
                "/fd",
                "sha256",
                f"{installer_exe}",
            ]
        )


def create_release(args: Dict[str, str]):
    """Create pyRevit release (build all projects, create installers)"""
    # utils.ensure_windows()

    # run a check on all tools
    if not install.check(args):
        _abort("At least one necessary tool is missing for release process")

    # update copyright notice
    props.set_year(args)

    # update release version
    # prepare required arg for props.set_ver
    args["<ver>"] = args["<tag>"]
    props.set_ver(args)

    # update product data
    set_product_data(args)

    # now build all projects
    build.build_binaries(args)

    # sign everything
    sign_binaries(args)

    # now build the installers
    build_installers(args)

    # now sign installers
    sign_installers(args)


def _commit_changes(msg):
    for commit_file in configs.COMMIT_FILES:
        utils.system(["git", "add", commit_file])
    utils.system(["git", "commit", "-m", msg])


def _tag_changes():
    build_version = props.get_version()
    utils.system(["git", "tag", f"v{build_version}"])


def commit_and_tag_build(_: Dict[str, str]):
    """Commit changes and tag repo"""
    _commit_changes("Publish!")
    _tag_changes()
