"""Manage package configurations."""
from pkgcommits import CommitTypes


class CommitConfigs(object):
    # _singleton = None

    # def __new__(cls):
    #     if not CommitConfigs._singleton:
    #         CommitConfigs._singleton = cls()
    #     return CommitConfigs._singleton

    def __init__(self):
        self._value_dict = {CommitTypes.Created: 'c',
                            CommitTypes.Issued: 'i',
                            CommitTypes.IssuedRe: 'ri',
                            CommitTypes.Updated: 'u',
                            CommitTypes.Revised: 'r',
                            CommitTypes.Merged: 'm',
                            CommitTypes.Deleted: 'd'}

    def get_commit_type(self, value):
        for ctype, cfg_value in self._value_dict.items():
            if cfg_value == value:
                return ctype

    def get_commit_value(self, commit_type):
        return self._value_dict.get(commit_type, '')