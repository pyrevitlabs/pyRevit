using System.Diagnostics;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using Build.Helpers;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
public sealed class TestCertificateHelperTests
{
    private static void Ensure(
        bool local = false,
        bool signTest = false,
        bool removeCert = false,
        bool pack = false,
        bool sign = false,
        bool publish = false,
        string channel = "none",
        bool ci = false,
        bool windows = true)
        => TestCertificateHelper.EnsureModesAllowed(
            new PipelineModes(
                Ci: false,
                Pack: pack,
                Sign: sign,
                Publish: publish,
                Notify: false,
                Release: false,
                Winget: false,
                Local: local,
                SignTest: signTest,
                RemoveCert: removeCert),
            channel,
            ci,
            windows);

    [TestMethod]
    public void EnsureModesAllowed_ignores_plain_builds()
    {
        Ensure(pack: true, sign: true, publish: true, channel: "release", ci: true);
    }

    [TestMethod]
    public void EnsureModesAllowed_accepts_local_on_developer_machine()
    {
        Ensure(local: true);
    }

    [TestMethod]
    public void EnsureModesAllowed_accepts_sign_test_on_ci()
    {
        Ensure(signTest: true, ci: true);
    }

    [TestMethod]
    public void EnsureModesAllowed_rejects_local_on_ci()
    {
        Assert.ThrowsExactly<InvalidOperationException>(() => Ensure(local: true, ci: true));
    }

    [TestMethod]
    public void EnsureModesAllowed_rejects_remove_cert_on_ci()
    {
        Assert.ThrowsExactly<InvalidOperationException>(() => Ensure(removeCert: true, ci: true));
    }

    [TestMethod]
    [DataRow("wip")]
    [DataRow("release")]
    [DataRow("WIP")]
    [DataRow("RELEASE")]
    public void EnsureModesAllowed_rejects_shipping_channels(string channel)
    {
        Assert.ThrowsExactly<InvalidOperationException>(() => Ensure(signTest: true, channel: channel));
        Assert.ThrowsExactly<InvalidOperationException>(() => Ensure(local: true, channel: channel));
    }

    [TestMethod]
    public void EnsureModesAllowed_rejects_production_modes()
    {
        Assert.ThrowsExactly<InvalidOperationException>(() => Ensure(signTest: true, sign: true));
        Assert.ThrowsExactly<InvalidOperationException>(() => Ensure(local: true, pack: true));
        Assert.ThrowsExactly<InvalidOperationException>(() => Ensure(signTest: true, publish: true));
    }

    [TestMethod]
    public void EnsureModesAllowed_rejects_local_with_sign_test()
    {
        Assert.ThrowsExactly<InvalidOperationException>(() => Ensure(local: true, signTest: true));
    }

    [TestMethod]
    public void EnsureModesAllowed_rejects_sign_test_with_remove_cert()
    {
        Assert.ThrowsExactly<InvalidOperationException>(() => Ensure(signTest: true, removeCert: true));
    }

    [TestMethod]
    public void EnsureModesAllowed_accepts_local_with_remove_cert()
    {
        Ensure(local: true, removeCert: true);
    }

    [TestMethod]
    public void EnsureModesAllowed_rejects_test_signing_off_windows()
    {
        Assert.ThrowsExactly<PlatformNotSupportedException>(() => Ensure(local: true, windows: false));
        Assert.ThrowsExactly<PlatformNotSupportedException>(() => Ensure(signTest: true, ci: true, windows: false));
        Assert.ThrowsExactly<PlatformNotSupportedException>(() => Ensure(removeCert: true, windows: false));
    }

    [TestMethod]
    public void EnsureModesAllowed_ignores_platform_for_plain_builds()
    {
        Ensure(pack: true, windows: false);
    }

    [TestMethod]
    public void LocalSubject_includes_machine_name()
    {
        Assert.AreEqual("CN=pyRevit Local Dev (BOX)", TestCertificateHelper.LocalSubject("BOX"));
    }

