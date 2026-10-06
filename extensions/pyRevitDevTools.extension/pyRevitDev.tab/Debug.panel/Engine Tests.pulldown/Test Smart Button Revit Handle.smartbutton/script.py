"""Verify the __revit__ host-handle contract on the ScriptExecutor path."""

# pylint: skip-file
import revithandle

# Smart buttons inject __revit__ through PyRevitLoader's ScriptExecutor, not
# through the runtime engines, so the pushbuttons above never exercise the
# second injection site.
revithandle.report("SmartButton (ScriptExecutor)")
