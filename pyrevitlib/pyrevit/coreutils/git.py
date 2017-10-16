"""
Description:
LibGit2Sharp wrapper module for pyRevit.

Documentation:
https://github.com/libgit2/libgit2sharp/wiki
"""

import importlib
import os.path as op

from pyrevit import HOST_APP, PyRevitException, EXEC_PARAMS
from pyrevit.framework import clr
from pyrevit.framework import DateTime, DateTimeOffset
from pyrevit.coreutils.logger import get_logger
from pyrevit.loader.addin import get_addin_dll_file


logger = get_logger(__name__)


GIT_LIB = 'LibGit2Sharp'
libgit_dll = get_addin_dll_file(GIT_LIB)
logger.debug('Loading dll: {}'.format(libgit_dll))


if not EXEC_PARAMS.doc_mode:
    try:
        clr.AddReferenceToFileAndPath(libgit_dll)
        # public libgit module
        libgit = importlib.import_module(GIT_LIB)
    except Exception as load_err:
        logger.error('Can not load {} module. '
                     'This module is necessary for getting pyRevit version '
                     'and staying updated. | {}'.format(GIT_LIB, load_err))


class PyRevitGitAuthenticationError(PyRevitException):
    pass


class RepoInfo:
    """
    Generic repo wrapper for passing repository information to other modules

    """
    def __init__(self, repo):
        self.directory = repo.Info.WorkingDirectory
        self.name = op.basename(op.normpath(self.directory))
        self.head_name = repo.Head.Name
        self.last_commit_hash = repo.Head.Tip.Id.Sha
        self.repo = repo
        self.branch = repo.Head.Name
        self.username = self.password = None

    def __repr__(self):
        return '<type \'RepoInfo\' head \'{}\' @ {}>'\
            .format(self.last_commit_hash, self.directory)


def _credentials_hndlr(username, password):
    up = libgit.UsernamePasswordCredentials()
    up.Username = username
    up.Password = password
    return up


def _get_credentials_hndlr(username, password):
    return libgit.Handlers. \
           CredentialsHandler(lambda url, uname, types:
                              _credentials_hndlr(username, password))


def _make_pull_options(repo_info):
    logger.debug('Making pull options: {}'.format(repo_info))
    pull_ops = libgit.PullOptions()
    pull_ops.FetchOptions = libgit.FetchOptions()
    if repo_info.username and repo_info.password:
        logger.debug('Making Credentials handler. '
                     '(Username and password are available but'
                     'will not be logged for privacy purposes.)')

        pull_ops.FetchOptions.CredentialsProvider = \
            _get_credentials_hndlr(repo_info.username, repo_info.password)

    return pull_ops


def _make_fetch_options(repo_info):
    logger.debug('Making fetch options: {}'.format(repo_info))
    fetch_ops = libgit.FetchOptions()
    if repo_info.username and repo_info.password:
        logger.debug('Making Credentials handler. '
                     '(Username and password are available but'
                     'will not be logged for privacy purposes.)')

        fetch_ops.CredentialsProvider = \
            _get_credentials_hndlr(repo_info.username, repo_info.password)

    return fetch_ops


def _make_clone_options(username=None, password=None):
    logger.debug('Making clone options.')
    clone_ops = libgit.CloneOptions()
    if username and password:
        logger.debug('Making Credentials handler. '
                     '(Username and password are available but'
                     'will not be logged for privacy purposes.)')

        clone_ops.CredentialsProvider = \
            _get_credentials_hndlr(username, password)

    return clone_ops


def _make_pull_signature():
    logger.debug('Creating pull signature for username: {}'
                 .format(HOST_APP.username))
    return libgit.Signature(HOST_APP.username,
                            HOST_APP.username,
                            DateTimeOffset(DateTime.Now))


