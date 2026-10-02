using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

public partial class McpServerTests {
    private static JObject DocumentContext(JObject request, string title = "Model", string path = null) {
        var document = new JObject { ["title"] = title };
        if (path != null)
            document["path"] = path;
        return FakeAgentHost.Result(request, new JObject { ["document"] = document });
    }

    private static JObject NoDocumentContext(JObject request) {
        return FakeAgentHost.Result(request, new JObject { ["document"] = JValue.CreateNull() });
    }

    [Fact]
    public void AnAutomationRunsItsReviewedScriptAsAQueryAndNeverTheCallersText() {
        host.Handler = request => request.Value<string>("method") == "get_context" ? DocumentContext(request) : RunResponse(request);

        var response = Single(ToolCall(1, "run_automation", new JObject {
            ["id"] = "pyrevit.levels.resolve",
            ["inputs"] = new JObject { ["name"] = "Level 1" },
            ["engine"] = "cpython",
            ["timeout_s"] = 9,
            ["workspace"] = "C:\\evil",
            ["script"] = "import os",
            ["title"] = "Hijack",
        }));

        var sent = Assert.Single(host.RequestsFor("run"))["params"];
        Assert.Equal("query", sent.Value<string>("mode"));
        Assert.Equal("Resolve level", sent.Value<string>("title"));
        Assert.Contains("find_level", sent.Value<string>("script"));
        Assert.DoesNotContain("import os", sent.Value<string>("script"));
        Assert.Equal("Level 1", sent["inputs"].Value<string>("name"));
        Assert.Equal("cpython", sent.Value<string>("engine"));
        Assert.Equal(9, sent.Value<int>("timeout_s"));
        Assert.Null(sent["workspace"]);
        Assert.False(IsError(response));
        Assert.Equal("abc123def456", Payload(response).Value<string>("run_id"));
    }

    [Fact]
    public void AnAutomationThatNeedsADocumentStopsBeforeRunningWhenNoneIsOpen() {
        host.Handler = request => NoDocumentContext(request);

        var response = Single(ToolCall(1, "run_automation", new JObject {
            ["id"] = "pyrevit.levels.resolve",
            ["inputs"] = new JObject { ["name"] = "Level 1" },
        }));

        Assert.True(IsError(response));
        Assert.Equal("no_active_document", Payload(response).Value<string>("error"));
        Assert.Empty(host.RequestsFor("run"));
    }

    [Fact]
    public void AnAutomationThatNeedsNoDocumentNeverAsksForTheContext() {
        host.Handler = request => RunResponse(request);

        Single(ToolCall(1, "run_automation", new JObject {
            ["id"] = "pyrevit.units.parse-length",
            ["inputs"] = new JObject { ["value"] = "10' 6\"" },
        }));

        Assert.Empty(host.RequestsFor("get_context"));
        Assert.Single(host.RequestsFor("run"));
    }

    [Fact]
    public void AnAutomationWithAnUnknownIdOrBadInputsNeverReachesRevit() {
        var unknown = Single(ToolCall(1, "run_automation", new JObject { ["id"] = "os.system", ["inputs"] = new JObject() }));
        var badInputs = Single(ToolCall(2, "run_automation", new JObject {
            ["id"] = "pyrevit.units.parse-slope",
            ["inputs"] = new JObject { ["value"] = "8:12", ["extra"] = 1 },
        }));

        Assert.Equal("unknown_automation_id", Payload(unknown).Value<string>("error"));
        Assert.Equal("invalid_params", Payload(badInputs).Value<string>("error"));
        Assert.Empty(host.Requests);
    }

    [Fact]
    public void ALinkToTheActiveDocumentSelectsAndZoomsByDefault() {
        host.Handler = request => request.Value<string>("method") == "get_context"
            ? DocumentContext(request, path: "C:\\Models\\Tower.rvt")
            : FakeAgentHost.Result(request, new JObject { ["count"] = 2 });

        var response = Single(ToolCall(1, "navigate_revit_link", new JObject {
            ["link"] = new JObject {
                ["destination"] = "element",
                ["document"] = new JObject { ["title"] = "Tower", ["path"] = "c:\\models\\TOWER.rvt" },
                ["ids"] = new JArray(10, 11),
            },
        }));

        var show = Assert.Single(host.RequestsFor("show"))["params"];
        Assert.Equal("select", show.Value<string>("action"));
        Assert.True(show.Value<bool>("zoom"));
        Assert.Equal(new[] { 10, 11 }, show["ids"].Select(id => id.Value<int>()));
        Assert.Equal(2, Payload(response).Value<int>("count"));
    }

