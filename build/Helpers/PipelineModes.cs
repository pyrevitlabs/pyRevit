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
    bool RemoveCert,
    bool TrustCert)
{
    /// <summary>
    /// Parses mode words case-insensitively. No arguments means <c>ci</c>; <c>local</c> implies <c>ci</c> unless
    /// <c>--remove-cert</c> or <c>--trust-cert</c> is present, which run only their certificate step.
    /// </summary>
    public static PipelineModes Parse(IEnumerable<string> args)
    {
        var argsSet = new HashSet<string>(args, StringComparer.OrdinalIgnoreCase);
        var local = argsSet.Contains("local") || argsSet.Contains("--local");
        var removeCert = argsSet.Contains("--remove-cert");
        var trustCert = argsSet.Contains("--trust-cert");
        var certificateOnly = removeCert || trustCert;

        return new PipelineModes(
            Ci: !certificateOnly && (argsSet.Count == 0 || argsSet.Contains("ci") || local),
            Pack: argsSet.Contains("pack"),
            Sign: argsSet.Contains("sign"),
            Publish: argsSet.Contains("publish"),
            Notify: argsSet.Contains("notify"),
            Release: argsSet.Contains("release"),
            Winget: argsSet.Contains("winget"),
            Local: local,
            SignTest: argsSet.Contains("sign-test"),
            RemoveCert: removeCert,
            TrustCert: trustCert);
    }

    /// <summary>Any mode that runs installer packaging; these must be gated on unsigned <c>bin/</c>.</summary>
    public bool Packages => Pack || Sign || Publish;

    /// <summary>Any mode that creates, uses, trusts or removes a test certificate.</summary>
    public bool UsesTestCertificates => Local || SignTest || RemoveCert || TrustCert;

    /// <summary>Signs <c>bin/</c> with the per-developer certificate created on demand.</summary>
    public bool SignsWithLocalCertificate => Local && !RemoveCert && !TrustCert;

    /// <summary>Runs <c>SignTestBinariesModule</c>, with either the developer or the CI throwaway certificate.</summary>
    public bool SignsTestBinaries => SignsWithLocalCertificate || SignTest;

    /// <summary>
    /// Guards the test-signing modes. Throws when they are combined with production modes, run on a shipping
    /// channel, run off Windows, or (for the modes that need a human) run under CI.
    /// </summary>
    /// <param name="channel">
    /// Read from the bound <c>Build</c> configuration section before the host is built, so a later
    /// <c>Configure&lt;BuildOptions&gt;</c> override of <c>Channel</c> would not be seen here.
    /// </param>
    /// <remarks>
    /// Runs before any module is registered, so a refused combination fails in under a second.
    /// <c>local</c> and <c>--remove-cert</c> create or delete a certificate in the developer's profile and
    /// <c>--trust-cert</c> needs someone to answer the Windows root prompt, so none of them can run unattended.
    /// </remarks>
    public void EnsureTestSigningAllowed(string channel, bool runningOnCi, bool runningOnWindows)
    {
        if (!UsesTestCertificates)
        {
            return;
        }

        if (!runningOnWindows)
        {
            throw new PlatformNotSupportedException(
                "Test signing (local, sign-test, --remove-cert, --trust-cert) is only supported on Windows.");
        }

        if (Packages)
        {
            throw new InvalidOperationException(
                "Test signing (local, sign-test, --remove-cert, --trust-cert) cannot be combined with pack, sign or publish.");
        }

        if (string.Equals(channel, "wip", StringComparison.OrdinalIgnoreCase)
            || string.Equals(channel, "release", StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException(
                $"Test signing refuses to run on the '{channel}' channel.");
        }

        if ((Local || RemoveCert || TrustCert) && runningOnCi)
        {
            throw new InvalidOperationException(
                "'local', '--remove-cert' and '--trust-cert' use a developer certificate and cannot run when CI is set.");
        }

        if (Local && SignTest)
        {
            throw new InvalidOperationException("'local' and 'sign-test' cannot be combined.");
        }

        if (SignTest && (RemoveCert || TrustCert))
        {
            throw new InvalidOperationException(
                "'sign-test' cannot be combined with '--remove-cert' or '--trust-cert'.");
        }

        if (Local && TrustCert)
        {
            throw new InvalidOperationException("'local' and '--trust-cert' cannot be combined.");
        }
    }
}
