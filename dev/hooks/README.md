# Repository hooks

`format_staged_csharp.py` groups staged C# paths by their owning solution and invokes `dotnet format` once per solution. `.pre-commit-config.yaml` calls it serially; it fails for review when formatting changes a file.

Install with `pipenv run install-hooks`. Compatibility/config validators used by other hooks live in `dev/checks/`.
