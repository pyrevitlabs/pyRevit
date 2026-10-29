"""Show plain Python data to WPF under pythonnet the way IronPython does.

Under the ``PythonBinding`` codecs from ``pyRevitLabs.PyRevit.Forms.Binding``,
a Python list or other iterable assigned to an ``IEnumerable`` such as
``ItemsSource`` becomes a live managed list, and a plain Python object assigned
to an ``object`` such as ``DataContext`` or ``Tag`` becomes a managed property
bag that reads its attributes live. WPF hands every item, selection and
``DataContext`` back to Python as the original object. Importing this module adds the hooks through which Reactive models
keep their managed ``BindingModel`` adapter (``_binding.binding_source``),
which also goes back to Python as the model.

Warning:
    The codecs are process-wide: the CPython engine registers them before the
    first script runs, so they apply to every CPython script's conversions to
    ``object``, ``IEnumerable``, ``IList`` and ``ICollection`` whether or not
    ``pyrevit.forms`` was imported. Python ints passed as ``object`` become
    ``Int32``/``Int64``; Python lists passed as ``object`` are left to
    pythonnet. The codec registration on import is an idempotent fallback.
"""

import clr

from ._binding import Reactive, binding_source, model_of

clr.AddReference("pyRevitLabs.PyRevit.Forms.Binding")
from PyRevitLabs.PyRevit.Forms.Binding import PythonBinding  # noqa: E402


def _adapt(value):
    if isinstance(value, Reactive):
        return binding_source(value)
    return None


PythonBinding.Register(_adapt, model_of)
