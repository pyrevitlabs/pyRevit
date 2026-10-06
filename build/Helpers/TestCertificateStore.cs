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
public static class TestCertificateStore {
    internal const int LocalLifetimeDays = 365;
    internal const int LocalRenewBeforeDays = 30;
    internal const string FingerprintMarker = "FINGERPRINT=";

    /// <summary>
    /// How long a certificate script may run. Deliberately short: the only step that can legitimately wait is the
    /// Windows root confirmation dialog on <c>--trust-cert</c>, so a build that reaches the timeout is
    /// unattended and must fail fast rather than hold the pipeline open for minutes.
    /// </summary>
    internal static readonly TimeSpan PowerShellTimeout = TimeSpan.FromSeconds(60);

    /// <summary>How long the post-failure cleanup script may run before it is abandoned.</summary>
    internal static readonly TimeSpan RollbackTimeout = TimeSpan.FromSeconds(30);

    /// <summary>Subject of the per-machine developer certificate; also what <c>--remove-cert</c> deletes.</summary>
    public static string LocalSubject(string machineName) =>
        $"{TestSignatureDetector.LocalSubjectPrefix} ({machineName})";

    /// <summary>
    /// Creates the developer certificate if missing or near expiry and removes superseded certificates with the same
    /// subject, including their private keys. Does not change any trust store.
    /// </summary>
    /// <remarks>
    /// Adding to <c>Root</c> raises a modal Windows Security Warning, so trust is never written from here; see
    /// <see cref="TrustLocalCertificateAsync"/>. Windows only accepts the signature when the self-signed certificate
    /// is in <c>Root</c>; <c>TrustedPublisher</c> alone leaves it untrusted. The certificate is created as a non-CA
    /// end entity with only the digital signature key usage, so that root trust cannot extend to any certificate it
    /// might issue. An existing certificate must satisfy the same profile and have a non-exportable private key
    /// before it is reused.
    /// </remarks>
    /// <returns>The SHA-256 fingerprint of the certificate to sign with.</returns>
    public static async Task<string> EnsureLocalCertificateAsync(CancellationToken cancellationToken) {
        var script = BuildEnsureScript(LocalSubject(Environment.MachineName), LocalLifetimeDays, LocalRenewBeforeDays);
        return ParseFingerprint(await RunPowerShellAsync(script, cancellationToken, trustStoreChanges: false));
    }

    /// <summary>
    /// Creates or reuses the developer certificate and adds it to <c>Root</c> and <c>TrustedPublisher</c> for the
    /// current user, which is the only operation that can prompt.
    /// </summary>
    /// <remarks>
    /// Run this on its own (<c>--trust-cert</c>) and answer the Windows Security Warning, so that
    /// <c>ci local</c> afterwards never has to prompt mid-build. Already-trusted certificates are left alone, so
    /// the prompt happens once per certificate rather than once per run.
    /// </remarks>
    /// <returns>The SHA-256 fingerprint of the trusted certificate.</returns>
    public static async Task<string> TrustLocalCertificateAsync(CancellationToken cancellationToken) {
        var script = BuildEnsureScript(
            LocalSubject(Environment.MachineName),
            LocalLifetimeDays,
            LocalRenewBeforeDays,
            trustInRootStore: true);
        return ParseFingerprint(await RunPowerShellAsync(script, cancellationToken, trustStoreChanges: true));
    }

    /// <summary>
    /// Refuses to sign unless some certificate with the developer subject is trusted in <c>Root</c> and
    /// <c>TrustedPublisher</c>.
    /// </summary>
    /// <remarks>
    /// Cheap side-effect-free precondition, so a developer who has never trusted anything is told what to run before
    /// a certificate is created. It cannot stand in for <see cref="EnsureCertificateIsTrusted(string)"/>: trust is per
    /// certificate, not per subject, so a stale trusted certificate must not vouch for a freshly renewed one.
    /// </remarks>
    /// <exception cref="InvalidOperationException">Nothing with this subject is trusted.</exception>
    public static void EnsureLocalCertificateIsTrusted() =>
        EnsureCertificateIsTrusted(LocalSubject(Environment.MachineName));

    /// <summary>Refuses unless anything with <paramref name="subject"/> is trusted in both trust stores.</summary>
    /// <exception cref="InvalidOperationException">Nothing with this subject is trusted.</exception>
    public static void EnsureCertificateIsTrusted(string subject) {
        var missing = TrustedStores().Where(store => !ContainsSubject(store, subject)).ToArray();
        if (missing.Length == 0) {
            return;
        }

        throw new InvalidOperationException(
            $"The developer certificate '{subject}' is not trusted in CurrentUser\\{string.Join(" and CurrentUser\\", missing)}. "
            + "Run '--trust-cert' on its own once and answer the Windows root confirmation, then rerun.");
    }

