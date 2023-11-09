"""Data structures for wrapping information returned by Revit server."""

import re
from collections import namedtuple
import datetime

import enum


ServerInfo = namedtuple('ServerInfo',
                        ['name',                   # type: str
                         'version',                # type: str
                         'machine_name',           # type: str
                         'roles',                  # type: list<ServerRole>
                         'access_level_types',     # type: list<str>
                         'max_path_length',        # type: int
                         'max_name_length',        # type: int
                         'servers',                # type: list<str>
                         ])
""" namedtuple for server properties

Attributes:
    name (str): Server name
    version (str): Revit Server version
    machine_name (str): Revit Server machine name
    roles (list<ServerRole>): List of server roles
    access_level_types (list<str>): List of access level types
    max_path_length (int): Maximum allowed length for server paths
    max_name_length (int): Maximum allowed length for server entry names
    servers (list<str>): List of neighbour servers
"""


class ServerRole(enum.Enum):
    """Enum representing various server role codes.

    Attributes:
        Host = 0
        Accelerator = 1
        Admin = 2
    """

    Host = 0
    Accelerator = 1
    Admin = 2


ServerDriveInfo = namedtuple('ServerDriveInfo',
                             ['drive_space',       # type: int
                              'drive_freespace',   # type: int
                              ])
""" namedtuple for server drive info

Attributes:
    drive_space (int): Total drive space in bytes
    drive_freespace (int): Free drive space in bytes
"""


EntryContents = namedtuple('EntryContents',
                           ['path',                # type: str
                            'drive_space',         # type: int
                            'drive_freespace',     # type: int
                            'files',               # type: list<FileInfo>
                            'folders',             # type: list<FolderInfo>
                            'lock_context',        # type: str
                            'lock_state',          # type: LockState
                            'locks_inprogress',    # type: list<IPLockInfo>
                            'models',              # type: list<ModelInfo>
                            ])
""" namedtuple for server entry contents
(Encapsulates result of /contents)

Attributes:
    path (str): Full path of this entry on server
    drive_space (int): Total server drive space in bytes
    drive_freespace (int): Free server drive space in bytes
    files (list<FileInfo>): List of all files under this entry
    folders (list<FolderInfo>): List of all folders under this entry
    lock_context (str): Lock context on this entry
    lock_state (LockState): Lock state on this entry
    locks_inprogress (list<IPLockInfo>): List of all in-progress locks
    models (list<ModelInfo>): List of all models under this entry
"""


EntryDirInfo = namedtuple('EntryDirInfo',
                          ['path',                # type: str
                           'name',                # type: str
                           'size',                # type: int
                           'date_created',        # type: DateEntry
                           'date_modified',       # type: DateEntry
                           'exists',              # type: bool
                           'folder_count',        # type: int
                           'is_folder',           # type: bool
                           'last_modified_by',    # type: str
                           'lock_context',        # type: str
                           'lock_state',          # type: LockState
                           'model_count',         # type: int
                           'model_size',          # type: int
                           'locks_inprogress',    # type: list<IPLockInfo>
                           ])
""" namedtuple for server entry directory info
(Encapsulates result of /directoryinfo)

Attributes:
    path (str): Full path of this entry on server
    name (str): Entry name including extension
    size (int): Entry size in bytes
    date_created (DateEntry): Date entry was created
    date_modified (DateEntry): Date entry was last modified
    exists (bool): True if entry exists
    folder_count (int): Number of sub folders
    is_folder (bool): True of this entry if a directory
    last_modified_by (str): Username of user who last modified the model
    lock_context (str): Lock context on this entry
    lock_state (LockState): Lock state on this entry
    model_count (int): Number of models under this entry
    model_size (int): If this entry is a model, size of model in bytes
    locks_inprogress (list<IPLockInfo>): List of all in-progress locks
"""


class LockState(enum.Enum):
    """Enum representing Revit Server lock states.

    Attributes:
        Unlocked = 0
        Locked = 1
        LockedParent = 2
        LockedChild = 3
        BeingUnlocked = 4
        BeingLocked = 5
    """

    Unlocked = 0
    Locked = 1
    LockedParent = 2
    LockedChild = 3
    BeingUnlocked = 4
    BeingLocked = 5


