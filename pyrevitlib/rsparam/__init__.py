"""Utilities for working with Revit shared parameter files."""

import re

import codecs
import csv
import locale
from collections import namedtuple, defaultdict


# pylama:ignore=D105

# rsparam version
__version__ = '0.1.15'
__sparamversion__ = (2, 1)


SharedParamEntries = namedtuple('SharedParamEntries', ['groups', 'params'])


class SharedParamFileItem(object):
    def __init__(self, lineno):
        # make line number start from 1
        self.lineno = lineno + 1

    def __contains__(self, key):
        for value in self:
            if bool(re.findall(key, str(value))):
                return True
        return False

    def __eq__(self, other):
        return hash(self) == hash(other)


class SharedParamGroup(SharedParamFileItem):
    def __init__(self, args, lineno=None):
        super(SharedParamGroup, self).__init__(lineno)
        self.guid = args[0]
        self.desc = args[1]
        self.name = self.desc

    def __str__(self):
        return self.desc

    def __iter__(self):
        return iter([self.guid, self.desc])

    def __repr__(self):
        return '<{} desc:"{}" guid:{}>'.format(self.__class__.__name__,
                                               self.desc, self.guid)

    def __hash__(self):
        return hash(self.guid + self.desc)


class SharedParam(SharedParamFileItem):
    def __init__(self, args, lineno=None):
        super(SharedParam, self).__init__(lineno)
        self.guid = args[0]
        self.name = args[1]
        self.datatype = args[2]
        self.datacategory = args[3]
        self.group = args[4]
        self.visible = args[5]
        self.desc = args[6]
        self.usermod = args[7]

    def __str__(self):
        return self.desc

    def __iter__(self):
        return iter([self.guid, self.name, self.datatype,
                     self.datacategory, self.group, self.visible,
                     self.desc, self.usermod])

    def __repr__(self):
        return '<{} name:"{}" guid:{}>'.format(self.__class__.__name__,
                                               self.name, self.guid)

    def __hash__(self):
        return hash(self.guid + self.name
                    + self.datatype + self.datacategory
                    + self.visible + self.desc + self.usermod)


def read_entries(src_file, encoding=None):
    # open file and collect shared param and groups
    spgroups = []
    sparams = []
    with codecs.open(src_file, 'r', encoding) as spf:
        count = 0
        for line in csv.reader(spf, delimiter="\t"):
            if len(line) >= 1:
                if line[0] == 'PARAM':
                    sparam = SharedParam(line[1:], lineno=count)
                    sparams.append(sparam)
                elif line[0] == 'GROUP':
                    spgroup = SharedParamGroup(line[1:], lineno=count)
                    spgroups.append(spgroup)
            count += 1

    # now update sparams with group obj
    for sp in sparams:
        for spg in spgroups:
            if sp.group == spg.guid:
                sp.group = spg

    return SharedParamEntries(spgroups, sparams)


def write_entries(entries, out_file, encoding=None):
    with codecs.open(out_file, 'w', encoding) as spf:
        spf.write("# This is a Revit shared parameter file.\r\n")
        spf.write("# Do not edit manually unless you know better!\r\n")
        spf.write("*META\tVERSION\tMINVERSION\r\n")
        spf.write("META\t{max_ver}\t{min_ver}\r\n"
                  .format(max_ver=__sparamversion__[0],
                          min_ver=__sparamversion__[1]))

        sparamwriter = csv.writer(spf, delimiter="\t")

        # write groups referenced by SharedParam instances and in entries
        spf.write("*GROUP\tID\tNAME\r\n")
        if isinstance(entries, SharedParamEntries):
            refgroups = {x.group for x in entries.params}
            spgroups = {x for x in entries.groups}
        else:
            refgroups = {x.group for x in entries if isinstance(x, SharedParam)}
            spgroups = {x for x in entries if isinstance(x, SharedParamGroup)}
        spgroups = spgroups.union(refgroups)
        sys_language = locale.getdefaultlocale(locale.LC_ALL)[0]
        try:
            locale.setlocale(locale.LC_ALL, "{}.UTF-8".format(sys_language))
        except locale.Error:  # Fix for python/ironpython 2
            locale.setlocale(locale.LC_ALL, sys_language)
        for spg in sorted(spgroups, key=lambda x: locale.strxfrm(x.name)):
            sparamwriter.writerow(['GROUP', spg.guid, spg.name])

        # write SharedParam in entries
        spf.write("*PARAM\tGUID\tNAME\tDATATYPE\tDATACATEGORY\tGROUP\t"
                  "VISIBLE\tDESCRIPTION\tUSERMODIFIABLE\r\n")
        if isinstance(entries, SharedParamEntries):
            sparams = {x for x in entries.params}
        else:
            sparams = {x for x in entries if isinstance(x, SharedParam)}
        for sp in sorted(sparams, key=lambda x: locale.strxfrm(x.name)):
            sparamwriter.writerow(
                ['PARAM', sp.guid, sp.name, sp.datatype, sp.datacategory,
                 sp.group.guid, sp.visible, sp.desc, sp.usermod]
                )


