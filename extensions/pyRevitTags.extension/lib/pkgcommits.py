"""Manage commit history."""
#pylint: disable=E0401,W0401,W0614
import copy

from pyrevit.coreutils import logger

from pkgexceptions import *


mlogger = logger.get_logger(__name__)


class CommitType(object):
    def __init__(self, order, idx, name,
                 starts_history=False, ends_history=False,
                 requires_after=None, requires_before=None,
                 recurring=False):
        self.order = order
        self.idx = idx
        self.name = name
        self.starts_history = starts_history
        self.ends_history = ends_history
        self.requires_after = requires_after
        self.requires_before = requires_before
        self.recurring = recurring

    def __str__(self):
        return self.idx

    def __repr__(self):
        return '<{} idx={} name={}>'.format(self.__class__.__name__,
                                            self.idx,
                                            self.name)

    def __hash__(self):
        return hash(self.idx)

    def __eq__(self, other):
        if isinstance(other, CommitType):
            return self.idx == other.idx
        return False


class CommitTypes(object):
    NotSet = CommitType(order=0, idx='notset', name='Not Set')

    # commits that start history
    Created = CommitType(
        order=1,
        idx='created',
        name='Created',
        starts_history=True,
        requires_after=CommitType(order=3, idx='issued', name='Issued'))

    IssuedRe = CommitType(
        order=2,
        idx='issuedref',
        name='Issued for Reference',
        starts_history=True,
        recurring=True)

    # inbetween commits
    Issued = CommitType(order=3, idx='issued', name='Issued')
    Updated = CommitType(order=4, idx='updated', name='Updated')
    Revised = CommitType(order=5, idx='revised', name='Revised')

     # commits that end history
    Merged = CommitType(
        order=6,
        idx='merged',
        name='Merged',
        ends_history=True)

    Deleted = CommitType(
        order=7,
        idx='deleted',
        name='Deleted',
        ends_history=True)

    @staticmethod
    def get_types():
        return [getattr(CommitTypes, x) for x in dir(CommitTypes)
                if isinstance(getattr(CommitTypes, x), CommitType)]


class CommitPointType(object):
    def __init__(self, idx, name,
                 requires_history_start=False,
                 allowed_history_start_commit_types=None,
                 allowed_history_end_commit_types=None,
                 default_commit_type=None,
                 allowed_commit_types=None):
        self.idx = idx
        self.name = name
        self.requires_history_start = requires_history_start
        if self.requires_history_start:
            self.allowed_history_start_commit_types = \
                allowed_history_start_commit_types
            self.allowed_history_end_commit_types = \
                allowed_history_end_commit_types
        self.default_commit_type = default_commit_type
        self.allowed_commit_types = {CommitTypes.NotSet}
        self.allowed_commit_types.update(
            allowed_commit_types or CommitTypes.get_types()
            )

    def __str__(self):
        return self.idx

    def __repr__(self):
        return '<{} idx={} name={}>'.format(self.__class__.__name__,
                                            self.idx,
                                            self.name)

    def __hash__(self):
        return hash(self.idx)

    def __eq__(self, other):
        if isinstance(other, CommitPointType):
            return self.idx == other.idx
        return False


