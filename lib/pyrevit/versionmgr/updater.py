from pyrevit import HOST_APP
from pyrevit.versionmgr import get_pyrevit_repo
from pyrevit.coreutils.logger import get_logger
import pyrevit.coreutils.git as git

from pyrevit.extensions.extensionmgr import get_installed_extension_data

# noinspection PyUnresolvedReferences
from System import DateTime, DateTimeOffset


logger = get_logger(__name__)


# noinspection PyUnusedLocal
def hndlr(url, uname, types):
    up = git.libgit.UsernamePasswordCredentials()
    up.Username = ''
    up.Password = ''
    return up


def _make_pull_options():
    pull_ops = git.libgit.PullOptions()
    pull_ops.FetchOptions = git.libgit.FetchOptions()
    # pull_ops.FetchOptions.CredentialsProvider = git.libgit.Handlers.CredentialsHandler(hndlr)
    return pull_ops


def _make_fetch_options():
    fetch_ops = git.libgit.FetchOptions()
    # fetch_ops.CredentialsProvider = git.libgit.Handlers.CredentialsHandler(hndlr)
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
        repo.Network.Pull(_make_pull_signature(), _make_pull_options())
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
            repo.Network.Fetch(remote, _make_fetch_options())
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
