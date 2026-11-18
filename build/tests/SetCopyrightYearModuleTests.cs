using Build.Modules;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using ModularPipelines.Attributes;

namespace Build.Tests;

[TestClass]
public sealed class SetCopyrightYearModuleTests
{
    [TestMethod]
    public void SetCopyrightYearModule_depends_on_StampVersionModule_because_both_write_the_nuspec_and_msi_props()
    {
        var dependsOn = typeof(SetCopyrightYearModule)
            .GetCustomAttributes(typeof(DependsOnAttribute<>).MakeGenericType(typeof(StampVersionModule)), inherit: false);

        Assert.HasCount(1, dependsOn);
    }
}
