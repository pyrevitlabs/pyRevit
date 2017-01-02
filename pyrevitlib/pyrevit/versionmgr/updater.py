from pyrevit import HOST_APP
import pyrevit.coreutils.git as git
from pyrevit.coreutils.logger import get_logger
from pyrevit.versionmgr import get_pyrevit_repo

from pyrevit.userconfig import user_config
from pyrevit.extensions.extensionmgr import get_installed_extension_data

# noinspection PyUnresolvedReferences
from System import DateTime, DateTimeOffset


logger = get_logger(__name__)


def _credentials_hndlr(username, password):
    up = git.libgit.UsernamePasswordCredentials()
    up.Username = username
    up.Password = password
    return up


def _hndlr(url, uname, types):
    up = git.libgit.UsernamePasswordCredentials()
    up.Username = 'eirannejad@gmail.com'
    up.Password = 'testpassword1891'
    return up


def _get_credentials_hndlr(username, password):
    return git.libgit.Handlers.CredentialsHandler(lambda url, uname, types: _credentials_hndlr(username, password))


def _get_credentials(repo_info):
    try:
        repo_config = getattr(user_config, repo_info.name)
        return repo_config.username, repo_config.password
    except:
        return None, None


def _make_pull_options(repo_info):
    pull_ops = git.libgit.PullOptions()
    pull_ops.FetchOptions = git.libgit.FetchOptions()
    username, password = _get_credentials(repo_info)
    if username and password:
        pull_ops.FetchOptions.CredentialsProvider = _get_credentials_hndlr(username, password)
    return pull_ops


def _make_fetch_options(repo_info):
    fetch_ops = git.libgit.FetchOptions()
    username, password = _get_credentials(repo_info)
    if username and password:
        fetch_ops.CredentialsProvider = _get_credentials_hndlr(username, password)
    return fetch_ops


def _make_pull_signature():
    return git.libgit.Signature(HOST_APP.username, HOST_APP.username, DateTimeOffset(DateTime.Now))


def get_thirdparty_ext_repos():
    # get a list of all directories that could include extensions
    extensions = []
    logger.debug('Finding installed repos...')
    ext_info_list = get_installed_extension_data()

    for ext_info in ext_info_list:
        if ext_info and git.libgit.Repository.IsValid(ext_info.directory):
            extensions.append(ext_info)

    logger.debug('Valid third-party extensions for update: {}'.format(extensions))

    repos = []
    for ext in extensions:
        repo_info = git.get_repo(ext.directory)
        if repo_info:
            repos.append(repo_info)

    return repos


def get_all_extension_repos():
    repo_info_list = [get_pyrevit_repo()]               # pyrevit main repo
    repo_info_list.extend(get_thirdparty_ext_repos())   # add all thirdparty extension repos
    return repo_info_list


def update_pyrevit(repo_info):
    repo = repo_info.repo
    logger.debug('Updating repo: {}'.format(repo_info.directory))
    head_msg = str(repo.Head.Tip.Message).replace('\n', '')
    logger.debug('Current head is: {} > {}'.format(repo.Head.Tip.Id.Sha, head_msg))
    try:
        repo.Network.Pull(_make_pull_signature(), _make_pull_options(repo_info))
        logger.debug('Successfully updated repo: {}'.format(repo_info.directory))
        head_msg = str(repo.Head.Tip.Message).replace('\n', '')
        logger.debug('New head is: {} > {}'.format(repo.Head.Tip.Id.Sha, head_msg))
        return git.RepoInfo(repo)

    except Exception as pull_err:
        logger.error('Failed updating: {} | {}'.format(repo_info.directory, pull_err))

    return False


def has_pending_updates(repo_info):
    repo = repo_info.repo
    logger.debug('Fetching updates for: {}'.format(repo_info.directory))
    repo_branches = repo.Branches
    logger.debug('Repo branches: {}'.format([b for b in repo_branches]))

    for remote in repo.Network.Remotes:
        logger.debug('Fetching remote: {} of {}'.format(remote.Name, repo_info.directory))
        try:
            repo.Network.Fetch(remote, _make_fetch_options(repo_info))
        except Exception as fetch_err:
            logger.error('Failed fetching: {} | {}'.format(repo_info.directory, str(fetch_err).replace('\n', '')))

    for branch in repo_branches:
        if not branch.IsRemote:
            try:
                if branch.TrackedBranch:
                    logger.debug('Comparing heads: {} of {}'.format(branch.CanonicalName,
                                                                    branch.TrackedBranch.CanonicalName))
                    hist_div = repo.ObjectDatabase.CalculateHistoryDivergence(branch.Tip, branch.TrackedBranch.Tip)
                    if hist_div.BehindBy > 0:
                        return True
            except Exception as compare_err:
                logger.error('Can not compare branch {} in repo: {} | {}'.format(branch,
                                                                                 repo,
                                                                                 str(compare_err).replace('\n', '')))

    return False