    [TestMethod]
    public void BuildEnsureScript_creates_non_exportable_certificate_and_trusts_it()
    {
        var script = TestCertificateHelper.BuildEnsureScript("CN=pyRevit Local Dev (BOX)", 365, 30);

        StringAssert.Contains(script, "$subject = 'CN=pyRevit Local Dev (BOX)'");
        StringAssert.Contains(script, "-KeyExportPolicy NonExportable");
        StringAssert.Contains(script, "AddDays(365)");
        StringAssert.Contains(script, "AddDays(30)");
        StringAssert.Contains(script, "'Root', 'TrustedPublisher'");
        StringAssert.Contains(script, "$store.Remove($stale)");
    }

    [TestMethod]
    public void BuildEnsureScript_escapes_single_quotes_in_subject()
    {
        var script = TestCertificateHelper.BuildEnsureScript("CN=O'Brien", 1, 0);

        StringAssert.Contains(script, "$subject = 'CN=O''Brien'");
    }

    [TestMethod]
    public void BuildRemoveScript_covers_all_three_stores()
    {
        var script = TestCertificateHelper.BuildRemoveScript("CN=pyRevit Local Dev (BOX)");

        StringAssert.Contains(script, "'My', 'Root', 'TrustedPublisher'");
        StringAssert.Contains(script, "-DeleteKey");
    }

    [TestMethod]
    public void ParseFingerprint_reads_marked_line_and_uppercases()
    {
        var thumbprint = TestCertificateHelper.ParseFingerprint(
            "noise\r\nFINGERPRINT=abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789\r\nmore noise\r\n");

        Assert.AreEqual("ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789", thumbprint);
    }

    [TestMethod]
    public void ParseFingerprint_ignores_unmarked_hash_lines()
    {
        Assert.ThrowsExactly<InvalidOperationException>(
            () => TestCertificateHelper.ParseFingerprint("abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"));
    }

    [TestMethod]
    public void ParseFingerprint_rejects_multiple_marked_lines()
    {
        const string line = "FINGERPRINT=abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789";
        Assert.ThrowsExactly<InvalidOperationException>(
            () => TestCertificateHelper.ParseFingerprint(line + "\n" + line));
    }

    [TestMethod]
    public void BuildEnsureScript_marks_the_fingerprint_line()
    {
        var script = TestCertificateHelper.BuildEnsureScript("CN=x", 1, 0);

        StringAssert.Contains(script, "Write-Output ('FINGERPRINT=' + ");
    }

    [TestMethod]
    public void ParseFingerprint_rejects_garbage()
    {
        Assert.ThrowsExactly<InvalidOperationException>(() => TestCertificateHelper.ParseFingerprint("oops"));
        Assert.ThrowsExactly<InvalidOperationException>(() => TestCertificateHelper.ParseFingerprint(""));
    }

    [TestMethod]
    [DataRow("CN=pyRevit Local Dev (BOX)", true)]
    [DataRow("CN=pyRevit CI Test 123", true)]
    [DataRow("cn=pyrevit local dev (box)", true)]
    [DataRow("CN=pyRevit Labs", false)]
    [DataRow("", false)]
    [DataRow(null, false)]
    public void IsTestSigner_matches_only_test_certificate_subjects(string? subject, bool expected)
    {
        Assert.AreEqual(expected, TestCertificateHelper.IsTestSigner(subject));
    }

    [TestMethod]
    public void FindTestSignedFiles_ignores_unsigned_files()
    {
        var file = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N") + ".dll");
        File.WriteAllBytes(file, [0x4D, 0x5A]);
        try
        {
            Assert.AreEqual(0, TestCertificateHelper.FindTestSignedFiles([file]).Count);
        }
        finally
        {
            File.Delete(file);
        }
    }

    [TestMethod]
    public void BuildEnsureScript_removes_superseded_certificates_with_their_keys()
    {
        var script = TestCertificateHelper.BuildEnsureScript("CN=x", 1, 0);

        StringAssert.Contains(script, "$_.Thumbprint -ne $cert.Thumbprint } |");
        StringAssert.Contains(script, "Remove-Item $_.PSPath -DeleteKey }");
    }

    [TestMethod]
    public void BuildRemoveScript_does_not_swallow_errors()
    {
        var script = TestCertificateHelper.BuildRemoveScript("CN=x");

        Assert.IsFalse(script.Contains("SilentlyContinue"));
    }

