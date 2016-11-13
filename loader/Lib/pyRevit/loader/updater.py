
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
    options = git.PullOptions()
    options.FetchOptions = git.FetchOptions()
    options.FetchOptions.CredentialsProvider = git.Handlers.CredentialsHandler(hndlr)
    return options

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
        except Exception as pull_err:
            logger.error('Failed updating: {} | {}'.format(repo_dir, pull_err))
