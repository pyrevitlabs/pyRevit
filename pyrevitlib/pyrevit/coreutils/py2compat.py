import __builtin__ as builtins


class safe_str(builtins.str):
    def __init__(self, obj):
        self._obj = obj

    def __str__(self):
        if isinstance(self._obj, builtins.str):
            return self._obj
        else:
            return builtins.str(self._obj)


builtins.unicode = safe_str
