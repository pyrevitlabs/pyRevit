using System.Linq;
using PyRevitLabs.PyRevit.Runtime.Agent;
using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    public sealed class AgentLogDetailsTests {
        private static JArray Elements(int count, string category) {
            return new JArray(Enumerable.Range(1, count).Select(index => new JObject {
                ["id"] = index,
                ["category"] = category,
                ["name"] = category + " " + index,
            }));
        }

        [Fact]
        public void ARunIsSummarizedForTheLog() {
            var response = new JObject {
                ["run_id"] = "abc123",
                ["run_dir"] = "C:\\runs\\abc123",
                ["mode"] = "modify",
                ["status"] = "ok",
                ["decision"] = "committed",
                ["approval"] = "user",
                ["elapsed_ms"] = 1500,
                ["document"] = "Tower.rvt",
                ["document_path"] = "C:\\models\\Tower.rvt",
                ["changes"] = new JObject {
                    ["added_count"] = 2,
                    ["modified_count"] = 1,
                    ["deleted_count"] = 0,
                    ["by_category"] = new JObject { ["Walls"] = 3 },
                    ["added"] = Elements(2, "Walls"),
                    ["modified"] = Elements(1, "Doors"),
                    ["other_documents"] = new JArray(new JObject()),
                },
                ["warnings"] = new JArray("Lost a commit"),
                ["output"] = "done",
                ["engine"] = new JObject { ["implementation"] = "ironpython", ["python"] = "2.7.12" },
            };

            var details = AgentLogDetails.FromRun(response, "print('done')");

            Assert.Equal("abc123", details.Value<string>("run_id"));
            Assert.Equal("C:\\runs\\abc123", details.Value<string>("run_dir"));
            Assert.Equal("committed", details.Value<string>("decision"));
            Assert.Equal("user", details.Value<string>("approval"));
            Assert.Equal(1500, details.Value<int>("elapsed_ms"));
            Assert.Equal("Tower.rvt", details.Value<string>("document"));
            Assert.Equal("C:\\models\\Tower.rvt", details.Value<string>("document_path"));
            Assert.Equal(2, details.Value<int>("added"));
            Assert.Equal(1, details.Value<int>("modified"));
            Assert.Equal(0, details.Value<int>("deleted"));
            Assert.Equal(3, details["by_category"].Value<int>("Walls"));
            Assert.Equal(new[] { "Walls 1", "Walls 2", "Doors 1" }, details["elements"].Select(element => element.Value<string>("name")));
            Assert.Equal(1, details.Value<int>("other_documents"));
            Assert.Equal("Lost a commit", details["warnings"][0].Value<string>());
            Assert.Equal("done", details.Value<string>("output"));
            Assert.Equal("ironpython 2.7.12", details.Value<string>("engine"));
            Assert.Equal("print('done')", details.Value<string>("script"));
            Assert.Equal(JTokenType.Null, details["error"].Type);
        }

        [Fact]
        public void OnlyDocumentsThatStillHoldTheRunsChangesAreUnreverted() {
            var response = new JObject {
                ["changes"] = new JObject {
                    ["other_documents"] = new JArray(
                        new JObject { ["document"] = "Rolled back", ["opened_during_run"] = false, ["rolled_back"] = true },
                        new JObject { ["document"] = "Created by the run", ["opened_during_run"] = true, ["rolled_back"] = false },
                        new JObject { ["document"] = "Closed unsaved", ["opened_during_run"] = false, ["rolled_back"] = false, ["discarded_on_close"] = true },
                        new JObject { ["document"] = "Annex", ["opened_during_run"] = false, ["rolled_back"] = false }),
                },
            };

            var details = AgentLogDetails.FromRun(response, null);

            Assert.Equal(3, details.Value<int>("other_documents"));
            Assert.Equal(new[] { "Annex" }, details["unreverted_documents"].Values<string>());
        }

        [Fact]
        public void ASessionDocumentTheRunKeptIsNeitherAnotherDocumentNorUnreverted() {
            var response = new JObject {
                ["decision"] = "committed",
                ["changes"] = new JObject {
                    ["other_documents"] = new JArray(
                        new JObject { ["document"] = "Annex", ["opened_during_run"] = false, ["in_session"] = true, ["kept"] = true, ["rolled_back"] = false }),
                },
            };

            var details = AgentLogDetails.FromRun(response, null);

            Assert.Equal(0, details.Value<int>("other_documents"));
            Assert.Empty((JArray)details["unreverted_documents"]);
            Assert.Equal(new[] { "Annex" }, details["kept_documents"].Values<string>());
        }

        [Fact]
        public void ADocumentTheRunCreatedIsNotAnotherDocument() {
            var response = new JObject {
                ["decision"] = "committed",
                ["changes"] = new JObject {
                    ["other_documents"] = new JArray(
                        new JObject { ["document"] = "Family1", ["opened_during_run"] = true, ["rolled_back"] = false }),
                },
            };

            var details = AgentLogDetails.FromRun(response, null);

            Assert.Equal(0, details.Value<int>("other_documents"));
            Assert.Empty((JArray)details["unreverted_documents"]);
        }

        [Fact]
        public void ARunThatDidNotCommitOffersOnlyTheElementsItModified() {
            var response = new JObject {
                ["decision"] = "rolled_back",
                ["changes"] = new JObject {
                    ["added"] = Elements(2, "Walls"),
                    ["modified"] = Elements(1, "Doors"),
                },
            };

            var details = AgentLogDetails.FromRun(response, null);

            Assert.Equal(new[] { "Doors 1" }, details["elements"].Select(element => element.Value<string>("name")));
        }

        [Fact]
        public void LongTextIsCutAndOnlyTheFirstElementsAreKept() {
            var response = new JObject {
                ["decision"] = "committed",
                ["output"] = new string('o', AgentLogDetails.MaxOutputChars + 10),
                ["error"] = new JObject {
                    ["type"] = "ValueError",
                    ["message"] = "bad",
                    ["traceback"] = new string('t', AgentLogDetails.MaxTracebackChars + 10),
                },
                ["changes"] = new JObject { ["added"] = Elements(AgentLogDetails.MaxElements + 5, "Walls") },
            };

            var details = AgentLogDetails.FromRun(response, new string('s', AgentLogDetails.MaxScriptChars + 10));

            Assert.StartsWith(new string('o', AgentLogDetails.MaxOutputChars), details.Value<string>("output"));
            Assert.EndsWith("…", details.Value<string>("output"));
            Assert.EndsWith("…", details["error"].Value<string>("traceback"));
            Assert.Equal("ValueError", details["error"].Value<string>("type"));
            Assert.EndsWith("…", details.Value<string>("script"));
            Assert.Equal(AgentLogDetails.MaxElements, ((JArray)details["elements"]).Count);
        }

        [Fact]
        public void ACaptureIsSummarizedWithItsViewAndImage() {
            var response = new JObject {
                ["mode"] = "export",
                ["view"] = new JObject { ["id"] = 31, ["name"] = "Level 1", ["type"] = "FloorPlan" },
                ["path"] = "C:\\agent\\captures\\20261107-a.png",
                ["width"] = 1200,
                ["height"] = 800,
                ["image_base64"] = "iVBORw0KGgo=",
            };

            var details = AgentLogDetails.FromCapture(response, "C:\\agent\\captures\\");

            Assert.Equal("export", details.Value<string>("mode"));
            Assert.Equal("Level 1", details.Value<string>("view"));
            Assert.Equal(1200, details.Value<int>("width"));
            Assert.Equal(800, details.Value<int>("height"));
            Assert.Equal("C:\\agent\\captures\\20261107-a.png", details.Value<string>("image"));
            Assert.Null(details["image_base64"]);
        }

        [Theory]
        [InlineData("C:\\agent\\captures-old\\a.png")]
        [InlineData("C:\\agent\\captures\\..\\runs\\a.png")]
        [InlineData("C:\\agent\\captures\\a.exe")]
        [InlineData("captures\\a.png")]
        [InlineData("")]
        [InlineData(null)]
        public void OnlyAPngInTheCapturesFolderIsKeptAsTheImage(string path) {
            var details = AgentLogDetails.FromCapture(new JObject { ["path"] = path }, "C:\\agent\\captures");

            Assert.Equal(JTokenType.Null, details["image"].Type);
        }

        [Fact]
        public void ARunWithoutChangesOrEngineIsSummarizedWithEmptyValues() {
            var details = AgentLogDetails.FromRun(new JObject { ["status"] = "error" }, null);

            Assert.Equal(0, details.Value<int>("added"));
            Assert.Empty((JObject)details["by_category"]);
            Assert.Empty((JArray)details["elements"]);
            Assert.Empty((JArray)details["warnings"]);
            Assert.Equal(JTokenType.Null, details["engine"].Type);
            Assert.Equal(JTokenType.Null, details["script"].Type);
        }
    }
}