def _process_git_error(exception_err):
    exception_msg = unicode(exception_err)
    if '401' in exception_msg:
        raise PyRevitGitAuthenticationError(exception_msg)
    else:
        raise PyRevitException(exception_msg)


def get_repo(repo_dir):
    """

    Args:
        repo_dir:

    Returns:
        RepoInfo:
    """
    repo = libgit.Repository(repo_dir)
    return RepoInfo(repo)


def git_pull(repo_info):
    repo = repo_info.repo
    try:
        repo.Network.Pull(_make_pull_signature(),
                          _make_pull_options(repo_info))

        logger.debug('Successfully pulled repo: {}'.format(repo_info.directory))
        head_msg = unicode(repo.Head.Tip.Message).replace('\n', '')

        logger.debug('New head is: {} > {}'.format(repo.Head.Tip.Id.Sha,
                                                   head_msg))
        return RepoInfo(repo)

    except Exception as pull_err:
        logger.debug('Failed git pull: {} '
                     '| {}'.format(repo_info.directory, pull_err))
        _process_git_error(pull_err)


def git_fetch(repo_info):
    repo = repo_info.repo
    try:
        repo.Network.Fetch(repo.Head.TrackedBranch.Remote,
                           _make_fetch_options(repo_info))

        logger.debug('Successfully pulled repo: {}'.format(repo_info.directory))
        head_msg = unicode(repo.Head.Tip.Message).replace('\n', '')

        logger.debug('New head is: {} > {}'.format(repo.Head.Tip.Id.Sha,
                                                   head_msg))
        return RepoInfo(repo)

    except Exception as fetch_err:
        logger.debug('Failed git fetch: {} '
                     '| {}'.format(repo_info.directory, fetch_err))
        _process_git_error(fetch_err)


def git_clone(repo_url, clone_dir, username=None, password=None):
    try:
        libgit.Repository.Clone(repo_url,
                                clone_dir,
                                _make_clone_options(username=username,
                                                    password=password))

        logger.debug('Completed git clone: {} @ {}'.format(repo_url, clone_dir))

    except Exception as clone_err:
        logger.debug('Error cloning repo: {} to {} '
                     '| {}'.format(repo_url, clone_dir, clone_err))
        _process_git_error(clone_err)


def compare_branch_heads(repo_info):
    repo = repo_info.repo
    repo_branches = repo.Branches

    logger.debug('Repo branches: {}'.format([b for b in repo_branches]))

    for branch in repo_branches:
        if not branch.IsRemote:
            try:
                if branch.TrackedBranch:
                    logger.debug('Comparing heads: {} of {}'
                                 .format(branch.CanonicalName,
                                         branch.TrackedBranch.CanonicalName))

                    hist_div = repo.ObjectDatabase. \
                        CalculateHistoryDivergence(branch.Tip,
                                                   branch.TrackedBranch.Tip)
                    return hist_div
            except Exception as compare_err:
                logger.error('Can not compare branch {} in repo: {} | {}'
                             .format(branch, repo,
                                     unicode(compare_err).replace('\n', '')))


def get_all_new_commits(repo_info):
    from collections import OrderedDict

    repo = repo_info.repo
    current_commit = repo_info.last_commit_hash

    ref_commit = repo.Lookup(libgit.ObjectId(current_commit),
                             libgit.ObjectType.Commit)

    # Let's only consider the refs that lead to this commit...
    refs = repo.Refs.ReachableFrom([ref_commit])

    # ...and create a filter that will retrieve all the commits...
    commit_filter = libgit.CommitFilter()
    commit_filter.Since = refs
    commit_filter.Until = ref_commit
    commit_filter.SortBy = libgit.CommitSortStrategies.Time

    commits = repo.Commits.QueryBy(commit_filter)
    commitsdict = OrderedDict()
    for c in commits:
        if c in repo.Head.Commits or c in repo.Head.TrackedBranch.Commits:
            commitsdict[c.Id.ToString()] = c.MessageShort

    return commitsdict
