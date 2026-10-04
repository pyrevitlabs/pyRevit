using System.Diagnostics;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using ModularPipelines.Context;
using ModularPipelines.Models;
using ModularPipelines.Options;

namespace Build.Helpers;

/// <summary>
/// Creates, trusts and removes the self-signed code-signing certificates used to sign test builds.
/// </summary>
/// <remarks>
/// These certificates must never sign anything that is uploaded, released or installed outside the machine
/// that created them. <see cref="EnsureModesAllowed"/> keeps them away from production signing,
/// <see cref="EnsureFingerprintIsTestCertificate"/> keeps every test signature recognisable, and
/// <see cref="EnsureNoTestSignedBinaries"/> rejects recognised signatures before packaging.
/// </remarks>
public static class TestCertificateHelper
{
    internal const int LocalLifetimeDays = 365;
    internal const int LocalRenewBeforeDays = 30;
    internal const string LocalSubjectPrefix = "CN=pyRevit Local Dev";
    internal const string CiSubjectPrefix = "CN=pyRevit CI Test";
    internal const string FingerprintMarker = "FINGERPRINT=";
    internal static readonly TimeSpan PowerShellTimeout = TimeSpan.FromMinutes(5);

    /// <summary>Subject of the per-machine developer certificate; also what <c>--remove-cert</c> deletes.</summary>
    public static string LocalSubject(string machineName) => $"{LocalSubjectPrefix} ({machineName})";

    /// <summary>
    /// True when <paramref name="subject"/> names a pyRevit test certificate (local developer or CI throwaway).
    /// </summary>
    /// <remarks>
    /// An accident guard, not a security check: it prefix-matches a name anyone can put in a certificate CN.
    /// Test signing refuses any other subject, so every test signature it produces is caught by this match.
    /// </remarks>
    internal static bool IsTestSigner(string? subject) =>
        subject is not null
        && (subject.StartsWith(LocalSubjectPrefix, StringComparison.OrdinalIgnoreCase)
            || subject.StartsWith(CiSubjectPrefix, StringComparison.OrdinalIgnoreCase));

    /// <summary>
    /// Returns the files whose Authenticode signer is a test certificate. Unsigned files and files
    /// signed by any other identity are not reported.
    /// </summary>
    public static IReadOnlyList<string> FindTestSignedFiles(IEnumerable<string> files)
    {
        var found = new List<string>();
        foreach (var file in files)
        {
            if (IsTestSigner(ReadSignerSubject(file)))
            {
                found.Add(file);
            }
        }

        return found;
    }

    /// <summary>Throws when any pyRevit binary under <paramref name="binPath"/> carries a test signature.</summary>
    /// <exception cref="InvalidOperationException">At least one test-signed binary was found.</exception>
    public static void EnsureNoTestSignedBinaries(string binPath)
    {
        var offenders = FindTestSignedFiles(SigningHelper.FindPyRevitBinaries(binPath));
        if (offenders.Count > 0)
        {
            throw new InvalidOperationException(
                $"{offenders.Count} binaries in bin/ are signed with a test certificate (first: {offenders[0]}). " +
                "Packaging needs unsigned binaries: rebuild them with 'ci', or in a pack job restore bin/ from " +
                "the unsigned-bin-<sha> artifact.");
        }
    }

    private static string? ReadSignerSubject(string file)
    {
        try
        {
#pragma warning disable SYSLIB0057
            return X509Certificate.CreateFromSignedFile(file).Subject;
#pragma warning restore SYSLIB0057
        }
        catch (CryptographicException)
        {
            return null;
        }
    }

    /// <summary>
    /// Guards the test-signing modes. Throws when they are combined with production modes, run on a shipping
    /// channel, run off Windows, or (for the developer-certificate modes) run under CI.
    /// </summary>
    /// <param name="channel">
    /// Read from the bound <c>Build</c> configuration section before the host is built, so a later
    /// <c>Configure&lt;BuildOptions&gt;</c> override of <c>Channel</c> would not be seen here.
    /// </param>
    /// <remarks>Runs before any module is registered, so a refused combination fails in under a second.</remarks>
    public static void EnsureModesAllowed(PipelineModes modes, string channel, bool runningOnCi, bool runningOnWindows)
    {
        if (!modes.UsesTestCertificates)
        {
            return;
        }

        if (!runningOnWindows)
        {
            throw new PlatformNotSupportedException(
                "Test signing (local, sign-test, --remove-cert) is only supported on Windows.");
        }

        if (modes.Packages)
        {
            throw new InvalidOperationException(
                "Test signing (local, sign-test, --remove-cert) cannot be combined with pack, sign or publish.");
        }

        if (string.Equals(channel, "wip", StringComparison.OrdinalIgnoreCase)
            || string.Equals(channel, "release", StringComparison.OrdinalIgnoreCase))
        {
            throw new InvalidOperationException(
                $"Test signing refuses to run on the '{channel}' channel.");
        }

        if ((modes.Local || modes.RemoveCert) && runningOnCi)
        {
            throw new InvalidOperationException(
                "'local' and '--remove-cert' use a developer certificate and cannot run when CI is set.");
        }

        if (modes.Local && modes.SignTest)
        {
            throw new InvalidOperationException("'local' and 'sign-test' cannot be combined.");
        }

        if (modes.SignTest && modes.RemoveCert)
        {
            throw new InvalidOperationException("'sign-test' and '--remove-cert' cannot be combined.");
        }
    }

