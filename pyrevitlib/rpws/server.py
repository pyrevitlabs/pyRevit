# -*- coding: utf-8 -*-
r"""Python wrapper for Autodesk Revit Server.

Example:
    ```python
    name = '<server name>'
    version = '2017'    # server version in XXXX format
    rserver = RevitServer(name, version)
    # listing all files, folders, and models in a server
    for parent, folders, files, models in rserver.walk():
        print(parent)
        for fd in folders:
            print('\t@d {}'.format(fd.path))
        for f in files:
            print('\t@f {}'.format(f.path))
        for m in models:
            print('\t@m {}'.format(m.path))
    ```
"""

import os.path as op
import uuid
import getpass
import socket
import urllib

# third party modules
import requests

# rpws components
import rpws
import rpws.api as api
import rpws.models as models


# Default portion of the server url. The only odd one is 2012 which does not
# include server version in url. Each Revit server version can only host
# Revit models of the same version. Also it's practical for a company to want
# a consistent server name to host models of different Revit version.
# Thus the server version was added to the url after 2012 version.
# Otherwise the url for two servers called X for 2016 and 2017 Revit models
# would have been the same url.
sroots = {"2012": "/RevitServerAdminRESTService/AdminRESTService.svc",
          "2013": "/RevitServerAdminRESTService2013/AdminRESTService.svc",
          "2014": "/RevitServerAdminRESTService2014/AdminRESTService.svc",
          "2015": "/RevitServerAdminRESTService2015/AdminRESTService.svc",
          "2016": "/RevitServerAdminRESTService2016/AdminRESTService.svc",
          "2017": "/RevitServerAdminRESTService2017/AdminRESTService.svc",
          "2018": "/RevitServerAdminRESTService2018/AdminRESTService.svc",
          "2019": "/RevitServerAdminRESTService2019/AdminRESTService.svc",
          "2020": "/RevitServerAdminRESTService2020/AdminRESTService.svc",
          "2021": "/RevitServerAdminRESTService2021/AdminRESTService.svc",
          "2022": "/RevitServerAdminRESTService2022/AdminRESTService.svc",
          "2023": "/RevitServerAdminRESTService2023/AdminRESTService.svc",
          "2024": "/RevitServerAdminRESTService2024/AdminRESTService.svc",
          "2025": "/RevitServerAdminRESTService2025/AdminRESTService.svc",
          "2026": "/RevitServerAdminRESTService2026/AdminRESTService.svc",
          }


