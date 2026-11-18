using Build.Modules;
using Microsoft.VisualStudio.TestTools.UnitTesting;
using ModularPipelines.Attributes;

namespace Build.Tests;

/// <summary>
/// Guards the ordering of the copyright and version stamping modules, which write the same files.
/// </summary>
[TestClass]
[TestCategory("HostFree")]
[TestCategory("Unit")]
public sealed class SetCopyrightYearModuleTests
{
    /// <summary>
    /// <see cref="SetCopyrightYearModule"/> must declare a dependency on <see cref="StampVersionModule"/> so the two never write the nuspec and MSI props concurrently.
    /// </summary>
    [TestMethod]
    public void SetCopyrightYearModule_depends_on_StampVersionModule_because_both_write_the_nuspec_and_msi_props()
    {
        var dependsOn = typeof(SetCopyrightYearModule)
            .GetCustomAttributes(typeof(DependsOnAttribute<>).MakeGenericType(typeof(StampVersionModule)), inherit: false);

        Assert.HasCount(1, dependsOn);
    }

    /// <summary>
    /// <see cref="BuildLabsModule"/> must declare a dependency on <see cref="SetCopyrightYearModule"/> so MSBuild never reads <c>Directory.Build.props</c> while the copyright stamp rewrites it.
    /// </summary>
    [TestMethod]
    public void BuildLabsModule_depends_on_SetCopyrightYearModule_because_msbuild_imports_the_stamped_Directory_Build_props()
    {
        var dependsOn = typeof(BuildLabsModule)
            .GetCustomAttributes(typeof(DependsOnAttribute<>).MakeGenericType(typeof(SetCopyrightYearModule)), inherit: false);

        Assert.HasCount(1, dependsOn);
    }
}
