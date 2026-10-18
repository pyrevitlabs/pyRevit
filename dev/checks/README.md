# Repository checks

Owner: repository tooling maintainers. These are executable validators; their tests live in `dev/testing/tests/tooling/`.

| Utility | Invocation | Caller |
|---|---|---|
| `check_py3_compat.py` | `pipenv run check-py3` | Explicit Python engine compatibility audit |
| `check_config_api.py` | `pipenv run check-config-api` | Config contract validation and the config pre-commit hook |
| `check_ipy2_compat.py` | `python dev/checks/check_ipy2_compat.py --fix <files>` | IronPython 2 formatting compatibility hook |

All three have active entry points. Checks belong here; test discovery and coverage policy belong in `dev/testing/`.
