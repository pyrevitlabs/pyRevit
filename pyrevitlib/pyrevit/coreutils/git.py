"""LibGit2Sharp wrapper module for pyRevit.

Documentation:
    https://github.com/libgit2/libgit2sharp/wiki
"""

import os.path as op
from collections import OrderedDict

from pyrevit import HOST_APP, PyRevitException
from pyrevit.compat import safe_strtype, IRONPY
from pyrevit import framework
from pyrevit.framework import clr
from pyrevit.framework import DateTime, DateTimeOffset
from pyrevit.coreutils.logger import get_logger

# pylint: disable=W0703,C0302
mlogger = get_logger(__name__)  # pylint: disable=C0103


GIT_LIB = "LibGit2Sharp"

LIBGIT_DLL = framework.get_dll_file(GIT_LIB)
mlogger.debug("Loading dll: %s", LIBGIT_DLL)

try:
    if IRONPY:
        clr.AddReferenceToFileAndPath(LIBGIT_DLL)
    else:
        clr.AddReference(LIBGIT_DLL)

    import LibGit2Sharp as libgit  # pylint: disable=import-error

except Exception as load_err:
    mlogger.error(
        "Can not load %s module. "
        "This module is necessary for getting pyRevit version "
        "and staying updated. | %s",
        GIT_LIB,
        load_err,
    )


class PyRevitGitAuthenticationError(PyRevitException):
    """Git authentication error."""

    pass


class RepoInfo(object):
    """Repo wrapper for passing around repository information.

    Attributes:
        directory (str): repo directory
        name (str): repo name
        head_name (str): head branch name
        last_commit_hash (str): hash of head commit
        repo (str): ``LibGit2Sharp.Repository`` object
        branch (str): current branch name
        username (str): credentials - username
        password (str): credentials - password
    """

    def __init__(self, repo):
        self.directory = repo.Info.WorkingDirectory
        self.name = op.basename(op.normpath(self.directory))
        self.head_name = repo.Head.FriendlyName
        self.last_commit_hash = repo.Head.Tip.Id.Sha
        self.repo = repo
        self.branch = repo.Head.FriendlyName
        self.username = self.password = None

    def __repr__(self):
        return "<type 'RepoInfo' head '{}' @ {}>".format(
            self.last_commit_hash, self.directory
        )


def _credentials_hndlr(username, password):
    userpass = libgit.UsernamePasswordCredentials()
    userpass.Username = username
    userpass.Password = password
    return userpass


def _get_credentials_hndlr(username, password):
    return libgit.Handlers.CredentialsHandler(
        lambda url, uname, types: _credentials_hndlr(username, password)
    )


def _make_pull_options(repo_info):
    mlogger.debug("Making pull options: %s", repo_info)
    pull_ops = libgit.PullOptions()
    pull_ops.FetchOptions = libgit.FetchOptions()
    if repo_info.username and repo_info.password:
        mlogger.debug(
            "Making Credentials handler. "
            "(Username and password are available but"
            "will not be logged for privacy purposes.)"
        )

        pull_ops.FetchOptions.CredentialsProvider = _get_credentials_hndlr(
            repo_info.username, repo_info.password
        )

    return pull_ops


def _make_fetch_options(repo_info):
    mlogger.debug("Making fetch options: %s", repo_info)
    fetch_ops = libgit.FetchOptions()
    if repo_info.username and repo_info.password:
        mlogger.debug(
            "Making Credentials handler. "
            "(Username and password are available but"
            "will not be logged for privacy purposes.)"
        )

        fetch_ops.CredentialsProvider = _get_credentials_hndlr(
            repo_info.username, repo_info.password
        )

    return fetch_ops


def _make_clone_options(username=None, password=None):
    mlogger.debug("Making clone options.")
    clone_ops = libgit.CloneOptions()

    if username and password:
        mlogger.debug("Making Credentials handler.")
        creds_handler = _get_credentials_hndlr(username, password)

        # Only set the CredentialsProvider if it's a valid property
        if hasattr(clone_ops, "CredentialsProvider"):
            clone_ops.CredentialsProvider = creds_handler
        elif hasattr(clone_ops, "FetchOptions") and hasattr(
            clone_ops.FetchOptions, "CredentialsProvider"
        ):
            clone_ops.FetchOptions.CredentialsProvider = creds_handler
        else:
            mlogger.warning(
                "CloneOptions does not support CredentialsProvider. "
                "Skipping credentials."
            )

    return clone_ops


def _make_pull_signature():
    mlogger.debug("Creating pull signature for username: %s",
                  HOST_APP.username)
    return libgit.Signature(
        HOST_APP.username, HOST_APP.username, DateTimeOffset(DateTime.Now)
    )


def _process_git_error(exception_err):
    exception_msg = safe_strtype(exception_err)
    if "401" in exception_msg:
        raise PyRevitGitAuthenticationError(exception_msg)
    else:
        raise PyRevitException(exception_msg)


