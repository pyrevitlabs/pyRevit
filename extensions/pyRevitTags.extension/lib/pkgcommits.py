class CommitTargets(object):
    Package = 'pkg'
    Revision = 'rev'


class CommitTypes(object):
    NotSet = 'notset'
    Created = 'created'
    Issued = 'issued'
    Reissued = 'refissued'
    Updated = 'updated'
    Revised = 'revised'
    Merged = 'merged'
    Deleted = 'deleted'


class CommitPoint(object):
    def __init__(self, cptype, target, idx, name):
        self.cptype = cptype
        self.target = target
        self.idx = idx
        self.name = name

    def __hash__(self):
        return hash(self.idx)

    def __eq__(self, other):
        if isinstance(other, CommitPoint):
            return self.idx == other.idx
        return False

    def __repr__(self):
        return '<{} cptype={} idx={} name={}>'.format(
            self.__class__.__name__,
            self.cptype,
            self.idx,
            self.name)


class Commit(CommitPoint):
    def __init__(self, cptype, target, idx, name, ctype=CommitTypes.NotSet):
        super(Commit, self).__init__(cptype, target, idx, name)
        self.ctype = ctype

    def __hash__(self):
        return hash(str(self.idx) + self.ctype)

    def __eq__(self, other):
        if isinstance(other, Commit):
            return self.idx == other.idx and self.ctype == other.ctype
        return False

    def __repr__(self):
        return '<{} cptype={} idx={} name={} ctype={}>'.format(
            self.__class__.__name__,
            self.cptype,
            self.idx,
            self.name,
            self.ctype
            )

    def is_at(self, commit_point):
        if isinstance(commit_point, CommitPoint):
            return self.idx == commit_point.idx
        return False

    @staticmethod
    def from_point(commit_pt, ctype=CommitTypes.NotSet):
        return Commit(cptype=commit_pt.cptype,
                      target=commit_pt.target,
                      idx=commit_pt.idx,
                      name=commit_pt.name,
                      ctype=ctype)


class CommitHistory(object):
    def __init__(self):
        self._chistory = []

    def __iter__(self):
        return iter(self._chistory)

    def __repr__(self):
        return repr(self._chistory)

    def get_prev(self, commit):
        try:
            idx = self._chistory.index(commit)
            prev_idx = idx - 1
            if prev_idx >= 0:
                return self._chistory[prev_idx]
        except ValueError:
            pass

    def get_next(self, commit):
        try:
            idx = self._chistory.index(commit)
            next_idx = idx + 1
            if next_idx < len(self._chistory):
                return self._chistory[next_idx]
        except ValueError:
            pass

    def commit_at_point(self, commit_point, commit_type):
        new_commit = Commit.from_point(commit_point, ctype=commit_type)
        prev_cmt_pts = [x for x in self._chistory if x.idx < commit_point.idx]
        next_cmt_pts = [x for x in self._chistory if x.idx > commit_point.idx]
        if prev_cmt_pts:
            prev_cmt_pt = sorted(prev_cmt_pts)[-1]        
            prev_index = self._chistory.index(prev_cmt_pt)
            self._chistory.insert(prev_index+1, new_commit)
        elif next_cmt_pts:
            next_cmt_pt = sorted(next_cmt_pts)[0]
            next_index = self._chistory.index(next_cmt_pt)
            self._chistory.insert(next_index, new_commit)
        else:
            self._chistory.insert(0, new_commit)
