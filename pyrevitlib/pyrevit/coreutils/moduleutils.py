"""Utility fuctions to support smart modules."""
import inspect
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
        (object): new python function objects
    """
    new_func = types.FunctionType(func.func_code, func.func_globals,
                                  func_name, tuple(arg_list), func.func_closure)
    new_func.__doc__ = doc_string
    return new_func


def mark(prop_name):
    """Decorator function to add a marker property to the given type."""
    def setter_decorator(type_obj):
        setattr(type_obj, prop_name, True)
        return type_obj
    return setter_decorator


def collect_marked(module_obj, prop_name):
    """Collect module objects that are marked with given property."""
    marked_objs = []
    for member in inspect.getmembers(module_obj):
        _, type_obj = member
        if (inspect.isclass(type_obj) or inspect.isfunction(type_obj)) \
                and getattr(type_obj, prop_name, False):
            marked_objs.append(type_obj)
    return marked_objs


def has_argument(function_obj, arg_name):
    """Check if given function object has argument matching arg_name."""
    return arg_name in inspect.getargspec(function_obj)[0] #pylint: disable=deprecated-method


def has_any_arguments(function_obj, arg_name_list):
    """Check if given function object has any of given arguments."""
    args = inspect.getargspec(function_obj)[0] #pylint: disable=deprecated-method
    if arg_name_list:
        return any(x in args for x in arg_name_list)
    return False


def filter_kwargs(function_obj, kwargs):
    """Filter given arguments dict for function_obj arguments."""
    filtered_kwargs = {}
    for arg_name in inspect.getargspec(function_obj)[0]: #pylint: disable=deprecated-method
        filtered_kwargs[arg_name] = kwargs.get(arg_name, None)
    return filtered_kwargs