class RevitServer(object):
    """Handles all communication with Revit Server as initialized.

    Args:
        name (str): Server name.
        version (str): Server version.
        username (str, optional): Username to be passed to in http calls.
                                  This is set to current user if not provided.
        machine (str, optional): Machine name to be passed to in http calls
                                 Set to current machine if not provided.

    Attributes:
        name (str): Server name.
        version (str): Server version.
        _base_uri (str, private): Base URI of the initialized server
        _huser (str, private): Username of the initialized server.
        _hmachine (str, private): Machine name of the initialized server

    Example:
        >>> rserver = RevitServer('server01', '2017')
        >>> print(rserver)
        <rpws.RevitServer name:server01 version:2017>
    """

    def __init__(self, name, version, username=None, machine=None):
        """Class constructor."""
        # make sure version is of type str
        if type(version) == int:
            version = str(version)

        # verify server version is supported
        if version not in sroots:
            raise rpws.ServerVersionNotSupported(
                'Supported versions are: {}'
                .format([x for x in sroots.keys()]))

        self.name = name
        self.version = version
        self._base_uri = "http://" + self.name + sroots[self.version]

        if username:
            self._huser = username
        else:
            self._huser = getpass.getuser()

        if machine:
            self._hmachine = machine
        else:
            self._hmachine = socket.gethostname()

    def __repr__(self):
        """Repr for RevitServer object.

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> print(rserver)
            <rpws.RevitServer name:server01 version:2017>
        """
        return '<rpws.{} name:{} version:{}>'\
               .format(self.__class__.__name__, self.name, self.version)

    @property
    def _header_dict(self):
        """Private property that creates and returns the http header dict.

        Returns:
            dict: Header dict to be passed to Revit Server
        """
        # using uuid module to generate a unique session id that is required
        # by the Revit Server for logging purposes
        return {api.REQ_HEADER_USERNAME: self._huser,
                api.REQ_HEADER_MACHINE: self._hmachine,
                api.REQ_HEADER_GUID: str(uuid.uuid4())}

    def _httpmethod(self, http_method, command, node_uri=None, rootcmd=False):
        """The single method that handles all http requests.

        Args:
            http_method (func): method from requests module (e.g. requests.get)
            command (str): Revit Server API command from rpws.api
            node_uri (str, optional): Path to an entry on the server.
                                      Root if not provided.
            rootcmd (bool, optional): True if command should be executed
                                      at root level. Default is False.

        Returns: Depending on the input command returns
            int: http response status code
            dict: data dict returned by server as the command result

        Raises:
            rpws.ServerNotImplemented: When server does not exist
            rpws.ServerFileNotFound: When file, folder, or model does not exist
            rpws.ServerForbiddenError: On accessing forbidden entries
            rpws.ServerInternalError: When server has internal error
            rpws.ServerMethodNotAllowedError: When method is not allowed
            rpws.ServerURITooLongError: When url is too long for server
            rpws.ServerTimeoutError: On connection timeout
            rpws.ServerConnectionError: On connection error
            rpws.ServerBadRequestError: On bad request url
            rpws.ServerServiceUnavailableError: When service is not available
            rpws.UnhandledException: Any other http status codes
        """
        # create the http request url
        if rootcmd:
            req_url = self._base_uri + command
        else:
            req_url = self._base_uri + '/' + urllib.quote(self._api_path(node_uri).encode('utf-8')) + command

        # send to server
        try:
            r = http_method(req_url, headers=self._header_dict)
        except requests.ConnectTimeout:
            raise rpws.ServerTimeoutError(req_url)
        except requests.ConnectionError:
            raise rpws.ServerConnectionError(self._base_uri)

        # process status codes and results
        if r.status_code == 200 and r.text:
            r.encoding = 'utf-8-sig'
            return r.json()
        elif 200 <= r.status_code < 300:
            return True
        elif r.status_code == 400:
            raise rpws.ServerBadRequestError(node_uri)
        elif r.status_code == 403:
            raise rpws.ServerForbiddenError(node_uri)
        elif r.status_code == 404:
            raise rpws.ServerFileNotFound(node_uri)
        elif r.status_code == 405:
            raise rpws.ServerMethodNotAllowedError(node_uri)
        elif r.status_code == 414:
            raise rpws.ServerURITooLongError(node_uri)
        elif r.status_code == 500:
            raise rpws.ServerInternalError(node_uri)
        elif r.status_code == 501:
            raise rpws.ServerNotImplemented('name:{} version:{}'
                                            .format(self.name, self.version))
        elif r.status_code == 503:
            raise rpws.ServerServiceUnavailableError(node_uri)
        else:
            raise rpws.UnhandledException('requests status code:{}'
                                          .format(r.status_code))

    def _get(self, command, node_uri=None, rootcmd=False):
        """Send a GET request to Revit Server.

        Args:
            command (str): Revit Server API command from rpws.api
            node_uri (str, optional): Path to an entry on the server.
                                      Root if not provided.
            rootcmd (bool, optional): True if command should be executed
                                      at root level. Default is False.

        Returns:
            See _httpmethod() method for results
        """
        return self._httpmethod(requests.get, command, node_uri, rootcmd)

    def _post(self, command, node_uri=None, rootcmd=False):
        """Send a POST request to Revit Server.

        Args:
            command (str): Revit Server API command from rpws.api
            node_uri (str, optional): Path to an entry on the server.
                                      Root if not provided.
            rootcmd (bool, optional): True if command should be executed
                                      at root level. Default is False.

        Returns:
            See _httpmethod() method for results
        """
        return self._httpmethod(requests.post, command, node_uri, rootcmd)

    def _put(self, command, node_uri=None, rootcmd=False):
        """Send a PUT request to Revit Server.

        Args:
            command (str): Revit Server API command from rpws.api
            node_uri (str, optional): Path to an entry on the server.
                                      Root if not provided.
            rootcmd (bool, optional): True if command should be executed
                                      at root level. Default is False.

        Returns:
            See _httpmethod() method for results
        """
        return self._httpmethod(requests.put, command, node_uri, rootcmd)

    def _delete(self, command, node_uri=None, rootcmd=False):
        """Send a DELETE request to Revit Server.

        Args:
            command (str): Revit Server API command from rpws.api
            node_uri (str, optional): Path to an entry on the server.
                                      Root if not provided.
            rootcmd (bool, optional): True if command should be executed
                                      at root level. Default is False.

        Returns:
            See _httpmethod() method for results
        """
        return self._httpmethod(requests.delete, command, node_uri, rootcmd)

    @staticmethod
    def _api_path(nodepath=None):
        """Format path for Revit server requests uri.

        Generate a Revit Server directory structure path from provided
        file, folder, or model path. Revit server uses '|' to separate
        directory entries so as not to conflict with '/' in http urls. So:
        "/Training/MyOffice/2017/Model.rvt" will be changed to:
        "|Training|MyOffice|2017|Model.rvt"

        Args:
            nodepath (str, optional): Path to an entry on the server.
                                      Root if not provided.

        Returns:
            str: Path formatted for Revit Server urls
        """
        if nodepath:
            return nodepath.replace(op.sep, api.DIVIDER)
        else:
            return api.DIVIDER

    @staticmethod
    def _root_path(nodepath=None):
        """Make sure that the path starts with / as root of the server.

        Args:
            nodepath (str, optional): Path to an entry on the server.
                                      Root if not provided.

        Returns:
            str: Reformatted path
        """
        if nodepath:
            npath = op.normpath(nodepath)
            return npath if npath.startswith(op.sep) \
                else op.join(op.sep, npath)
        else:
            return op.sep

    @staticmethod
    def _getserverdriveinfo(contents_dict):
        """Return drive space info acquired from server.

        Data keys: "DriveFreeSpace" and "DriveSpace"

        Args:
            contents_dict (dict): Data dict returned by server

        Returns:
            rpws.models.ServerDriveInfo
        """
        # make the server drive info obj
        return models.ServerDriveInfo(
            drive_space=contents_dict[api.NODE_DRIVE_TOTALSPACE_KEY],
            drive_freespace=contents_dict[api.NODE_DRIVE_FREESPACE_KEY])

    @staticmethod
    def _getlocks(ip_lock_list):
        """Extract locks from list of locks in progress returned by server.

        Args:
            ip_lock_list (list): List of dict returned by server representing
                             locks in progress.

        Returns:
            rpws.models.IPLockInfo
        """
        locks_list = []

        # check to make sure ip_lock_list is not None
        if ip_lock_list:
            # for each lock in progress dict
            for ip_lock in ip_lock_list:

                # extract and create timestamp obj
                ts = models.DateEntry.\
                    fromrsdatestring(ip_lock[api.NODE_LIP_TIMESTAMP_KEY])

                # extract and create timespan obj
                tspan = models.TimeSpanEntry.\
                    fromrstimespanstring(ip_lock[api.NODE_LIP_AGE_KEY])

                # extract and create lock options and type
                lop = models.LockOptions(ip_lock[api.NODE_LIP_LOCKOPTIONS_KEY])
                lt = models.LockType(ip_lock[api.NODE_LIP_LOCKTYPE_KEY])

                # extract and create in-progress lock info obj
                locks_list.append(
                    models.IPLockInfo(
                        age=tspan,
                        lock_options=lop,
                        lock_type=lt,
                        model_path=ip_lock[api.NODE_LIP_MODELPATH_KEY],
                        timestamp=ts,
                        username=ip_lock[api.NODE_LIP_USERNAME_KEY]))

        return locks_list

    def _getfiles(self, nodepath, contents_dict):
        """Extract and return the list of all files under provided path.

        Args:
            nodepath (str): Path to an entry on the server.
            contents_dict (dict): data dict from server

        Returns:
            list of rpws.models.FileInfo
        """
        return [models.FileInfo(
            path=op.join(nodepath if nodepath else self.path,
                         x[api.NODE_FILES_NAME_KEY]),
            name=x[api.NODE_FILES_NAME_KEY],
            size=x[api.NODE_FILES_SIZE_KEY],
            is_text=x[api.NODE_FILES_ISTXT_KEY])
            for x in contents_dict.get(api.NODE_FILES_KEY, [])]

    def _getfolders(self, nodepath, contents_dict):
        """Extract and return the list of subfolders.

        Args:
            nodepath (str): Path to an entry on the server.
            contents_dict (dict): data dict from server

        Returns:
            list of rpws.models.FolderInfo
        """
        folder_infos = []

        for fdict in contents_dict.get(api.NODE_FOLDERS_KEY, []):
            # get in-progress lock objs
            ip_locks = self._getlocks(
                fdict[api.NODE_FOLDERS_LOCKINPROGRESS_KEY])
            # make lock state obj
            lock_state = \
                models.LockState(fdict[api.NODE_FOLDERS_LOCKSTATE_KEY])
            # create folder info obj
            finfo = models.FolderInfo(
                path=op.join(nodepath if nodepath else self.path,
                             fdict[api.NODE_FOLDERS_NAME_KEY]),
                name=fdict[api.NODE_FOLDERS_NAME_KEY],
                size=fdict[api.NODE_FOLDERS_SIZE_KEY],
                has_contents=fdict[api.NODE_FOLDERS_HASCONTENTS_KEY],
                lock_context=fdict[api.NODE_FOLDERS_LOCKCONTEXT_KEY],
                lock_state=lock_state,
                locks_inprogress=ip_locks)

            folder_infos.append(finfo)

        return folder_infos

    def _getmodels(self, nodepath, contents_dict):
        """Extract and return the list of models in source.

        Args:
            nodepath (str): Path to an entry on the server.
            contents_dict (dict): data dict from server

        Returns:
            list of rpws.models.ModelInfo
        """
        model_infos = []
        for mdict in contents_dict.get(api.NODE_MODELS_KEY, []):
            # get in-progress lock objs
            ip_locks = \
                self._getlocks(mdict[api.NODE_MODELS_LOCKINPROGRESS_KEY])
            # make lock state obj
            lock_state = models.LockState(mdict[api.NODE_MODELS_LOCKSTATE_KEY])
            # create model info obj
            minfo = models.ModelInfo(
                path=op.join(nodepath if nodepath else self.path,
                             mdict[api.NODE_MODELS_NAME_KEY]),
                name=mdict[api.NODE_MODELS_NAME_KEY],
                size=mdict[api.NODE_MODELS_SIZE_KEY],
                support_size=mdict[api.NODE_MODELS_SUPPORTSIZE_KEY],
                product_version=mdict[api.NODE_MODELS_PRODUCTVERSION_KEY],
                lock_context=mdict[api.NODE_MODELS_LOCKCONTEXT_KEY],
                lock_state=lock_state,
                locks_inprogress=ip_locks)

            model_infos.append(minfo)

        return model_infos

    @property
    def path(self):
        """Root path of server.

        Returns:
            str: Root path
        """
        return op.sep

    def getinfo(self):
        """Return server properties.

        API command:
            /serverproperties

        Returns:
            rpws.models.ServerInfo

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> sinfo = rserver.getinfo()
        """
        # get properties dict from server on root
        props_dict = self._get(api.REQ_CMD_SERVERPROP, rootcmd=True)

        # server roles
        sroles = [models.ServerRole(x)
                  for x in props_dict[api.SERVER_ROLES_KEY]]

        # make the server info obj
        return models.ServerInfo(
            name=self.name,
            version=self.version,
            machine_name=props_dict[api.SERVER_MACHINENAME_KEY],
            roles=sroles,
            access_level_types=props_dict[api.SERVER_ACCESSLEVEL_KEY],
            max_path_length=props_dict[api.SERVER_MAXPATHLENGTH_KEY],
            max_name_length=props_dict[api.SERVER_MAXNAMELENGTH_KEY],
            servers=props_dict[api.SERVER_SERVERS_KEY])

    def getdriveinfo(self):
        """Return server drive information.

        API command:
            /contents

        API keys:
            DriveFreeSpace and DriveSpace

        Returns:
            rpws.models.ServerDriveInfo

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> dinfo = rserver.getdriveinfo()
            >>> print(dinfo.drive_space)
        """
        return self._getserverdriveinfo(self._get(api.REQ_CMD_CONTENTS))

    def scandir(self, nodepath=None):
        """Return files, folders, and models from root or provided path.

        API command:
            /contents

        Args:
            nodepath (str, optional): Path to an entry on the server.
                                      Root if not provided.

        Returns:
            rpws.models.EntryContents

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> for entry in rserver.scandir('/example/path'):
            ...     print(entry.path)
        """
        # get the entry contents (root if nodepath is none
        contents_dict = self._get(api.REQ_CMD_CONTENTS, nodepath)

        # get drive info
        sdriveinfo = self._getserverdriveinfo(contents_dict)

        # get the files, folders, and models
        node_files = self._getfiles(nodepath, contents_dict)
        node_folders = self._getfolders(nodepath, contents_dict)
        node_models = self._getmodels(nodepath, contents_dict)

        lock_ctx = contents_dict[api.NODE_LOCK_CTX_KEY]
        lock_state = models.LockState(contents_dict[api.NODE_LOCK_STATE_KEY])
        ip_locks = self._getlocks(contents_dict[api.NODE_LOCKS_INPROGRESS_KEY])

        return models.EntryContents(
            path=nodepath,
            drive_space=sdriveinfo.drive_space,
            drive_freespace=sdriveinfo.drive_freespace,
            files=node_files,
            folders=node_folders,
            lock_context=lock_ctx,
            lock_state=lock_state,
            locks_inprogress=ip_locks,
            models=node_models)

    def listfiles(self, nodepath=None):
        """Return files from root or provided path.

        API command:
            /contents

        API key:
            Files

        Args:
            nodepath (str, optional): Path to an entry on the server.
                                      Root if not provided.

        Returns:
            list of rpws.models.FileInfo

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> for file in rserver.listfiles('/example/path'):
            ...     print(file.path)
        """
        return self._getfiles(nodepath,
                              self._get(api.REQ_CMD_CONTENTS, nodepath))

    def listfolders(self, nodepath=None):
        """Return folders from root or provided path.

        API command:
            /contents

        API key:
            Folders

        Args:
            nodepath (str, optional): Path to an entry on the server.
                                      Root if not provided.

        Returns:
            list of rpws.models.FolderInfo

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> for folder in rserver.listfolders('/example/path'):
            ...     print(folder.path)
        """
        return self._getfolders(nodepath,
                                self._get(api.REQ_CMD_CONTENTS, nodepath))

    def listmodels(self, nodepath=None):
        """Return models from root or provided path.

        API command:
            /contents

        API key:
            Models

        Args:
            nodepath (str, optional): Path to an entry on the server.
                                      Root if not provided.

        Returns:
            list of rpws.models.ModelInfo

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> for model in rserver.listmodels('/example/path'):
            ...     print(model.path)
        """
        return self._getmodels(nodepath,
                               self._get(api.REQ_CMD_CONTENTS, nodepath))

    def getfolderinfo(self, nodepath):
        """Return directory info for provided path.

        API command:
            /directoryinfo

        Args:
            nodepath (str): Path to an entry on the server.

        Returns:
            rpws.models.EntryDirInfo

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> for folder in rserver.listfolders('/example/path'):
            ...     finfo = rserver.getfolderinfo(folder.path)
            ...     print(finfo.date_created)
        """
        if nodepath:
            # directory info from the entry
            ddict = self._get(api.REQ_CMD_DIRINFO, nodepath)

            # in-progress locks
            ip_locks = self._getlocks(
                ddict[api.NODE_DIRINFO_LOCKSINPROGRESS_KEY])

            # make lock state
            lock_state = \
                models.LockState(ddict[api.NODE_DIRINFO_LOCKSTATE_KEY])

            # make time stamps
            date_created = models.DateEntry.\
                fromrsdatestring(ddict[api.NODE_DIRINFO_DATECREATED_KEY])
            date_modified = models.DateEntry.\
                fromrsdatestring(ddict[api.NODE_DIRINFO_DATEMODIFIED_KEY])

            # make the directory info obj
            return models.EntryDirInfo(
                path=nodepath,
                name=op.basename(nodepath),
                size=ddict[api.NODE_DIRINFO_SIZE_KEY],
                date_created=date_created,
                date_modified=date_modified,
                exists=ddict[api.NODE_DIRINFO_EXISTS_KEY],
                folder_count=ddict[api.NODE_DIRINFO_FOLDERCOUNT_KEY],
                is_folder=ddict[api.NODE_DIRINFO_ISFOLDER_KEY],
                last_modified_by=ddict[api.NODE_DIRINFO_LASTMODIFIEDBY_KEY],
                lock_context=ddict[api.NODE_DIRINFO_LOCKCTX_KEY],
                lock_state=lock_state,
                model_count=ddict[api.NODE_DIRINFO_MODELCOUNT_KEY],
                model_size=ddict[api.NODE_DIRINFO_MODELSIZE_KEY],
                locks_inprogress=ip_locks)

    def getmodelinfo(self, nodepath):
        """Return model info from provided model path.

        API command:
            /modelinfo

        Args:
            nodepath (str): Path to a model on the server.

        Returns:
            rpws.models.ModelInfoEx

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> for model in rserver.listmodels('/example/path'):
            ...     minfo = rserver.getmodelinfo(model.path)
            ...     print(minfo.size)
        """
        if nodepath:
            # model info from the entry
            mdict = self._get(api.REQ_CMD_MODELINFO, nodepath)

            # make time stamps
            dc = models.DateEntry.\
                fromrsdatestring(mdict[api.NODE_MODELINFO_DATECREATED_KEY])
            dm = models.DateEntry.\
                fromrsdatestring(mdict[api.NODE_MODELINFO_DATEMODIFIED_KEY])

            # make the model info obj
            return models.ModelInfoEx(
                path=nodepath,
                name=op.basename(nodepath),
                size=mdict[api.NODE_MODELINFO_MODELSIZE_KEY],
                guid=mdict[api.NODE_MODELINFO_MODELGUID_KEY],
                date_created=dc,
                date_modified=dm,
                last_modified_by=mdict[api.NODE_MODELINFO_LASTMODIFIEDBY_KEY],
                support_size=mdict[api.NODE_MODELINFO_SUPPORTSIZE_KEY])

    def getmodelhistory(self, nodepath):
        """Return model info from provided model path.

        API command:
            /history

        Args:
            nodepath (str): Path to a model on the server.

        Returns:
            rpws.models.MHistoryInfo

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> for model in rserver.listmodels('/example/path'):
            ...     mhist = rserver.getmodelhistory(model.path)
            ...     for hist in mhist.items:
            ...        print(hist.comment, hist.user)
        """
        # get history data from server
        mhist_dict = self._get(api.REQ_CMD_MHISTORY, nodepath)

        hist_items = []

        for hitem_dict in mhist_dict[api.MHISTORY_ITEMS_KEY]:
            # make time stamp
            mhist_date = models.DateEntry.\
                fromrsdatestring(hitem_dict[api.MHISTORY_DATE_KEY])

            # make model history item info
            mhist = models.MHistoryItemInfo(
                id=hitem_dict[api.MHISTORY_VERSION_KEY],
                comment=hitem_dict[api.MHISTORYITEM_COMMENT_KEY],
                date=mhist_date,
                model_size=hitem_dict[api.MHISTORY_MODELSIZE_KEY],
                overwrittenby=hitem_dict[api.MHISTORY_OVERWRITE_KEY],
                support_size=hitem_dict[api.MHISTORY_SUPPORTSIZE_KEY],
                user=hitem_dict[api.MHISTORY_USER_KEY])

            hist_items.append(mhist)

        # make model history info obj
        return models.MHistoryInfo(path=mhist_dict[api.MHISTORY_PATH_KEY],
                                   items=hist_items)

    def getprojectinfo(self, nodepath):
        """Return project info from provided model path.

        API command:
            /projectinfo

        Args:
            nodepath (str): Path to an entry on the server.

        Returns:
            rpws.models.ProjectInfo

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> for model in rserver.listmodels('/example/path'):
            ...     pinfo = rserver.getprojectinfo(model.path)
            ...     for pparam in pinfo.paramters:
            ...        print(pparam.name, pparam.value)
        """
        param_list = []

        if nodepath:
            # get all parameter categories from server for this model
            param_cats = self._get(api.REQ_CMD_PROJINFO, nodepath)

            for cat in param_cats:
                # for each category create parameter obj for its parameters
                catname = cat[api.PARAM_CATNAME_KEY]
                cat.pop(api.PARAM_CATNAME_KEY)

                for pname, param in cat.items():
                    # get the type string for the property
                    # and setup param type obj
                    ptypestr = param.get(api.PARAM_TYPE_KEY, '').lower()
                    if ptypestr:
                        ptype = models.ParamType(ptypestr)
                    else:
                        ptype = models.ParamType.Unknown

                    # get the datatype string for the property
                    # and setup param data type obj
                    pdatatypestr = param.get(api.PARAM_DTYPE_KEY, '').lower()
                    if pdatatypestr:
                        pdatatype = models.ParamDataType(pdatatypestr)
                    else:
                        pdatatype = models.ParamDataType.Unknown

                    # make the project parameter obj
                    pparam = models.ProjParameter(
                        name=param.get(api.PARAM_NAME_KEY, ''),
                        value=param.get(api.PARAM_VALUE_KEY, ''),
                        id=param.get(api.PARAM_ID_KEY, ''),
                        category=catname,
                        type=ptype,
                        datatype=pdatatype)

                    param_list.append(pparam)

        return models.ProjectInfo(param_list)

    def lock(self, nodepath):
        """Lock model.

        Args:
            nodepath (str): Path to a model on the server.

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> for model in rserver.listmodels('/example/path'):
            ...     rserver.lock(model.path)
        """
        return self._put(api.REQ_CMD_LOCK, nodepath)

    def cancellock(self, nodepath):
        """Cancel any in-progress locks on model.

        Args:
            nodepath (str): Path to a model on the server.

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> for model in rserver.listmodels('/example/path'):
            ...     rserver.cancellock(model.path)
        """
        return self._delete(api.REQ_CMD_CANCELLOCK, nodepath)

    def unlock(self, nodepath):
        """Unlock model.

        Args:
            nodepath (str): Path to a model on the server.

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> for model in rserver.listmodels('/example/path'):
            ...     rserver.unlock(model.path)
        """
        return self._delete(api.REQ_CMD_UNLOCK, nodepath)

    def getdescendentlocks(self, nodepath):
        """Return the decendent locks info.

        API command:
            /descendent/locks

        Args:
            nodepath (str): Path to a dirctory on the server.

        Returns:
            rpws.models.ChildrenLockInfo

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> for folder in rserver.listfolders('/example/path'):
            ...     clockinfo = rserver.getdescendentlocks(folder.path)
            ...     for locked_model_path in clockinfo.items:
            ...         print(locked_model_path)
        """
        # get decendent lock data
        chlocks_dict = self._get(api.REQ_CMD_CHILDNLOCKS, nodepath)
        # get the locked children list
        chlocks = chlocks_dict[api.CHILDLOCKS_ITEMS_KEY]
        if chlocks:
            # corrent the paths so they're from root
            locked_childs = [self._root_path(x) for x in chlocks]
        else:
            locked_childs = []

        # make the children lock info obj
        return models.ChildrenLockInfo(
            path=nodepath,
            items=locked_childs,
            lock_context=chlocks_dict[api.CHILDLOCKS_LOCKCTX])

    def deletedescendentlocks(self, nodepath):
        """Delete the decendent locks.

        API command:
            /descendent/locks

        Args:
            nodepath (str): Path to a dirctory on the server.

        Returns:
            list of str for list of entries with failed locks

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> for folder in rserver.listfolders('/example/path'):
            ...     rserver.deletedescendentlocks(folder.path)
        """
        # get decendent lock data
        chlocks_dict = self._delete(api.REQ_CMD_CHILDNLOCKS, nodepath)
        # get the list of failed locks
        failedchlocks = chlocks_dict[api.CHILDLOCKS_DELFAILEDITEMS_KEY]
        if failedchlocks:
            # corrent the paths so they're from root
            return [self._root_path(x) for x in failedchlocks]
        else:
            return []

    def mkdir(self, nodepath):
        """Create a new directory.

        Args:
            nodepath (str): Path to a dirctory on the server.

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> rserver.mkdir('/example/path')
        """
        return self._put(api.REQ_CMD_MKDIR, nodepath)

    def rename(self, nodepath, new_nodename):
        """Rename a file, folder, or model.

        Args:
            nodepath (str): Path to a file, folder, or model on the server.
            new_nodename (str): New name for file, folder, or model

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> rserver.rename('/example/path', '/example/newpath')
        """
        return self._delete(api.REQ_CMD_RENAME.format(new_name=new_nodename),
                            nodepath)

    def rmdir(self, nodepath):
        """Delete a file, folder, or model.

        Args:
            nodepath (str): Path to a file, folder, or model on the server.

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> rserver.rmdir('/example/path')
        """
        return self._delete(api.REQ_CMD_DELETE, nodepath)

    def delete(self, nodepath):
        """Delete a file, folder, or model.

        Args:
            nodepath (str): Path to a file, folder, or model on the server.

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> rserver.delete('/example/path/model.rvt')
        """
        return self._delete(api.REQ_CMD_DELETE, nodepath)

    def copy(self, nodepath, new_nodepath, overwrite=False):
        """Copy a file, folder, or model to new location.

        Args:
            nodepath (str): Path to a file, folder, or model on the server.
            new_nodepath (str): Full path to new location and name.
            overwrite (bool): True to overwrite any existing entries.

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> rserver.copy('/example/model.rvt', '/example/newmodel.rvt')
        """
        # get api path for the new location
        new_apipath = self._api_path(new_nodepath)
        return self._post(api.REQ_CMD_COPY.format(
            dest_path=new_apipath,
            replace_exist=overwrite), nodepath)

    def move(self, nodepath, new_nodepath, overwrite=False):
        """Move a file, folder, or model to new location.

        Args:
            nodepath (str): Path to a file, folder, or model on the server.
            new_nodepath (str): Full path to new location and name.
            overwrite (bool): True to overwrite any existing entries.

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> rserver.move('/example/model.rvt', '/example/newmodel.rvt')
        """
        # get api path for the new location
        new_apipath = self._api_path(new_nodepath)
        return self._post(api.REQ_CMD_MOVE.format(dest_path=new_apipath,
                                                  replace_exist=overwrite),
                          nodepath)

    def walk(self, top=None, topdown=True, digmodels=False):
        r"""Walk the provided path or root.

        Yields a 4-tuple of parent directory, folders, files, and models

        Args:
            top (str, optional): Parent directory. Root if not provided.
            topdown (bool): True to start from top and walk down
            digmodels (bool): True to list entries under a model folder
                              Revit models on Revit Server are actually folders
                              with files, and other subfolders.

        Returns:
            tuple: (parent, folders, files, models)

        Example:
            >>> rserver = RevitServer('server01', '2017')
            >>> for parent, folders, files, models in rserver.walk():
            ...     print(parent)
            ...     for fd in folders:
            ...         print('\t@d {}'.format(fd.path))
            ...     for f in files:
            ...         print('\t@f {}'.format(f.path))
            ...     for m in models:
            ...         print('\t@m {}'.format(m.path))
        """
        if not top:
            top = self.path

        entry_info = self.scandir(top)

        if topdown:
            # Yield before recursion if going top down
            yield top, entry_info.folders, entry_info.files, entry_info.models

        # Recurse into sub-directories
        for finfo in entry_info.folders:
            for x in self.walk(top=finfo.path, topdown=topdown):
                yield x

        # Recurse into sub-directories inside models
        if digmodels:
            for minfo in entry_info.models:
                for x in self.walk(top=minfo.path,
                                   topdown=topdown,
                                   digmodels=digmodels):
                    yield x
        if not topdown:
            # Yield before recursion if going top down
            yield top, entry_info.folders, entry_info.files, entry_info.models
