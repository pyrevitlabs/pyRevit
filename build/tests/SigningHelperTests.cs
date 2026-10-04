using Build.Helpers;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
public sealed class SigningHelperTests
{
    [TestMethod]
    public void BuildSigningSummary_groups_files_by_extension()
    {
        var summary = SigningHelper.BuildSigningSummary(
        [
            @"C:\bin\pyRevitLabs.Common.dll",
            @"C:\bin\pyrevit.exe",
            @"C:\dist\pyRevit_1.0_signed.exe",
            @"C:\dist\pyRevit_CLI_1.0_admin_signed.msi",
            @"C:\dist\pyrevit-cli.1.0.0.nupkg",
            @"C:\bin\pyRevitLabs.PyRevit.dll",
        ]);

        Assert.AreEqual("6 file(s): 2 .dll, 2 .exe, 1 .msi, 1 .nupkg", summary);
    }

    [TestMethod]
    public void BuildSigningSummary_handles_single_file()
    {
        var summary = SigningHelper.BuildSigningSummary([@"C:\dist\pyrevit-cli.1.0.0.nupkg"]);

        Assert.AreEqual("1 file(s): 1 .nupkg", summary);
    }

    [TestMethod]
    public void BuildSignArguments_places_files_before_shared_and_provider_options()
    {
        var invocation = new SignInvocation("certificate-store", ["--certificate-fingerprint", "AB"], "Test signing", "Binaries");

        var arguments = SigningHelper.BuildSignArguments(invocation, ["a.dll", "b.exe"]);

        CollectionAssert.AreEqual(
            new[] { "code", "certificate-store", "a.dll", "b.exe", "--file-digest", "SHA256", "--certificate-fingerprint", "AB" },
            arguments);
    }

    [TestMethod]
    public void SignInvocation_defaults_to_an_empty_environment()
    {
        var invocation = new SignInvocation("certificate-store", [], "Test signing", "Binaries");

        Assert.AreEqual(0, invocation.EnvironmentVariables.Count);
    }
}
