""" Custom RPW exceptions """  #

from rpw.utils.logger import logger

class RpwException(Exception):
    """ Revit Python Wrapper Base Exception """


class RpwTypeError(TypeError):
    """ Revit Python Wrapper Base Exception """
    def __init__(self, type_expected, type_received=None):
        type_received = type_received or 'not reported'
        msg = 'expected [{}], got [{}]'.format(type_expected, type_received)
        super(RpwTypeError, self).__init__(msg)


class RpwParameterNotFound(RpwException, KeyError):
    """ Revit Python Wrapper Parameter Error """
    def __init__(self, element, param_name):
        msg = 'parameter not found [element:{}]:[param_name:{}]'.format(element, param_name)
        super(RpwParameterNotFound, self).__init__(msg)


class RpwWrongStorageType(RpwException, TypeError):
    """ Wrong Storage Type """
    def __init__(self, storage_type, value):
        msg = 'Wrong Storage Type: [{}]:[{}:{}]'.format(storage_type,
                                                        type(value), value)
        super(RpwWrongStorageType, self).__init__(msg)


class RpwCoerceError(RpwException, ValueError):
    """ Coerce Error """
    def __init__(self, value, target_type):
        msg = 'Could not cast value:{} to target_type:{}'.format(value, target_type)
        super(RpwCoerceError, self).__init__(msg)
