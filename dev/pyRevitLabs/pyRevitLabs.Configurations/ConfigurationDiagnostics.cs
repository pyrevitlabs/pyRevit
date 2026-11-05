namespace pyRevitLabs.Configurations;

/// <summary>
/// Optional diagnostic sink for the Configurations assemblies, which carry no
/// logging dependency of their own. A host assigns <see cref="Warn"/> and
/// <see cref="Info"/> to route messages to its logger; when unset, diagnostics
/// are dropped.
/// </summary>
public static class ConfigurationDiagnostics
{
    /// <summary>
    /// Receives messages about degraded behavior: a value that could not be read
    /// and fell back to its default, or a configuration that could not be
    /// written. Null discards them.
    /// </summary>
    public static Action<string>? Warn { get; set; }

    /// <summary>
    /// Receives messages about normal but noteworthy events: config discovery,
    /// migration outcomes, and legacy-format reads. Null discards them.
    /// </summary>
    public static Action<string>? Info { get; set; }

    internal static void ReportFallback(string sectionName, string keyName, Exception error)
    {
        Warn?.Invoke(
            "Config value [" + sectionName + "] " + keyName +
            " could not be read (" + error.Message + "); using default.");
    }

    /// <summary>Sends a message to <see cref="Warn"/>, if a host has set one.</summary>
    public static void ReportWarning(string message) => Warn?.Invoke(message);

    /// <summary>Sends a message to <see cref="Info"/>, if a host has set one.</summary>
    public static void ReportInfo(string message) => Info?.Invoke(message);
}
