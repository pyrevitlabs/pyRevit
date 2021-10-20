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
import _buildall as buildall
import _props as props


logger = logging.getLogger()


PyRevitProduct = namedtuple("PyRevitProduct", "product,release,version,key")


def _abort(message):
    print("Release failed")
    print(message)
    sys.exit(1)


def _installer_set_uuid() -> List[str]:
    product_codes = []
    uuid_finder = re.compile(r"^#define MyAppUUID \"(\w{8}-\w{4}-\w{4}-\w{4}-\w{12})\"")
    for installer_file in configs.INSTALLER_FILES:
        contents = []
        file_changed = False
        product_code = str(uuid.uuid4())
        with open(installer_file, "r") as instfile:
            logger.debug(f"Setting uuid in file {installer_file} to {product_code}")
            for cline in instfile.readlines():
                if uuid_finder.match(cline):
                    newcline = uuid_finder.sub(f"#define MyAppUUID \"{product_code}\"", cline)
                    if cline != newcline:
                        file_changed = True
                    contents.append(newcline)
                else:
                    contents.append(cline)
        if file_changed:
            with open(installer_file, "w") as instfile:
                instfile.writelines(contents)

        product_codes.append(product_code)
    return product_codes


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


def set_product_data(args: Dict[str, str]):
    pyrevit_pc, pyrevitcli_pc = _installer_set_uuid()
    release_ver = props.get_version()
    _update_product_data_file(release_ver, pyrevit_pc)
    _update_product_data_file(release_ver, pyrevitcli_pc, cli=True)


def _get_binaries():
    for dirname, _, files in os.walk(configs.BINPATH):
        for fn in files:
            bf = fn.lower()
            if bf.startswith('pyrevit') \
                    and any(bf.endswith(x) for x in ['.exe', '.dll']):
                yield op.join(dirname, fn)


def _sign_binaries():
    print("digitally signing binaries...")
    for bin_file in _get_binaries():
        utils.system([
            'signtool', 'sign',
            '/n', 'Ehsan Iran Nejad',
            '/t', 'http://timestamp.digicert.com',
            '/fd', 'sha256',
            f'{bin_file}'
        ])


def _ensure_clean_tree():
    res = utils.system(['git', 'status'])
    if 'nothing to commit' not in res:
        print('You have uncommited changes in working tree. Commit those first')
        sys.exit(1)


def _commit_changes(msg):
    utils.system(['git', 'add', '--all'])
    utils.system(['git', 'commit', '-m', msg])


def build_installers(args: Dict[str, str]):
    """Build pyRevit and CLI installers"""
    installer = "advancedinstaller.com"
    for script in [configs.PYREVIT_INSTALLERFILE, configs.PYREVIT_CLI_INSTALLERFILE]:
        print(f"Building installer {script}")
        utils.system(
            [installer, "/build", op.abspath(script),]
        )


def create_release(args: Dict[str, str]):
    """Create pyRevit release (build all, create installers)"""
    # utils.ensure_windows()

    # _ensure_clean_tree()

    # run a check on all tools
    if not install.check(args):
        _abort('At least one necessary tool is missing for release process')

    release_ver = args["<tag>"]
    # update copyright notice
    props.set_year(args)
    # prepare required arg for setprop.set_ver
    args["<ver>"] = release_ver
    props.set_ver(args)

    # update installers and get new product versions
    update_product_data(args)

    # _commit_changes(f"Updated version: {release_ver}")

    # now build all projects
    buildall.build_all(args)

    # sign everything
    # _sign_binaries()

    # now build the installers
    # installer are signed by the installer builder
    # build_installers(args)
