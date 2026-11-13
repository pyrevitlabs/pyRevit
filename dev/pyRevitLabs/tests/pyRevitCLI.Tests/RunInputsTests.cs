using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;

namespace pyRevitCLI.Tests;

[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public sealed class RunInputsTests : IDisposable {
    private readonly string inputsFile = Path.GetTempFileName();

    public void Dispose() {
        File.Delete(inputsFile);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void NoInputsStayNull(string inputs) {
        Assert.Null(PyRevitRunner.NormalizeInputs(inputs));
    }

    [Fact]
    public void InputsAreCompactedToASingleLine() {
        var normalized = PyRevitRunner.NormalizeInputs("{\n  \"name\": \"Wall\",\n  \"ids\": [1, 2]\n}");

        Assert.Equal("{\"name\":\"Wall\",\"ids\":[1,2]}", normalized);
    }

    [Fact]
    public void NonAsciiTextIsEscapedAndQuotesSurviveTheRoundTrip() {
        var normalized = PyRevitRunner.NormalizeInputs("{\"name\":\"Gr\u00f6\u00dfe \\\"A\\\"\"}");

        Assert.Equal("{\"name\":\"Gr\\u00f6\\u00dfe \\\"A\\\"\"}", normalized);
    }

    [Fact]
    public void DateLikeStringsAreNotReformatted() {
        var normalized = PyRevitRunner.NormalizeInputs("{\"on\":\"2024-01-31\"}");

        Assert.Equal("{\"on\":\"2024-01-31\"}", normalized);
    }

    [Theory]
    [InlineData("[1, 2]")]
    [InlineData("\"text\"")]
    [InlineData("42")]
    [InlineData("null")]
    public void InputsThatAreNotAnObjectAreRefused(string inputs) {
        var refused = Assert.Throws<PyRevitException>(() => PyRevitRunner.NormalizeInputs(inputs));

        Assert.Contains("JSON object", refused.Message);
    }

    [Fact]
    public void InputsThatAreNotJsonAreRefused() {
        var refused = Assert.Throws<PyRevitException>(() => PyRevitRunner.NormalizeInputs("{name: "));

        Assert.Contains("not valid JSON", refused.Message);
    }

    [Theory]
    [InlineData("{\"a\":1} garbage")]
    [InlineData("{\"a\":1}{\"b\":2}")]
    [InlineData("{\"a\":1} 7")]
    public void TextAfterTheJsonObjectIsRefused(string inputs) {
        var refused = Assert.Throws<PyRevitException>(() => PyRevitRunner.NormalizeInputs(inputs));

        Assert.Contains("not valid JSON", refused.Message);
    }

    [Fact]
    public void TrailingWhitespaceAfterTheJsonObjectIsAccepted() {
        Assert.Equal("{\"a\":1}", PyRevitRunner.NormalizeInputs("{\"a\":1}  "));
    }

    [Fact]
    public void InputsFileIsReadAndNormalized() {
        File.WriteAllText(inputsFile, "{\n \"count\": 3\n}");

        Assert.Equal("{\"count\":3}", PyRevitRunner.ReadInputs(null, inputsFile));
    }

    [Fact]
    public void MissingInputsFileIsRefused() {
        var refused = Assert.Throws<PyRevitException>(
            () => PyRevitRunner.ReadInputs(null, inputsFile + ".missing"));

        Assert.Contains("Inputs file not found", refused.Message);
    }

    [Fact]
    public void WithoutAnyOptionThereAreNoInputs() {
        Assert.Null(PyRevitRunner.ReadInputs(null, null));
    }
}
