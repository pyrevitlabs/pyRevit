using System.Diagnostics;
using System.Text;
using Build.Options;
using ModularPipelines.Context;
using ModularPipelines.Models;
using ModularPipelines.Options;

namespace Build.Helpers;

/// <summary>
/// Creates, trusts and removes the self-signed code-signing certificates used to sign test builds.
/// </summary>
/// <remarks>
/// These certificates must never sign anything that is uploaded, released or installed outside the machine
/// that created them. <see cref="EnsureModesAllowed"/> is the guard that keeps them away from production signing.
/// </remarks>
public static class TestCertificateHelper
{
    public const int LocalLifetimeDays = 365;
    public const int LocalRenewBeforeDays = 30;
    public const string LocalSubjectPrefix = "CN=pyRevit Local Dev";
    public const string CiSubjectPrefix = "CN=pyRevit CI Test";

    /// <summary>Subject of the per-machine developer certificate; also what <c>--remove-cert</c> deletes.</summary>
    public static string LocalSubject(string machineName) => $"{LocalSubjectPrefix} ({machineName})";

    public static bool IsTestSigner(string? subject) =>
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

    private static string? ReadSignerSubject(string file)
    {
        try
        {
#pragma warning disable SYSLIB0057
            return System.Security.Cryptography.X509Certificates.X509Certificate.CreateFromSignedFile(file).Subject;
#pragma warning restore SYSLIB0057
        }
        catch (System.Security.Cryptography.CryptographicException)
        {
            return null;
        }
    }

    /// <summary>
    /// Guards the test-signing modes. Throws when they are combined with production modes, run on a shipping
    /// channel, or (for the developer-certificate modes) run under CI.
    /// </summary>
    public static void EnsureModesAllowed(
        bool local,
        bool signTest,
        bool removeCert,
        bool pack,
        bool sign,
        bool publish,
        string channel,
        bool runningOnCi)
    {
        if (!local && !signTest && !removeCert)
        {
            return;
        }

        if (pack || sign || publish)
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

        if ((local || removeCert) && runningOnCi)
        {
            throw new InvalidOperationException(
                "'local' and '--remove-cert' use a developer certificate and cannot run when CI is set.");
        }

        if (local && signTest)
        {
            throw new InvalidOperationException("'local' and 'sign-test' cannot be combined.");
        }

        if (signTest && removeCert)
        {
            throw new InvalidOperationException("'sign-test' and '--remove-cert' cannot be combined.");
        }
    }

    public static string BuildEnsureScript(string subject, int lifetimeDays, int renewBeforeDays)
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
            Write-Output (($hash | ForEach-Object { $_.ToString('X2') }) -join '')
            """;
    }

    public static string BuildRemoveScript(string subject)
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

    public static string ParseFingerprint(string scriptOutput)
    {
        var fingerprint = scriptOutput
            .Split(['\r', '\n'], StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .LastOrDefault();

        if (string.IsNullOrEmpty(fingerprint) || fingerprint.Length != 64 || !fingerprint.All(Uri.IsHexDigit))
        {
            throw new InvalidOperationException("Certificate script did not return a valid SHA-256 fingerprint.");
        }

        return fingerprint.ToUpperInvariant();
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
    public static async Task<CommandResult> SignFilesAsync(
        IModuleContext context,
        string fingerprint,
        IEnumerable<string> files,
        string summaryLabel,
        CancellationToken cancellationToken)
    {
        var fileList = files.ToArray();
        if (fileList.Length == 0)
        {
            throw new InvalidOperationException("No files were provided for signing.");
        }

        context.Summary.KeyValue("Test signing", summaryLabel, SigningHelper.BuildSigningSummary(fileList));

        await SigningHelper.EnsureSignToolInstalledAsync(context, cancellationToken);

        var arguments = new List<string> { "code", "certificate-store" };
        arguments.AddRange(fileList);
        arguments.AddRange(
        [
            "--certificate-fingerprint", fingerprint,
            "--file-digest", "SHA256",
        ]);

        return await context.Shell.Command.ExecuteCommandLineTool(
            new GenericCommandLineToolOptions(SigningHelper.GetSignExecutablePath())
            {
                Arguments = arguments,
            },
            cancellationToken: cancellationToken);
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

        using var process = Process.Start(startInfo)
            ?? throw new InvalidOperationException("Could not start powershell.exe.");
        var stdout = process.StandardOutput.ReadToEndAsync(cancellationToken);
        var stderr = process.StandardError.ReadToEndAsync(cancellationToken);
        try
        {
            await process.WaitForExitAsync(cancellationToken);
        }
        catch (OperationCanceledException)
        {
            process.Kill(entireProcessTree: true);
            await process.WaitForExitAsync(CancellationToken.None);
            throw;
        }

        if (process.ExitCode != 0)
        {
            throw new InvalidOperationException($"Certificate script failed: {await stderr}");
        }

        return await stdout;
    }
}
