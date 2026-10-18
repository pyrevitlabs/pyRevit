using Build.Helpers;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

/// <summary>Guards classification before any test fixture can execute.</summary>
[TestClass]
[TestCategory("HostFree")]
[TestCategory("Unit")]
public class TestMetadataTests {
    /// <summary>Framework-specific fixtures are classified using the symbols they compile with.</summary>
    [TestMethod]
    public void ConditionalFixtureUsesFrameworkSymbols() {
        const string source = """
            #if HOSTED
            [Category("Revit"), Category("Integration")]
            #else
            [Category("HostFree"), Category("Unit")]
            #endif
            class ConditionalTests { [Test] public void Case() {} }
            """;
        Assert.AreEqual("Revit", TestMetadata.Read(source, "fixture.cs", ["HOSTED"]).Single().Environment);
        Assert.AreEqual("HostFree", TestMetadata.Read(source, "fixture.cs", []).Single().Environment);
    }

    /// <summary>Parameterized cases inherit their class classification.</summary>
    [TestMethod]
    public void ClassDefaultsApplyToParameterizedTests() {
        var tests = TestMetadata.Read("""
            [Category("HostFree"), Category("Integration")]
            public class ParserTests {
                [TestCase("class Fake {}")]
                public void Parses(string text) { }
            }
            """, "fixture.cs");
        Assert.AreEqual(1, tests.Count);
        Assert.AreEqual("HostFree", tests[0].Environment);
        Assert.AreEqual("Integration", tests[0].Level);
    }

    /// <summary>A hosted override is detected without constructing the fixture.</summary>
    [TestMethod]
    public void MethodOverrideSelectsRevitWithoutRunningFixture() {
        var tests = TestMetadata.Read("""
            [Trait("Environment", "HostFree"), Trait("Level", "Unit")]
            class Tests {
                [Fact, Trait("Environment", "Revit")]
                public void Hosted() { throw new Exception(); }
            }
            """, "fixture.cs");
        Assert.AreEqual("Revit", tests.Single().Environment);
    }

    /// <summary>New tests cannot silently avoid validation through missing tags.</summary>
    [TestMethod]
    public void MissingMetadataFailsClosed() {
        Assert.ThrowsExactly<InvalidDataException>(() => TestMetadata.Read(
            "class Tests { [TestMethod] public void Missing() {} }", "fixture.cs"));
    }

    /// <summary>Only real method attributes contribute to the catalog.</summary>
    [TestMethod]
    public void CommentsAndStringContentsAreNotTests() {
        var tests = TestMetadata.Read("""
            // [Fact] public void Fake() {}
            class Helper { string text = "[Test] public void Fake() {}"; }
            """, "fixture.cs");
        Assert.AreEqual(0, tests.Count);
    }
}
