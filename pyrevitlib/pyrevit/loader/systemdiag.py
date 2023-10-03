"""Session diagnostics."""
from pyrevit import HOST_APP

from pyrevit.userconfig import user_config
from pyrevit.framework import DriveInfo, Path
from pyrevit.coreutils.logger import get_logger


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


def check_min_host_version():
    # get required version and build from user config
    req_build = user_config.required_host_build
    if req_build:
        if HOST_APP.build != req_build:
            mlogger.warning('You are not using the required host build: %s',
                            req_build)


def check_host_drive_freespace():
    # get min free space from user config
    min_freespace = user_config.min_host_drivefreespace
    if min_freespace:
        # find host drive and check free space
        host_drive = Path.GetPathRoot(HOST_APP.proc_path)
        for drive in DriveInfo.GetDrives():
            if drive.Name == host_drive:
                free_hd_space = float(drive.TotalFreeSpace) / (1024 ** 3)

                if free_hd_space < min_freespace:
                    mlogger.warning('Remaining space on local drive '
                                    'is less than %sGB...', min_freespace)


def system_diag():
    """Verifies system status is appropriate for a pyRevit session."""
    # checking available drive space
    check_host_drive_freespace()

    # check if user is running the required host version and build
    check_min_host_version()
