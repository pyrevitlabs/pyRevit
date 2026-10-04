using Build.Helpers;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
public sealed class TestCertificateStoreTests
{
    private const string Hash = "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789";

    [TestMethod]
    public void LocalSubject_includes_machine_name()
    {
        Assert.AreEqual("CN=pyRevit Local Dev (BOX)", TestCertificateStore.LocalSubject("BOX"));
    }

    [TestMethod]
    public void BuildEnsureScript_creates_non_exportable_certificate_and_trusts_it()
    {
        var script = TestCertificateStore.BuildEnsureScript("CN=pyRevit Local Dev (BOX)", 365, 30);

        StringAssert.Contains(script, "$subject = 'CN=pyRevit Local Dev (BOX)'");
        StringAssert.Contains(script, "-KeyExportPolicy NonExportable");
        StringAssert.Contains(script, "AddDays(365)");
        StringAssert.Contains(script, "AddDays(30)");
        StringAssert.Contains(script, "'Root', 'TrustedPublisher'");
        StringAssert.Contains(script, "$store.Remove($stale)");
    }

    [TestMethod]
    public void BuildEnsureScript_creates_an_end_entity_that_cannot_issue_certificates()
    {
        var script = TestCertificateStore.BuildEnsureScript("CN=x", 1, 0);

        StringAssert.Contains(script, "-KeyUsage DigitalSignature");
        StringAssert.Contains(script, "2.5.29.19={critical}{text}ca=false");
    }

    [TestMethod]
    public void BuildEnsureScript_escapes_single_quotes_in_subject()
    {
        var script = TestCertificateStore.BuildEnsureScript("CN=O'Brien", 1, 0);

        StringAssert.Contains(script, "$subject = 'CN=O''Brien'");
    }

    [TestMethod]
    public void BuildEnsureScript_removes_superseded_certificates_with_their_keys()
    {
        var script = TestCertificateStore.BuildEnsureScript("CN=x", 1, 0);

        StringAssert.Contains(script, "$_.Thumbprint -ne $cert.Thumbprint } |");
        StringAssert.Contains(script, "Remove-Item $_.PSPath -DeleteKey }");
    }

    [TestMethod]
    public void BuildEnsureScript_marks_the_fingerprint_line()
    {
        var script = TestCertificateStore.BuildEnsureScript("CN=x", 1, 0);

        StringAssert.Contains(script, "Write-Output ('FINGERPRINT=' + ");
    }

    [TestMethod]
    public void BuildRemoveScript_covers_all_three_stores()
    {
        var script = TestCertificateStore.BuildRemoveScript("CN=pyRevit Local Dev (BOX)");

        StringAssert.Contains(script, "'My', 'Root', 'TrustedPublisher'");
        StringAssert.Contains(script, "-DeleteKey");
    }

    [TestMethod]
    public void BuildRemoveScript_does_not_swallow_errors()
    {
        var script = TestCertificateStore.BuildRemoveScript("CN=x");

        Assert.IsFalse(script.Contains("SilentlyContinue"));
    }

    [TestMethod]
    public void ParseFingerprint_reads_marked_line_and_uppercases()
    {
        var fingerprint = TestCertificateStore.ParseFingerprint($"noise\r\nFINGERPRINT={Hash}\r\nmore noise\r\n");

        Assert.AreEqual(Hash.ToUpperInvariant(), fingerprint);
    }

    [TestMethod]
    public void ParseFingerprint_ignores_unmarked_hash_lines()
    {
        Assert.ThrowsExactly<InvalidOperationException>(() => TestCertificateStore.ParseFingerprint(Hash));
    }

    [TestMethod]
    public void ParseFingerprint_rejects_multiple_marked_lines()
    {
        Assert.ThrowsExactly<InvalidOperationException>(
            () => TestCertificateStore.ParseFingerprint($"FINGERPRINT={Hash}\nFINGERPRINT={Hash}"));
    }

    [TestMethod]
    public void ParseFingerprint_rejects_garbage()
    {
        Assert.ThrowsExactly<InvalidOperationException>(() => TestCertificateStore.ParseFingerprint("FINGERPRINT=oops"));
        Assert.ThrowsExactly<InvalidOperationException>(() => TestCertificateStore.ParseFingerprint(""));
    }

    [TestMethod]
    public void EnsureFingerprintIsTestCertificate_rejects_unknown_fingerprint()
    {
        if (!OperatingSystem.IsWindows())
        {
            Assert.Inconclusive("Certificate stores are only probed on Windows.");
        }

        Assert.ThrowsExactly<InvalidOperationException>(
            () => TestCertificateStore.EnsureFingerprintIsTestCertificate(new string('0', 64)));
    }
}
