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
        bool ci = false)
        => TestCertificateHelper.EnsureModesAllowed(local, signTest, removeCert, pack, sign, publish, channel, ci);

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
    public void ParseFingerprint_takes_last_line_and_uppercases()
    {
        var thumbprint = TestCertificateHelper.ParseFingerprint("noise\r\nabcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789\r\n");

        Assert.AreEqual("ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789", thumbprint);
    }

    [TestMethod]
    public void ParseFingerprint_rejects_garbage()
    {
        Assert.ThrowsExactly<InvalidOperationException>(() => TestCertificateHelper.ParseFingerprint("oops"));
        Assert.ThrowsExactly<InvalidOperationException>(() => TestCertificateHelper.ParseFingerprint(""));
    }
}
