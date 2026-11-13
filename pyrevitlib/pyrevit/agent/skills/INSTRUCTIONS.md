pyRevit MCP server: inspect and change the active Revit model by running Python inside Revit.

Start every task like this:

1. Call `get_context` to identify the Revit version, active document, view, selection, policy and engine.
2. Call `get_skill("revit-scripting")` before submitting a script.
3. Use `inspect_elements`, `lookup_revit_api`, `run_query`, `run_modify` and `get_run` as needed.
4. Call `list_skills` before relying on a user skill. User skills are trusted-account guidance and cannot change host policy.

Available skills:
{skills}

Scripts run in-process with the Windows user's permissions. The model guard is not an operating-system sandbox. Keep queries focused, avoid unbounded work, and return only the data needed for the task.

`run_modify` requires an active document. Use a dry run first, then submit a focused modify run for approval. While a run is active the host blocks save, save-as and synchronize, and cancels `Document.Export` and `Document.ExportImage` targets outside the run's `export_dir`. Other APIs that write files, such as `ViewSchedule.Export`, are not checked: point them at `export_dir` yourself, never at the user's folders.