class CommitPointTypes(object):
    Package = CommitPointType(
        idx='pkg',
        name='Package',
        requires_history_start=True,
        allowed_history_start_commit_types=[CommitTypes.Created,
                                            CommitTypes.IssuedRe],
        allowed_history_end_commit_types=[CommitTypes.Deleted,
                                          CommitTypes.Merged]
        )

    Revision = CommitPointType(
        idx='rev',
        name='Revision',
        default_commit_type=CommitTypes.Revised,
        allowed_commit_types=[CommitTypes.Revised]
        )

    @staticmethod
    def get_targets():
        return [getattr(CommitPointTypes, x) for x in dir(CommitPointTypes)
                if isinstance(getattr(CommitPointTypes, x), CommitPointType)]


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
        self.read_only = False

    def __hash__(self):
        return hash(str(self.idx) + self.ctype)

    def __eq__(self, other):
        if isinstance(other, Commit):
            return self.idx == other.idx and self.ctype == other.ctype
        return super(Commit, self).__eq__(other)

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
    def __init__(self, commit_points):
        self._commits = []
        self._cpoints = commit_points

    def __iter__(self):
        return iter(self._commits)

    def __len__(self):
        return len(self._commits)

    def __repr__(self):
        return repr(self._commits)

    def _find_starting_commit(self):
        starting_commits = \
            [x for x in self._commits if x.ctype.starts_history]
        return starting_commits[0] if starting_commits else None

    def _find_ending_commit(self):
        ending_commits = \
            [x for x in self._commits if x.ctype.ends_history]
        return ending_commits[-1] if ending_commits else None

    def _refresh_commits(self):
        next_commit_type = None
        starting_commit = self._find_starting_commit()
        ending_commit = self._find_ending_commit()

        if starting_commit:
            if starting_commit.ctype.requires_after:
                next_commit_type = starting_commit.ctype.requires_after
            elif starting_commit.ctype.recurring:
                next_commit_type = starting_commit.ctype

            if next_commit_type:
                ending_index = len(self._cpoints)
                if ending_commit:
                    ending_index = ending_commit.idx

                for commit_pt in \
                        self._cpoints[starting_commit.idx:ending_index]:
                    if commit_pt.cptype.requires_history_start:
                        if not self.get_commit_at_point(commit_pt):
                            self.commit_at_point(
                                commit_point=commit_pt,
                                commit_type=next_commit_type
                                )

    def _reposition_start(self, index, commit):
        # delete any 'created' commit after
        created_after_cmts = [x for x in self._commits[index:]
                              if x.ctype.starts_history]
        if created_after_cmts:
            for created_commit in created_after_cmts:
                if created_commit.read_only:
                    raise ReadOnlyStart()
                self._commits.remove(created_commit)

        # insert the new create
        self._commits.insert(index, commit)

        # delete all commits before
        for prev_commit in self._commits[:index]:
            if not prev_commit.read_only:
                self._commits.remove(prev_commit)

    def _reposition_end(self, index, commit):
        # delete all commits after
        for after_commit in self._commits[index:]:
            if after_commit.read_only:
                raise ReadOnlyCommitInHistory()
            self._commits.remove(after_commit)

        # insert the new delete
        self._commits.insert(index, commit)

        # delete any 'deleted' commit before
        deleted_before_cmts = [x for x in self._commits[:index]
                               if x.ctype.ends_history]
        if deleted_before_cmts:
            for deleted_commit in deleted_before_cmts:
                if deleted_commit.read_only:
                    raise ReadOnlyEnd()
                self._commits.remove(deleted_commit)

    def _can_insert_commit(self, insert_idx, commit):
        ctype = commit.ctype

        commits_before = self._commits[:insert_idx]
        if commits_before:
            hist_started = any([x.ctype.starts_history for x in commits_before])
            hist_recurring = any([x.ctype.starts_history
                                  and x.ctype.recurring
                                  for x in commits_before])
            hist_ended = any([x.ctype.ends_history for x in commits_before])

            if ctype.starts_history and ctype.recurring and hist_recurring:
                return True

            if ctype.starts_history and ctype.recurring and hist_started:
                raise HistoryStartedBefore()

            if ctype.starts_history and (hist_started or hist_recurring):
                raise HistoryStartedBefore()

            if ctype.ends_history and hist_ended:
                raise HistoryEndedBefore()

        commits_after = self._commits[insert_idx:]
        if commits_after:
            hist_started = any([x.ctype.starts_history for x in commits_after])
            hist_recurring = any([x.ctype.starts_history
                                  and x.ctype.recurring
                                  for x in commits_after])
            hist_ended = any([x.ctype.ends_history for x in commits_after])

            if ctype.starts_history and ctype.recurring and hist_recurring:
                return True

            if ctype.starts_history and ctype.recurring and hist_started:
                raise HistoryStartedAfter()

            if ctype.starts_history and (hist_started or hist_recurring):
                raise HistoryStartedAfter()

            if ctype.ends_history and hist_ended:
                raise HistoryEndedAfter()

        # if not prev or next, this is the first commit inserted in history



        # if commit point type does not require a create commit
        # allow the commit
        if not commit.cptype.requires_history_start:
            return True

        # is this commit before the history starts?
        commits_after = self._commits[insert_idx:]
        if any([x.ctype.starts_history for x in commits_after]):
            raise HistoryStartedAfter()

        # is this a recurring commit?
        if commit.ctype.recurring and insert_idx > 0:
            return True

        # is this commit after the history starts?
        if commit.ctype.starts_history and insert_idx > 0:
            raise HistoryStartedBefore()

        last_idx = len(self._commits)
        if commit.ctype.ends_history and insert_idx < last_idx:
            raise HistoryEndedAfter()

        start_commit_types = \
            commit.cptype.allowed_history_start_commit_types
        if commit.ctype not in start_commit_types and insert_idx == 0:
            raise HistoryStartMustBeFirst()

        return True

    def _insert_commit(self, insert_idx, commit,
                       allow_endpoint_change=False):
        try:
            if self._can_insert_commit(insert_idx, commit):
                self._commits.insert(insert_idx, commit)
                self._refresh_commits()
        except (HistoryStartMustBeFirst, HistoryStartedBefore, HistoryStartedAfter) \
                as start_commit_err:
            if allow_endpoint_change and commit.ctype.starts_history:
                self._reposition_start(insert_idx, commit)
                self._refresh_commits()
            else:
                raise start_commit_err
        except (HistoryEndMustBeLast, HistoryEndedAfter, HistoryEndedBefore) \
                as end_commit_err:
            if allow_endpoint_change and commit.ctype.ends_history:
                self._reposition_end(insert_idx, commit)
                self._refresh_commits()
            else:
                raise end_commit_err
        except Exception as commit_err:
            raise commit_err

        return commit

    def _can_delete_commit(self, commit):
        if commit.ctype.starts_history:
            raise CanNotRemoveStart()

        return True

    def _delete_commit(self, existing_commit, replacement=None,
                       allow_endpoint_change=False):
        commit_index = self._commits.index(existing_commit)
        backup_commits = copy.copy(self._commits)
        try:
            if self._can_delete_commit(existing_commit):
                self._commits.remove(existing_commit)
                if replacement:
                    return self._insert_commit(
                        commit_index,
                        replacement,
                        allow_endpoint_change=allow_endpoint_change
                        )
                self._refresh_commits()
        except Exception as delete_err:
            self._commits = backup_commits
            raise delete_err

    def _replace_commit(self, existing_commit, new_commit,
                        allow_endpoint_change=False):
        self._delete_commit(existing_commit,
                            replacement=new_commit,
                            allow_endpoint_change=allow_endpoint_change)

    @property
    def commit_points(self):
        return self._cpoints

    def get_prev(self, commit):
        try:
            idx = self._commits.index(commit)
            prev_idx = idx - 1
            if prev_idx >= 0:
                return self._commits[prev_idx]
        except ValueError:
            pass

    def get_next(self, commit):
        try:
            idx = self._commits.index(commit)
            next_idx = idx + 1
            if next_idx < len(self._commits):
                return self._commits[next_idx]
        except ValueError:
            pass

    def get_commit_at_prev_point(self, commit_point):
        prev_commits = [x for x in self._commits if x.idx < commit_point.idx]
        if prev_commits:
            return sorted(prev_commits)[-1]

    def get_commit_at_next_point(self, commit_point):
        next_commits = [x for x in self._commits if x.idx > commit_point.idx]
        if next_commits:
            return sorted(next_commits)[0]

    def get_commit_at_point(self, commit_point):
        for commit in self._commits:
            if commit.is_at(commit_point):
                return commit

    def commit_at_point(self,
                        commit_point, commit_type,
                        allow_endpoint_change=False):
        # no commit?
        none_commit = \
            commit_type == CommitTypes.NotSet \
            or commit_type is None

        # make a commit object
        new_commit = Commit.from_point(commit_point, ctype=commit_type)
        mlogger.debug('Attempting to commit %s', new_commit)

        # check if there is a commit at this commit point
        matched_commit = self.get_commit_at_point(commit_point)
        if matched_commit:
            mlogger.debug('Commit %s exists at point %s',
                          matched_commit, commit_point)

            # unset, means delete the existing commit
            if none_commit:
                return self._delete_commit(matched_commit)
            # otherwise replace the existing with new commit
            else:
                return self._replace_commit(
                    matched_commit,
                    new_commit,
                    allow_endpoint_change=allow_endpoint_change
                    )
        else:
            # it does not make sense to insert a notset commit
            if none_commit:
                raise CanNotUnsetNonExisting()

        insert_idx = 0
        # otherwise find previous commit point and insert after
        prev_commit = self.get_commit_at_prev_point(commit_point)
        if prev_commit:
            mlogger.debug('Previous commit %s exists before point %s',
                          prev_commit, commit_point)
            insert_idx = self._commits.index(prev_commit) + 1

        # if nothing prev, check next and insert before
        next_commit = self.get_commit_at_next_point(commit_point)
        if next_commit:
            mlogger.debug('Next commit %s exists after point %s',
                          next_commit, commit_point)
            insert_idx = self._commits.index(next_commit)

        # if no prev or next, means the history is empty so just insert
        return self._insert_commit(
            insert_idx,
            new_commit,
            allow_endpoint_change=allow_endpoint_change
            )
