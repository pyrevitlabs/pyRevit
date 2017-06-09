# basic exceptions
class RpwException(Exception):
    """ RevitPythonWrapper Base Exception """


class RpwTypeError(RpwException, TypeError):
    """ Wrong Type"""
    def __init__(self, type_expected, type_received):
        msg = 'expected {}, got {}'.format(type_expected, type_received)
        super(RpwTypeError, self).__init__(msg)


class RpwAttributeError(RpwException, AttributeError):
    """ Wrong Attribute"""

    def __init__(self, obj, attr_name):
        msg = 'attribute "{}" not found in: {}'.format(attr_name, obj)
        super(RpwAttributeError, self).__init__(msg)
