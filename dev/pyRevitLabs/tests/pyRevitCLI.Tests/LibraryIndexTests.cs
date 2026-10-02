using pyRevitCLI;

namespace pyRevitCLI.Tests;

public class LibraryIndexTests : IDisposable {
    private readonly string root = Directory.CreateTempSubdirectory("pyrevit-index-").FullName;

    public void Dispose() {
        Directory.Delete(root, recursive: true);
    }

    private List<LibrarySymbol> Parse(string source, string file = "sample.py") {
        var path = Path.Combine(root, file);
        File.WriteAllText(path, source);
        return PyRevitLibraryIndex.ParseFile(root, path);
    }

    private static LibrarySymbol Named(List<LibrarySymbol> symbols, string name) => Assert.Single(symbols, symbol => symbol.Name == name);

    [Fact]
    public void ThePublicApiIsIndexedWithSignaturesDocstringsAndOwners() {
        var symbols = Parse(
            "\"\"\"Sample module.\"\"\"\n\n"
            + "def find(name, doc=None):\n    \"\"\"Find a thing.\n\n    More text.\n    \"\"\"\n    return name\n\n"
            + "class Box(object):\n    \"\"\"A box.\"\"\"\n\n"
            + "    def __init__(self, size):\n        self.size = size\n\n"
            + "    def open(self, force=False):\n        \"\"\"Open it.\"\"\"\n\n"
            + "    @property\n    def width(self):\n        \"\"\"The width.\"\"\"\n");

        Assert.Equal("module", symbols[0].Kind);
        Assert.Equal("sample", symbols[0].Name);
        Assert.Contains("Sample module.", symbols[0].Doc);
        var find = Named(symbols, "find");
        Assert.Equal("function", find.Kind);
        Assert.Equal("(name, doc=None)", find.Signature);
        Assert.Equal("Find a thing.", find.Summary);
        Assert.Equal("sample.find", find.FullName);
        var box = Named(symbols, "Box");
        Assert.Equal("class", box.Kind);
        Assert.Equal("(size)", box.Signature);
        Assert.Contains("Bases: object.", box.Doc);
        var open = Named(symbols, "open");
        Assert.Equal("method", open.Kind);
        Assert.Equal("Box", open.Owner);
        Assert.Equal("(force=False)", open.Signature);
        Assert.Equal("sample.Box.open", open.FullName);
        Assert.Equal("property", Named(symbols, "width").Kind);
    }

    [Fact]
    public void PrivateNamesAreLeftOut() {
        var symbols = Parse(
            "def _helper():\n    pass\n\n"
            + "class _Hidden(object):\n    def visible(self):\n        pass\n\n"
            + "class Shown(object):\n    def _private(self):\n        pass\n    def public(self):\n        pass\n");

        Assert.DoesNotContain(symbols, symbol => symbol.Name == "_helper");
        Assert.DoesNotContain(symbols, symbol => symbol.Name == "_Hidden");
        Assert.DoesNotContain(symbols, symbol => symbol.Name == "visible");
        Assert.DoesNotContain(symbols, symbol => symbol.Name == "_private");
        Assert.Contains(symbols, symbol => symbol.Name == "public" && symbol.Owner == "Shown");
    }

    [Fact]
    public void SignaturesSpanningSeveralLinesAreJoined() {
        var symbols = Parse("def long_one(\n    first,\n    second=2,\n):\n    pass\n");

        Assert.Equal("(first, second=2)", Named(symbols, "long_one").Signature.Replace(",)", ")").Replace(", )", ")"));
    }

    [Fact]
    public void AnOperationMarkerAttachesItsMetadataWithDefaults() {
        var symbols = Parse(
            "@automation.operation(\n    \"pyrevit.units.parse-length\",\n    PlainEnglish=\"Convert a length.\",\n)\n"
            + "def parse_length(value):\n    pass\n");

        var automation = Named(symbols, "parse_length").Automation;

        Assert.Equal("pyrevit.units.parse-length", automation.Id);
        Assert.Equal("Convert a length.", automation.PlainEnglish);
        Assert.Equal("query", automation.Mode);
        Assert.Empty(automation.Effects);
        Assert.Equal("document", automation.Context);
        Assert.Equal("none", automation.Transaction);
    }

    [Fact]
    public void AMarkerWithEveryFieldKeepsEachOfThem() {
        var symbols = Parse(
            "@automation.operation(\n    \"pyrevit.geometry.point\",\n    PlainEnglish=\"Make a point.\",\n    mode=\"pure\",\n"
            + "    effects=(\"model.read\", \"view.change\"),\n    context=\"none\",\n    transaction=\"owned\",\n)\n"
            + "def to_xyz(point):\n    pass\n");

        var automation = Named(symbols, "to_xyz").Automation;

        Assert.Equal("pure", automation.Mode);
        Assert.Equal(new[] { "model.read", "view.change" }, automation.Effects);
        Assert.Equal("none", automation.Context);
        Assert.Equal("owned", automation.Transaction);
    }

    [Fact]
    public void ATypeMarkerDefaultsToInfrastructureWithoutAContext() {
        var symbols = Parse("@automation.type(\"rpw.types.element\", PlainEnglish=\"Wrap an element.\")\nclass Element(object):\n    pass\n");

        var automation = Named(symbols, "Element").Automation;

        Assert.Equal("infrastructure", automation.Mode);
        Assert.Equal("none", automation.Context);
    }

    [Fact]
    public void AMarkerAppliesOnlyToTheSymbolRightAfterIt() {
        var symbols = Parse(
            "@automation.operation(\"a.one\", PlainEnglish=\"One.\")\ndef first():\n    pass\n\ndef second():\n    pass\n");

        Assert.NotNull(Named(symbols, "first").Automation);
        Assert.Null(Named(symbols, "second").Automation);
    }

    [Fact]
    public void AMalformedMarkerLeavesTheSymbolIndexedWithoutMetadata() {
        var symbols = Parse(
            "@automation.operation(\"a.one\")\ndef broken():\n    pass\n\n"
            + "@automation.operation(\"a.two\", PlainEnglish=\"Fine.\")\ndef fine():\n    pass\n");

        Assert.Null(Named(symbols, "broken").Automation);
        Assert.Equal("a.two", Named(symbols, "fine").Automation.Id);
    }

    [Fact]
    public void AMarkerCannotCarryAnEmptyId() {
        var symbols = Parse("@automation.operation(\"\", PlainEnglish=\"Empty id.\")\ndef nameless():\n    pass\n");

        Assert.Null(Named(symbols, "nameless").Automation);
    }

    [Fact]
    public void ModuleNamesFollowTheFolderLayoutAndInitFilesBecomeTheirPackage() {
        Directory.CreateDirectory(Path.Combine(root, "pkg", "sub"));
        Parse("def top():\n    pass\n", Path.Combine("pkg", "sub", "mod.py"));
        var init = Parse("def package_level():\n    pass\n", Path.Combine("pkg", "__init__.py"));

        Assert.Equal("pkg", Named(init, "package_level").Module);
        var nested = PyRevitLibraryIndex.ParseFile(root, Path.Combine(root, "pkg", "sub", "mod.py"));
        Assert.Equal("pkg.sub.mod", Named(nested, "top").Module);
    }
}
