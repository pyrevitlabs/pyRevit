namespace Build.Helpers;

/// <summary>
/// The pipeline modes requested on the command line, and the module groups they switch on.
/// </summary>
/// <remarks>
/// <c>Program.cs</c> registers modules purely from these flags, so the derived properties are the test-signing
/// containment: <see cref="SignsWithLocalCertificate"/> is the only source of <c>TestSigningOptions.Local</c>.
/// </remarks>
public sealed record PipelineModes(
    bool Ci,
    bool Pack,
    bool Sign,
    bool Publish,
    bool Notify,
    bool Release,
    bool Winget,
    bool Local,
    bool SignTest,
    bool RemoveCert)
{
    /// <summary>
    /// Parses mode words case-insensitively. No arguments means <c>ci</c>; <c>local</c> implies <c>ci</c> unless
    /// <c>--remove-cert</c> is present, which runs only the certificate removal.
    /// </summary>
    public static PipelineModes Parse(IEnumerable<string> args)
    {
        var argsSet = new HashSet<string>(args, StringComparer.OrdinalIgnoreCase);
        var local = argsSet.Contains("local") || argsSet.Contains("--local");
        var removeCert = argsSet.Contains("--remove-cert");

        return new PipelineModes(
            Ci: !removeCert && (argsSet.Count == 0 || argsSet.Contains("ci") || local),
            Pack: argsSet.Contains("pack"),
            Sign: argsSet.Contains("sign"),
            Publish: argsSet.Contains("publish"),
            Notify: argsSet.Contains("notify"),
            Release: argsSet.Contains("release"),
            Winget: argsSet.Contains("winget"),
            Local: local,
            SignTest: argsSet.Contains("sign-test"),
            RemoveCert: removeCert);
    }

    /// <summary>Any mode that runs installer packaging; these must be gated on unsigned <c>bin/</c>.</summary>
    public bool Packages => Pack || Sign || Publish;

    /// <summary>Any mode that creates, uses or removes a test certificate.</summary>
    public bool UsesTestCertificates => Local || SignTest || RemoveCert;

    /// <summary>Signs <c>bin/</c> with the per-developer certificate created on demand.</summary>
    public bool SignsWithLocalCertificate => Local && !RemoveCert;

    /// <summary>Runs <c>SignTestBinariesModule</c>, with either the developer or the CI throwaway certificate.</summary>
    public bool SignsTestBinaries => SignsWithLocalCertificate || SignTest;
}
