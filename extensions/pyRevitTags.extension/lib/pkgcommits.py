"""Manage commit history."""
#pylint: disable=E0401,W0401,W0614,W0703,C0103,C0111
from pyrevit.coreutils import logger

from pkgexceptions import *


mlogger = logger.get_logger(__name__)


class CommitType(object):
    def __init__(self, order, idx, name,
                 starts_history=False, ends_history=False,
                 requires_after=None, requires_before=None,
                 recurring=False, allows_override=True):
        self.order = order
        self.idx = idx
        self.name = name
        self.starts_history = starts_history
        self.ends_history = ends_history
        self.requires_after = requires_after
        self.requires_before = requires_before
        self.recurring = recurring
        self.allows_override = allows_override

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
        recurring=True,
        allows_override=False)

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

    def __repr__(self):
        return '<{} cptype={} idx={} name={}>'.format(
            self.__class__.__name__,
            self.cptype,
            self.idx,
            self.name)

    def __hash__(self):
        return hash(str(self.idx) + str(self.cptype))

    def __eq__(self, other):
        if isinstance(other, CommitPoint):
            return hash(self) == hash(other)
        return False

    def __lt__(self, other):
        return self.idx < other.idx

    def __le__(self, other):
        return self.idx <= other.idx

    def __gt__(self, other):
        return self.idx > other.idx

    def __ge__(self, other):
        return self.idx >= other.idx

    def is_before(self, commit_point):
        return self < commit_point

    def is_after(self, commit_point):
        return self > commit_point


class CommitSources(object):
    User = 'user'
    Recurring = 'recurring'
    Required = 'required'


class Commit(object):
    def __init__(self, commit_point,
                 commit_source=CommitSources.User,
                 commit_type=CommitTypes.NotSet):
        self.commit_point = commit_point
        self.commit_type = commit_type
        self.read_only = False
        self.commit_source = commit_source

    @classmethod
    def from_point(cls, commit_pt,
                   commit_source=CommitSources.User,
                   commit_type=CommitTypes.NotSet):
        return cls(commit_point=commit_pt,
                   commit_source=commit_source,
                   commit_type=commit_type)

    def __hash__(self):
        return hash(str(self.commit_point)
                    + str(self.commit_type)
                    + str(self.commit_source))

    def __eq__(self, other):
        if isinstance(other, Commit):
            return hash(self) == hash(other)
        return False

    def __repr__(self):
        return '<{} commit_point={} commit_type={} commit_source={}>'.format(
            self.__class__.__name__,
            self.commit_point,
            self.commit_type,
            self.commit_source
            )

    def is_at(self, commit_point):
        if isinstance(commit_point, CommitPoint):
            return self.commit_point == commit_point
        return False


