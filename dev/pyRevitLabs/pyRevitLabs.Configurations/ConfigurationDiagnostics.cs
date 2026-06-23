namespace pyRevitLabs.Configurations;

/// <summary>
/// Optional diagnostic sink for the Configurations assembly, which carries no
/// logging dependency of its own. A host assigns <see cref="Warn"/> to route
/// messages to its logger; when unset, diagnostics are dropped.
/// </summary>
public static class ConfigurationDiagnostics
{
    public static Action<string>? Warn { get; set; }

    internal static void ReportFallback(string sectionName, string keyName, Exception error)
    {
        Warn?.Invoke(
            "Config value [" + sectionName + "] " + keyName +
            " could not be read (" + error.Message + "); using default.");
    }
}
