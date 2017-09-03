from collections import namedtuple
import datetime

import enum


class DateEntry(datetime.datetime):
    @classmethod
    def fromrsdatestring(cls, date_string):
        seconds_since_epoch = int(date_string[6:-2])/1000
        return cls.utcfromtimestamp(seconds_since_epoch)


class ServerRole(enum.Enum):
    Host = 0
    Accelerator = 1
    Admin = 2


class LockState(enum.Enum):
    Unlocked = 0
    Locked = 1
    LockedParent = 2
    LockedChild = 3
    BeingUnlocked = 4
    BeingLocked = 5


class ParamType(enum.Enum):
    System = 'system'
    Custom = 'custom'
    Shared = 'shared'
    Unknown = 'unknown'


class ParamDataType(enum.Enum):
    Length = 'length'
    Number = 'number'
    Material = 'material'
    Text = 'text'
    MultilineText = "multiline text"
    YesNo = 'yes/no'
    Unknown = 'unknown'


ServerInfo = namedtuple('ServerInfo', ['name',
                                       'version',
                                       'machine_name',
                                       'roles',
                                       'access_level_types',
                                       'max_path_length',
                                       'max_name_length',
                                       'servers'])


ServerDriveInfo = namedtuple('ServerDriveInfo', ['drive_space',
                                                 'drive_freespace'])


EntryInfo = namedtuple('EntryInfo', ['path',
                                     'drive_space',
                                     'drive_freespace',
                                     'files',
                                     'folders',
                                     'lock_context',
                                     'lock_state',
                                     'locks_inprogress',
                                     'models'])


FileInfo = namedtuple('FileInfo', ['path', 'name', 'size', 'is_text'])


FolderInfo = namedtuple('FolderInfo', ['path', 'name', 'size',
                                       'has_contents',
                                       'lock_context',
                                       'lock_state',
                                       'locks_inprogress'])


ModelInfo = namedtuple('ModelInfo', ['path', 'name', 'size',
                                     'support_size',
                                     'product_version',
                                     'lock_context',
                                     'lock_state',
                                     'locks_inprogress'])


InProgressLockInfo = namedtuple('InProgressLockInfo',
                                ['age',
                                 'lock_options',
                                 'lock_type',
                                 'model_path',
                                 'timestamp',
                                 'username'])


DirectoryInfo = namedtuple('DirectoryInfo', ['path', 'name', 'size',
                                             'date_created',
                                             'date_modified',
                                             'exists',
                                             'folder_count',
                                             'is_folder',
                                             'last_modified_by',
                                             'lock_context',
                                             'lock_state',
                                             'model_count',
                                             'model_size',
                                             'locks_inprogress'])


ModelInfoEx = namedtuple('ModelInfoEx', ['path', 'name', 'size',
                                         'guid',
                                         'date_created',
                                         'date_modified',
                                         'last_modified_by',
                                         'support_size'])


ProjectInfo = namedtuple('ProjectInfo', ['parameters'])


ProjectParameter = namedtuple('ProjectParameter', ['name',
                                                   'value',
                                                   'id',
                                                   'category',
                                                   'type',
                                                   'datatype'])


ModelHistoryInfo = namedtuple('ModelHistoryInfo', ['path',
                                                   'items'])


ModelHistoryItemInfo = namedtuple('ModelHistoryItemInfo', ['id',
                                                           'comment',
                                                           'date',
                                                           'model_size',
                                                           'overwrittenby',
                                                           'support_size',
                                                           'user'])


ChildrenLockInfo = namedtuple('ChildrenLockInfo', ['path',
                                                   'items',
                                                   'lock_context'])
