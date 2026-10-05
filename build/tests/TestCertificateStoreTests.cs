using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using Build.Helpers;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
public sealed class TestCertificateStoreTests {
    private const string Hash = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789";

    [TestMethod]
    public void LocalSubject_includes_machine_name() {
        Assert.AreEqual("CN=pyRevit Local Dev (BOX)", TestCertificateStore.LocalSubject("BOX"));
    }
    [TestMethod]
    public void BuildEnsureScript_creates_non_exportable_certificate_and_trusts_it()
    {
        var script = TestCertificateStore.BuildEnsureScript("CN=pyRevit Local Dev (BOX)", 365, 30, trustInRootStore: true);

        StringAssert.Contains(script, "$subject = 'CN=pyRevit Local Dev (BOX)'");
        StringAssert.Contains(script, "-KeyExportPolicy NonExportable");
        StringAssert.Contains(script, "AddDays(365)");
        StringAssert.Contains(script, "AddDays(30)");
        StringAssert.Contains(script, "'Root', 'TrustedPublisher'");
        StringAssert.Contains(script, "$store.Remove($stale)");
    }

    [TestMethod]
    public void BuildEnsureScript_without_trust_writes_no_trust_store()
    {
        // The build path must never raise the modal Windows root prompt, so trust-store writes belong to
        // '--trust-cert' only.
        var script = TestCertificateStore.BuildEnsureScript("CN=pyRevit Local Dev (BOX)", 365, 30);

        Assert.IsFalse(script.Contains("$store.Add("), script);
        Assert.IsFalse(script.Contains("'Root', 'TrustedPublisher'"), script);
        Assert.IsFalse(script.Contains("X509Store"), script);
        StringAssert.Contains(script, "-CertStoreLocation Cert:\\CurrentUser\\My");
    }

    [TestMethod]
    public void BuildEnsureScript_defaults_to_not_trusting()
    {
        Assert.AreEqual(
            TestCertificateStore.BuildEnsureScript("CN=x", 365, 30),
            TestCertificateStore.BuildEnsureScript("CN=x", 365, 30, trustInRootStore: false));
    }

    [TestMethod]
    public void BuildEnsureScript_creates_an_end_entity_that_cannot_issue_certificates() {
        var script = TestCertificateStore.BuildEnsureScript("CN=x", 1, 0);

        StringAssert.Contains(script, "-KeyUsage DigitalSignature");
        StringAssert.Contains(script, "2.5.29.19={critical}{text}ca=false");
    }

    [TestMethod]
    public void BuildEnsureScript_rejects_a_reused_ca_or_exportable_certificate() {
        var script = TestCertificateStore.BuildEnsureScript("CN=pyRevit Local Dev (BOX)", 365, 30);

        StringAssert.Contains(script, "Test-LocalCertificate $_ $subject $threshold");
        StringAssert.Contains(script, "$basicConstraints.CertificateAuthority");
        StringAssert.Contains(script, "$privateKey.Key.ExportPolicy -eq [System.Security.Cryptography.CngExportPolicies]::None");
        StringAssert.Contains(script, "if (-not (Test-LocalCertificate $cert $subject $threshold))");
    }

    [TestMethod]
    public void BuildEnsureScript_escapes_single_quotes_in_subject() {
        var script = TestCertificateStore.BuildEnsureScript("CN=O'Brien", 1, 0);

        StringAssert.Contains(script, "$subject = 'CN=O''Brien'");
    }

    [TestMethod]
    public void BuildEnsureScript_removes_superseded_certificates_with_their_keys() {
        var script = TestCertificateStore.BuildEnsureScript("CN=x", 1, 0);

        StringAssert.Contains(script, "$_.Thumbprint -ne $cert.Thumbprint } |");
        StringAssert.Contains(script, "Remove-Item $_.PSPath -DeleteKey }");
    }

    [TestMethod]
    public void BuildEnsureScript_marks_the_fingerprint_line() {
        var script = TestCertificateStore.BuildEnsureScript("CN=x", 1, 0);

        StringAssert.Contains(script, "Write-Output ('FINGERPRINT=' + ");
    }

    [TestMethod]
    public void BuildRemoveScript_covers_all_three_stores() {
        var script = TestCertificateStore.BuildRemoveScript("CN=pyRevit Local Dev (BOX)");

        StringAssert.Contains(script, "'My', 'Root', 'TrustedPublisher'");
        StringAssert.Contains(script, "-DeleteKey");
    }

