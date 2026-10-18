# Shared loader fixtures

The parser, assembly-builder, and loader integration suites link these sources into their test assemblies. `TempFileTestBase` isolates temporary files and configuration; `TestExtensionBuilder` creates local extension fixtures; `TestConfiguration` locates checked-in DevTools fixtures; `RecordingParserLogger` captures parser diagnostics. The assembly-builder and integration suites also link `AssemblyBuilder/MockLogger.cs` for the builder logging interface.

Keep loader-specific fixtures here. Cross-module repository lookup lives under `dev/testing/csharp/`; runtime tests own their temporary-file fixtures. None of these helpers is a production dependency.
