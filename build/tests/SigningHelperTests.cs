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
}