    [TestMethod]
    public void BuildRemoveScript_does_not_swallow_errors() {
        var script = TestCertificateStore.BuildRemoveScript("CN=x");

        Assert.IsFalse(script.Contains("SilentlyContinue"));
    }

    [TestMethod]
    public void BuildRollbackScript_only_deletes_an_untrusted_certificate() {
        // A killed trust step used to leave the private key behind, so the next run hit the same prompt again.
        var script = TestCertificateStore.BuildRollbackScript("CN=pyRevit Local Dev (BOX)");

        StringAssert.Contains(script, "$subject = 'CN=pyRevit Local Dev (BOX)'");
        StringAssert.Contains(script, "if (-not $trusted) {");
        StringAssert.Contains(script, "Cert:\\CurrentUser\\Root");
        StringAssert.Contains(script, "Remove-Item $_.PSPath -DeleteKey");
    }

    [TestMethod]
    public void BuildRollbackScript_never_writes_a_trust_store() {
        var script = TestCertificateStore.BuildRollbackScript("CN=x");

        Assert.IsFalse(script.Contains("X509Store"), script);
        Assert.IsFalse(script.Contains(".Add("), script);
    }

    [TestMethod]
    public void Certificate_script_timeout_is_short_enough_to_fail_an_unattended_run()
    {
        // The only step that can legitimately wait is the root confirmation, and that is now its own mode.
        Assert.IsTrue(
            TestCertificateStore.PowerShellTimeout <= TimeSpan.FromMinutes(2),
            $"timeout was {TestCertificateStore.PowerShellTimeout}");
        Assert.IsTrue(TestCertificateStore.RollbackTimeout < TestCertificateStore.PowerShellTimeout);
    }

    [TestMethod]
    public void ContainsSubject_matches_the_local_subject_including_its_parentheses()
    {
        // FindBySubjectName does not match this subject, which would make every 'ci local' run report the
        // certificate as untrusted even after it was trusted.
        using var certificate = CreateSelfSigned(TestCertificateStore.LocalSubject("BOX"));
        var certificates = new X509Certificate2Collection(certificate);

        Assert.IsTrue(TestCertificateStore.ContainsSubject(certificates, "CN=pyRevit Local Dev (BOX)"));
        Assert.IsFalse(TestCertificateStore.ContainsSubject(certificates, "CN=pyRevit Local Dev (OTHER)"));
        Assert.IsFalse(TestCertificateStore.ContainsSubject(certificates, "CN=pyRevit Labs"));
    }

    [TestMethod]
    public void EnsureFingerprintIsTrusted_refuses_a_certificate_that_is_not_the_trusted_one()
    {
        if (!OperatingSystem.IsWindows()) {
            Assert.Inconclusive("Certificate stores are only probed on Windows.");
        }

        // The shape that produced 100 binaries Windows reported as unverified: something with the right subject is
        // trusted, but the certificate actually signing is a different one.
        using var installed = InstalledCertificate.ForLocalDeveloperSubject();

        var error = Assert.ThrowsExactly<InvalidOperationException>(
            () => TestCertificateStore.EnsureFingerprintIsTrusted(installed.Fingerprint));

        StringAssert.Contains(error.Message, installed.Fingerprint);
        StringAssert.Contains(error.Message, "--trust-cert");
    }

