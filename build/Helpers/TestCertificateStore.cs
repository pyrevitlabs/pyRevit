using System.Diagnostics;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;

namespace Build.Helpers;

/// <summary>
/// Creates, trusts, finds and removes the self-signed code-signing certificates used to sign test builds.
/// </summary>
/// <remarks>
/// These certificates must never sign anything that is uploaded, released or installed outside the machine
/// that created them. <see cref="PipelineModes.EnsureTestSigningAllowed"/> keeps them away from production signing,
/// <see cref="EnsureFingerprintIsTestCertificate"/> keeps every test signature recognisable, and
/// <see cref="TestSignatureDetector.EnsureNoTestSignedBinaries"/> rejects recognised signatures before packaging.
/// </remarks>
public static class TestCertificateStore
{
    internal const int LocalLifetimeDays = 365;
    internal const int LocalRenewBeforeDays = 30;
    internal const string FingerprintMarker = "FINGERPRINT=";
    internal static readonly TimeSpan PowerShellTimeout = TimeSpan.FromMinutes(5);

    /// <summary>Subject of the per-machine developer certificate; also what <c>--remove-cert</c> deletes.</summary>
    public static string LocalSubject(string machineName) =>
        $"{TestSignatureDetector.LocalSubjectPrefix} ({machineName})";

    /// <summary>
    /// Creates the developer certificate if missing or near expiry, trusts it for the current user, and removes
    /// superseded certificates with the same subject (including their private keys).
    /// </summary>
    /// <remarks>
    /// Windows only accepts the signature when the self-signed certificate is in <c>Root</c>; <c>TrustedPublisher</c>
    /// alone leaves it untrusted. The certificate is created as a non-CA end entity with only the digital signature
    /// key usage, so that root trust cannot extend to any certificate it might issue.
    /// </remarks>
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

    /// <summary>
    /// Finds the certificate with SHA-256 <paramref name="fingerprint"/> in <c>CurrentUser\My</c> and refuses it
    /// unless its subject marks it as a test certificate.
    /// </summary>
    /// <remarks>
    /// Whatever certificate a workflow hands to <c>sign-test</c>, it can only sign if packaging will recognise and
    /// reject its signatures later. Only <c>CurrentUser\My</c> is searched because that is where the sign tool's
    /// certificate-store provider is known to find certificates, so an accepted certificate is always the one used.
    /// </remarks>
    /// <exception cref="InvalidOperationException">No such certificate, or it is not a test certificate.</exception>
    public static void EnsureFingerprintIsTestCertificate(string fingerprint)
    {
        using var store = new X509Store(StoreName.My, StoreLocation.CurrentUser);
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
                    TestSignatureDetector.EnsureTestSigner(certificate);
                    return;
                }
            }
        }

        throw new InvalidOperationException(
            $"No certificate with SHA-256 fingerprint {fingerprint} is in CurrentUser\\My; import the test certificate there.");
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
                    -KeyUsage DigitalSignature -TextExtension @('2.5.29.19={critical}{text}ca=false') `
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
