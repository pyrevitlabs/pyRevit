# -*- coding: utf-8 -*-
"""Manage package configurations."""
from collections import OrderedDict

from pkgcommits import CommitTypes


class CommitConfigs(object):
    # _singleton = None

    # def __new__(cls):
    #     if not CommitConfigs._singleton:
    #         CommitConfigs._singleton = cls()
    #     return CommitConfigs._singleton

    def __init__(self):
        commit_types = OrderedDict()
        commit_types[CommitTypes.Created] = '■'
        commit_types[CommitTypes.Issued] = '◊'
        commit_types[CommitTypes.IssuedRe] = '□'
        commit_types[CommitTypes.Updated] = '●'
        commit_types[CommitTypes.Revised] = '●'
        commit_types[CommitTypes.Merged] = '∩'
        commit_types[CommitTypes.Deleted] = 'X'

        self._value_dict = commit_types

    def get_commit_type(self, value):
        for ctype, cfg_value in self._value_dict.items():
            if cfg_value == value:
                return ctype

    def get_commit_value(self, commit_type):
        return self._value_dict.get(commit_type, '')