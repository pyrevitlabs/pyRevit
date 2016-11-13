
# fixme rewrite update mechanism to use this to update all(?) extensions
# todo: add support for versioning based on git head hash

import sys
import clr

from ..logger import get_logger
logger = get_logger(__name__)

from ..config import HOME_DIR
from ..git import git

from System import DateTime, DateTimeOffset


def hndlr(url, uname, types):
    up = git.UsernamePasswordCredentials()
    up.Username = 'eirannejad@gmail.com'
    up.Password = 'ehsan2010'
    return up


def _make_pull_options():
    pull_ops = git.PullOptions()
    pull_ops.FetchOptions = git.FetchOptions()
    pull_ops.FetchOptions.CredentialsProvider = git.Handlers.CredentialsHandler(hndlr)
    return pull_ops


def _make_fetch_options():
    fetch_ops = git.FetchOptions()
    fetch_ops.CredentialsProvider = git.Handlers.CredentialsHandler(hndlr)
    return fetch_ops


def _make_pull_signature():
    return git.Signature('eirannejad', 'eirannejad@gmail.com', DateTimeOffset(DateTime.Now))


def _find_all_pkg_repos():
    logger.debug('Finding installed repos.')
    repos = [git.Repository(HOME_DIR)]
    logger.debug('Installed repos: {}'.format(repos))
    return repos


def update_pyrevit():
    for repo in _find_all_pkg_repos():
        repo_dir = repo.Info.WorkingDirectory
        logger.debug('Updating repo: {}'.format(repo_dir))
        head_msg = str(repo.Head.Tip.Message).replace('\n','')
        logger.debug('Current head is: {} > {}'.format(repo.Head.Tip.Id.Sha, head_msg))
        try:
            repo.Network.Pull(_make_pull_signature(), _make_pull_options())
            logger.info('Successfully updated repo: {}'.format(repo_dir))
            head_msg = str(repo.Head.Tip.Message).replace('\n','')
            logger.debug('New head is: {} > {}'.format(repo.Head.Tip.Id.Sha, head_msg))
        except Exception as pull_err:
            logger.error('Failed updating: {} | {}'.format(repo_dir, pull_err))

def has_pending_updates(repo):
    repo_dir = repo.Info.WorkingDirectory
    logger.debug('Fetching updates for: {}'.format(repo_dir))
    repo_branches = repo.Branches
    logger.debug('Repo branches: {}'.format([b for b in repo_branches]))

    for remote in repo.Network.Remotes:
        logger.debug('Fetching remote: {} of {}'.format(remote.Name, repo_dir))
        try:
            repo.Network.Fetch(remote, _make_fetch_options())
        except Exception as fetch_err:
            logger.error('Failed fetching: {} | {}'.format(repo_dir, fetch_err))

    for branch in repo_branches:
        if not branch.IsRemote:
            logger.debug('Comparing heads: {} of {}'.format(branch.CanonicalName, branch.TrackedBranch.CanonicalName))
            hist_div = repo.ObjectDatabase.CalculateHistoryDivergence(branch.Tip, branch.TrackedBranch.Tip)
            if hist_div.BehindBy > 0:
                return True

    return False
