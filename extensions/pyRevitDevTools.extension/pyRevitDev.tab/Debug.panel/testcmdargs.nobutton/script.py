"""Test docopt argument processing.

Usage:
    testdocopt (-h | --help)
    testdocopt (-V | --version)
    testdocopt -e <encod> <src_file>

Options:
    -h, --help                          Show this help
    -V, --version                       Show command version
    -e <encod>, --encode <encod>        File encoding [default: utf-8]
""" # noqa

import sys

from pyrevit import forms
from pyrevit import script

import docopt


logger = script.get_logger()


try:
    logger.debug(sys.argv)
    args = docopt.docopt(__doc__,
                         version='testdocopt {}'.format('v0.1'),
                         help=True)
    print(args)
except docopt.DocoptExit:
    forms.alert('This command needs command line arguments. '
                'Run from pyRevit search and provide arguments')
