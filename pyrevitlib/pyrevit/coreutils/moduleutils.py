import types


def copy_func(f, func_name, doc_string=None, arg_list=[]):
    new_func = types.FunctionType(f.func_code, f.func_globals, func_name, tuple(arg_list), f.func_closure)
    new_func.__doc__ = doc_string
    return new_func
