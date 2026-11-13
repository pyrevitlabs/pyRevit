using NUnit.Framework;
using pyRevitAssemblyBuilder.AssemblyMaker;

namespace pyRevitExtensionParserTest
{
    /// <summary>
    /// Regression tests for #4047: extension assemblies are matched by exact extension name.
    /// </summary>
    [TestFixture]
    [Category("HostFree")]
    [Category("Unit")]
    public class ExtensionAssemblyNameTests
    {
        [TestCase("pyRevit_2026_0123456789abcdef_Tools", "Tools", true)]
        [TestCase("pyRevit_2026_0123456789abcdef_MyTools", "Tools", false)]
        [TestCase("pyRevit_2026_0123456789abcdef_Tools", "MyTools", false)]
        [TestCase("pyRevit_2026_0123456789abcdef_my_tools", "my_tools", true)]
        [TestCase("pyRevit_2026_0123456789abcdef_TOOLS", "tools", true)]
        [TestCase("pyRevit_2026_0123456789abcdef_Other_Tools", "Tools", false)]
        [TestCase("pyRevit_2026_0123456789abcdef", "Tools", false)]
        [TestCase("Unrelated_Tools", "Tools", false)]
        public void BelongsTo_MatchesExtensionNamePartExactly(string assemblyName, string extensionName, bool expected)
        {
            Assert.That(ExtensionAssemblyName.BelongsTo(assemblyName, extensionName), Is.EqualTo(expected));
        }
    }
}
