"""Handle updating pyRevit repository and its extensions."""

import pyrevit.coreutils.git as libgit
from pyrevit.compat import safe_strtype
from pyrevit import coreutils
from pyrevit import HOME_DIR
from pyrevit.coreutils.logger import get_logger
from pyrevit import versionmgr
from pyrevit.versionmgr import upgrade

from pyrevit.userconfig import user_config
from pyrevit.extensions import extensionmgr

import socket

#pylint: disable=C0103,W0703
logger = get_logger(__name__)


COREUPDATE_TRIGGER = 'COREUPDATE'

COREUPDATE_MESSAGE = '<div class="coreupdatewarn">' \
                     '<strong>IMPORTANT</strong>\n' \
                     'pyRevit has a major core update. This update ' \
                     '<u>can not</u> be applied when Revit is running. ' \
                     'Please close all Revit instances, and update the clone ' \
                     'using the pyRevit CLI. Start Revit ' \
                     'again after the update and pyRevit will load with ' \
                     'the new core changes.' \
                     '</div>'


def _check_connection(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        logger.debug('Internet access detected.')
        return True
    except socket.error as ex:
        logger.debug('No internet access detected. %s', ex)
        return False


def _get_extension_credentials(repo_info):
    try:
        repo_config = user_config.get_section(repo_info.name)
        if repo_config.private_repo:
            return repo_config.username, repo_config.password
        return None, None
    except Exception:
        return None, None


def _fetch_remote(remote, repo_info):
    logger.debug('Fetching remote: %s of %s', remote.Name, repo_info.directory)
    username, password = _get_extension_credentials(repo_info)
    if username and password:
        repo_info.username = username
        repo_info.password = password

    libgit.git_fetch(repo_info)


def get_thirdparty_ext_repos():
    """Return a list of repos for installed third-party extensions."""
    processed_paths = set()
    valid_exts = []
    ext_repos = []
    logger.debug('Finding installed repos...')
    ext_info_list = extensionmgr.get_thirdparty_extension_data()

    for ext_info in ext_info_list:
        repo_path = libgit.libgit.Repository.Discover(ext_info.directory)
        if repo_path:
            repo_info = libgit.get_repo(repo_path)
            if repo_info:
                valid_exts.append(ext_info)
                if repo_info.directory not in processed_paths:
                    processed_paths.add(repo_info.directory)
                    ext_repos.append(repo_info)

    logger.debug('Valid third-party extensions for update: %s', valid_exts)

    return ext_repos


def get_all_extension_repos():
    """Return a list of repos for all installed extensions."""
    logger.debug('Finding all extension repos.')
    # pyrevit main repo
    repo_info_list = []
    pyrevit_repo = versionmgr.get_pyrevit_repo()
    if pyrevit_repo:
        repo_info_list.append(pyrevit_repo)
    # add all thirdparty extension repos
    repo_info_list.extend(get_thirdparty_ext_repos())
    logger.debug('Repos are: %s', repo_info_list)
    return repo_info_list


def update_repo(repo_info):
    """Update repository.

    Args:
        repo_info (:obj:`pyrevit.coreutils.git.RepoInfo`):
            repository info wrapper object
    """
    repo = repo_info.repo
    logger.debug('Updating repo: %s', repo_info.directory)
    head_msg = safe_strtype(repo.Head.Tip.Message).replace('\n', '')
    logger.debug('Current head is: %s > %s', repo.Head.Tip.Id.Sha, head_msg)
    username, password = _get_extension_credentials(repo_info)
    if username and password:
        repo_info.username = username
        repo_info.password = password

    try:
        updated_repo_info = libgit.git_pull(repo_info)
        logger.debug('Successfully updated repo: %s',
                     updated_repo_info.directory)
        return updated_repo_info

    except libgit.PyRevitGitAuthenticationError as auth_err:
        logger.debug('Can not login to git repository to get updates: %s | %s',
                     repo_info, auth_err)
        raise auth_err

    except Exception as update_err:
        logger.debug('Failed updating repo: %s | %s', repo_info, update_err)
        raise update_err


def get_updates(repo_info):
    """Fetch updates on repository.

    Args:
        repo_info (:obj:`pyrevit.coreutils.git.RepoInfo`):
            repository info wrapper object
    """
    repo = repo_info.repo
    at_least_one_fetch_was_successful = False

    logger.debug('Fetching updates for: %s', repo_info.directory)
    for remote in repo.Network.Remotes:
        try:
            _fetch_remote(remote, repo_info)
            at_least_one_fetch_was_successful = True

        except libgit.PyRevitGitAuthenticationError:
            logger.debug('Failed fetching updates. '
                         'Can not login to repo to get updates: %s', repo_info)
            continue

        except Exception:
            logger.debug('Failed fetching updates: %s', repo_info)
            continue

    if at_least_one_fetch_was_successful:
        return True

    return False


def has_pending_updates(repo_info):
    """Check for updates on repository.

    Args:
        repo_info (:obj:`pyrevit.coreutils.git.RepoInfo`):
            repository info wrapper object
    """
    if get_updates(repo_info):
        hist_div = libgit.compare_branch_heads(repo_info)
        if hist_div.BehindBy > 0:
            return True


def check_for_updates():
    """Check whether any available repo has pending updates."""
    if _check_connection():
        logger.info('Checking for updates...')

        for repo in get_all_extension_repos():
            if has_pending_updates(repo):
                logger.info('Updates are available for %s...', repo.name)
                return True
            else:
                logger.info('%s is up-to-date...', repo.name)
    else:
        logger.warning('No internet access detected. '
                       'Skipping check for updates.')
        return False


def has_core_updates():
    """Check whether pyRevit repo has core updates.

    This would require host application to be closed to release the file lock
    of core DLLs so they can be updated separately.
    """
    pyrevit_repo = versionmgr.get_pyrevit_repo()
    if pyrevit_repo and get_updates(pyrevit_repo):
        new_commits = libgit.get_all_new_commits(pyrevit_repo)

        logger.debug('Checking new commits on pyrevit repo.')
        for cmt_sha, cmt_msg in new_commits.items():
            logger.debug('%s: %s', cmt_sha, cmt_msg)
            if COREUPDATE_TRIGGER in cmt_msg:
                logger.debug('pyrevit repo has core update at %s: %s',
                             cmt_sha, cmt_msg)
                return True

    return False


def update_pyrevit():
    """Update pyrevit and its extension repositories."""
    if _check_connection():
        third_party_updated = False
        pyrevit_updated = False
        pyrevit_has_coreupdates = has_core_updates()
        thirdparty_repos = get_thirdparty_ext_repos()

        logger.debug('List of thirdparty repos to be updated: %s',
                     thirdparty_repos)

        # update third-party extensions first, one by one
        for repo_info in thirdparty_repos:
            logger.debug('Updating repo: %s', repo_info.directory)
            try:
                upped_repo_info = update_repo(repo_info)
                logger.info(':inbox_tray: Successfully updated: %s to %s',
                            upped_repo_info.name,
                            upped_repo_info.last_commit_hash[:7])
                third_party_updated = True
            except Exception:
                logger.info('Can not update repo: %s (Run in debug to see why)',
                            repo_info.name)

        # now update pyrevit repo and reload
        pyrevit_repo = versionmgr.get_pyrevit_repo()
        if pyrevit_repo:
            if not pyrevit_has_coreupdates:
                logger.debug('Updating pyrevit repo: %s',
                             pyrevit_repo.directory)
                try:
                    upped_pyrevit_repo_info = update_repo(pyrevit_repo)
                    logger.info(':inbox_tray: Successfully updated: %s to %s',
                                upped_pyrevit_repo_info.name,
                                upped_pyrevit_repo_info.last_commit_hash[:7])
                    pyrevit_updated = True
                except Exception as err:
                    logger.info('Can not update pyrevit repo '
                                '(Run in debug to see why) | %s', err)
                # perform upgrade tasks
                logger.info('Upgrading settings...')
                upgrade.upgrade_existing_pyrevit()
        if not pyrevit_has_coreupdates:
            if third_party_updated or pyrevit_updated:
                # now reload pyrevit
                from pyrevit.loader import sessionmgr
                sessionmgr.reload_pyrevit()
            else:
                logger.info('pyRevit and extensions seem to be up-to-date.')
        else:
            from pyrevit import script
            output = script.get_output()
            output.print_html(COREUPDATE_MESSAGE)
            logger.debug('Core updates. Skippin update and reload.')
    else:
        logger.warning('No internet access detected. Skipping update.')
