import six
from pyrevit import script

if six.PY2:
    import imp

    def load_module_from_path(name, path):
        return imp.load_source(name, path)
else:
    import importlib.util

    def load_module_from_path(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    
load_module_from_path("script", script.get_bundle_file("script.py")).main(advanced=True)