    /// <summary>
    /// Refuses unless the certificate with SHA-256 <paramref name="fingerprint"/> — the one signing will use — is
    /// itself trusted in <c>Root</c> and <c>TrustedPublisher</c>.
    /// </summary>
    /// <remarks>
    /// Matched on the certificate, not the subject: after a renewal the trusted certificate and the signing one differ,
    /// and signing with an untrusted certificate produces binaries Windows reports as unverified.
    /// </remarks>
    /// <exception cref="InvalidOperationException">The certificate is not trusted where it needs to be.</exception>
    public static void EnsureFingerprintIsTrusted(string fingerprint) {
        foreach (var storeName in TrustedStores())
        {
            using var store = new X509Store(storeName, StoreLocation.CurrentUser);
            store.Open(OpenFlags.ReadOnly | OpenFlags.OpenExistingOnly);
            var trusted = store.Certificates
                .Any(candidate => string.Equals(
                    candidate.GetCertHashString(HashAlgorithmName.SHA256),
                    fingerprint,
                    StringComparison.OrdinalIgnoreCase));

            if (!trusted)
            {
                throw new InvalidOperationException(
                    $"Certificate {fingerprint} is not trusted in CurrentUser\\{storeName}, so Windows would report "
                    + "the binaries it signs as unverified. Run '--trust-cert' on its own once and answer the Windows "
                    + "root confirmation, then rerun.");
            }
        }
    }

    /// <summary>Deletes the developer certificate and its private key from <c>My</c>, <c>Root</c> and <c>TrustedPublisher</c>.</summary>
    public static async Task RemoveLocalCertificateAsync(CancellationToken cancellationToken) {
        await RunPowerShellAsync(
            BuildRemoveScript(LocalSubject(Environment.MachineName)),
            cancellationToken,
            trustStoreChanges: true);
    }

    private static IEnumerable<string> TrustedStores() => ["Root", "TrustedPublisher"];

    private static bool ContainsSubject(string storeName, string subject) {
        using var store = new X509Store(storeName, StoreLocation.CurrentUser);
        store.Open(OpenFlags.ReadOnly | OpenFlags.OpenExistingOnly);
        return ContainsSubject(store.Certificates, subject);
    }

    /// <summary>True when a certificate whose subject is exactly <paramref name="subject"/> is in the collection.</summary>
    /// <remarks>
    /// Matched on the full distinguished name, not on
    /// <see cref="X509FindType.FindBySubjectName"/>, which treats its argument as a partial name and silently matches
    /// nothing for a subject with spaces and parentheses — which is exactly this certificate's subject.
    /// </remarks>
    internal static bool ContainsSubject(X509Certificate2Collection certificates, string subject) =>
        certificates.Find(X509FindType.FindBySubjectDistinguishedName, subject, validOnly: false).Count > 0;

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
    public static void EnsureFingerprintIsTestCertificate(string fingerprint) {
        using var store = new X509Store(StoreName.My, StoreLocation.CurrentUser);
        store.Open(OpenFlags.ReadOnly | OpenFlags.OpenExistingOnly);
        foreach (var certificate in store.Certificates) {
            using (certificate) {
                if (string.Equals(
                        certificate.GetCertHashString(HashAlgorithmName.SHA256),
                        fingerprint,
                        StringComparison.OrdinalIgnoreCase)) {
                    TestSignatureDetector.EnsureTestSigner(certificate);
                    return;
                }
            }
        }

        throw new InvalidOperationException(
            $"No certificate with SHA-256 fingerprint {fingerprint} is in CurrentUser\\My; import the test certificate there.");
    }

    internal static string BuildEnsureScript(string subject, int lifetimeDays, int renewBeforeDays) =>
        BuildEnsureScript(subject, lifetimeDays, renewBeforeDays, trustInRootStore: false);