    [TestMethod]
    [DataRow("CN=pyRevit CI Test run-42")]
    [DataRow("CN=pyRevit Local Dev (BOX)")]
    public void EnsureTestSigner_accepts_test_subjects(string subject)
    {
        using var certificate = CreateCodeSigningCertificate(subject);

        TestCertificateHelper.EnsureTestSigner(certificate);
    }

    [TestMethod]
    [DataRow("CN=GitHub Actions Runner")]
    [DataRow("CN=pyRevit Labs")]
    public void EnsureTestSigner_refuses_other_subjects(string subject)
    {
        using var certificate = CreateCodeSigningCertificate(subject);

        Assert.ThrowsExactly<InvalidOperationException>(() => TestCertificateHelper.EnsureTestSigner(certificate));
    }

    [TestMethod]
    public void EnsureFingerprintIsTestCertificate_rejects_unknown_fingerprint()
    {
        if (!OperatingSystem.IsWindows())
        {
            Assert.Inconclusive("Certificate stores are only probed on Windows.");
        }

        Assert.ThrowsExactly<InvalidOperationException>(
            () => TestCertificateHelper.EnsureFingerprintIsTestCertificate(new string('0', 64)));
    }

    [TestMethod]
    public void EnsureNoTestSignedBinaries_rejects_a_test_signed_binary()
    {
        using var bin = new TempBin();
        SignWithThrowawayCertificate(bin.AddBinary("pyRevitProbe.dll"), "CN=pyRevit CI Test probe");

        var error = Assert.ThrowsExactly<InvalidOperationException>(
            () => TestCertificateHelper.EnsureNoTestSignedBinaries(bin.Path));
        StringAssert.Contains(error.Message, "pyRevitProbe.dll");
    }

    [TestMethod]
    public void EnsureNoTestSignedBinaries_accepts_unsigned_and_other_signers()
    {
        using var bin = new TempBin();
        bin.AddBinary("pyRevitUnsigned.dll");
        SignWithThrowawayCertificate(bin.AddBinary("pyRevitOther.dll"), "CN=Someone Else");

        TestCertificateHelper.EnsureNoTestSignedBinaries(bin.Path);
    }

    private static X509Certificate2 CreateCodeSigningCertificate(string subject)
    {
        using var rsa = RSA.Create(2048);
        var request = new CertificateRequest(subject, rsa, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
        request.CertificateExtensions.Add(
            new X509EnhancedKeyUsageExtension([new Oid("1.3.6.1.5.5.7.3.3")], critical: false));
        return request.CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-5), DateTimeOffset.UtcNow.AddDays(1));
    }

    private static void SignWithThrowawayCertificate(string file, string subject)
    {
        if (!OperatingSystem.IsWindows())
        {
            Assert.Inconclusive("Authenticode signing is only available on Windows.");
        }

        using var certificate = CreateCodeSigningCertificate(subject);
        var pfx = file + ".pfx";
        var password = Guid.NewGuid().ToString("N");
        File.WriteAllBytes(pfx, certificate.Export(X509ContentType.Pfx, password));

        var script = $$"""
            $ErrorActionPreference = 'Stop'
            $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2('{{pfx}}', '{{password}}')
            $result = Set-AuthenticodeSignature -FilePath '{{file}}' -Certificate $cert -HashAlgorithm SHA256
            if (-not $result.SignerCertificate) { throw $result.StatusMessage }
            """;
        var startInfo = new ProcessStartInfo("powershell.exe")
        {
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        startInfo.ArgumentList.Add("-NoProfile");
        startInfo.ArgumentList.Add("-EncodedCommand");
        startInfo.ArgumentList.Add(Convert.ToBase64String(System.Text.Encoding.Unicode.GetBytes(script)));

        using var process = Process.Start(startInfo)!;
        var stderr = process.StandardError.ReadToEnd();
        process.WaitForExit();
        File.Delete(pfx);
        Assert.AreEqual(0, process.ExitCode, stderr);
    }

    private sealed class TempBin : IDisposable
    {
        public string Path { get; } = Directory.CreateTempSubdirectory("pyrevit-bin-").FullName;

        public string AddBinary(string name)
        {
            var file = System.IO.Path.Combine(Path, name);
            File.Copy(typeof(TestCertificateHelperTests).Assembly.Location, file);
            return file;
        }

        public void Dispose() => Directory.Delete(Path, recursive: true);
    }
}
