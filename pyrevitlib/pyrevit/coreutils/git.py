"""
Description:
LibGit2Sharp wrapper module for pyRevit.

Documentation:
https://github.com/libgit2/libgit2sharp/wiki
"""

import clr
import importlib
import os.path as op

from pyrevit import HOST_APP, PyRevitException
from pyrevit.coreutils.logger import get_logger

# noinspection PyUnresolvedReferences
import System
# noinspection PyUnresolvedReferences
from System import DateTime, DateTimeOffset


GIT_LIB = 'LibGit2Sharp'

# todo: figure out how to import extensions on the caller's scope.
clr.AddReference("System.Core")
clr.ImportExtensions(System.Linq)
clr.AddReferenceByName(GIT_LIB)


logger = get_logger(__name__)


# public libgit module
libgit = importlib.import_module(GIT_LIB)


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
        self.username = self.password = None

    def __repr__(self):
        return '<type \'RepoInfo\' head \'{}\' @ {}>'.format(self.last_commit_hash, self.directory)


def _credentials_hndlr(username, password):
    up = libgit.UsernamePasswordCredentials()
    up.Username = username
    up.Password = password
    return up


def _get_credentials_hndlr(username, password):
    return libgit.Handlers.CredentialsHandler(lambda url, uname, types: _credentials_hndlr(username, password))


def _make_pull_options(repo_info):
    logger.debug('Making pull options: {}'.format(repo_info))
    pull_ops = libgit.PullOptions()
    pull_ops.FetchOptions = libgit.FetchOptions()
    if repo_info.username and repo_info.password:
        logger.debug('Making Credentials handler. (Username and password are available but cant\' log private info.)')
        pull_ops.FetchOptions.CredentialsProvider = _get_credentials_hndlr(repo_info.username, repo_info.password)
    return pull_ops


def _make_fetch_options(repo_info):
    logger.debug('Making fetch options: {}'.format(repo_info))
    fetch_ops = libgit.FetchOptions()
    if repo_info.username and repo_info.password:
        logger.debug('Making Credentials handler. (Username and password are available but cant\' log private info.)')
        fetch_ops.CredentialsProvider = _get_credentials_hndlr(repo_info.username, repo_info.password)
    return fetch_ops


def _make_clone_options(username=None, password=None):
    logger.debug('Making clone options.')
    clone_ops = libgit.CloneOptions()
    if username and password:
        logger.debug('Making Credentials handler. (Username and password are available but cant\' log private info.)')
        clone_ops.CredentialsProvider = _get_credentials_hndlr(username, password)
    return clone_ops


def _make_pull_signature():
    logger.debug('Creating pull signature for username: {}'.format(HOST_APP.username))
    return libgit.Signature(HOST_APP.username, HOST_APP.username, DateTimeOffset(DateTime.Now))


def _process_git_error(exception_err):
    exception_msg = str(exception_err)
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
        repo.Network.Pull(_make_pull_signature(), _make_pull_options(repo_info))
        logger.debug('Successfully pulled repo: {}'.format(repo_info.directory))
        head_msg = str(repo.Head.Tip.Message).replace('\n', '')
        logger.debug('New head is: {} > {}'.format(repo.Head.Tip.Id.Sha, head_msg))
        return RepoInfo(repo)

    except Exception as pull_err:
        logger.debug('Failed git pull: {} | {}'.format(repo_info.directory, pull_err))
        _process_git_error(pull_err)


def git_fetch(repo_info):
    repo = repo_info.repo
    try:
        repo.Network.Pull(_make_pull_signature(), _make_pull_options(repo_info))
        logger.debug('Successfully pulled repo: {}'.format(repo_info.directory))
        head_msg = str(repo.Head.Tip.Message).replace('\n', '')
        logger.debug('New head is: {} > {}'.format(repo.Head.Tip.Id.Sha, head_msg))
        return RepoInfo(repo)

    except Exception as fetch_err:
        logger.debug('Failed git fetch: {} | {}'.format(repo_info.directory, fetch_err))
        _process_git_error(fetch_err)


def git_clone(repo_url, clone_dir, username=None, password=None):
    try:
        libgit.Repository.Clone(repo_url, clone_dir, _make_clone_options(username=username,
                                                                         password=password))
        logger.debug('Completed git clone: {} @ {}'.format(repo_url, clone_dir))
    except Exception as clone_err:
        logger.debug('Error cloning repo: {} to {} | {}'.format(repo_url, clone_dir, clone_err))
        _process_git_error(clone_err)


def compare_branch_heads(repo_info):
    repo = repo_info.repo
    repo_branches = repo.Branches

    logger.debug('Repo branches: {}'.format([b for b in repo_branches]))

    for branch in repo_branches:
        if not branch.IsRemote:
            try:
                if branch.TrackedBranch:
                    logger.debug('Comparing heads: {} of {}'.format(branch.CanonicalName,
                                                                    branch.TrackedBranch.CanonicalName))
                    hist_div = repo.ObjectDatabase.CalculateHistoryDivergence(branch.Tip, branch.TrackedBranch.Tip)
                    return hist_div
            except Exception as compare_err:
                logger.error('Can not compare branch {} in repo: {} | {}'.format(branch,
                                                                                 repo,
                                                                                 str(compare_err).replace('\n', '')))
