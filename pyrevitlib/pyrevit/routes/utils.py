"""Utility functions and types"""
import inspect


def has_argument(function_obj, arg_name):
    """Check if given function object has argument matching arg_name"""
    return arg_name in inspect.getargspec(function_obj)[0] #pylint: disable=deprecated-method
