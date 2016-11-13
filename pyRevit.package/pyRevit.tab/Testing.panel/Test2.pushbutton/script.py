from pyrevit.loader import updater

from pyrevit.loader import updater
for repo in updater._find_all_pkg_repos():
    if updater.has_pending_updates(repo):
        print('Yes on:\n{}'.format(repo))
    else:
        print('No updates on:\n{}'.format(repo.Info.WorkingDirectory))
