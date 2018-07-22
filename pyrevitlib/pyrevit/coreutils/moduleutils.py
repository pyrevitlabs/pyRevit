"""Utility fuctions to support smart modules."""

import types


def copy_func(f, func_name, doc_string=None, arg_list=None):
    """Copy a function object to create a new function.

    This is used inside smart modules that auto-generate functions based on
    context.

    Args:
        f (object): python source function object
        func_name (str): new function name
        doc_string (str): new function docstring
        arg_list (list): list of default values for function arguments

    Returns:
        object: new python function objects
    """
    # noinspection PyArgumentList
    new_func = types.FunctionType(f.func_code, f.func_globals,
                                  func_name, tuple(arg_list), f.func_closure)
    new_func.__doc__ = doc_string
    return new_func
