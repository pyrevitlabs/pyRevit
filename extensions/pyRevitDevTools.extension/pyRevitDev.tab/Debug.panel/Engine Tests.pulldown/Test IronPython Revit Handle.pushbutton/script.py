"""Verify the __revit__ host-handle contract under IronPython."""

# pylint: skip-file
import revithandle

revithandle.report("IronPython pushbutton", revithandle.RUNTIME_ENGINE_SITE)