    private static X509Certificate2 CreateSelfSigned(string subject)
    {
        using var rsa = RSA.Create(2048);
        return new CertificateRequest(subject, rsa, HashAlgorithmName.SHA256, RSASignaturePadding.Pkcs1)
            .CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-5), DateTimeOffset.UtcNow.AddDays(1));
    }

    [TestMethod]
    public void EnsureCertificateIsTrusted_reports_the_command_that_fixes_it() {
        if (!OperatingSystem.IsWindows()) {
            Assert.Inconclusive("Certificate stores are only probed on Windows.");
        }

        // A subject this test owns is never trusted, so the check must refuse and name --trust-cert.
        var subject = TestCertificateStore.LocalSubject($"untrusted-{Guid.NewGuid():N}");

        var error = Assert.ThrowsExactly<InvalidOperationException>(
            () => TestCertificateStore.EnsureCertificateIsTrusted(subject));

        StringAssert.Contains(error.Message, subject);
        // The message must name a command that is actually accepted: 'local' and '--trust-cert' are refused together.
        StringAssert.Contains(error.Message, "Run '--trust-cert' on its own");
    }

    [TestMethod]
    public void ParseFingerprint_reads_marked_line_and_uppercases() {
        var fingerprint = TestCertificateStore.ParseFingerprint($"noise\r\nFINGERPRINT={Hash}\r\nmore noise\r\n");

        Assert.AreEqual(Hash.ToUpperInvariant(), fingerprint);
    }

    [TestMethod]
    public void ParseFingerprint_ignores_unmarked_hash_lines() {
        Assert.ThrowsExactly<InvalidOperationException>(() => TestCertificateStore.ParseFingerprint(Hash));
    }

    [TestMethod]
    public void ParseFingerprint_rejects_multiple_marked_lines() {
        Assert.ThrowsExactly<InvalidOperationException>(
            () => TestCertificateStore.ParseFingerprint($"FINGERPRINT={Hash}\nFINGERPRINT={Hash}"));
    }

    [TestMethod]
    public void ParseFingerprint_rejects_garbage() {
        Assert.ThrowsExactly<InvalidOperationException>(() => TestCertificateStore.ParseFingerprint("FINGERPRINT=oops"));
        Assert.ThrowsExactly<InvalidOperationException>(() => TestCertificateStore.ParseFingerprint(""));
    }
    [TestMethod]
    public void EnsureFingerprintIsTestCertificate_rejects_unknown_fingerprint()
    {
        if (!OperatingSystem.IsWindows()) {
            Assert.Inconclusive("Certificate stores are only probed on Windows.");
        }

        Assert.ThrowsExactly<InvalidOperationException>(
            () => TestCertificateStore.EnsureFingerprintIsTestCertificate(new string('0', 64)));
    }

    [TestMethod]
    public void EnsureFingerprintIsTestCertificate_accepts_a_local_certificate_in_the_store()
    {
        if (!OperatingSystem.IsWindows()) {
            Assert.Inconclusive("Certificate stores are only probed on Windows.");
        }

        using var installed = InstalledCertificate.ForLocalDeveloperSubject();

        TestCertificateStore.EnsureFingerprintIsTestCertificate(installed.Fingerprint);
    }

    [TestMethod]
    public void EnsureFingerprintIsTestCertificate_refuses_a_non_test_certificate_in_the_store()
    {
        if (!OperatingSystem.IsWindows()) {
            Assert.Inconclusive("Certificate stores are only probed on Windows.");
        }

        using var installed = InstalledCertificate.ForSubject("CN=pyRevit Labs");

        Assert.ThrowsExactly<InvalidOperationException>(
            () => TestCertificateStore.EnsureFingerprintIsTestCertificate(installed.Fingerprint));
    }

    /// <summary>A throwaway certificate added to <c>CurrentUser\My</c> for the duration of one test.</summary>
    private sealed class InstalledCertificate : IDisposable
    {
        private InstalledCertificate(string thumbprint, string subject, X509Certificate2 certificate)
        {
            Thumbprint = thumbprint;
            Fingerprint = certificate.GetCertHashString(HashAlgorithmName.SHA256);
        }

        public string Fingerprint { get; }

        private string Thumbprint { get; }

        public static InstalledCertificate ForSubject(string subject)
        {
            var certificate = CreateSelfSigned(subject);

            var store = new X509Store(StoreName.My, StoreLocation.CurrentUser);
            store.Open(OpenFlags.ReadWrite);
            store.Add(certificate);
            store.Close();

            return new InstalledCertificate(certificate.Thumbprint, subject, certificate);
        }

        public static InstalledCertificate ForLocalDeveloperSubject() =>
            ForSubject(TestCertificateStore.LocalSubject(Environment.MachineName));

        /// <remarks>
        /// Removes only the certificate it added, matched on its own thumbprint. Deleting by subject would take the
        /// developer's real <c>CN=pyRevit Local Dev</c> certificate with it.
        /// </remarks>
        public void Dispose()
        {
            var store = new X509Store(StoreName.My, StoreLocation.CurrentUser);
            store.Open(OpenFlags.ReadWrite);
            foreach (var certificate in store.Certificates.Where(candidate => candidate.Thumbprint == Thumbprint))
            {
                store.Remove(certificate);
            }

            store.Close();
        }
    }
}
