using pyRevitCLI;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

public class AutomationOperationsTests {
    private static readonly string[] Ids = {
        "pyrevit.units.parse-length", "pyrevit.units.parse-slope", "pyrevit.levels.resolve", "pyrevit.elements.by-category",
    };

    private static string Code(Action action) => Assert.Throws<AgentClientException>(action).Code;

    private static JObject Valid(string id) {
        return id switch {
            "pyrevit.levels.resolve" => new JObject { ["name"] = "Level 1" },
            "pyrevit.elements.by-category" => new JObject { ["categories"] = new JArray("Walls") },
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
    public void CategoriesNeedBetweenOneAndTwentyNonBlankShortNames() {
        PyRevitAutomationOperations.Resolve("pyrevit.elements.by-category", new JObject { ["categories"] = new JArray(Enumerable.Repeat("Walls", 20)) });
        PyRevitAutomationOperations.Resolve("pyrevit.elements.by-category", new JObject { ["categories"] = new JArray(new string('c', 128)) });

        foreach (var categories in new JToken[] {
            new JArray(),
            new JArray(Enumerable.Repeat("Walls", 21)),
            new JArray(""),
            new JArray("  "),
            new JArray(new string('c', 129)),
            new JArray(1),
            new JValue("Walls"),
        })
            Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve("pyrevit.elements.by-category", new JObject { ["categories"] = categories })));
        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve("pyrevit.elements.by-category", new JObject())));
    }

    [Fact]
    public void TheCategoryLimitDefaultsToFiftyAndIsBoundedToTwoHundred() {
        var defaulted = PyRevitAutomationOperations.Resolve("pyrevit.elements.by-category", new JObject { ["categories"] = new JArray("Walls") });
        Assert.Equal(50, defaulted["inputs"].Value<int>("limit"));
        Assert.Equal(1, PyRevitAutomationOperations.Resolve("pyrevit.elements.by-category", new JObject { ["categories"] = new JArray("Walls"), ["limit"] = 1 })["inputs"].Value<int>("limit"));
        Assert.Equal(200, PyRevitAutomationOperations.Resolve("pyrevit.elements.by-category", new JObject { ["categories"] = new JArray("Walls"), ["limit"] = 200 })["inputs"].Value<int>("limit"));

        foreach (var limit in new JToken[] { 0, -1, 201, 1.5, "5", true })
            Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve("pyrevit.elements.by-category", new JObject { ["categories"] = new JArray("Walls"), ["limit"] = limit })));
        Assert.Equal("invalid_params", Code(() => PyRevitAutomationOperations.Resolve("pyrevit.elements.by-category", new JObject { ["categories"] = new JArray("Walls"), ["extra"] = 1 })));
    }

    [Theory]
    [InlineData("pyrevit.units.parse-length")]
    [InlineData("pyrevit.units.parse-slope")]
    [InlineData("pyrevit.levels.resolve")]
    [InlineData("pyrevit.elements.by-category")]
    public void TheScriptNeverContainsTheCallersInput(string id) {
        var marker = "SENTINEL_" + Guid.NewGuid().ToString("N");
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
}
