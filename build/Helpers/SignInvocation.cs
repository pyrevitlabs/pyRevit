namespace Build.Helpers;

/// <summary>
/// What distinguishes one <c>sign code</c> run from another: the provider, its arguments, the environment it needs
/// and where the run is reported. Everything else (file list, file digest, tool install) is shared.
/// </summary>
internal sealed record SignInvocation(
    string Provider,
    IReadOnlyList<string> ProviderArguments,
    string SummarySection,
    string SummaryLabel)
{
    public IReadOnlyDictionary<string, string?> EnvironmentVariables { get; init; } =
        new Dictionary<string, string?>();
}
