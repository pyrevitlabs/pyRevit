"""Manage pyRevit release tasks"""
# pylint: disable=invalid-name,broad-except
import sys
import os
import os.path as op
from typing import Dict, Tuple
import json
from collections import namedtuple

from scripts import configs
from scripts import utils

import _buildall as buildall
import _setprop as setprop


PyRevitProduct = namedtuple("PyRevitProduct", "product,release,version,key")


def _abort(message):
    print("Release failed")
    print(message)
    sys.exit(1)


def _installer_set_version(version) -> Tuple[str, str]:
    installer = "advancedinstaller.com"
    product_codes = []
    for script in [configs.PYREVIT_AIPFILE, configs.PYREVIT_CLI_AIPFILE]:
        print(f"Updating installer script {script} to {version}")
        utils.system(
            [installer, "/edit", op.abspath(script), "/setversion", version]
        )
        product_code_report = utils.system(
            [installer, "/edit", script, "/getproperty", "ProductCode",]
        )
        # e.g. 1033:{uuid}
        product_codes.append(product_code_report.split(":")[1])
    return (product_codes[0], product_codes[1])


def _update_product_data(ver, key, cli=False):
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


def _installer_build():
    installer = "advancedinstaller.com"
    for script in [configs.PYREVIT_AIPFILE, configs.PYREVIT_CLI_AIPFILE]:
        print(f"Building installer {script}")
        utils.system(
            [installer, "/build", op.abspath(script),]
        )


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


def create_release(args: Dict[str, str]):
    """Create pyRevit release (build, test, publish)"""
    utils.ensure_windows()

    release_ver = args["<tag>"]
    # update copyright notice
    setprop.set_year(args)
    # prepare required arg for setprop.set_ver
    args["<ver>"] = release_ver
    setprop.set_ver(args)

    # now build all projects
    buildall.build_all(args)

    # update installers and get new product versions
    pyrevit_pc, pyrevitcli_pc = _installer_set_version(release_ver)
    _update_product_data(release_ver, pyrevit_pc)
    _update_product_data(release_ver, pyrevitcli_pc, cli=True)

    # sign everything
    _sign_binaries()

    # now build the installers
    # installer are signed by the installer builder
    _installer_build()
