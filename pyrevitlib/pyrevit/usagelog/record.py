"""Provides base class for usage records."""

import datetime

from pyrevit import EXEC_PARAMS
from pyrevit.coreutils.logger import get_logger


logger = get_logger(__name__)


# result dictionary that maps human-readable names to resultcodes
RESULT_DICT = {0: 'Succeeded',
               1: 'SysExited', 2: 'ExecutionException', 3: 'CompileException',
               9: 'UnknownException'}

# format for converting time stamps
# this is used for sorting records by date:time
TIMESTAMP_FORMAT = '%Y/%m/%d %H:%M:%S:%f'


class _CommandCustomResults(object):
    """
    This class provides an interface wrapper around the EXEC_PARAMS.result_dict
    dictionary that is provided by the ScriptExecutor C# object.
    ScriptExecutor provides this results dictionary to all scripts, and scripts
    can add key:value pairs to the dictionary. But since the provided
    dictionary is a C# dictionary, this class provides a very easy
    to use wrapper around it.

    Example:
        >>> _CommandCustomResults().returnparam = 'some return value'

    """

    # list of standard/default usage log record params provided
    # by the c-sharp logger scripts should not use these names
    RESERVED_NAMES = ['time', 'username', 'revit', 'revitbuild', 'sessionid',
                      'pyrevit', 'debug', 'alternate', 'commandname',
                      'result', 'source']

    def __getattr__(self, key):
        # return value of the given key,
        # let it raise exception if the value is not there
        return unicode(EXEC_PARAMS.result_dict[key])

    def __setattr__(self, key, value):
        if key in _CommandCustomResults.RESERVED_NAMES:
            # making sure the script is not using a reserved name
            logger.error('{} is a standard log param. '
                         'Can not override this value.'.format(key))
        else:
            # if all is okay lets add the key:value to the return dict
            EXEC_PARAMS.result_dict.Add(key, unicode(value))


class UsageRecord:
    """
    Usage record object. This is created by ``pyrevit.usagelog.db``
    module when reading records.

    Attributes:
        date (str): Date of usage log entry
                    e.g. '2017/03/28'
        time (str): Time of usage log entry
                    e.g. '18:35:22:1235'
        username (str): Usename if user that used this command
                        e.g. 'eirannejad'
        revit (str): Year of Revit used to run the command
                     e.g. '2017'
        revitbuild (str): Build of Revit used to run the command
                          e.g. '20160720_1515(x64)'
        sessionid (str): pyRevit session id that his command was executed in
                         e.g. 'f5351ce1-13fc-11e7-97e9-7323ba0b5bf7'
        pyrevit (str): pyRevit version that his command was executed by
                       e.g. '4.2:dcf4090'
        debug (bool): Was command run in debug mode?
        alternate (bool): Was command run while holding down the SHIFT key?
        commandname (str): Name of the executed command
                           e.g. 'Usage Records'
        commandbundle (str): Bundle name of the executed command
                             e.g. 'Usage Records.pushbutton'
        commandextension (str): pyRevit extension name of the executed command
                                e.g. 'pyRevitDevTools'
        resultcode (int): Result code return from the executed command e.g. 3
        commandresults (dict): Custom data returned from command
                               e.g. {'param1': 'value'}
        scriptpath (str): Path of the executed command
                          e.g. 'C:\...\SomeButton.pushbutton\script.py'
    """

    def __init__(self):
        # setup all params
        self._src_dict = None
        self.date = self.time = self.username = ''
        self.revit = self.revitbuild = self.sessionid = self.pyrevit = ''
        self.debug = self.alternate = False
        self.commandname = self.commandbundle = self.commandextension = ''
        self.resultcode = 0
        self.commandresults = {}
        self.scriptpath = ''
        self._logfilename = ''

    def __repr__(self):
        return '<UsageRecord {}>'.format(self.commandname)

    def __eq__(self, other):
        # fixme: this won't work since the dictionaries are not ordered
        # compares hash of the internal dictionaries for comparison
        return hash(str(self.__dict__)) == hash(str(other.__dict__))

    def __hash__(self):
        return hash(str(self.__dict__))

    def __lt__(self, other):
        # less-than operator overload for object comparison
        # compares objects based on date:time
        # whichever that got logged earlier (is older) is less
        mydate = datetime.datetime.strptime('{} {}'
                                            .format(self.date, self.time),
                                            TIMESTAMP_FORMAT)
        otherdate = datetime.datetime.strptime('{} {}'
                                               .format(other.date, other.time),
                                               TIMESTAMP_FORMAT)
        return mydate < otherdate

    @property
    def logfilename(self):
        """Returns the log file name that this record has been saved to.
        The file path will be setup by the ``pyrevit.usagelog.db`` module
        when parsing the log records.

        Returns:
            str: Full file path of the usage log file containing this record
        """

        return self._logfilename

    @logfilename.setter
    def logfilename(self, logfile_path):
        """Sets the log file name that this record has been saved to.
        The file path will be set by the ``pyrevit.usagelog.db`` module
        when parsing the log records.
        """

        self._logfilename = logfile_path

    @property
    def result(self):
        """Command execution result in human readable format
        (e.g. CompileException)

        Returns:
            str: Command execution result in human readable format
                 (e.g. CompileException)
        """

        return RESULT_DICT[self.resultcode]

    @property
    def original_record(self):
        """Returns original dictionary used to create/update this record.

        Returns:
            dict: original dictionary used to create/update this record.
        """
        rec_string = str(self._src_dict)
        rec_string = rec_string \
            .replace('\'', '\"') \
            .replace('False', 'false') \
            .replace('True', 'true')
        return rec_string

    def has_term(self, search_term):
        """Checks all parameters for the search_term.

        Returns:
            bool: Returns True if search_term is found in any of the
                  parameter values
        """

        for value in self._src_dict.values():
            if search_term in unicode(value).lower():
                return True

    def update(self, src_dict):
        """Updates all parameters in this record object based on the
        given src_dict. This is the promary method for the
        ``pyrevit.usagelog.db`` module to create the records from
        a dictionary return by the record file reader.

        Args:
            src_dict (dict): Source dictionary containing values
                             for record parameters
        """

        self.__dict__.update(src_dict)
        self._src_dict = src_dict