class LockOptions(enum.Enum):
    """Enum representing Revit Server lock options.

    Attributes:
        NotSet = 0
        Read = 1
        Write = 2
        NonExclusiveReadWrite = 128
        ReadAndNonExclusiveReadWrite = 129
        WriteAndNonExclusiveReadWrite = 130
        ReadWriteAndNonExclusiveReadWrite = 130
    """

    NotSet = 0
    Read = 1
    Write = 2
    NonExclusiveReadWrite = 128
    ReadAndNonExclusiveReadWrite = 129
    WriteAndNonExclusiveReadWrite = 130
    ReadWriteAndNonExclusiveReadWrite = 130


class LockType(enum.Enum):
    """Enum representing Revit Server lock type.

    Attributes:
        Data = 0
        Permission = 1
    """

    Data = 0
    Permissions = 1


FileInfo = namedtuple('FileInfo',
                      ['path',                     # type: str
                       'name',                     # type: str
                       'size',                     # type: int
                       'is_text',                  # type: bool
                       ])
""" namedtuple for info on a server file

Attributes:
    path (str): Full path of this file on server
    name (str): File name including extension
    size (int): File size in bytes
    is_text (bool): True if text file
"""


FolderInfo = namedtuple('FolderInfo',
                        ['path',                   # type: str
                         'name',                   # type: str
                         'size',                   # type: int
                         'has_contents',           # type: bool
                         'lock_context',           # type: str
                         'lock_state',             # type: LockState
                         'locks_inprogress',       # type: list<IPLockInfo>
                         ])
""" namedtuple for info on a server folder

Attributes:
    path (str): Full path of this folder on server
    name (str): File name including extension
    size (int): File size in bytes
    has_contents (bool): True if folder has contents
    lock_context (str): Lock context on this entry
    lock_state (LockState): Lock state on this entry
    locks_inprogress (list<IPLockInfo>): List of all in-progress locks
"""


ModelInfo = namedtuple('ModelInfo',
                       ['path',                    # type: str
                        'name',                    # type: str
                        'size',                    # type: int
                        'support_size',            # type: int
                        'product_version',         # type: int
                        'lock_context',            # type: str
                        'lock_state',              # type: LockState
                        'locks_inprogress',        # type: list<IPLockInfo>
                        ])
""" namedtuple for info on a server model

Attributes:
    path (str): Full path of this model on server
    name (str): File name including extension
    size (int): File size in bytes
    support_size (int): Size of all support files in bytes
    product_version (int): Revit version of this model
    lock_context (str): Lock context on this entry
    lock_state (LockState): Lock state on this entry
    locks_inprogress (list<IPLockInfo>): List of all in-progress locks
"""


ModelInfoEx = namedtuple('ModelInfoEx',
                         ['path',                  # type: str
                          'name',                  # type: str
                          'size',                  # type: int
                          'guid',                  # type: str
                          'date_created',          # type: DateEntry
                          'date_modified',         # type: DateEntry
                          'last_modified_by',      # type: str
                          'support_size',          # type: int
                          ])
""" namedtuple for extended info on a server model

Attributes:
    path (str): Full path of this model on server
    name (str): File name including extension
    size (int): File size in bytes
    guid (str): GUID of the model
    date_created (DateEntry): Date model was created
    date_modified (DateEntry): Date model was last modified
    last_modified_by (str): Username of user who last modified the model
    support_size (int): Size of all support files in bytes
"""


ProjectInfo = namedtuple('ProjectInfo',
                         ['parameters',            # type: list<ProjParameter>
                          ])
""" namedtuple for project info of a hosted model

Attributes:
    parameters (list<ProjParameter>): List of project parameters in this model
"""


ProjParameter = namedtuple('ProjParameter',
                           ['name',                # type: str
                            'value',               # type: str
                            'id',                  # type: str
                            'category',            # type: str
                            'type',                # type: ParamType
                            'datatype',            # type: ParamDataType
                            ])
""" namedtuple for info project parameters in a hosted model

Attributes:
    name (str): Parameter display name
    value (str): Parameter value
    id (str): Parameter unique id
    category (str): Parameter category name
    type (ParamType): Parameter Type
    datatype (ParamDataType): Parameter storage type
"""


class ParamType(enum.Enum):
    """Enum representing parameter types.

    Attributes:
        System = 'system'
        Custom = 'custom'
        Shared = 'shared'
        Unknown = 'unknown'
    """

    System = 'system'
    Custom = 'custom'
    Shared = 'shared'
    Unknown = 'unknown'


