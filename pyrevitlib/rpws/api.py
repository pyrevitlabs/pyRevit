"""Revit Server API commands and dictionary keys."""

# http request header
REQ_HEADER_USERNAME = 'User-Name'
REQ_HEADER_MACHINE = 'User-Machine-Name'
REQ_HEADER_GUID = 'Operation-GUID'

# folder structure
DIVIDER = '|'

# commands
# ------------------------------------------------------------------------------
REQ_CMD_SERVERPROP = "/serverproperties"
# {
#     "AccessLevelTypes": list,
#     "MachineName": str,
#     "MaximumFolderPathLength": int,
#     "MaximumModelNameLength": int,
#     "ServerRoles": list,
#     "Servers": list
# }
SERVER_ACCESSLEVEL_KEY = "AccessLevelTypes"
SERVER_MACHINENAME_KEY = "MachineName"
SERVER_MAXPATHLENGTH_KEY = "MaximumFolderPathLength"
SERVER_MAXNAMELENGTH_KEY = "MaximumModelNameLength"
SERVER_ROLES_KEY = "ServerRoles"
SERVER_SERVERS_KEY = "Servers"

# ------------------------------------------------------------------------------
REQ_CMD_CONTENTS = "/contents"
# {
#     "Path": str,
#     "DriveFreeSpace": int,
#     "DriveSpace": int,
#     "Files": list,
#     "Folders": list,
#     "LockContext": str,
#     "LockState": int,
#     "ModelLocksInProgress": list,
#     "Models": list
# }
NODE_PATH_KEY = "Path"
NODE_DRIVE_FREESPACE_KEY = "DriveFreeSpace"
NODE_DRIVE_TOTALSPACE_KEY = "DriveSpace"
NODE_FILES_KEY = "Files"
NODE_FOLDERS_KEY = "Folders"
NODE_LOCK_CTX_KEY = "LockContext"
NODE_LOCK_STATE_KEY = "LockState"
NODE_LOCKS_INPROGRESS_KEY = "ModelLocksInProgress"
NODE_MODELS_KEY = "Models"

# "Files" key
# {
#     "IsText": bool,
#     "Name": str,
#     "Size": int
# }
NODE_FILES_ISTXT_KEY = "IsText"
NODE_FILES_NAME_KEY = "Name"
NODE_FILES_SIZE_KEY = "Size"

# "Folders" key
# {
#     "HasContents": bool,
#     "LockContext": str,
#     "LockState": int,
#     "ModelLocksInProgress": list,
#     "Name": str,
#     "Size": int
# }
NODE_FOLDERS_HASCONTENTS_KEY = "HasContents"
NODE_FOLDERS_LOCKCONTEXT_KEY = "LockContext"
NODE_FOLDERS_LOCKSTATE_KEY = "LockState"
NODE_FOLDERS_LOCKINPROGRESS_KEY = "ModelLocksInProgress"
NODE_FOLDERS_NAME_KEY = "Name"
NODE_FOLDERS_SIZE_KEY = "Size"

# "Models" key
# {
#     "LockContext": str,
#     "LockState": int,
#     "ModelLocksInProgress": list,
#     "ModelSize": int,
#     "Name": str,
#     "ProductVersion": int,
#     "SupportSize": int
# }
NODE_MODELS_LOCKCONTEXT_KEY = "LockContext"
NODE_MODELS_LOCKSTATE_KEY = "LockState"
NODE_MODELS_LOCKINPROGRESS_KEY = "ModelLocksInProgress"
NODE_MODELS_SIZE_KEY = "ModelSize"
NODE_MODELS_NAME_KEY = "Name"
NODE_MODELS_PRODUCTVERSION_KEY = "ProductVersion"
NODE_MODELS_SUPPORTSIZE_KEY = "SupportSize"


# ------------------------------------------------------------------------------
REQ_CMD_DIRINFO = "/directoryinfo"
# {
#     "Path": str,
#     "DateCreated": str, # "/Date(1483465123167)/"
#     "DateModified": str, # "/Date(1501619985043)/"
#     "Exists": bool,
#     "FolderCount": int,
#     "IsFolder": bool,
#     "LastModifiedBy": str,
#     "LockContext": str,
#     "LockState": int,
#     "ModelCount": int,
#     "ModelLocksInProgress": list,
#     "ModelSize": int,
#     "Size": int
# }
NODE_DIRINFO_PATH_KEY = "Path"
NODE_DIRINFO_DATECREATED_KEY = "DateCreated"
NODE_DIRINFO_DATEMODIFIED_KEY = "DateModified"
NODE_DIRINFO_EXISTS_KEY = "Exists"
NODE_DIRINFO_FOLDERCOUNT_KEY = "FolderCount"
NODE_DIRINFO_ISFOLDER_KEY = "IsFolder"
NODE_DIRINFO_LASTMODIFIEDBY_KEY = "LastModifiedBy"
NODE_DIRINFO_LOCKCTX_KEY = "LockContext"
NODE_DIRINFO_LOCKSTATE_KEY = "LockState"
NODE_DIRINFO_MODELCOUNT_KEY = "ModelCount"
NODE_DIRINFO_LOCKSINPROGRESS_KEY = "ModelLocksInProgress"
NODE_DIRINFO_MODELSIZE_KEY = "ModelSize"
NODE_DIRINFO_SIZE_KEY = "Size"


