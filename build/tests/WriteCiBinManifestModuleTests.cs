using Build.Modules;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using ModularPipelines.Attributes;

namespace Build.Tests;

[TestClass]
public sealed class WriteCiBinManifestModuleTests
{
    [TestMethod]
    public void WriteCiBinManifestModule_depends_on_ResolveVersioningModule()
    {
        var dependsOn = typeof(WriteCiBinManifestModule)
            .GetCustomAttributes(typeof(DependsOnAttribute<>).MakeGenericType(typeof(ResolveVersioningModule)), inherit: false);

        Assert.HasCount(1, dependsOn);
    }
}
