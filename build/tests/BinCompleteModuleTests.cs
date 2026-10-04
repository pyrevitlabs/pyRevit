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

    private static List<Type> DependenciesOf(Type module) =>
        module.GetCustomAttributes()
            .Select(attribute => attribute.GetType())
            .Where(type => type.IsGenericType && type.Name.StartsWith("DependsOn", StringComparison.Ordinal))
            .Select(type => type.GenericTypeArguments[0])
            .ToList();
}
