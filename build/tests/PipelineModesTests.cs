using Build.Helpers;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
public sealed class PipelineModesTests
{
    [TestMethod]
    public void Parse_without_arguments_runs_ci_only()
    {
        var modes = PipelineModes.Parse([]);

        Assert.IsTrue(modes.Ci);
        Assert.IsFalse(modes.Packages);
        Assert.IsFalse(modes.UsesTestCertificates);
        Assert.IsFalse(modes.SignsTestBinaries);
    }

    [TestMethod]
    [DataRow("local")]
    [DataRow("--local")]
    [DataRow("LOCAL")]
    public void Parse_local_implies_ci_and_signs_with_local_certificate(string word)
    {
        var modes = PipelineModes.Parse([word]);

        Assert.IsTrue(modes.Ci);
        Assert.IsTrue(modes.SignsWithLocalCertificate);
        Assert.IsTrue(modes.SignsTestBinaries);
    }

    [TestMethod]
    public void Parse_remove_cert_runs_only_certificate_removal()
    {
        var modes = PipelineModes.Parse(["--remove-cert"]);

        Assert.IsFalse(modes.Ci);
        Assert.IsTrue(modes.RemoveCert);
        Assert.IsFalse(modes.SignsTestBinaries);
    }

    [TestMethod]
    public void Parse_local_with_remove_cert_neither_builds_nor_signs()
    {
        var modes = PipelineModes.Parse(["local", "--remove-cert"]);

        Assert.IsFalse(modes.Ci);
        Assert.IsFalse(modes.SignsWithLocalCertificate);
        Assert.IsFalse(modes.SignsTestBinaries);
    }

    [TestMethod]
    public void Parse_trust_cert_runs_only_the_trust_step()
    {
        var modes = PipelineModes.Parse(["--trust-cert"]);

        Assert.IsFalse(modes.Ci);
        Assert.IsTrue(modes.TrustCert);
        Assert.IsFalse(modes.SignsTestBinaries);
        Assert.IsTrue(modes.UsesTestCertificates);
    }

    [TestMethod]
    [DataRow("local", "--trust-cert")]
    [DataRow("--trust-cert", "local")]
    public void Parse_local_with_trust_cert_neither_builds_nor_signs(string first, string second)
    {
        var modes = PipelineModes.Parse([first, second]);

        Assert.IsFalse(modes.Ci);
        Assert.IsFalse(modes.SignsWithLocalCertificate);
        Assert.IsFalse(modes.SignsTestBinaries);
    }

    [TestMethod]
    public void Parse_sign_test_signs_without_local_certificate()
    {
        var modes = PipelineModes.Parse(["ci", "sign-test"]);

        Assert.IsTrue(modes.Ci);
        Assert.IsTrue(modes.SignsTestBinaries);
        Assert.IsFalse(modes.SignsWithLocalCertificate);
    }

    [TestMethod]
    public void Parse_sign_test_alone_does_not_build()
    {
        var modes = PipelineModes.Parse(["sign-test"]);

        Assert.IsFalse(modes.Ci);
        Assert.IsTrue(modes.SignsTestBinaries);
    }

    [TestMethod]
    [DataRow("pack")]
    [DataRow("sign")]
    [DataRow("publish")]
    public void Parse_packaging_modes_require_the_reject_guard(string word)
    {
        var modes = PipelineModes.Parse([word]);

        Assert.IsTrue(modes.Packages);
        Assert.IsFalse(modes.Ci);
    }

    [TestMethod]
    public void Parse_reads_remaining_modes()
    {
        var modes = PipelineModes.Parse(["notify", "release", "winget"]);

        Assert.IsTrue(modes.Notify);
        Assert.IsTrue(modes.Release);
        Assert.IsTrue(modes.Winget);
        Assert.IsFalse(modes.Ci);
    }

    private static void Ensure(
        bool local = false,
        bool signTest = false,
        bool removeCert = false,
        bool trustCert = false,
        bool pack = false,
        bool sign = false,
        bool publish = false,
        string channel = "none",
        bool ci = false,
        bool windows = true)
        => new PipelineModes(
                Ci: false,
                Pack: pack,
                Sign: sign,
                Publish: publish,
                Notify: false,
                Release: false,
                Winget: false,
                Local: local,
                SignTest: signTest,
                RemoveCert: removeCert,
                TrustCert: trustCert)
            .EnsureTestSigningAllowed(channel, ci, windows);