    /// <param name="trustInRootStore">
    /// When <see langword="true"/> the certificate is added to <c>Root</c> and <c>TrustedPublisher</c>, which raises
    /// the modal Windows root confirmation. When <see langword="false"/> only <c>My</c> is written, so the caller can
    /// never block on a prompt.
    /// </param>
    internal static string BuildEnsureScript(
        string subject,
        int lifetimeDays,
        int renewBeforeDays,
        bool trustInRootStore) {
        var escaped = EscapeSingleQuoted(subject);
        var trustBlock = trustInRootStore
            ? $$"""
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
                """
            : "            # Trust-store writes happen only in '--trust-cert', which can prompt.";

        return $$"""
            $ErrorActionPreference = 'Stop'
            $ProgressPreference = 'SilentlyContinue'
            $subject = '{{escaped}}'
            $threshold = (Get-Date).AddDays({{renewBeforeDays}})
            function Test-LocalCertificate($candidate, $expectedSubject, $renewalThreshold) {
                if ($candidate.Subject -ne $expectedSubject -or $candidate.Issuer -ne $expectedSubject -or
                    $candidate.NotAfter -le $renewalThreshold -or -not $candidate.HasPrivateKey) {
                    return $false
                }
                $basicExtension = $candidate.Extensions['2.5.29.19']
                $usageExtension = $candidate.Extensions['2.5.29.15']
                $enhancedUsageExtension = $candidate.Extensions['2.5.29.37']
                if (-not $basicExtension -or -not $basicExtension.Critical -or
                    -not $usageExtension -or -not $enhancedUsageExtension) {
                    return $false
                }
                $basicConstraints = [System.Security.Cryptography.X509Certificates.X509BasicConstraintsExtension]::new($basicExtension, $basicExtension.Critical)
                $keyUsage = [System.Security.Cryptography.X509Certificates.X509KeyUsageExtension]::new($usageExtension, $usageExtension.Critical)
                $enhancedKeyUsage = [System.Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension]::new($enhancedUsageExtension, $enhancedUsageExtension.Critical)
                if ($basicConstraints.CertificateAuthority -or
                    ($keyUsage.KeyUsages -band [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::DigitalSignature) -eq 0 -or
                    ($keyUsage.KeyUsages -band [System.Security.Cryptography.X509Certificates.X509KeyUsageFlags]::KeyCertSign) -ne 0 -or
                    -not @($enhancedKeyUsage.EnhancedKeyUsages | Where-Object { $_.Value -eq '1.3.6.1.5.5.7.3.3' }).Count) {
                    return $false
                }
                $privateKey = $null
                try {
                    $privateKey = [System.Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPrivateKey($candidate)
                    return ($privateKey -is [System.Security.Cryptography.RSACng] -and
                        $privateKey.Key.ExportPolicy -eq [System.Security.Cryptography.CngExportPolicies]::None -and
                        $privateKey.Key.KeySize -ge 3072)
                } catch [System.Security.Cryptography.CryptographicException] {
                    return $false
                } finally {
                    if ($privateKey) { $privateKey.Dispose() }
                }
            }
            $cert = Get-ChildItem Cert:\CurrentUser\My |
                Where-Object { Test-LocalCertificate $_ $subject $threshold } |
                Sort-Object NotAfter -Descending |
                Select-Object -First 1
            if (-not $cert) {
                $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $subject `
                    -KeyUsage DigitalSignature -TextExtension @('2.5.29.19={critical}{text}ca=false') `
                    -KeyExportPolicy NonExportable -KeyAlgorithm RSA -KeyLength 3072 -HashAlgorithm SHA256 `
                    -NotAfter (Get-Date).AddDays({{lifetimeDays}}) -CertStoreLocation Cert:\CurrentUser\My
            }
            if (-not (Test-LocalCertificate $cert $subject $threshold)) {
                throw 'The local test certificate does not meet the required code-signing profile.'
            }
            Get-ChildItem Cert:\CurrentUser\My |
                Where-Object { $_.Subject -eq $subject -and $_.Thumbprint -ne $cert.Thumbprint } |
                ForEach-Object { Remove-Item $_.PSPath -DeleteKey }
            {{trustBlock}}
            $hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($cert.RawData)
            Write-Output ('{{FingerprintMarker}}' + (($hash | ForEach-Object { $_.ToString('X2') }) -join ''))
            """;
    }