    [Fact]
    public void ALinkHonoursTheRequestedActionAndZoom() {
        host.Handler = request => request.Value<string>("method") == "get_context"
            ? DocumentContext(request)
            : FakeAgentHost.Result(request, new JObject());

        Single(ToolCall(1, "navigate_revit_link", new JObject {
            ["link"] = new JObject {
                ["destination"] = "element",
                ["document"] = new JObject { ["title"] = "Model" },
                ["ids"] = new JArray(1),
            },
            ["action"] = "isolate",
            ["zoom"] = false,
        }));

        var show = Assert.Single(host.RequestsFor("show"))["params"];
        Assert.Equal("isolate", show.Value<string>("action"));
        Assert.False(show.Value<bool>("zoom"));
    }

    [Fact]
    public void ALinkToAnotherDocumentIsStaleAndNothingIsShown() {
        host.Handler = request => DocumentContext(request, "Tower", "C:\\Models\\Tower.rvt");

        var byPath = Single(ToolCall(1, "navigate_revit_link", new JObject {
            ["link"] = new JObject {
                ["destination"] = "element",
                ["document"] = new JObject { ["title"] = "Tower", ["path"] = "C:\\Models\\Annex.rvt" },
                ["ids"] = new JArray(1),
            },
        }));
        var byTitle = Single(ToolCall(2, "navigate_revit_link", new JObject {
            ["link"] = new JObject {
                ["destination"] = "element",
                ["document"] = new JObject { ["title"] = "Annex" },
                ["ids"] = new JArray(1),
            },
        }));

        Assert.Equal("stale_link", Payload(byPath).Value<string>("error"));
        Assert.Equal("stale_link", Payload(byTitle).Value<string>("error"));
        Assert.Empty(host.RequestsFor("show"));
    }

    [Fact]
    public void ALinkWithoutAnActiveDocumentIsStale() {
        host.Handler = request => NoDocumentContext(request);

        var response = Single(ToolCall(1, "navigate_revit_link", new JObject {
            ["link"] = new JObject {
                ["destination"] = "element",
                ["document"] = new JObject { ["title"] = "Model" },
                ["ids"] = new JArray(1),
            },
        }));

        Assert.Equal("stale_link", Payload(response).Value<string>("error"));
    }

    [Fact]
    public void MalformedLinksAreRejectedWithoutReachingRevit() {
        var links = new JToken[] {
            new JValue("not an object"),
            new JObject { ["destination"] = "view", ["document"] = new JObject { ["title"] = "M" }, ["ids"] = new JArray(1) },
            new JObject { ["destination"] = "element", ["document"] = new JObject { ["title"] = "M" }, ["ids"] = new JArray() },
            new JObject { ["destination"] = "element", ["document"] = new JObject { ["title"] = "M" } },
            new JObject { ["destination"] = "element", ["ids"] = new JArray(1) },
        };

        foreach (var link in links) {
            var response = Single(ToolCall(1, "navigate_revit_link", new JObject { ["link"] = link }));
            Assert.Equal("invalid_params", Payload(response).Value<string>("error"));
        }
        Assert.Empty(host.Requests);
    }

    [Fact]
    public void EveryInvocableAutomationIsAlsoMarkedInTheLibrary() {
        var listing = Payload(Single(ToolCall(1, "list_automation", new JObject { ["limit"] = 50 })));

        var ids = listing["operations"].Select(operation => operation["automation"].Value<string>("id")).ToList();
        foreach (var id in new[] { "pyrevit.units.parse-length", "pyrevit.units.parse-slope", "pyrevit.levels.resolve", "pyrevit.elements.by-category" })
            Assert.Contains(id, ids);
        foreach (var operation in listing["operations"]) {
            Assert.False(string.IsNullOrWhiteSpace(operation["automation"].Value<string>("plain_english")), operation.Value<string>("name"));
            Assert.False(string.IsNullOrWhiteSpace(operation["automation"].Value<string>("mode")), operation.Value<string>("name"));
        }
        Assert.Equal(ids.Count, ids.Distinct(StringComparer.OrdinalIgnoreCase).Count());
    }

    [Fact]
    public void ThePyrevitLookupFindsALibraryFunctionWithoutRevit() {
        var lookup = Payload(Single(ToolCall(1, "lookup_pyrevit_api", new JObject { ["query"] = "find_level" })));

        Assert.True(lookup.Value<bool>("found"));
        Assert.Contains("pyrevit.revit.db.query.find_level", lookup["matches"].Select(match => match.Value<string>("name")));
        Assert.Empty(host.Requests);
    }

    [Fact]
    public void ListedSkillsCarryTheirSourceAndAHash() {
        var skills = JArray.Parse(Text(Single(ToolCall(1, "list_skills")))).Cast<JObject>().ToList();

        var core = Assert.Single(skills, skill => skill.Value<string>("name") == "revit-scripting");
        Assert.Equal("pyrevit", core.Value<string>("source"));
        Assert.Matches("^[0-9a-f]{64}$", core.Value<string>("sha256"));
        Assert.All(skills, skill => Assert.False(string.IsNullOrWhiteSpace(skill.Value<string>("description"))));
    }
}
