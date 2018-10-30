from pkgcommits import CommitTypes


class CommitConfigs(object):
    def __init__(self):
        self._value_dict = {CommitTypes.Created: 'c',
                            CommitTypes.Issued: 'i',
                            CommitTypes.Reissued: 'ri',
                            CommitTypes.Updated: 'u',
                            CommitTypes.Revised: 'r',
                            CommitTypes.Merged: 'm',
                            CommitTypes.Deleted: 'd'}

    def get_commit_type(self, value):
        for ctype, cfg_value in self._value_dict.items():
            if cfg_value == value:
                return ctype
