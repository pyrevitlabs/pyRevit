using System.Diagnostics;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using Build.Helpers;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
public sealed class TestSignatureDetectorTests {
    [TestMethod]
    [DataRow("CN=pyRevit Local Dev (BOX)", true)]
    [DataRow("CN=pyRevit CI Test 123", true)]
    [DataRow("cn=pyrevit local dev (box)", true)]
    [DataRow("CN=pyRevit Labs", false)]
    [DataRow("", false)]
    [DataRow(null, false)]
    public void IsTestSigner_matches_only_test_certificate_subjects(string? subject, bool expected) {
        Assert.AreEqual(expected, TestSignatureDetector.IsTestSigner(subject));
    }

    [TestMethod]
    public void IsTestSigner_accepts_the_local_developer_subject() {
        Assert.IsTrue(TestSignatureDetector.IsTestSigner(TestCertificateStore.LocalSubject("BOX")));
    }

    [TestMethod]
    [DataRow("CN=pyRevit CI Test run-42")]
    [DataRow("CN=pyRevit Local Dev (BOX)")]
    public void EnsureTestSigner_accepts_test_subjects(string subject) {
        using var certificate = CreateCodeSigningCertificate(subject);

        TestSignatureDetector.EnsureTestSigner(certificate);
    }

    [TestMethod]
    [DataRow("CN=GitHub Actions Runner")]
    [DataRow("CN=pyRevit Labs")]
    public void EnsureTestSigner_refuses_other_subjects(string subject) {
        using var certificate = CreateCodeSigningCertificate(subject);

        Assert.ThrowsExactly<InvalidOperationException>(() => TestSignatureDetector.EnsureTestSigner(certificate));
    }

    [TestMethod]
    public void EnsureTestSigner_rejects_null_certificate() {
        Assert.ThrowsExactly<ArgumentNullException>(() => TestSignatureDetector.EnsureTestSigner(null!));
    }

    [TestMethod]
    public void FindTestSignedFiles_ignores_unsigned_files() {
        using var bin = new TempBin();
        var file = bin.AddBinary("pyRevitUnsigned.dll");

        Assert.AreEqual(0, TestSignatureDetector.FindTestSignedFiles([file]).Count);
    }

    [TestMethod]
    public void EnsureNoTestSignedBinaries_rejects_a_test_signed_binary() {
        using var bin = new TempBin();
        SignWithThrowawayCertificate(bin.AddBinary("pyRevitProbe.dll"), "CN=pyRevit CI Test probe");

        var error = Assert.ThrowsExactly<InvalidOperationException>(
            () => TestSignatureDetector.EnsureNoTestSignedBinaries(bin.Path));
        StringAssert.Contains(error.Message, "pyRevitProbe.dll");
    }

    [TestMethod]
    public void EnsureNoTestSignedBinaries_accepts_unsigned_and_other_signers() {
        using var bin = new TempBin();
        bin.AddBinary("pyRevitUnsigned.dll");
        SignWithThrowawayCertificate(bin.AddBinary("pyRevitOther.dll"), "CN=Someone Else");

        TestSignatureDetector.EnsureNoTestSignedBinaries(bin.Path);
    }

    private static X509Certificate2 CreateCodeSigningCertificate(string subject) {
        using var rsa = RSA.Create(2048);
        var request = new CertificateRequest(subject, rsa, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1);
        request.CertificateExtensions.Add(
            new X509EnhancedKeyUsageExtension([new Oid("1.3.6.1.5.5.7.3.3")], critical: false));
        return request.CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-5), DateTimeOffset.UtcNow.AddDays(1));
    }

    private static void SignWithThrowawayCertificate(string file, string subject) {
        if (!OperatingSystem.IsWindows()) {
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
        var startInfo = new ProcessStartInfo("powershell.exe") {
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

    private sealed class TempBin : IDisposable {
        public string Path { get; } = Directory.CreateTempSubdirectory("pyrevit-bin-").FullName;

        public string AddBinary(string name) {
            var file = System.IO.Path.Combine(Path, name);
            File.Copy(typeof(TestSignatureDetectorTests).Assembly.Location, file);
            return file;
        }

        public void Dispose() => Directory.Delete(Path, recursive: true);
    }
}
