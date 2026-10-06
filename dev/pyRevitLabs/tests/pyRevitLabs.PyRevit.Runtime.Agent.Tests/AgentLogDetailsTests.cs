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
        public void LongTextIsCutAndOnlyTheFirstElementsAreKept() {
            var response = new JObject {
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
