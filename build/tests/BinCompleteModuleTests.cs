using System.Reflection;
using Build.Modules;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
public sealed class BinCompleteModuleTests
{
    [TestMethod]
    [DataRow(typeof(WriteCiBinManifestModule))]
    [DataRow(typeof(BuildShellModule))]
    [DataRow(typeof(TestConfigurationsModule))]
    [DataRow(typeof(VerifyLibGit2Module))]
    public void BinCompleteModule_waits_for_every_bin_writer(Type writer)
    {
        CollectionAssert.Contains(DependenciesOf(typeof(BinCompleteModule)), writer);
    }

    [TestMethod]
    [DataRow(typeof(SignTestBinariesModule))]
    [DataRow(typeof(RejectTestSignedBinariesModule))]
    public void Bin_readers_wait_for_BinCompleteModule(Type reader)
    {
        CollectionAssert.Contains(DependenciesOf(reader), typeof(BinCompleteModule));
    }

    [TestMethod]
    [DataRow(typeof(BuildInstallersModule))]
    [DataRow(typeof(BuildChocoModule))]
    [DataRow(typeof(SignBinariesModule))]
    [DataRow(typeof(SignChocoPackageModule))]
    // winget, release and notify are not gated by PipelineModes.Packages, so they carry the guard themselves.
    // Without this, the next publish mode that reads bin/ becomes a hole in the containment.
    [DataRow(typeof(PublishWingetModule))]
    [DataRow(typeof(NotifyIssuesModule))]
    public void Every_mode_that_touches_bin_waits_for_the_reject_guard(Type module)
    {
        CollectionAssert.Contains(DependenciesOf(module), typeof(RejectTestSignedBinariesModule));
    }

    private static List<Type> DependenciesOf(Type module) =>
        module.GetCustomAttributes()
            .Select(attribute => attribute.GetType())
            .Where(type => type.IsGenericType && type.Name.StartsWith("DependsOn", StringComparison.Ordinal))
            .Select(type => type.GenericTypeArguments[0])
            .ToList();
}