def get_repo(repo_dir):
    """Return repo object for given git repo directory.

    Args:
        repo_dir (str): full path of git repo directory

    Returns:
        (RepoInfo): repo object
    """
    repo = libgit.Repository(repo_dir)
    return RepoInfo(repo)


def git_pull(repo_info):
    """Pull the current head of given repo.

    Args:
        repo_info (RepoInfo): target repo object

    Returns:
        (RepoInfo): repo object with updated head
    """
    repo = repo_info.repo
    try:
        libgit.Commands.Pull(
            repo, _make_pull_signature(), _make_pull_options(repo_info)
        )

        mlogger.debug("Successfully pulled repo: %s", repo_info.directory)
        head_msg = safe_strtype(repo.Head.Tip.Message).replace("\n", "")

        mlogger.debug("New head is: %s > %s", repo.Head.Tip.Id.Sha, head_msg)
        return RepoInfo(repo)

    except Exception as pull_err:
        mlogger.debug("Failed git pull: %s | %s",
                      repo_info.directory, pull_err)
        _process_git_error(pull_err)


def git_fetch(repo_info):
    """Fetch current branch of given repo.

    Args:
        repo_info (RepoInfo): target repo object

    Returns:
        (RepoInfo): repo object with updated head
    """
    repo = repo_info.repo
    try:
        libgit.Commands.Fetch(
            repo,
            repo.Head.TrackedBranch.RemoteName,
            [],
            _make_fetch_options(repo_info),
            "fetching pyrevit updates",
        )

        mlogger.debug("Successfully pulled repo: %s", repo_info.directory)
        head_msg = safe_strtype(repo.Head.Tip.Message).replace("\n", "")

        mlogger.debug("New head is: %s > %s", repo.Head.Tip.Id.Sha, head_msg)
        return RepoInfo(repo)

    except Exception as fetch_err:
        mlogger.debug("Failed git fetch: %s | %s",
                      repo_info.directory, fetch_err)
        _process_git_error(fetch_err)


def git_clone(repo_url, clone_dir, username=None, password=None):
    """Clone git repository to given location.

    Args:
        repo_url (str): repo .git url
        clone_dir (str): destination path
        username (str): credentials - username
        password (str): credentials - password
    """
    try:
        libgit.Repository.Clone(
            repo_url,
            clone_dir,
            _make_clone_options(username=username, password=password),
        )

        mlogger.debug("Completed git clone: %s @ %s", repo_url, clone_dir)

    except Exception as clone_err:
        mlogger.debug(
            "Error cloning repo: %s to %s | %s", repo_url, clone_dir, clone_err
        )
        _process_git_error(clone_err)


def compare_branch_heads(repo_info):
    """Compare local and remote branch heads and return ???

    Args:
        repo_info (RepoInfo): target repo object
    """
    # FIXME: need return type. possibly simplify
    repo = repo_info.repo
    repo_branches = repo.Branches

    mlogger.debug("Repo branches: %s", [b.FriendlyName for b in repo_branches])

    for branch in repo_branches:
        if branch.FriendlyName == repo_info.branch and not branch.IsRemote:
            try:
                if branch.TrackedBranch:
                    mlogger.debug(
                        "Comparing heads: %s of %s",
                        branch.CanonicalName,
                        branch.TrackedBranch.CanonicalName,
                    )

                    hist_div = repo.ObjectDatabase.CalculateHistoryDivergence(
                        branch.Tip, branch.TrackedBranch.Tip
                    )
                    return hist_div
            except Exception as compare_err:
                mlogger.error(
                    "Can not compare branch %s in repo: %s | %s",
                    branch,
                    repo,
                    safe_strtype(compare_err).replace("\n", ""),
                )
        else:
            mlogger.debug("Skipping remote branch: %s", branch.CanonicalName)


def get_all_new_commits(repo_info):
    """Fetch and return new commits ahead of current head.

    Args:
        repo_info (RepoInfo): target repo object

    Returns:
        (OrderedDict[str, str]): ordered dict of commit hash:message
    """
    repo = repo_info.repo
    current_commit = repo_info.last_commit_hash

    ref_commit = repo.Lookup(libgit.ObjectId(current_commit),
                             libgit.ObjectType.Commit)

    # Let's only consider the refs that lead to this commit...
    refs = repo.Refs.ReachableFrom([ref_commit])

    # ...and create a filter that will retrieve all the commits...
    commit_filter = libgit.CommitFilter()
    commit_filter.IncludeReachableFrom = refs
    commit_filter.ExcludeReachableFrom = ref_commit
    commit_filter.SortBy = libgit.CommitSortStrategies.Time

    commits = repo.Commits.QueryBy(commit_filter)
    commitsdict = OrderedDict()
    for commit in commits:
        if commit in repo.Head.Commits or commit in repo.Head.TrackedBranch.Commits:
            commitsdict[commit.Id.ToString()] = commit.MessageShort

    return commitsdict
