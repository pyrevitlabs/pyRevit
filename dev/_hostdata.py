"""Manage Host data file tasks"""
# pylint: disable=invalid-name,broad-except
import sys
from typing import Dict, Tuple
import json
from collections import namedtuple

from scripts import configs
from scripts import utils

import _buildall as buildall
import _setprop as setprop

# {
#     "meta": {
#         "schema": "1.0",
#         "source": "https://www.revitforum.org/architecture-general-revit-questions/105-revit-builds-updates-product-support.html"
#     },
#     "product": "Autodesk Revit",
#     "release": "2008 Architecture Service Pack 1",
#     "version": "",
#     "build": "20070607_1700",
#     "target": "x64"
# }
PyRevitHostMeta = namedtuple("PyRevitHostMeta", ["schema,source"])
PyRevitHost = namedtuple(
    "PyRevitHost", ["meta,product,release,version,build,target"]
)


def add_hostdata(ver, key, cli=False):
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