def get_paramgroups(src_file, encoding=None):
    spgroups, sparams = read_entries(src_file, encoding=encoding)
    return spgroups


def get_params(src_file, encoding=None, groupid=None):
    spgroups, sparams = read_entries(src_file, encoding=encoding)
    if groupid:
        return [x for x in sparams if x.group.guid == groupid]

    return sparams


def find_duplicates(src_file, encoding=None, byname=False):
    param_guid_lut = defaultdict(list)
    group_guid_lut = defaultdict(list)

    spgroups, sparams = read_entries(src_file, encoding=encoding)

    duplparam = 'name' if byname else 'guid'

    for sparam in sparams:
        param_guid_lut[getattr(sparam, duplparam)].append(sparam)

    for spgroup in spgroups:
        group_guid_lut[getattr(spgroup, duplparam)].append(spgroup)

    duplgroups = [v for k, v in group_guid_lut.items() if len(v) > 1]
    duplparams = [v for k, v in param_guid_lut.items() if len(v) > 1]

    return SharedParamEntries(duplgroups, duplparams)


def find(src_file, searchstr, encoding=None):
    spgroups, sparams = read_entries(src_file, encoding=encoding)
    matchedgroups = [x for x in spgroups if searchstr in x]
    matchedparams = [x for x in sparams if searchstr in x]

    return SharedParamEntries(matchedgroups, matchedparams)


def compare(first_file, second_file, encoding=None):
    spgroups1, sparams1 = read_entries(first_file, encoding=encoding)
    spgroups2, sparams2 = read_entries(second_file, encoding=encoding)

    uniqgroups1 = [x for x in spgroups1 if x not in spgroups2]
    uniqparams1 = [x for x in sparams1 if x not in sparams2]
    uniqgroups2 = [x for x in spgroups2 if x not in spgroups1]
    uniqparams2 = [x for x in sparams2 if x not in sparams1]

    return SharedParamEntries(uniqgroups1, uniqparams1), \
        SharedParamEntries(uniqgroups2, uniqparams2)


def merge(source_files, out_file=None, encoding=None):
    merged_spgroups = set()
    merged_sparams = set()
    for sfile in source_files:
        spgroups, sparams = read_entries(sfile, encoding=encoding)
        merged_spgroups = merged_spgroups.union(spgroups)
        merged_sparams = merged_sparams.union(sparams)

    if out_file:
        write_entries(list(merged_spgroups) + list(merged_sparams),
                      out_file, encoding=encoding)
    else:
        return SharedParamEntries(list(merged_spgroups), list(merged_sparams))


def subtract(first_file, source_files, out_file=None, encoding=None):
    spgroups, sparams = read_entries(first_file, encoding=encoding)
    subtracted_spgroups = set(spgroups)
    subtracted_sparams = set(sparams)
    for sfile in source_files:
        spgroups, sparams = read_entries(sfile, encoding=encoding)
        subtracted_spgroups = subtracted_spgroups.difference(spgroups)
        subtracted_sparams = subtracted_sparams.difference(sparams)

    if out_file:
        write_entries(list(subtracted_spgroups) + list(subtracted_sparams),
                      out_file, encoding=encoding)
    else:
        return SharedParamEntries(subtracted_spgroups, subtracted_sparams)
