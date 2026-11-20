# Repository checks

Owner: repository tooling maintainers. These are executable validators; their tests live in `dev/tests/python/tooling/`.

| Utility | Invocation | Caller |
|---|---|---|
| `check_py3_compat.py` | `pipenv run check-py3` | Explicit Python engine compatibility audit |
| `check_config_api.py` | `pipenv run check-config-api` | Config contract validation and the config pre-commit hook |
| `check_ipy2_compat.py` | `python dev/checks/check_ipy2_compat.py --fix <files>` | IronPython 2 formatting compatibility hook |
| `check_revit_api_compat.py` | `pipenv run check-revit-api` | Revit API version compatibility lint; the build runs it against the committed baseline |
| `build_revit_api_catalog.py` | `python dev/checks/build_revit_api_catalog.py` (needs `dnfile`) | On-demand catalog regeneration when a Revit release ships |

`revit_api_catalog/` holds the data the Revit API lint reads: `catalog.json` (generated from the RevitAPI/RevitAPIUI assemblies by `build_revit_api_catalog.py`), `overrides.json` (hand-edited helpers, fix wording and tiers, merged at run time) and `baseline.json` (frozen existing findings, refreshed with `--update-baseline`).

Checks belong here; test discovery and coverage policy belong in `dev/tests/`. `dev/scripts/` holds developer utilities that are neither checks nor tests, such as `Stop-McpServers.ps1` and `forms_usage.py`.