    [TestMethod]
    public void EnsureTestSigningAllowed_ignores_plain_builds()
    {
        Ensure(pack: true, sign: true, publish: true, channel: "release", ci: true);
    }

    [TestMethod]
    public void EnsureTestSigningAllowed_accepts_local_on_developer_machine()
    {
        Ensure(local: true);
    }

    [TestMethod]
    public void EnsureTestSigningAllowed_accepts_sign_test_on_ci()
    {
        Ensure(signTest: true, ci: true);
    }

    [TestMethod]
    public void EnsureTestSigningAllowed_rejects_local_on_ci()
    {
        Assert.ThrowsExactly<InvalidOperationException>(() => Ensure(local: true, ci: true));
    }

    [TestMethod]
    public void EnsureTestSigningAllowed_rejects_remove_cert_on_ci()
    {
        Assert.ThrowsExactly<InvalidOperationException>(() => Ensure(removeCert: true, ci: true));
    }

    [TestMethod]
    public void EnsureTestSigningAllowed_rejects_trust_cert_on_ci()
    {
        // Trusting a root needs someone to answer the Windows prompt, so it can never run unattended.
        Assert.ThrowsExactly<InvalidOperationException>(() => Ensure(trustCert: true, ci: true));
    }

    [TestMethod]
    [DataRow("wip")]
    [DataRow("release")]
    [DataRow("WIP")]
    [DataRow("RELEASE")]
    public void EnsureTestSigningAllowed_rejects_shipping_channels(string channel)
    {
        Assert.ThrowsExactly<InvalidOperationException>(() => Ensure(signTest: true, channel: channel));
        Assert.ThrowsExactly<InvalidOperationException>(() => Ensure(local: true, channel: channel));
    }

    [TestMethod]
    public void EnsureTestSigningAllowed_rejects_production_modes()
    {
        Assert.ThrowsExactly<InvalidOperationException>(() => Ensure(signTest: true, sign: true));
        Assert.ThrowsExactly<InvalidOperationException>(() => Ensure(local: true, pack: true));
        Assert.ThrowsExactly<InvalidOperationException>(() => Ensure(signTest: true, publish: true));
    }

    [TestMethod]
    public void EnsureTestSigningAllowed_rejects_local_with_sign_test()
    {
        Assert.ThrowsExactly<InvalidOperationException>(() => Ensure(local: true, signTest: true));
    }

    [TestMethod]
    public void EnsureTestSigningAllowed_rejects_sign_test_with_remove_cert()
    {
        Assert.ThrowsExactly<InvalidOperationException>(() => Ensure(signTest: true, removeCert: true));
    }

    [TestMethod]
    public void EnsureTestSigningAllowed_rejects_sign_test_with_trust_cert()
    {
        Assert.ThrowsExactly<InvalidOperationException>(() => Ensure(signTest: true, trustCert: true));
    }

    [TestMethod]
    public void EnsureTestSigningAllowed_rejects_local_with_trust_cert()
    {
        Assert.ThrowsExactly<InvalidOperationException>(() => Ensure(local: true, trustCert: true));
    }

    [TestMethod]
    public void EnsureTestSigningAllowed_accepts_trust_cert_alone()
    {
        Ensure(trustCert: true);
    }

    [TestMethod]
    public void EnsureTestSigningAllowed_accepts_local_with_remove_cert()
    {
        Ensure(local: true, removeCert: true);
    }

    [TestMethod]
    public void EnsureTestSigningAllowed_rejects_test_signing_off_windows()
    {
        Assert.ThrowsExactly<PlatformNotSupportedException>(() => Ensure(local: true, windows: false));
        Assert.ThrowsExactly<PlatformNotSupportedException>(() => Ensure(signTest: true, ci: true, windows: false));
        Assert.ThrowsExactly<PlatformNotSupportedException>(() => Ensure(removeCert: true, windows: false));
        Assert.ThrowsExactly<PlatformNotSupportedException>(() => Ensure(trustCert: true, windows: false));
    }

    [TestMethod]
    public void EnsureTestSigningAllowed_ignores_platform_for_plain_builds()
    {
        Ensure(pack: true, windows: false);
    }
}
