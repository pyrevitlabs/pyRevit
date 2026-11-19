"""Measure native WPF binding against Python objects and managed dynamic models."""

import json
import time

try:
    clr.AddReference("System.Linq.Expressions")
except System.IO.FileNotFoundException:
    clr.AddReference("System.Core")

from System.Dynamic import ExpandoObject
from System.Collections.Generic import IDictionary
from System.Windows.Data import Binding


def read_binding(model):
    """Read a bound TextBlock through WPF, not through the Python object."""
    text = Controls.TextBlock()
    text.DataContext = model
    expression = text.SetBinding(Controls.TextBlock.TextProperty, Binding("name"))
    expression.UpdateTarget()
    return text.Text


class PythonItem:
    """Represent the current plain Python item model at the binding boundary."""

    @property
    def name(self):
        """Expose the display name used by SelectFromList.xaml."""
        return "python item"


plain_result = read_binding(PythonItem())
model = ExpandoObject()
values = IDictionary[System.String, System.Object](model)
values["name"] = "managed item"
assert read_binding(model) == "managed item"
values["name"] = "updated item"
assert read_binding(model) == "updated item"

started = time.perf_counter()
for index in range(2000):
    item = ExpandoObject()
    data = IDictionary[System.String, System.Object](item)
    data["name"] = "item {}".format(index)
    assert read_binding(item) == "item {}".format(index)

binding_report = json.dumps(
    {
        "plain_python_binding": plain_result,
        "managed_dynamic_binding": "passed",
        "two_thousand_bindings_seconds": round(time.perf_counter() - started, 3),
    }
)
