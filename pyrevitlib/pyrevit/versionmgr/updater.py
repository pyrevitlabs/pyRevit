import pyrevit.coreutils.git as git
from pyrevit.coreutils.logger import get_logger
from pyrevit.versionmgr import get_pyrevit_repo

from pyrevit.userconfig import user_config
from pyrevit.extensions.extensionmgr import get_installed_extension_data


logger = get_logger(__name__)


def _get_extension_credentials(repo_info):
    try:
        repo_config = user_config.get_section(repo_info.name)
        return repo_config.username, repo_config.password
    except:
        return None, None


def _fetch_remote(remote, repo_info):
    logger.debug('Fetching remote: {} of {}'.format(remote.Name, repo_info.directory))
    username, password = _get_extension_credentials(repo_info)
    if username and password:
        repo_info.username = username
        repo_info.password = password

    git.git_fetch(repo_info)


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
    logger.debug('Finding all extension repos.')
    repo_info_list = [get_pyrevit_repo()]               # pyrevit main repo
    repo_info_list.extend(get_thirdparty_ext_repos())   # add all thirdparty extension repos
    logger.debug('Repos are: {}'.format(repo_info_list))
    return repo_info_list


def update_pyrevit(repo_info):
    repo = repo_info.repo
    logger.debug('Updating repo: {}'.format(repo_info.directory))
    head_msg = str(repo.Head.Tip.Message).replace('\n', '')
    logger.debug('Current head is: {} > {}'.format(repo.Head.Tip.Id.Sha, head_msg))
    username, password = _get_extension_credentials(repo_info)
    if username and password:
        repo_info.username = username
        repo_info.password = password

    updated_repo_info = git.git_pull(repo_info)

    if not updated_repo_info:
        logger.error('Failed updating: {}'.format(repo_info.directory))
        return False
    else:
        logger.debug('Successfully updated repo: {}'.format(repo_info.directory))
        return updated_repo_info


def has_pending_updates(repo_info):
    repo = repo_info.repo
    logger.debug('Fetching updates for: {}'.format(repo_info.directory))

    for remote in repo.Network.Remotes:
        _fetch_remote(remote, repo_info)

    repo_branches = repo.Branches
    logger.debug('Repo branches: {}'.format([b for b in repo_branches]))

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
