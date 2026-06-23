namespace pyRevitLabs.Configurations;

/// <summary>
/// Optional diagnostic sink for the Configurations assemblies, which carry no
/// logging dependency of their own. A host assigns <see cref="Warn"/> and
/// <see cref="Info"/> to route messages to its logger; when unset, diagnostics
/// are dropped.
/// </summary>
public static class ConfigurationDiagnostics
{
    public static Action<string>? Warn { get; set; }
    public static Action<string>? Info { get; set; }

    internal static void ReportFallback(string sectionName, string keyName, Exception error)
    {
        Warn?.Invoke(
            "Config value [" + sectionName + "] " + keyName +
            " could not be read (" + error.Message + "); using default.");
    }

    public static void ReportWarning(string message) => Warn?.Invoke(message);

    public static void ReportInfo(string message) => Info?.Invoke(message);
}
