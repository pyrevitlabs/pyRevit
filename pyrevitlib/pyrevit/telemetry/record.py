"""Provides base class for telemetry records."""
from pyrevit import EXEC_PARAMS
from pyrevit.compat import safe_strtype



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
        # if all is okay lets add the key:value to the return dict
        EXEC_PARAMS.result_dict.Add(key, safe_strtype(value))