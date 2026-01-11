# -*- coding: utf-8 -*-
"""Defines the basic server management api."""
#pylint: disable=invalid-name,broad-except,useless-object-inheritance
#pylint: disable=too-few-public-methods,too-many-arguments
import os.path as op
import pickle
from collections import OrderedDict

from pyrevit import HOST_APP
from pyrevit.coreutils.logger import get_logger
from pyrevit.labs import TargetApps
from pyrevit.coreutils import appdata
from pyrevit.userconfig import user_config


DATAFILE_ID = 'serverinfo'


mlogger = get_logger(__name__)


class RoutesServerInfo(object):
    """Routes server info."""
    def __init__(self,
                 host, version, process_id,
                 server_host, server_port):
        # host app info
        self.host = host
        self.version = version
        self.process_id = process_id
        # server info
        self.server_host = server_host
        self.server_port = server_port

    def get_cache_data(self):
        """Get json string of this instance."""
        data_dict = OrderedDict()
        for key in sorted(self.__dict__.keys()):
            data_dict[key] = self.__dict__[key]
        return data_dict


def _get_host_serverinfo_file():
    return appdata.get_instance_data_file(
        file_id=DATAFILE_ID,
        file_ext='pickle'
        )


def _read_serverinfo(data_file):
    try:
        with open(data_file, 'rb') as df:
            return pickle.load(df)
    except Exception as readEx:
        mlogger.debug('Failed reading serverinfo file | %s', str(readEx))


def _write_serverinfo(data_file, rsinfo):
    with open(data_file, 'wb') as df:
        pickle.dump(rsinfo, df)


def _get_all_serverinfo():
    rsinfo_list = []
    for revit_inst in TargetApps.Revit.RevitController.ListRunningRevits():
        for dfile in appdata.find_instance_data_files(
                file_ext='pickle',
                instance_id=revit_inst.ProcessId):
            if DATAFILE_ID in dfile:
                rsinfo = _read_serverinfo(dfile)
                if rsinfo:
                    rsinfo_list.append(rsinfo)
    return rsinfo_list


def _get_next_available_port(used_ports):
    # TODO: implement range?
    # starts from configured port and goes up
    # picks the first unused one
    next_port = user_config.routes_port
    while next_port in used_ports:
        next_port += 1
    return next_port


def _get_new_serverinfo(data_file):
    # determine latest port
    used_ports = [x.server_port for x in _get_all_serverinfo()]
    new_port = _get_next_available_port(used_ports)
    # create new routes server info
    rsinfo = RoutesServerInfo(
        host=HOST_APP.pretty_name,
        version=HOST_APP.version,
        process_id=HOST_APP.proc_id,
        server_host=user_config.routes_host,
        server_port=new_port
        )
    # store server info
    _write_serverinfo(data_file, rsinfo)
    return rsinfo


def get_registered_servers():
    """Get all registered servers on this machine.

    Returns:
        (list[RoutesServerInfo]): list of registered servers
    """
    return _get_all_serverinfo()


def register():
    """Register host:port for this host instance."""
    data_file = _get_host_serverinfo_file()
    if op.exists(data_file):
        return _read_serverinfo(data_file)
    else:
        return _get_new_serverinfo(data_file)


def unregister():
    """Remove registered server host:port for this host instance."""
    data_file = _get_host_serverinfo_file()
    if op.exists(data_file):
        appdata.garbage_data_file(data_file)
