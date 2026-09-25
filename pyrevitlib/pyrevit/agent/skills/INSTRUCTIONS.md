pyRevit MCP server: read and change the live Revit model by running Python inside Revit.

Start every task like this:

1. Call get_context. It reports the Revit version, the open document, the active view, the selection, the agent policy, and the Python engine your scripts run on.
2. Call get_skill("revit-scripting"). It covers the script contract, transactions, units and the Revit API mistakes agents make most often. Read it before your first script.
3. Call get_skill for the skill that matches your task, and follow it.

Available skills:
{skills}

Model changes go through run_modify: dry-run first, then run it for real. Under agent policy "ask" the user approves each change in Revit.