# ------------------------------------------------------------------------------
REQ_CMD_MODELINFO = "/modelinfo"
# {
#     "Path": str,
#     "DateCreated": str, #"/Date(1483465179783)/"
#     "DateModified": str, # "/Date(1503702490000)/"
#     "LastModifiedBy": str,
#     "ModelGUID": str, # "b04725c0-9369-4482-aecf-5ad900d4c1bb"
#     "ModelSize": int,
#     "SupportSize": int
# }
NODE_MODELINFO_PATH_KEY = "Path"
NODE_MODELINFO_DATECREATED_KEY = "DateCreated"
NODE_MODELINFO_DATEMODIFIED_KEY = "DateModified"
NODE_MODELINFO_LASTMODIFIEDBY_KEY = "LastModifiedBy"
NODE_MODELINFO_MODELGUID_KEY = "ModelGUID"
NODE_MODELINFO_MODELSIZE_KEY = "ModelSize"
NODE_MODELINFO_SUPPORTSIZE_KEY = "SupportSize"


# ------------------------------------------------------------------------------
REQ_CMD_PROJINFO = "/projectinfo"
# [
#     {
#         "A:title": "Text",
#         "<>": dict
#     }
# ]
PARAM_CATNAME_KEY = "A:title"

# Parameter dict keys
# {
#     "#text": "BLDG",
#     "@displayName": "Building Name",
#     "@id": "940f16f5-879a-4bf6-b722-b6a0043ffa9b",
#     "@type": "system",
#     "@typeOfParameter": "Text"
# }
PARAM_VALUE_KEY = "#text"
PARAM_NAME_KEY = "@displayName"
PARAM_ID_KEY = "@id"
PARAM_TYPE_KEY = "@type"
PARAM_DTYPE_KEY = "@typeOfParameter"

# ------------------------------------------------------------------------------
REQ_CMD_MHISTORY = "/history"
# {
#     "Path": str,
#     "Items": list
# }
MHISTORY_PATH_KEY = "Path"
MHISTORY_ITEMS_KEY = "Items"

# {
#     "Comment": str,
#     "Date": str, # "/Date(1483465201000)/"
#     "ModelSize": int,
#     "OverwrittenByHistoryNumber": int,
#     "SupportSize": int,
#     "User": str,
#     "VersionNumber": int
# }
MHISTORYITEM_COMMENT_KEY = "Comment"
MHISTORY_DATE_KEY = "Date"
MHISTORY_MODELSIZE_KEY = "ModelSize"
MHISTORY_OVERWRITE_KEY = "OverwrittenByHistoryNumber"
MHISTORY_SUPPORTSIZE_KEY = "SupportSize"
MHISTORY_USER_KEY = "User"
MHISTORY_VERSION_KEY = "VersionNumber"

# ------------------------------------------------------------------------------
# shared data types
# "ModelLocksInProgress" key
# {
#     "Age": str, # "PT29M32.1723042S"
#     "ModelLockOptions": int,
#     "ModelLockType": int,
#     "ModelPath": str,
#     "TimeStamp": str, # "/Date(1504130384000)/"
#     "UserName": str
# }
NODE_LIP_AGE_KEY = "Age"
NODE_LIP_LOCKOPTIONS_KEY = "ModelLockOptions"
NODE_LIP_LOCKTYPE_KEY = "ModelLockType"
NODE_LIP_MODELPATH_KEY = "ModelPath"
NODE_LIP_TIMESTAMP_KEY = "TimeStamp"
NODE_LIP_USERNAME_KEY = "UserName"


# ------------------------------------------------------------------------------
REQ_CMD_LOCK = "/lock"
# ------------------------------------------------------------------------------
REQ_CMD_CANCELLOCK = "/inProgressLock"
# ------------------------------------------------------------------------------
REQ_CMD_UNLOCK = "/lock?objectMustExist=true"
# ------------------------------------------------------------------------------
REQ_CMD_CHILDNLOCKS = "/descendent/locks"
# {
#     "Path": str,
#     "Items": list
#     "DescendentHasLockContext": bool
# }
CHILDLOCKS_PATH_KEY = "Path"
CHILDLOCKS_ITEMS_KEY = "Items"
CHILDLOCKS_LOCKCTX = "DescendentHasLockContext"

# {
#     "Path": str,
#     "FailedItems": list
# }
CHILDLOCKS_DELPATH_KEY = "Path"
CHILDLOCKS_DELFAILEDITEMS_KEY = "FailedItems"

# ------------------------------------------------------------------------------
REQ_CMD_MKDIR = ""
# ------------------------------------------------------------------------------
REQ_CMD_DELETE = "?newObjectName"
# ------------------------------------------------------------------------------
REQ_CMD_RENAME = "?newObjectName={new_name}"
# ------------------------------------------------------------------------------
REQ_CMD_COPY = "?destinationObjectPath={dest_path}"\
               "&pasteAction=Copy"\
               "&replaceExisting={replace_exist}"
# ------------------------------------------------------------------------------
REQ_CMD_MOVE = "?destinationObjectPath={dest_path}"\
               "&pasteAction=Move"\
               "&replaceExisting={replace_exist}"
