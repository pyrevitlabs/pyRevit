using pyRevitCLI;
using pyRevitLabs.Common;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

[Collection(CliGlobalState.Name)]
[Trait("Environment", "HostFree")]
[Trait("Level", "Unit")]
public sealed class AgentViewCommandsTests : IDisposable {
    private static readonly byte[] PngBytes = { 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 1, 2, 3 };

    private readonly FakeAgentHost host = new FakeAgentHost();
    private readonly string outputFolder = Directory.CreateTempSubdirectory("pyrevit-agent-out-").FullName;

    public void Dispose() {
        host.Dispose();
        Directory.Delete(outputFolder, recursive: true);
    }

    private static string Printed(Action command) {
        var original = Console.Out;
        var captured = new StringWriter();
        Console.SetOut(captured);
        try {
            command();
        }
        finally {
            Console.SetOut(original);
        }
        return captured.ToString();
    }

    private void AnswerCaptureWithImage() {
        host.Handler = request => FakeAgentHost.Result(request, new JObject {
            ["mode"] = "export",
            ["path"] = @"C:\agent\captures\host-copy.png",
            ["width"] = 1280,
            ["height"] = 720,
            ["image_base64"] = Convert.ToBase64String(PngBytes),
        });
    }

    [Fact]
    public void CaptureWithoutArgumentsAsksForTheActiveViewAndPrintsTheHostCopyWithoutImageData() {
        AnswerCaptureWithImage();

        var printed = Printed(() => PyRevitCLIAgentCmds.CaptureView(null, null, null, null, null));

        var request = Assert.Single(host.RequestsFor("capture"));
        Assert.Empty(request["params"].Children());
        var output = JObject.Parse(printed);
        Assert.Equal(@"C:\agent\captures\host-copy.png", output.Value<string>("path"));
        Assert.Null(output["image_base64"]);
    }

    [Fact]
    public void CapturePassesViewModeAndWidthToTheHost() {
        AnswerCaptureWithImage();

        Printed(() => PyRevitCLIAgentCmds.CaptureView("Level 1", "viewport", "800", null, null));

        var parameters = (JObject)Assert.Single(host.RequestsFor("capture"))["params"];
        Assert.Equal("Level 1", parameters.Value<string>("view"));
        Assert.Equal("viewport", parameters.Value<string>("mode"));
        Assert.Equal(800, parameters.Value<int>("width"));
    }

    [Fact]
    public void CapturePassesTheViewTypeToTheHostOnlyWhenGiven() {
        AnswerCaptureWithImage();

        Printed(() => PyRevitCLIAgentCmds.CaptureView("Level 1", null, null, null, null, viewType: "FloorPlan"));
        Printed(() => PyRevitCLIAgentCmds.CaptureView("Level 1", null, null, null, null));

        var requests = host.RequestsFor("capture");
        Assert.Equal("FloorPlan", requests[0]["params"].Value<string>("view_type"));
        Assert.Null(requests[1]["params"]["view_type"]);
    }

    [Fact]
    public void CaptureWritesTheImageToOutAndReportsThatFileAsThePath() {
        AnswerCaptureWithImage();
        var target = Path.Combine(outputFolder, "nested", "view.png");

        var printed = Printed(() => PyRevitCLIAgentCmds.CaptureView("3d", null, null, target, null));

        Assert.Equal(PngBytes, File.ReadAllBytes(target));
        Assert.Equal(target, JObject.Parse(printed).Value<string>("path"));
    }

    [Theory]
    [InlineData("wide")]
    [InlineData("12.5")]
    [InlineData("")]
    public void CaptureRefusesAWidthThatIsNotAWholeNumberBeforeConnecting(string width) {
        var refused = Assert.Throws<PyRevitException>(
            () => PyRevitCLIAgentCmds.CaptureView(null, null, width, null, "no-such-revit"));

        Assert.Contains("--width", refused.Message);
        Assert.Empty(host.Requests);
    }

    [Fact]
    public void CaptureRefusesAnAnswerWithoutAnImage() {
        host.Handler = request => FakeAgentHost.Result(request, new JObject { ["mode"] = "export" });

        var refused = Assert.Throws<PyRevitException>(
            () => PyRevitCLIAgentCmds.CaptureView(null, null, null, Path.Combine(outputFolder, "none.png"), null));

        Assert.Contains("without an image", refused.Message);
        Assert.False(File.Exists(Path.Combine(outputFolder, "none.png")));
    }

    [Fact]
    public void CaptureListsTheCandidatesOfAnAmbiguousViewName() {
        host.Handler = request => FakeAgentHost.Failure(request, "view_ambiguous", "2 views are named 'Level 1'.", new JObject {
            ["views"] = new JArray(
                new JObject { ["id"] = 311, ["name"] = "Level 1", ["type"] = "FloorPlan", ["number"] = null },
                new JObject { ["id"] = 922, ["name"] = "Level 1", ["type"] = "DrawingSheet", ["number"] = "A101" }),
        });

        var refused = Assert.Throws<PyRevitException>(
            () => PyRevitCLIAgentCmds.CaptureView("Level 1", null, null, null, null));

        Assert.Contains("2 views are named 'Level 1'", refused.Message);
        Assert.Contains("311  FloorPlan  Level 1", refused.Message);
        Assert.Contains("922  DrawingSheet  Level 1 (sheet A101)", refused.Message);
    }

