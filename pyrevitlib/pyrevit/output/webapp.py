from functools import wraps


def route(target_url):
    def wrap(f):
        @wraps(f)
        def wrapped_f(*args, **kwargs):
            return f(*args, **kwargs)
        return wrapped_f
    return wrap
