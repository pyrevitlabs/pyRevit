"""Unit Tests for pyrevit.coreutils.appdata module."""
#pylint: disable=E0401
import re

import pyrevit
from pyrevit.coreutils import appdata


__context__ = 'zero-doc'


TEST_STRINGS = ['pyRevit_some-randomename',
                'pyRevit_2018_some-randomename',
                'pyRevit_2018_14422_some-randomname',
                'pyRevit_eirannejad_some-randomename',
                'pyRevit_2018_eirannejad_some-randomename',
                'pyRevit_2018_eirannejad_14422_some-randomename']

for tstring in TEST_STRINGS:
    print('Testing: "{}"'.format(tstring))

    # e.g. pyRevit_2018_eirannejad_14422_
    m = re.match(pyrevit.PYREVIT_FILE_PREFIX_STAMPED_USER_REGEX, tstring)
    if m:
        print('\tMatched: {}'.format(
            pyrevit.PYREVIT_FILE_PREFIX_STAMPED_USER_REGEX))
        print('\t' + str(m.groupdict()))

    # e.g. pyRevit_2018_14422_
    m = re.match(pyrevit.PYREVIT_FILE_PREFIX_STAMPED_REGEX, tstring)
    if m:
        print('\tMatched: {}'.format(pyrevit.PYREVIT_FILE_PREFIX_STAMPED_REGEX))
        print('\t' + str(m.groupdict()))

    # e.g. pyRevit_2018_eirannejad_
    m = re.match(pyrevit.PYREVIT_FILE_PREFIX_USER_REGEX, tstring)
    if m:
        print('\tMatched: {}'.format(pyrevit.PYREVIT_FILE_PREFIX_USER_REGEX))
        print('\t' + str(m.groupdict()))

    # e.g. pyRevit_2018_
    m = re.match(pyrevit.PYREVIT_FILE_PREFIX_REGEX, tstring)
    if m:
        print('\tMatched: {}'.format(pyrevit.PYREVIT_FILE_PREFIX_REGEX))
        print('\t' + str(m.groupdict()))

    # e.g. pyRevit_eirannejad_
    m = re.match(pyrevit.PYREVIT_FILE_PREFIX_UNIVERSAL_USER_REGEX, tstring)
    if m:
        print('\tMatched: {}'.format(
            pyrevit.PYREVIT_FILE_PREFIX_UNIVERSAL_USER_REGEX))
        print('\t' + str(m.groupdict()))

    # e.g. pyRevit_
    m = re.match(pyrevit.PYREVIT_FILE_PREFIX_UNIVERSAL_REGEX, tstring)
    if m:
        print('\tMatched: {}'.format(
            pyrevit.PYREVIT_FILE_PREFIX_UNIVERSAL_REGEX))
        print('\t' + str(m.groupdict()))