    /// <summary>
    /// Finds the certificate with SHA-256 <paramref name="fingerprint"/> in the current user or local machine
    /// <c>My</c> store and refuses it unless its subject marks it as a test certificate.
    /// </summary>
    /// <remarks>
    /// This is what lets <see cref="EnsureNoTestSignedBinaries"/> catch every test signature: whatever certificate
    /// a workflow hands to <c>sign-test</c>, it can only sign if <see cref="IsTestSigner"/> recognises it later.
    /// </remarks>
    /// <exception cref="InvalidOperationException">No such certificate, or it is not a test certificate.</exception>
    public static void EnsureFingerprintIsTestCertificate(string fingerprint)
    {
        foreach (var location in new[] { StoreLocation.CurrentUser, StoreLocation.LocalMachine })
        {
            using var store = new X509Store(StoreName.My, location);
            store.Open(OpenFlags.ReadOnly | OpenFlags.OpenExistingOnly);
            foreach (var certificate in store.Certificates)
            {
                using (certificate)
                {
                    if (string.Equals(
                            certificate.GetCertHashString(HashAlgorithmName.SHA256),
                            fingerprint,
                            StringComparison.OrdinalIgnoreCase))
                    {
                        EnsureTestSigner(certificate);
                        return;
                    }
                }
            }
        }

        throw new InvalidOperationException(
            $"No certificate with SHA-256 fingerprint {fingerprint} is in the CurrentUser or LocalMachine My store.");
    }

    internal static void EnsureTestSigner(X509Certificate2 certificate)
    {
        if (!IsTestSigner(certificate.Subject))
        {
            throw new InvalidOperationException(
                $"Refusing to test-sign with '{certificate.Subject}': the subject must start with " +
                $"'{LocalSubjectPrefix}' or '{CiSubjectPrefix}' so packaging can detect and reject the signature.");
        }
    }

    internal static string BuildEnsureScript(string subject, int lifetimeDays, int renewBeforeDays)
    {
        var escaped = EscapeSingleQuoted(subject);
        return $$"""
            $ErrorActionPreference = 'Stop'
            $ProgressPreference = 'SilentlyContinue'
            $subject = '{{escaped}}'
            $threshold = (Get-Date).AddDays({{renewBeforeDays}})
            $cert = Get-ChildItem Cert:\CurrentUser\My |
                Where-Object { $_.Subject -eq $subject -and $_.NotAfter -gt $threshold -and $_.HasPrivateKey } |
                Sort-Object NotAfter -Descending |
                Select-Object -First 1
            if (-not $cert) {
                $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $subject `
                    -KeyExportPolicy NonExportable -KeyAlgorithm RSA -KeyLength 3072 -HashAlgorithm SHA256 `
                    -NotAfter (Get-Date).AddDays({{lifetimeDays}}) -CertStoreLocation Cert:\CurrentUser\My
            }
            Get-ChildItem Cert:\CurrentUser\My |
                Where-Object { $_.Subject -eq $subject -and $_.Thumbprint -ne $cert.Thumbprint } |
                ForEach-Object { Remove-Item $_.PSPath -DeleteKey }
            foreach ($name in 'Root', 'TrustedPublisher') {
                $store = New-Object System.Security.Cryptography.X509Certificates.X509Store($name, 'CurrentUser')
                $store.Open('ReadWrite')
                try {
                    foreach ($stale in @($store.Certificates | Where-Object { $_.Subject -eq $subject -and $_.Thumbprint -ne $cert.Thumbprint })) {
                        $store.Remove($stale)
                    }
                    if (-not $store.Certificates.Find('FindByThumbprint', $cert.Thumbprint, $false).Count) {
                        $store.Add((New-Object System.Security.Cryptography.X509Certificates.X509Certificate2(,$cert.RawData)))
                    }
                } finally {
                    $store.Close()
                }
            }
            $hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($cert.RawData)
            Write-Output ('{{FingerprintMarker}}' + (($hash | ForEach-Object { $_.ToString('X2') }) -join ''))
            """;
    }