    internal static string BuildRemoveScript(string subject) {
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

    /// <summary>
    /// Deletes an untrusted developer certificate from <c>My</c> so an interrupted run leaves no private key behind.
    /// </summary>
    /// <remarks>
    /// Skips anything already present in <c>Root</c>: that developer answered the confirmation, and taking the key away
    /// would break a working setup. Only <c>My</c> is written, so this never prompts either.
    /// </remarks>
    internal static string BuildRollbackScript(string subject) {
        var escaped = EscapeSingleQuoted(subject);
        return $$"""
            $ErrorActionPreference = 'Stop'
            $subject = '{{escaped}}'
            $trusted = @(Get-ChildItem Cert:\CurrentUser\Root |
                Where-Object { $_.Subject -eq $subject }).Count -gt 0
            if (-not $trusted) {
                Get-ChildItem Cert:\CurrentUser\My |
                    Where-Object { $_.Subject -eq $subject } |
                    ForEach-Object { Remove-Item $_.PSPath -DeleteKey }
            }
            """;
    }

    internal static string ParseFingerprint(string scriptOutput) {
        var fingerprints = scriptOutput
            .Split(['\r', '\n'], StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Where(line => line.StartsWith(FingerprintMarker, StringComparison.Ordinal))
            .Select(line => line[FingerprintMarker.Length..])
            .ToArray();

        if (fingerprints.Length != 1 || fingerprints[0].Length != 64 || !fingerprints[0].All(Uri.IsHexDigit)) {
            throw new InvalidOperationException("Certificate script did not return a valid SHA-256 fingerprint.");
        }

        return fingerprints[0].ToUpperInvariant();
    }

    private static string EscapeSingleQuoted(string value) => value.Replace("'", "''");

    private static async Task<string> RunPowerShellAsync(
        string script,
        CancellationToken cancellationToken,
        bool trustStoreChanges) {
        if (!OperatingSystem.IsWindows()) {
            throw new PlatformNotSupportedException("Test certificates are only supported on Windows.");
        }

        var encoded = Convert.ToBase64String(Encoding.Unicode.GetBytes(script));
        var startInfo = new ProcessStartInfo("powershell.exe") {
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
        var stdout = process.StandardOutput.ReadToEndAsync(CancellationToken.None);
        var stderr = process.StandardError.ReadToEndAsync(CancellationToken.None);
        try {
            await process.WaitForExitAsync(timeout.Token);
        }
        catch (OperationCanceledException) {
            process.Kill(entireProcessTree: true);
            await process.WaitForExitAsync(CancellationToken.None);
            if (cancellationToken.IsCancellationRequested) {
                throw;
            }

            await RollBackCertificateAsync(cancellationToken);
            throw new TimeoutException(
                $"Certificate script did not finish within {PowerShellTimeout.TotalSeconds:0} seconds"
                + (trustStoreChanges
                    ? ". If Windows is asking whether to trust the pyRevit Local Dev root certificate, answer it and rerun."
                    : "."));
        }

        if (process.ExitCode != 0) {
            await RollBackCertificateAsync(cancellationToken);
            throw new InvalidOperationException($"Certificate script failed: {await stderr}");
        }

        return await stdout;
    }

    /// <summary>
    /// Removes an untrusted developer certificate after a failed or interrupted script, so no private key is left in
    /// <c>My</c> for a trust step the developer never completed.
    /// </summary>
    /// <remarks>
    /// Best effort by design: the original failure is what the caller needs to see, so nothing here can mask it. A
    /// failed rollback only leaves the key for <c>ci local --remove-cert</c> to clear. It goes through
    /// <see cref="ExecutePowerShellAsync"/> rather than <see cref="RunPowerShellAsync"/>, which would recurse back
    /// into this rollback on its own failure.
    /// </remarks>
    private static async Task RollBackCertificateAsync(CancellationToken cancellationToken) {
        try {
            using var rollback = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            rollback.CancelAfter(RollbackTimeout);
            await ExecutePowerShellAsync(BuildRollbackScript(LocalSubject(Environment.MachineName)), rollback.Token);
        }
        catch (Exception) {
        }
    }

    /// <summary>Runs a certificate script and returns its output, with no rollback of its own.</summary>
    private static async Task<string> ExecutePowerShellAsync(string script, CancellationToken cancellationToken) {
        var encoded = Convert.ToBase64String(Encoding.Unicode.GetBytes(script));
        var startInfo = new ProcessStartInfo("powershell.exe") {
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        startInfo.ArgumentList.Add("-NoProfile");
        startInfo.ArgumentList.Add("-EncodedCommand");
        startInfo.ArgumentList.Add(encoded);

        using var process = Process.Start(startInfo)
            ?? throw new InvalidOperationException("Could not start powershell.exe.");
        var stdout = process.StandardOutput.ReadToEndAsync(CancellationToken.None);
        await process.WaitForExitAsync(cancellationToken);
        if (process.ExitCode != 0) {
            throw new InvalidOperationException(
                $"Certificate script failed: {await process.StandardError.ReadToEndAsync(CancellationToken.None)}");
        }

        return await stdout;
    }
}