class CommitHistory(object):
    def __init__(self, commit_points):
        self._cpoints = commit_points
        self._commits = []
        self._last_replaced = None

    def __iter__(self):
        return iter(self.commits)

    def __len__(self):
        return len(self.commits)

    def __repr__(self):
        history_graph = '-----'.join(
            ['[{}:{}]'.format(x.commit_point.idx, x.commit_type)
             for x in self.commits]
            )
        return '<{} graph={} commits={}>'.format(self.__class__.__name__,
                                                 history_graph,
                                                 self.commits)

    def _find_starting_commits(self):
        return \
            sorted([x for x in self.commits if x.commit_type.starts_history],
                   key=lambda x: x.commit_point.idx)

    def _find_ending_commits(self):
        return \
            sorted([x for x in self.commits if x.commit_type.ends_history],
                   key=lambda x: x.commit_point.idx)

    @property
    def commits(self):
        return sorted(self._commits, key=lambda x: x.commit_point.idx)

    @property
    def commit_points(self):
        return sorted(self._cpoints, key=lambda x: x.idx)

    @property
    def starting_commit(self):
        starting_commits = self._find_starting_commits()
        if starting_commits:
            starting_commit = starting_commits[0]
            mlogger.debug('Starting commit is: %s', starting_commit)
            return starting_commit

    @property
    def ending_commit(self):
        ending_commits = self._find_ending_commits()
        if ending_commits:
            ending_commit = ending_commits[-1]
            mlogger.debug('Ending commit is: %s', ending_commit)
            return ending_commit

    def _uncommit_from_history(self, commit):
        if commit.read_only:
            raise ReadOnlyCommitInHistory()
        self._commits.remove(commit)

    def _commit_to_history(self, commit):
        insert_index = 0

        mlogger.debug('Calculating insersion index...')
        existing_commit = self.get_commit_at(commit.commit_point)

        if existing_commit:
            insert_index = self._commits.index(existing_commit)
            self._last_replaced = self._commits.pop(insert_index)
        else:
            prev_commit = self.get_commit_before(commit.commit_point)
            if prev_commit:
                insert_index = self._commits.index(prev_commit) + 1
            else:
                next_commit = self.get_commit_after(commit.commit_point)
                if next_commit:
                    insert_index = self._commits.index(next_commit)

        mlogger.debug('Inserting %s at index %s', commit, insert_index)
        self._commits.insert(insert_index, commit)

    def _clear_nonuser_commits(self):
        for commit in self.commits:
            if commit.commit_source != CommitSources.User:
                self._uncommit_from_history(commit)

    def _clear_commits_before_start(self):
        starting_commit = self.starting_commit
        if starting_commit:
            mlogger.debug('Cleaning commit before start %s', starting_commit)
            for commit in self.get_commits_before(starting_commit.commit_point):
                mlogger.debug('Removing %s', commit)
                self._uncommit_from_history(commit)

    def _clear_commits_after_end(self):
        ending_commit = self.ending_commit
        if ending_commit:
            mlogger.debug('Cleaning commit after end %s', ending_commit)
            for commit in self.get_commits_after(ending_commit.commit_point):
                mlogger.debug('Removing %s', commit)
                self._uncommit_from_history(commit)

    def _add_nonuser_commits(self):
        next_commit_type = None
        commit_source = None

        for commit_point in self.commit_points:
            commit = self.get_commit_at(commit_point)
            mlogger.debug('Processing %s for non-user commits.', commit)
            if commit:
                # check if this commit creates commits after
                # if yes set the required data and continue
                if commit.commit_type.requires_after:
                    next_commit_type = commit.commit_type.requires_after
                    commit_source = CommitSources.Required
                    mlogger.debug('Commit %s requires after: %s',
                                  commit, next_commit_type)
                    continue
                elif commit.commit_type.recurring:
                    next_commit_type = commit.commit_type
                    commit_source = CommitSources.Recurring
                    mlogger.debug('Commit %s is recurring.', commit)
                    continue

                # check if this is an ending commit
                # if yes, stop creating non-user commits
                if commit.commit_type.ends_history:
                    next_commit_type = None
                    commit_source = None
                    mlogger.debug('Ends creating non-user commits.', commit)

                # if existing commit matches the set non-user
                # then set the source to non-user
                if (next_commit_type and commit_source):
                    if commit.commit_type == next_commit_type:
                        commit.commit_source = commit_source

            # create the non-user commit if type data is set
            # and no existing commit is found
            if (next_commit_type and commit_source) \
                    and not commit \
                    and commit_point.cptype.requires_history_start:
                mlogger.debug('Applying non-user(%s) commit type: %s',
                              commit_source, next_commit_type)
                self._commit_to_history(
                    Commit.from_point(commit_point,
                                      commit_type=next_commit_type,
                                      commit_source=commit_source)
                    )

    def _update_history(self):
        self._clear_nonuser_commits()
        self._add_nonuser_commits()
        self._clear_commits_before_start()
        self._clear_commits_after_end()

    def _commit_new_start(self, commit):
        # remove all starting commits
        for starting_commit in self._find_starting_commits():
            self._uncommit_from_history(starting_commit)

        # insert the new create
        self._commit_to_history(commit)

        # delete all commits before
        for before_commit in self.get_commits_before(commit.commit_point):
            self._uncommit_from_history(before_commit)

    def _commit_new_end(self, commit):
        # remove all ending commits
        for ending_commit in self._find_ending_commits():
            self._uncommit_from_history(ending_commit)

        # insert the new create
        self._commit_to_history(commit)

        # delete all commits before
        for after_commit in self.get_commits_after(commit.commit_point):
            self._uncommit_from_history(after_commit)

    def _commit_and_update(self, commit, new_start=False, new_end=False):
        if new_start:
            self._commit_new_start(commit)

        if new_end:
            self._commit_new_end(commit)

        self._commit_to_history(commit)
        self._update_history()

    def _can_commit(self, commit):
        mlogger.debug('Test commit possibility: %s', commit)
        commit_type = commit.commit_type
        commit_point = commit.commit_point

        # process commits before
        commits_before = self.get_commits_before(commit_point)
        user_commits_before = [x for x in commits_before
                               if x.commit_source == CommitSources.User]
        mlogger.debug('User commits before: %s', user_commits_before)
        hist_ended_before = \
            any([x.commit_type.ends_history for x in user_commits_before])
        hist_started_before = \
            any([x.commit_type.starts_history for x in user_commits_before])

        mlogger.debug('History ended before: %s', hist_ended_before)
        mlogger.debug('History started before: %s', hist_started_before)

        if user_commits_before:
            # if starting history
            if commit_type.starts_history and hist_ended_before:
                mlogger.debug('Insert start and history has ended before. '
                              'raising HistoryEndedBefore')
                raise HistoryEndedBefore()

            if commit_type.starts_history and hist_started_before:
                mlogger.debug('Insert start and history has started or is '
                              'recurring before. raising HistoryStartedBefore')
                raise HistoryStartedBefore()

            # if ending history
            if commit_type.ends_history and hist_ended_before:
                mlogger.debug('Insert end and history has ended before. '
                              'raising HistoryEndedBefore')
                raise HistoryEndedBefore()

            # if ending history
            if commit_type.ends_history and hist_started_before:
                mlogger.debug('Insert end and history has started or is '
                              'recurring before. skipping...')

            if not (commit_type.starts_history or commit_type.ends_history) \
                    and hist_ended_before:
                mlogger.debug('Insert non-starting non-ending '
                              'and history has ended before. '
                              'raising HistoryEndedBefore')
                raise HistoryEndedBefore()

        commits_after = self.get_commits_after(commit_point)
        user_commits_after = [x for x in commits_after
                              if x.commit_source == CommitSources.User]
        mlogger.debug('User commits after: %s', user_commits_after)
        hist_started_after = \
            any([x.commit_type.starts_history for x in user_commits_after])
        hist_ended_after = \
            any([x.commit_type.ends_history for x in user_commits_after])

        mlogger.debug('History ended after: %s', hist_ended_after)
        mlogger.debug('History started after: %s', hist_started_after)

        if user_commits_after:
            # if starting history
            if commit_type.starts_history and hist_started_after:
                mlogger.debug('Insert start and history has started or '
                              'is recurring after. raising HistoryStartedAfter')
                raise HistoryStartedAfter()

            if not commit_type.starts_history and hist_started_after:
                mlogger.debug('Insert non-starting non-ending '
                              'and history has started after. '
                              'raising HistoryStartedAfter')
                raise HistoryStartedAfter()

            # if ending history
            if commit_type.ends_history and hist_ended_after:
                mlogger.debug('Insert end and history has ended after. '
                              'raising HistoryEndedAfter')
                raise HistoryEndedAfter()

        # if not prev or next, this is the first commit inserted in history
        # if commit point type does not require a create commit
        # allow the commit
        if not commit_point.cptype.requires_history_start:
            mlogger.debug('Insert into commit point type that '
                          'does not require a start. returning ok to insert')
            return True

        if commit_point.cptype.requires_history_start \
                and commit_type.ends_history \
                and hist_started_after:
            mlogger.debug('Insert as first ending into commit point '
                          'type that requires a start commit. '
                          'raising HistoryEndMustBeLast')
            raise HistoryEndMustBeLast()

        if commit_point.cptype.requires_history_start \
                and not commit_type.starts_history \
                and not (hist_started_before or hist_started_after):
            mlogger.debug('Insert as first non-starting into commit point '
                          'type that requires a start commit. '
                          'raising HistoryStartMustBeFirst')
            raise HistoryStartMustBeFirst()

        return True

    def _uncommit_and_update(self, commit):
        # remove any non_user
        self._uncommit_from_history(commit)
        self._update_history()

    def _can_delete(self, commit):
        # allow deleting recurrin commits
        if commit.commit_source != CommitSources.User:
            raise CanNotRemoveNonUser()

        if commit.commit_type.starts_history:
            raise CanNotRemoveStart()

        return True

    def get_commits_before(self, commit_point):
        mlogger.debug('Searching for commit before point %s', commit_point)
        prev_commits = \
            [x for x in self.commits if x.commit_point.is_before(commit_point)]
        mlogger.debug('Commits before %s', prev_commits)
        return prev_commits

    def get_commits_after(self, commit_point):
        mlogger.debug('Searching for commit after point %s', commit_point)
        next_commits = \
            [x for x in self.commits if x.commit_point.is_after(commit_point)]
        mlogger.debug('Commits after %s', next_commits)
        return next_commits

    def get_commit_before(self, commit_point):
        mlogger.debug('Searching for commit before point %s', commit_point)
        prev_commits = \
            [x for x in self.commits if x.commit_point.is_before(commit_point)]
        if prev_commits:
            prev_commit = \
                sorted(prev_commits, key=lambda x: x.commit_point.idx)[-1]
            mlogger.debug('Commit %s found at point %s',
                          prev_commit, commit_point)
            return prev_commit

    def get_commit_after(self, commit_point):
        mlogger.debug('Searching for commit after point %s', commit_point)
        next_commits = \
            [x for x in self.commits if x.commit_point.is_after(commit_point)]
        if next_commits:
            next_commit = \
                sorted(next_commits, key=lambda x: x.commit_point.idx)[0]
            mlogger.debug('Commit %s found at point %s',
                          next_commit, commit_point)
            return next_commit

    def get_commit_at(self, commit_point):
        mlogger.debug('Searching for commit at point %s', commit_point)
        for commit in self.commits:
            if commit.is_at(commit_point):
                mlogger.debug('Commit %s found at point %s',
                              commit, commit_point)
                return commit

    def get_prev_commit(self, commit):
        try:
            prev_idx = self.commits.index(commit) - 1
            mlogger.debug('Previous index: %s before %s', prev_idx, commit)
            if prev_idx >= 0:
                prev_commit = self.commits[prev_idx]
                mlogger.debug('Previous commit: %s', prev_commit)
                return prev_commit
        except ValueError:
            return None
        except Exception as ex:
            mlogger.error(ex)

    def get_next_commit(self, commit):
        try:
            next_idx = self.commits.index(commit) + 1
            mlogger.debug('Next index: %s after %s', next_idx, commit)
            if next_idx < len(self.commits):
                next_commit = self.commits[next_idx]
                mlogger.debug('Next commit: %s', next_commit)
                return next_commit
        except ValueError:
            return None
        except Exception as ex:
            mlogger.error(ex)

    def can_commit_at_point(self, commit_point, commit_type,
                            allow_endpoint_change=False):
        try:
            self.commit_at_point(commit_point,
                                 commit_type,
                                 allow_endpoint_change=allow_endpoint_change,
                                 dry_run=True)
            mlogger.debug('Can commit type %s: yes', commit_type)
            return True
        except Exception as ex:
            mlogger.debug('Can commit type %s: %s', commit_type, type(ex))
            return False

    def commit_at_point(self, commit_point, commit_type,
                        commit_source=CommitSources.User,
                        allow_endpoint_change=False,
                        dry_run=False):
        existing_commit = self.get_commit_at(commit_point)

        # does existing allow override?
        if existing_commit \
                and not existing_commit.commit_type.allows_override \
                and not commit_type.starts_history \
                and not commit_type.ends_history:
            raise DoesNotAllowOverride()
        # is the commit really needed?
        elif existing_commit \
                and existing_commit.commit_type == commit_type \
                and not commit_type.starts_history \
                and not commit_type.ends_history:
            return existing_commit
        # notset commit?
        elif commit_type == CommitTypes.NotSet:
            # if notset and existing delete commit
            if existing_commit:
                try:
                    if self._can_delete(existing_commit):
                        if not dry_run:
                            self._uncommit_and_update(existing_commit)
                except Exception as ex:
                    raise ex
            else:
                raise CanNotUnsetNonExisting()
        else:
            new_commit = Commit.from_point(commit_point,
                                           commit_source=commit_source,
                                           commit_type=commit_type)
            try:
                mlogger.debug('History before commit: %s', self.commits)
                mlogger.debug('Attempting commit %s', new_commit)
                if self._can_commit(new_commit):
                    if not dry_run:
                        self._commit_and_update(new_commit)
            except (HistoryStartMustBeFirst,
                    HistoryStartedBefore,
                    HistoryStartedAfter) as start_commit_err:
                if allow_endpoint_change and commit_type.starts_history:
                    if not dry_run:
                        self._commit_and_update(new_commit, new_start=True)
                else:
                    raise start_commit_err
            except (HistoryEndMustBeLast,
                    HistoryEndedAfter,
                    HistoryEndedBefore) as end_commit_err:
                if allow_endpoint_change and commit_type.ends_history:
                    if not dry_run:
                        self._commit_and_update(new_commit, new_end=True)
                else:
                    raise end_commit_err
            except Exception as commit_err:
                raise commit_err

            return new_commit
