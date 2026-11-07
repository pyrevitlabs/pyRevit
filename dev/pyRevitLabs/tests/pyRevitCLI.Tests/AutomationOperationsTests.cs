using pyRevitCLI;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public class AutomationOperationsTests {
    private static readonly string[] Ids = {
        "pyrevit.units.parse-length", "pyrevit.units.parse-slope", "pyrevit.levels.resolve", "pyrevit.elements.by-category",
    };

    private static string Code(Action action) => Assert.Throws<AgentClientException>(action).Code;

    private static JObject Valid(string id) {
        return id switch {
            "pyrevit.levels.resolve" => new JObject { ["name"] = "Level 1" },
            "pyrevit.elements.by-category" => new JObject { ["categories"] = new JArray("OST_Walls") },
            _ => new JObject { ["value"] = "8:12" },
        };
    }

    [Theory]
    [InlineData("pyrevit.units.parse-length")]
    [InlineData("pyrevit.units.parse-slope")]
    [InlineData("pyrevit.levels.resolve")]
    [InlineData("pyrevit.elements.by-category")]
    public void EveryOperationResolvesWithValidInputs(string id) {
        var operation = PyRevitAutomationOperations.Resolve(id, Valid(id));

        Assert.Equal(id, operation.Value<string>("id"));
        Assert.False(string.IsNullOrWhiteSpace(operation.Value<string>("title")));
        Assert.False(string.IsNullOrWhiteSpace(operation.Value<string>("source")));
    }

    [Fact]
    public void OnlyTheOperationsThatNeedADocumentSaySo() {
        Assert.False(PyRevitAutomationOperations.Resolve("pyrevit.units.parse-length", Valid("pyrevit.units.parse-length")).Value<bool>("requires_document"));
        Assert.False(PyRevitAutomationOperations.Resolve("pyrevit.units.parse-slope", Valid("pyrevit.units.parse-slope")).Value<bool>("requires_document"));
        Assert.True(PyRevitAutomationOperations.Resolve("pyrevit.levels.resolve", Valid("pyrevit.levels.resolve")).Value<bool>("requires_document"));
        Assert.True(PyRevitAutomationOperations.Resolve("pyrevit.elements.by-category", Valid("pyrevit.elements.by-category")).Value<bool>("requires_document"));
    }

    [Fact]
    public void IdsAreMatchedIgnoringCaseAndResolveToTheCanonicalId() {
        var operation = PyRevitAutomationOperations.Resolve("PYREVIT.Units.Parse-Length", new JObject { ["value"] = 3 });

        Assert.Equal("pyrevit.units.parse-length", operation.Value<string>("id"));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void ABlankIdIsInvalid(string id) {
        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve(id, new JObject())));
    }

    [Fact]
    public void AnUnknownIdIsNotInvocable() {
        Assert.Equal("unknown_automation_id", Code(() => PyRevitAutomationOperations.Resolve("os.system", new JObject())));
        Assert.Equal("unknown_automation_id", Code(() => PyRevitAutomationOperations.Resolve("pyrevit.units.parse-length; import os", new JObject())));
    }

    [Fact]
    public void InputsMustBeAnObject() {
        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve("pyrevit.units.parse-length", null)));
        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve("pyrevit.units.parse-length", new JArray(1))));
        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve("pyrevit.units.parse-length", new JValue("8:12"))));
    }

    [Theory]
    [InlineData("pyrevit.units.parse-length")]
    [InlineData("pyrevit.units.parse-slope")]
    public void UnitParsersTakeOneNumberOrStringAndNothingElse(string id) {
        PyRevitAutomationOperations.Resolve(id, new JObject { ["value"] = 12 });
        PyRevitAutomationOperations.Resolve(id, new JObject { ["value"] = 1.5 });
        PyRevitAutomationOperations.Resolve(id, new JObject { ["value"] = "8:12" });

        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve(id, new JObject())));
        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve(id, new JObject { ["value"] = "8:12", ["extra"] = 1 })));
        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve(id, new JObject { ["other"] = "8:12" })));
        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve(id, new JObject { ["value"] = true })));
        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve(id, new JObject { ["value"] = JValue.CreateNull() })));
        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve(id, new JObject { ["value"] = new JArray(1) })));
        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve(id, new JObject { ["value"] = new JObject() })));
    }

    [Fact]
    public void StringInputsAreNonBlankAndAtMost256Characters() {
        PyRevitAutomationOperations.Resolve("pyrevit.units.parse-length", new JObject { ["value"] = new string('1', 256) });

        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve("pyrevit.units.parse-length", new JObject { ["value"] = new string('1', 257) })));
        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve("pyrevit.units.parse-length", new JObject { ["value"] = "   " })));
        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve("pyrevit.levels.resolve", new JObject { ["name"] = "" })));
    }

    [Fact]
    public void ALevelNameMustBeAString() {
        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve("pyrevit.levels.resolve", new JObject { ["name"] = 1 })));
        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve("pyrevit.levels.resolve", new JObject { ["name"] = "L1", ["extra"] = 1 })));
    }

    [Fact]
    public void CategoriesNeedBetweenOneAndTwentyBuiltInCategoryNames() {
        PyRevitAutomationOperations.Resolve("pyrevit.elements.by-category", new JObject { ["categories"] = new JArray(Enumerable.Repeat("OST_Walls", 20)) });
        PyRevitAutomationOperations.Resolve("pyrevit.elements.by-category", new JObject { ["categories"] = new JArray("OST_" + new string('c', 124)) });

        foreach (var categories in new JToken[] {
            new JArray(),
            new JArray(Enumerable.Repeat("OST_Walls", 21)),
            new JArray(""),
            new JArray("  "),
            new JArray("Walls"),
            new JArray("OST_"),
            new JArray("OST_" + new string('c', 125)),
            new JArray(1),
            new JValue("OST_Walls"),
        })
            Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve("pyrevit.elements.by-category", new JObject { ["categories"] = categories })));
        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve("pyrevit.elements.by-category", new JObject())));
    }

    [Fact]
    public void TheCategoryLimitDefaultsToFiftyAndIsBoundedToTwoHundred() {
        var defaulted = PyRevitAutomationOperations.Resolve("pyrevit.elements.by-category", new JObject { ["categories"] = new JArray("OST_Walls") });
        Assert.Equal(50, defaulted["inputs"].Value<int>("limit"));
        Assert.Equal(1, PyRevitAutomationOperations.Resolve("pyrevit.elements.by-category", new JObject { ["categories"] = new JArray("OST_Walls"), ["limit"] = 1 })["inputs"].Value<int>("limit"));
        Assert.Equal(200, PyRevitAutomationOperations.Resolve("pyrevit.elements.by-category", new JObject { ["categories"] = new JArray("OST_Walls"), ["limit"] = 200 })["inputs"].Value<int>("limit"));

        foreach (var limit in new JToken[] { 0, -1, 201, 1.5, "5", true })
            Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve("pyrevit.elements.by-category", new JObject { ["categories"] = new JArray("OST_Walls"), ["limit"] = limit })));
        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve("pyrevit.elements.by-category", new JObject { ["categories"] = new JArray("OST_Walls"), ["extra"] = 1 })));
    }

    [Theory]
    [InlineData("pyrevit.units.parse-length")]
    [InlineData("pyrevit.units.parse-slope")]
    [InlineData("pyrevit.levels.resolve")]
    [InlineData("pyrevit.elements.by-category")]
    public void TheScriptNeverContainsTheCallersInput(string id) {
        var marker = "OST_SENTINEL_" + Guid.NewGuid().ToString("N");
        var inputs = Valid(id);
        foreach (var property in inputs.Properties().ToList())
            if (property.Value.Type == JTokenType.String)
                property.Value = marker;
            else if (property.Value is JArray array)
                inputs[property.Name] = new JArray(marker);

        var first = PyRevitAutomationOperations.Resolve(id, inputs);
        var second = PyRevitAutomationOperations.Resolve(id, Valid(id));

        Assert.DoesNotContain(marker, first.Value<string>("source"));
        Assert.Equal(second.Value<string>("source"), first.Value<string>("source"));
        Assert.Contains("inputs[", first.Value<string>("source"));
    }

    [Fact]
    public void AMarkedOperationRunsTheFixedScriptWithTheFunctionAsData() {
        var operation = PyRevitAutomationOperations.Resolve(
            "PYREVIT.elements.NAME", new JObject { ["element"] = 316542, ["title_on_sheet"] = true });

        Assert.Equal("pyrevit.elements.name", operation.Value<string>("id"));
        Assert.Equal(PyRevitAutomationOperations.MarkedOperationSource, operation.Value<string>("source"));
        Assert.True(operation.Value<bool>("requires_document"));
        Assert.False(string.IsNullOrWhiteSpace(operation.Value<string>("title")));
        Assert.True(operation.Value<string>("title").Length <= 80);
        var call = operation["inputs"]["operation"];
        Assert.Equal("pyrevit.elements.name", call.Value<string>("id"));
        Assert.Equal("pyrevit.revit.db.query", call.Value<string>("module"));
        Assert.Equal("get_name", call.Value<string>("function"));
        Assert.Equal(316542, operation["inputs"]["inputs"].Value<int>("element"));
        Assert.True(operation["inputs"]["inputs"].Value<bool>("title_on_sheet"));
    }

    [Fact]
    public void AMarkedOperationWithNoInputsTakesAnEmptyObjectOnly() {
        PyRevitAutomationOperations.Resolve("pyrevit.revisions.list", new JObject());

        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve("pyrevit.revisions.list", new JObject { ["doc"] = 1 })));
        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve("pyrevit.revisions.list", null)));
    }

    [Fact]
    public void TheCallersTextNeverReachesTheScriptOfAMarkedOperation() {
        var marker = "SENTINEL_" + Guid.NewGuid().ToString("N");

        var operation = PyRevitAutomationOperations.Resolve("pyrevit.elements.by-family", new JObject { ["family_name"] = marker });

        Assert.Equal(PyRevitAutomationOperations.MarkedOperationSource, operation.Value<string>("source"));
        Assert.Equal(marker, operation["inputs"]["inputs"].Value<string>("family_name"));
    }

    [Theory]
    [InlineData("pyrevit.walls.create")]
    [InlineData("pyrevit.elements.delete")]
    [InlineData("pyrevit.geometry.point")]
    [InlineData("rpw.elements.name")]
    public void ModifyOperationsMethodsAndUndeclaredMarkersStayUnexposed(string id) {
        Assert.False(PyRevitAutomationOperations.IsInvocable(id));
        Assert.Equal("automation_not_exposed", Code(() => PyRevitAutomationOperations.Resolve(id, new JObject())));
    }

    private static LibrarySymbol Marked(string mode = "query", string transaction = "none", string owner = null,
                                        string kind = "function", string module = "pyrevit.revit.db.query",
                                        string name = "get_name", bool declared = true) {
        return new LibrarySymbol {
            Module = module,
            Name = name,
            Owner = owner,
            Kind = kind,
            Automation = new AutomationMetadata {
                Id = "test.marked",
                PlainEnglish = "Test.",
                Mode = mode,
                Effects = new List<string>(),
                Context = "document",
                Transaction = transaction,
                Inputs = declared ? AutomationInput.ParseAll(new[] { "element: element" }) : null,
            },
        };
    }

    [Fact]
    public void OnlyModuleLevelQueryOrPureFunctionsWithInputsRunFromTheirMarker() {
        Assert.True(PyRevitAutomationOperations.IsMarkedInvocable(Marked()));
        Assert.True(PyRevitAutomationOperations.IsMarkedInvocable(Marked(mode: "pure", module: "rpw.db.element")));

        Assert.False(PyRevitAutomationOperations.IsMarkedInvocable(Marked(declared: false)));
        Assert.False(PyRevitAutomationOperations.IsMarkedInvocable(Marked(mode: "modify")));
        Assert.False(PyRevitAutomationOperations.IsMarkedInvocable(Marked(mode: "interactive")));
        Assert.False(PyRevitAutomationOperations.IsMarkedInvocable(Marked(transaction: "caller")));
        Assert.False(PyRevitAutomationOperations.IsMarkedInvocable(Marked(owner: "Element", kind: "method")));
        Assert.False(PyRevitAutomationOperations.IsMarkedInvocable(Marked(kind: "property")));
        Assert.False(PyRevitAutomationOperations.IsMarkedInvocable(Marked(module: "os")));
        Assert.False(PyRevitAutomationOperations.IsMarkedInvocable(Marked(module: "pyrevitx.db")));
        Assert.False(PyRevitAutomationOperations.IsMarkedInvocable(Marked(name: "_private")));
        Assert.False(PyRevitAutomationOperations.IsMarkedInvocable(null));
    }

    private static readonly List<AutomationInput> Declared = AutomationInput.ParseAll(new[] {
        "name: string", "count: integer?", "ratio: number?", "flag: boolean?", "element: element?", "value: scalar?",
    });

    [Fact]
    public void DeclaredInputsAcceptEachTypeAndReturnTheObjectUnchanged() {
        var inputs = new JObject {
            ["name"] = "Level 1", ["count"] = 3, ["ratio"] = 1.5, ["flag"] = false, ["element"] = 316542L, ["value"] = "Concrete",
        };

        Assert.Same(inputs, AutomationInput.Validate(Declared, inputs));
        AutomationInput.Validate(Declared, new JObject { ["name"] = new string('x', 256) });
        foreach (var scalar in new JToken[] { 2, 2.5, true, "x" })
            AutomationInput.Validate(Declared, new JObject { ["name"] = "a", ["value"] = scalar });
    }

    public static IEnumerable<object[]> InvalidInputs() {
        yield return new object[] { new JObject() };
        yield return new object[] { new JObject { ["name"] = "a", ["extra"] = 1 } };
        yield return new object[] { new JObject { ["name"] = JValue.CreateNull() } };
        yield return new object[] { new JObject { ["name"] = "a", ["count"] = JValue.CreateNull() } };
        yield return new object[] { new JObject { ["name"] = 1 } };
        yield return new object[] { new JObject { ["name"] = "   " } };
        yield return new object[] { new JObject { ["name"] = new string('x', 257) } };
        yield return new object[] { new JObject { ["name"] = "a", ["count"] = 1.0 } };
        yield return new object[] { new JObject { ["name"] = "a", ["count"] = true } };
        yield return new object[] { new JObject { ["name"] = "a", ["count"] = "3" } };
        yield return new object[] { new JObject { ["name"] = "a", ["count"] = JToken.Parse("9223372036854775808") } };
        yield return new object[] { new JObject { ["name"] = "a", ["ratio"] = double.PositiveInfinity } };
        yield return new object[] { new JObject { ["name"] = "a", ["ratio"] = double.NaN } };
        yield return new object[] { new JObject { ["name"] = "a", ["ratio"] = "1.5" } };
        yield return new object[] { new JObject { ["name"] = "a", ["flag"] = 1 } };
        yield return new object[] { new JObject { ["name"] = "a", ["element"] = "316542" } };
        yield return new object[] { new JObject { ["name"] = "a", ["element"] = 3.0 } };
        yield return new object[] { new JObject { ["name"] = "a", ["value"] = new JArray() } };
        yield return new object[] { new JObject { ["name"] = "a", ["value"] = new JObject() } };
        yield return new object[] { new JObject { ["name"] = "a", ["value"] = "" } };
    }

    [Theory]
    [MemberData(nameof(InvalidInputs))]
    public void DeclaredInputsRejectMissingUnknownNullAndMistypedValues(JObject inputs) {
        Assert.Equal("invalid_params", Code(() => AutomationInput.Validate(Declared, inputs)));
    }

    [Fact]
    public void DeclaredInputsMustBeAnObject() {
        Assert.Equal("invalid_params", Code(() => AutomationInput.Validate(Declared, new JArray("name"))));
        Assert.Equal("invalid_params", Code(() => AutomationInput.Validate(new List<AutomationInput>(), new JObject { ["any"] = 1 })));
    }
}
