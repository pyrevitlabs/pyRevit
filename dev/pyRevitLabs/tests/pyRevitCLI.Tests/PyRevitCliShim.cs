namespace pyRevitCLI;

internal static class PyRevitCLI {
    public static string CLIInfoVersion => "0.0.0-tests";

    internal static string UsagePatterns =>
        File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "UsagePatterns.txt"));
}
