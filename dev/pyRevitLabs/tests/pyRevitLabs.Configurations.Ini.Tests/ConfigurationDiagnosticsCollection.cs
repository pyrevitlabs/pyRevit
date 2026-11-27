namespace pyRevitLabs.Configurations.Ini.Tests;

/// <summary>
/// Serializes the test classes that swap the static <see cref="ConfigurationDiagnostics.Warn"/>
/// handler or the machine config override, so one class cannot capture another's warnings.
/// </summary>
[CollectionDefinition(Name)]
public class ConfigurationDiagnosticsCollection
{
    /// <summary>The collection name the serialized test classes join.</summary>
    public const string Name = "ConfigurationDiagnostics";
}
