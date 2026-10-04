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
}