    [Fact]
    public void CaptureKeepsOtherHostErrorsAsTheyAre() {
        host.Handler = request => FakeAgentHost.Failure(request, "view_not_found", "No view named 'x'.");

        var failure = Assert.Throws<AgentClientException>(
            () => PyRevitCLIAgentCmds.CaptureView("x", null, null, null, null));

        Assert.Equal("view_not_found", failure.Code);
    }

    [Fact]
    public void InspectSendsEveryIdAsANumberAndAsksForParametersByDefault() {
        host.Handler = request => FakeAgentHost.Result(request, new JObject { ["elements"] = new JArray() });

        Printed(() => PyRevitCLIAgentCmds.InspectElements(new[] { "311", "-1", "9007199254740993" }, true, null));

        var parameters = (JObject)Assert.Single(host.RequestsFor("inspect_elements"))["params"];
        Assert.Equal(new long[] { 311, -1, 9007199254740993 }, parameters["ids"].Select(id => id.Value<long>()));
        Assert.True(parameters.Value<bool>("parameters"));
    }

    [Fact]
    public void InspectCanLeaveTheParametersOut() {
        host.Handler = request => FakeAgentHost.Result(request, new JObject());

        Printed(() => PyRevitCLIAgentCmds.InspectElements(new[] { "311" }, false, null));

        var parameters = (JObject)Assert.Single(host.RequestsFor("inspect_elements"))["params"];
        Assert.False(parameters.Value<bool>("parameters"));
    }

    [Fact]
    public void InspectRefusesAnIdThatIsNotAWholeNumberBeforeConnecting() {
        var refused = Assert.Throws<PyRevitException>(
            () => PyRevitCLIAgentCmds.InspectElements(new[] { "311", "wall" }, true, "no-such-revit"));

        Assert.Contains("wall", refused.Message);
        Assert.Empty(host.Requests);
    }

    [Fact]
    public void LookupSendsTheNameAndPrintsTheHostAnswer() {
        host.Handler = request => FakeAgentHost.Result(request, new JObject { ["kind"] = "type", ["name"] = "Wall" });

        var printed = Printed(() => PyRevitCLIAgentCmds.LookupApi("Wall.Create", null));

        Assert.Equal("Wall.Create", Assert.Single(host.RequestsFor("lookup_api"))["params"].Value<string>("name"));
        Assert.Equal("Wall", JObject.Parse(printed).Value<string>("name"));
    }

    private static IDictionary<string, DocoptNet.ValueObject> Parse(params string[] argv) {
        var usage = File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "UsagePatterns.txt"));
        return new DocoptNet.Docopt().Apply(usage, argv, help: false, exit: false);
    }

    [Fact]
    public void InspectIdsComeBackInCommandLineOrderNextToTheOptions() {
        var arguments = Parse("agent", "inspect", "3", "1", "2", "--no-parameters", "--revit=2026");

        Assert.Equal(new[] { "3", "1", "2" }, PyRevitCLIArguments.Values(arguments, "<element_id>"));
        Assert.True(arguments["--no-parameters"].IsTrue);
        Assert.Equal("2026", PyRevitCLIArguments.Value(arguments, "--revit"));
    }

    [Fact]
    public void AnArgumentThatIsNotRepeatedHasNoValues() {
        var arguments = Parse("agent", "lookup", "Wall.Create");

        Assert.Empty(PyRevitCLIArguments.Values(arguments, "<api_name>"));
        Assert.Empty(PyRevitCLIArguments.Values(arguments, "<missing>"));
        Assert.Equal("Wall.Create", PyRevitCLIArguments.Value(arguments, "<api_name>"));
    }

    [Fact]
    public void CaptureOptionsAreParsedAndTheViewIsOptional() {
        var withView = Parse("agent", "capture", "Level 1", "--view-type=FloorPlan", "--mode=viewport", "--width=800", "--out=view.png");
        var withoutView = Parse("agent", "capture");

        Assert.Equal("Level 1", PyRevitCLIArguments.Value(withView, "<view>"));
        Assert.Equal("FloorPlan", PyRevitCLIArguments.Value(withView, "--view-type"));
        Assert.Equal("viewport", PyRevitCLIArguments.Value(withView, "--mode"));
        Assert.Equal("800", PyRevitCLIArguments.Value(withView, "--width"));
        Assert.Equal("view.png", PyRevitCLIArguments.Value(withView, "--out"));
        Assert.True(withoutView["capture"].IsTrue);
        Assert.Null(PyRevitCLIArguments.Value(withoutView, "<view>"));
    }

    [Fact]
    public void RunKeepsItsOwnModeOption() {
        var arguments = Parse("agent", "run", "script.py", "--mode=dry_run");

        Assert.True(arguments["run"].IsTrue);
        Assert.False(arguments["capture"].IsTrue);
        Assert.Equal("dry_run", PyRevitCLIArguments.Value(arguments, "--mode"));
    }
}
