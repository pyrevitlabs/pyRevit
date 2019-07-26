"""Provides base class for telemetry records."""

import datetime

from pyrevit import EXEC_PARAMS
from pyrevit.compat import safe_strtype
from pyrevit.coreutils.logger import get_logger


#pylint: disable=W0703,C0302,C0103
mlogger = get_logger(__name__)


# result dictionary that maps human-readable names to resultcodes
RESULT_DICT = {0: 'Succeeded',
               1: 'SysExited', 2: 'ExecutionException', 3: 'CompileException',
               9: 'UnknownException'}

# format for converting time stamps
# this is used for sorting records by date:time
TIMESTAMP_FORMAT = '%Y/%m/%d %H:%M:%S:%f'


class CommandCustomResults(object):
    """
    This class provides an interface wrapper around the EXEC_PARAMS.result_dict
    dictionary that is provided by the ScriptExecutor C# object.
    ScriptExecutor provides this results dictionary to all scripts, and scripts
    can add key:value pairs to the dictionary. But since the provided
    dictionary is a C# dictionary, this class provides a very easy
    to use wrapper around it.

    Example:
        >>> CommandCustomResults().returnparam = 'some return value'

    """

    # list of standard/default telemetry record params provided
    # by the c-sharp logger scripts should not use these names
    RESERVED_NAMES = ['time', 'username', 'revit', 'revitbuild', 'sessionid',
                      'pyrevit', 'debug', 'config', 'commandname',
                      'result', 'source']

    def __getattr__(self, key):
        # return value of the given key,
        # let it raise exception if the value is not there
        return safe_strtype(EXEC_PARAMS.result_dict[key])

    def __setattr__(self, key, value):
        if key in CommandCustomResults.RESERVED_NAMES:
            # making sure the script is not using a reserved name
            mlogger.error('%s is a standard log param. '
                          'Can not override this value.', key)
        else:
            # if all is okay lets add the key:value to the return dict
            EXEC_PARAMS.result_dict.Add(key, safe_strtype(value))


class TelemetryRecord:
    r"""
    Telemetry record object. This is created by ``pyrevit.telemetry.db``
    module when reading records.

    Attributes:
        date (str): Date of telemetry entry
                    e.g. '2017/03/28'
        time (str): Time of telemetry entry
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
        config (bool): Was command run while holding down the SHIFT key?
        commandname (str): Name of the executed command
                           e.g. 'Telemetry Data'
        commandbundle (str): Bundle name of the executed command
                             e.g. 'Telemetry Data.pushbutton'
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
        self.debug = self.config = False
        self.commandname = self.commandbundle = self.commandextension = ''
        self.resultcode = 0
        self.commandresults = {}
        self.scriptpath = ''
        self._logfilename = ''

    def __repr__(self):
        return '<TelemetryRecord {}>'.format(self.commandname)

    def __eq__(self, other):
        # FIXME: this won't work since the dictionaries are not ordered
        # compares hash of the internal dictionaries for comparison
        return hash(safe_strtype(self.__dict__)) \
            == hash(safe_strtype(other.__dict__))

    def __hash__(self):
        return hash(safe_strtype(self.__dict__))

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
        The file path will be setup by the ``pyrevit.telemetry.db`` module
        when parsing the log records.

        Returns:
            str: Full file path of the telemetry file containing this record
        """

        return self._logfilename

    @logfilename.setter
    def logfilename(self, logfile_path):
        """Sets the log file name that this record has been saved to.
        The file path will be set by the ``pyrevit.telemetry.db`` module
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
        rec_string = safe_strtype(self._src_dict)
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
            if search_term in safe_strtype(value).lower():
                return True

    def update(self, src_dict):
        """Updates all parameters in this record object based on the
        given src_dict. This is the promary method for the
        ``pyrevit.telemetry.db`` module to create the records from
        a dictionary return by the record file reader.

        Args:
            src_dict (dict): Source dictionary containing values
                             for record parameters
        """

        self.__dict__.update(src_dict)
        self._src_dict = src_dict
