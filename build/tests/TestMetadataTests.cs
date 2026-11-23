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

    /// <summary>A misspelled override cannot fall back to the class's HostFree tag and reach CI.</summary>
    [TestMethod]
    public void MisspelledCategoryFailsClosed() {
        var error = Assert.ThrowsExactly<InvalidDataException>(() => TestMetadata.Read("""
            [Category("HostFree"), Category("Integration")]
            class Tests {
                [Test, Category("Revti")]
                public void Hosted() { }
            }
            """, "fixture.cs"));
        StringAssert.Contains(error.Message, "Revti");
    }

    /// <summary>A class tag the catalog cannot read fails instead of disagreeing with the runtime filter.</summary>
    [TestMethod]
    public void NonLiteralClassCategoryFailsClosed() {
        var error = Assert.ThrowsExactly<InvalidDataException>(() => TestMetadata.Read("""
            [Category(Cats.HostFree), Category("Unit")]
            class Tests { [Test] public void Case() { } }
            """, "fixture.cs"));
        StringAssert.Contains(error.Message, "fixture.cs");
        StringAssert.Contains(error.Message, "Tests");
        StringAssert.Contains(error.Message, "Cats.HostFree");
    }

    /// <summary>Tags on a base class are not read; the failure tells the author to tag the class itself.</summary>
    [TestMethod]
    public void InheritedCategoryFailsWithActionableMessage() {
        var error = Assert.ThrowsExactly<InvalidDataException>(() => TestMetadata.Read("""
            class DerivedTests : BaseTests { [Test] public void Case() { } }
            """, "fixture.cs"));
        StringAssert.Contains(error.Message, "DerivedTests.Case");
        StringAssert.Contains(error.Message, "on the class itself");
    }

    /// <summary>A [Test] on an abstract base is cataloged under the base, which the HostFree count check treats as a minimum.</summary>
    [TestMethod]
    public void AbstractBaseTestIsCatalogedUnderTheBase() {
        var tests = TestMetadata.Read("""
            [Category("HostFree"), Category("Unit")]
            abstract class BaseTests { [Test] public void Shared() { } }
            """, "fixture.cs");
        Assert.AreEqual("BaseTests", tests.Single().ClassName);
    }

    /// <summary>A method override the catalog cannot read cannot leave the class's HostFree tag in place.</summary>
    [TestMethod]
    public void NonLiteralMethodCategoryFailsClosed() {
        var error = Assert.ThrowsExactly<InvalidDataException>(() => TestMetadata.Read("""
            [Category("HostFree"), Category("Integration")]
            class Tests {
                [Test, Category(Cats.Revit)]
                public void Hosted() { }
            }
            """, "fixture.cs"));
        StringAssert.Contains(error.Message, "Tests.Hosted");
        StringAssert.Contains(error.Message, "Cats.Revit");
    }

    /// <summary>MSTest categories follow the same literal-only rule.</summary>
    [TestMethod]
    public void NonLiteralTestCategoryFailsClosed() {
        Assert.ThrowsExactly<InvalidDataException>(() => TestMetadata.Read("""
            [TestCategory("HostFree"), TestCategory("Unit")]
            class Tests { [TestMethod, TestCategory(Cats.Revit)] public void Hosted() { } }
            """, "fixture.cs"));
    }

    /// <summary>xUnit traits with a non-literal key or value fail closed.</summary>
    [TestMethod]
    [DataRow("Keys.Env, \"Revit\"")]
    [DataRow("\"Environment\", Envs.Revit")]
    public void NonLiteralTraitFailsClosed(string arguments) {
        var error = Assert.ThrowsExactly<InvalidDataException>(() => TestMetadata.Read($$"""
            [Trait("Environment", "HostFree"), Trait("Level", "Unit")]
            class Tests { [Fact, Trait({{arguments}})] public void Hosted() { } }
            """, "fixture.cs"));
        StringAssert.Contains(error.Message, "Tests.Hosted");
    }

    /// <summary>Declared purpose categories sit beside the classification tags.</summary>
    [TestMethod]
    public void PurposeCategoryIsAllowed() {
        var tests = TestMetadata.Read("""
            [Category("HostFree"), Category("Integration"), Category("Regression")]
            class Tests { [Test] public void Case() { } }
            """, "fixture.cs");
        Assert.AreEqual("HostFree", tests.Single().Environment);
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

    /// <summary>Struct and record fixtures are cataloged instead of aborting discovery.</summary>
    [TestMethod]
    public void StructAndRecordFixturesAreClassified() {
        var tests = TestMetadata.Read("""
            [Category("HostFree"), Category("Unit")]
            struct StructTests { [Test] public void Case() { } }
            [Category("Revit"), Category("Integration")]
            record RecordTests { [Test] public void Case() { } }
            """, "fixture.cs");
        Assert.AreEqual(2, tests.Count);
        Assert.AreEqual("StructTests", tests[0].ClassName);
        Assert.AreEqual("Revit", tests[1].Environment);
    }

    /// <summary>A nested fixture inherits the outer type's tags and may override them.</summary>
    [TestMethod]
    public void NestedFixtureInheritsOuterTags() {
        var tests = TestMetadata.Read("""
            [Category("HostFree"), Category("Unit")]
            class Outer {
                class Inherits { [Test] public void Case() { } }
                [Category("Integration")]
                class Overrides { [Test] public void Case() { } }
            }
            """, "fixture.cs");
        Assert.AreEqual("Unit", tests.Single(test => test.ClassName == "Inherits").Level);
        Assert.AreEqual("Integration", tests.Single(test => test.ClassName == "Overrides").Level);
        Assert.IsTrue(tests.All(test => test.Environment == "HostFree"));
    }

    /// <summary>A nested fixture without any metadata still fails closed.</summary>
    [TestMethod]
    public void NestedFixtureWithoutMetadataFailsClosed() {
        Assert.ThrowsExactly<InvalidDataException>(() => TestMetadata.Read(
            "class Outer { class Inner { [Test] public void Case() { } } }", "fixture.cs"));
    }

    /// <summary>Modern syntax in a fixture file is parsed, not dropped.</summary>
    [TestMethod]
    public void CurrentLanguageSyntaxIsParsed() {
        var tests = TestMetadata.Read("""""
            namespace Fixtures;
            file class Helper(int size) { string Text = """raw"""; }
            [Category("HostFree"), Category("Unit")]
            public class Tests(int size) {
                [Test] public void Case() { var text = """quoted"""; }
            }
            """"", "fixture.cs");
        Assert.AreEqual("Tests", tests.Single().ClassName);
    }
}
