# Shared C# test infrastructure

`RepositoryPaths.cs` locates the checkout by its `pyRevitfile` marker. The parser, assembly-builder, loader integration, and runtime test projects link this source into their own assemblies. It adds no production dependency or shared test base.

Keep module fixtures beside their suites. Only helpers used across module boundaries belong here; loader fixture builders stay under `dev/pyRevitLoader/tests/TestSupport/`.