    internal static string BuildRemoveScript(string subject)
    {
        var escaped = EscapeSingleQuoted(subject);
        return $$"""
            $ErrorActionPreference = 'Stop'
            $subject = '{{escaped}}'
            foreach ($store in 'My', 'Root', 'TrustedPublisher') {
                Get-ChildItem "Cert:\CurrentUser\$store" |
                    Where-Object { $_.Subject -eq $subject } |
                    ForEach-Object { Remove-Item $_.PSPath -DeleteKey }
            }
            """;
    }

    internal static string ParseFingerprint(string scriptOutput)
    {
        var fingerprints = scriptOutput
            .Split(['\r', '\n'], StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Where(line => line.StartsWith(FingerprintMarker, StringComparison.Ordinal))
            .Select(line => line[FingerprintMarker.Length..])
            .ToArray();

        if (fingerprints.Length != 1 || fingerprints[0].Length != 64 || !fingerprints[0].All(Uri.IsHexDigit))
        {
            throw new InvalidOperationException("Certificate script did not return a valid SHA-256 fingerprint.");
        }

        return fingerprints[0].ToUpperInvariant();
    }

    /// <summary>
    /// Creates the developer certificate if missing or near expiry, trusts it for the current user, and removes
    /// superseded certificates with the same subject (including their private keys).
    /// </summary>
    /// <returns>The SHA-256 fingerprint of the certificate to sign with.</returns>
    public static async Task<string> EnsureLocalCertificateAsync(CancellationToken cancellationToken)
    {
        var script = BuildEnsureScript(LocalSubject(Environment.MachineName), LocalLifetimeDays, LocalRenewBeforeDays);
        return ParseFingerprint(await RunPowerShellAsync(script, cancellationToken));
    }

    /// <summary>Deletes the developer certificate and its private key from <c>My</c>, <c>Root</c> and <c>TrustedPublisher</c>.</summary>
    public static async Task RemoveLocalCertificateAsync(CancellationToken cancellationToken)
    {
        await RunPowerShellAsync(BuildRemoveScript(LocalSubject(Environment.MachineName)), cancellationToken);
    }

    /// <summary>Signs <paramref name="files"/> in place with the certificate in the current user store.</summary>
    /// <param name="fingerprint">SHA-256 fingerprint; the sign tool rejects a SHA-1 thumbprint.</param>
    /// <remarks>Re-signing an already signed file replaces its signature, so repeated <c>ci local</c> runs succeed.</remarks>
    public static Task<CommandResult> SignFilesAsync(
        IModuleContext context,
        string fingerprint,
        IEnumerable<string> files,
        string summaryLabel,
        CancellationToken cancellationToken)
    {
        return SigningHelper.RunSignToolAsync(
            context,
            files,
            "Test signing",
            summaryLabel,
            "certificate-store",
            ["--certificate-fingerprint", fingerprint],
            new CommandExecutionOptions(),
            cancellationToken);
    }

    private static string EscapeSingleQuoted(string value) => value.Replace("'", "''");

    private static async Task<string> RunPowerShellAsync(string script, CancellationToken cancellationToken)
    {
        if (!OperatingSystem.IsWindows())
        {
            throw new PlatformNotSupportedException("Test certificates are only supported on Windows.");
        }

        var encoded = Convert.ToBase64String(Encoding.Unicode.GetBytes(script));
        var startInfo = new ProcessStartInfo("powershell.exe")
        {
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        startInfo.ArgumentList.Add("-NoProfile");
        startInfo.ArgumentList.Add("-EncodedCommand");
        startInfo.ArgumentList.Add(encoded);

        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        timeout.CancelAfter(PowerShellTimeout);

        using var process = Process.Start(startInfo)
            ?? throw new InvalidOperationException("Could not start powershell.exe.");
        var stdout = process.StandardOutput.ReadToEndAsync(timeout.Token);
        var stderr = process.StandardError.ReadToEndAsync(timeout.Token);
        try
        {
            await process.WaitForExitAsync(timeout.Token);
        }
        catch (OperationCanceledException)
        {
            process.Kill(entireProcessTree: true);
            await process.WaitForExitAsync(CancellationToken.None);
            if (!cancellationToken.IsCancellationRequested)
            {
                throw new TimeoutException(
                    $"Certificate script did not finish within {PowerShellTimeout.TotalMinutes} minutes. " +
                    "If Windows is asking whether to trust the pyRevit Local Dev root certificate, answer it and rerun.");
            }

            throw;
        }

        if (process.ExitCode != 0)
        {
            throw new InvalidOperationException($"Certificate script failed: {await stderr}");
        }

        return await stdout;
    }
}