class ParamDataType(enum.Enum):
    """Enum representing parameter storage types.

    Attributes:
        Length = 'length'
        Number = 'number'
        Material = 'material'
        Text = 'text'
        MultilineText = "multiline text"
        YesNo = 'yes/no'
        Unknown = 'unknown'
    """

    Length = 'length'
    Number = 'number'
    Material = 'material'
    Text = 'text'
    MultilineText = "multiline text"
    YesNo = 'yes/no'
    Unknown = 'unknown'


MHistoryInfo = namedtuple('MHistoryInfo',
                          ['path',               # type: str
                           'items',              # type: list<MHistoryItemInfo>
                           ])
""" namedtuple for model history info

Attributes:
    path (str): Full path of the hosted model
    items (list<MHistoryItemInfo>): List of history items
"""


MHistoryItemInfo = namedtuple('MHistoryItemInfo',
                              ['id',               # type: str
                               'comment',          # type: str
                               'date',             # type: DateEntry
                               'model_size',       # type: int
                               'overwrittenby',    # type: str
                               'support_size',     # type: int
                               'user',             # type: str
                               ])
""" namedtuple for model history item info

Attributes:
    id (str): History item id
    comment (str): Comment recorded when syncing
    date (DateEntry): Date this history item was recorded
    size (int): File size in bytes
    overwrittenby (str): Id of history item overwriting this item
    support_size (int): Size of all support files in bytes
    user (str): Username recording the history item (by syncing model)
"""


IPLockInfo = namedtuple('IPLockInfo',
                        ['age',                    # type: TimeSpanEntry
                         'lock_options',           # type: LockOptions
                         'lock_type',              # type: LockType
                         'model_path',             # type: str
                         'timestamp',              # type: DateEntry
                         'username',               # type: str
                         ])
""" namedtuple for info on an in-progress entry lock

Attributes:
    age (str): Age of the lock
    lock_options (int): Lock options
    lock_type (int): Lock type
    model_path (str): Full path of the model being locked
    timestamp (DateEntry): Timestamp for when the lock was initiated
    username (str): Username who initiated this lock
"""


ChildrenLockInfo = namedtuple('ChildrenLockInfo',
                              ['path',             # type: str
                               'items',            # type: list<str>
                               'lock_context',     # type: str
                               ])
""" namedtuple for info locked children under an entry

Attributes:
    path (str): Full path of parent entry
    items (list<str>): List of paths of locked models under this entry
    lock_context (str): Lock context of parent entry
"""


class DateEntry(datetime.datetime):
    """Timestamp data type wrapping Revit Server string timestamps.

    Wraps Revit Server string timestamps in a typical python
    datetime.datetime subclass.

    Example:
        >>> ts = DateEntry.fromrsdatestring("/Date(1483465201000)/")
        DateEntry(2017, 1, 3, 17, 40, 1)
    """

    @classmethod
    def fromrsdatestring(cls, date_string):
        """Construct a class instance from Revit server timestamp.

        Args:
            date_string (str): Revit server timestamp string
        """
        seconds_since_epoch = int(date_string[6:-2])/1000
        return cls.utcfromtimestamp(seconds_since_epoch)


class TimeSpanEntry(datetime.timedelta):
    """Timespan data type wrapping Revit Server timespan.

    Wraps Revit Server string timespan in a typical python
    datetime.timedelta subclass

    Example:
        >>> ts = TimeSpanEntry.fromrstimespanstring("PT11M42.5154811S")
        TimeSpanEntry(0, 5856, 811000)
    """

    @classmethod
    def fromrstimespanstring(cls, timespan_string):
        """Construct a class instance from Revit server timespan.

        Args:
            timespan_string (str): Revit server timespan string
        """
        days = re.findall('(\d+)D', timespan_string)
        days = int(days[0]) if days else 0

        minutes = re.findall('(\d+)M', timespan_string)
        minutes = int(minutes[0]) if minutes else 0

        seconds = re.findall('(\d+)\.(\d+)S', timespan_string)
        seconds, millisecs = (int(seconds[0][0]), int(seconds[0][1])) \
            if seconds else (0, 0)

        return cls(days=days, minutes=minutes,
                   seconds=seconds, milliseconds=millisecs)
