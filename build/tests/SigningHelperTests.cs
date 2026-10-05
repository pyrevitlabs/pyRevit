using Build.Helpers;
using Build.Options;
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
    public void BuildSignArguments_pins_the_production_trusted_signing_argument_list()
    {
        var invocation = SigningHelper.BuildProductionInvocation(
            new SigningOptions
            {
                SigningAccountName = "account",
                CertificateProfileName = "profile",
                Endpoint = "https://eus.codesigning.azure.net",
            },
            new BuildOptions { TimestampUrl = "http://timestamp.acs.microsoft.com/" },
            "Binaries");

        CollectionAssert.AreEqual(
            new[]
            {
                "code", "trusted-signing", "a.dll", "b.exe",
                "--file-digest", "SHA256",
                "--trusted-signing-account", "account",
                "--trusted-signing-certificate-profile", "profile",
                "--trusted-signing-endpoint", "https://eus.codesigning.azure.net",
                "--timestamp-url", "http://timestamp.acs.microsoft.com/",
                "--timestamp-digest", "SHA256",
            },
            SigningHelper.BuildSignArguments(invocation, ["a.dll", "b.exe"]));
    }

    [TestMethod]
    public void BuildProductionInvocation_passes_azure_credentials_in_the_environment_only()
    {
        var invocation = SigningHelper.BuildProductionInvocation(
            new SigningOptions { TenantId = "tenant", ClientId = "client", ClientSecret = "secret" },
            new BuildOptions(),
            "Binaries");

        Assert.AreEqual("tenant", invocation.EnvironmentVariables["AZURE_TENANT_ID"]);
        Assert.AreEqual("client", invocation.EnvironmentVariables["AZURE_CLIENT_ID"]);
        Assert.AreEqual("secret", invocation.EnvironmentVariables["AZURE_CLIENT_SECRET"]);
        Assert.IsFalse(SigningHelper.BuildSignArguments(invocation, ["a.dll"]).Contains("secret"));
    }

    [TestMethod]
    public void SelectSignToolVersion_picks_the_newest_dotnet_tool_release()
    {
        // The stable 1.x line is a different package that shares the id 'sign'; installing it fails with
        // "Package sign is not a .NET tool.".
        var published = new[] { "1.1.5", "1.0.0", "0.9.0-beta.22609.3", "0.9.1-beta.26301.2", "0.9.1-beta.26475.3" };

        Assert.AreEqual("0.9.1-beta.26475.3", SigningHelper.SelectSignToolVersion(published));
    }

    [TestMethod]
    public void SelectSignToolVersion_orders_numeric_parts_numerically()
    {
        var published = new[] { "0.9.1-beta.1", "0.10.0-beta.1", "0.9.1-beta.2" };

        Assert.AreEqual("0.10.0-beta.1", SigningHelper.SelectSignToolVersion(published));
    }

    [TestMethod]
    public void SelectSignToolVersion_returns_null_when_no_release_is_a_tool()
    {
        Assert.IsNull(SigningHelper.SelectSignToolVersion(["1.1.5", "1.0.0"]));
        Assert.IsNull(SigningHelper.SelectSignToolVersion([]));
    }

    [TestMethod]
    public void SignInvocation_defaults_to_an_empty_environment()
    {
        var invocation = new SignInvocation("certificate-store", [], "Test signing", "Binaries");

        Assert.AreEqual(0, invocation.EnvironmentVariables.Count);
    }
}
