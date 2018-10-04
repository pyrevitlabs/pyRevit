"""Utility fuctions to support smart modules."""

import types


def copy_func(func, func_name, doc_string=None, arg_list=None):
    """Copy a function object to create a new function.

    This is used inside smart modules that auto-generate functions based on
    context.

    Args:
        func (object): python source function object
        func_name (str): new function name
        doc_string (str): new function docstring
        arg_list (list): list of default values for function arguments

    Returns:
        object: new python function objects
    """
    new_func = types.FunctionType(func.func_code, func.func_globals,
                                  func_name, tuple(arg_list), func.func_closure)
    new_func.__doc__ = doc_string
    return new_func
