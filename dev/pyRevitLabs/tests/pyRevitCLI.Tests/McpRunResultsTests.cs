using pyRevitCLI;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI.Tests;

public class McpRunResultsTests {
    private static JObject Error(string type, string message, string failingLine = null) {
        var error = new JObject { ["type"] = type, ["message"] = message };
        if (failingLine != null)
            error["traceback"] = "Traceback (most recent call last):\n  File \"<agent-script>\", line 3, in <module>\n    "
                + failingLine + "\n" + type + ": " + message;
        return error;
    }

    private static JObject Changes(int added = 0, int modified = 0, int deleted = 0) {
        return new JObject {
            ["added_count"] = added,
            ["modified_count"] = modified,
            ["deleted_count"] = deleted,
            ["by_category"] = new JObject(),
            ["added"] = new JArray(Enumerable.Range(1, added).Select(id => new JObject { ["id"] = id })),
        };
    }

    private static JObject Run(string mode = "query", JObject changes = null, JObject extra = null) {
        var run = new JObject {
            ["status"] = "ok",
            ["run_id"] = "abc123",
            ["mode"] = mode,
            ["decision"] = "rolled_back",
            ["elapsed_ms"] = 12,
            ["changes"] = changes ?? Changes(),
            ["warnings"] = new JArray(),
            ["failures"] = new JArray(),
            ["dialogs"] = new JArray(),
            ["blocked"] = new JArray(),
        };
        if (extra != null)
            run.Merge(extra);
        return run;
    }

    public class CompactTests {
        [Fact]
        public void StatusAndRunIdLeadTheResult() {
            var names = PyRevitMcpRunResults.Compact(Run()).Properties().Select(property => property.Name).ToList();

            Assert.Equal("status", names[0]);
            Assert.Equal("run_id", names[1]);
        }

        [Fact]
        public void QueryRunsDropTheDecisionAndModifyRunsKeepIt() {
            Assert.Null(PyRevitMcpRunResults.Compact(Run("query"))["decision"]);
            Assert.Equal("rolled_back", PyRevitMcpRunResults.Compact(Run("modify"))["decision"].Value<string>());
        }

        [Fact]
        public void EmptyBookkeepingIsDropped() {
            var compact = PyRevitMcpRunResults.Compact(Run());

            foreach (var key in new[] { "changes", "warnings", "failures", "dialogs", "blocked", "output", "result", "approval" })
                Assert.Null(compact[key]);
        }

        [Fact]
        public void NonEmptyBookkeepingIsKept() {
            var compact = PyRevitMcpRunResults.Compact(Run(extra: new JObject {
                ["warnings"] = new JArray("lost commit"),
                ["failures"] = new JArray(new JObject { ["severity"] = "Warning" }),
                ["dialogs"] = new JArray(new JObject { ["message"] = "hi" }),
                ["blocked"] = new JArray(new JObject { ["operation"] = "save" }),
                ["approval"] = "user",
            }));

            foreach (var key in new[] { "warnings", "failures", "dialogs", "blocked" })
                Assert.Single((JArray)compact[key]);
            Assert.Equal("user", compact["approval"].Value<string>());
        }

        [Fact]
        public void AddedIdsAreCappedAtTwentyAndPointToGetRun() {
            var compact = PyRevitMcpRunResults.Compact(Run("modify", Changes(added: 25)));

            Assert.Equal(20, ((JArray)compact["changes"]["added_ids"]).Count);
            Assert.Contains("get_run", compact["changes"].Value<string>("details"));
        }

        [Fact]
        public void ModifiedOrDeletedChangesPointToGetRunForTheDetails() {
            Assert.Contains("get_run", PyRevitMcpRunResults.Compact(Run("modify", Changes(modified: 1)))["changes"].Value<string>("details"));
            Assert.Contains("get_run", PyRevitMcpRunResults.Compact(Run("modify", Changes(deleted: 1)))["changes"].Value<string>("details"));
        }

        [Fact]
        public void FewAddedElementsNeedNoDetailsPointer() {
            var compact = PyRevitMcpRunResults.Compact(Run("modify", Changes(added: 3)));

            Assert.Equal(3, ((JArray)compact["changes"]["added_ids"]).Count);
            Assert.Null(compact["changes"]["details"]);
        }

        [Fact]
        public void ARunThatOnlyChangedAnotherDocumentKeepsItsChanges() {
            var changes = Changes();
            changes["other_documents"] = new JArray(new JObject { ["document"] = "other", ["rolled_back"] = true });

            var compact = PyRevitMcpRunResults.Compact(Run("modify", changes));

            Assert.True(compact["changes"]["other_documents"][0].Value<bool>("rolled_back"));
        }

        [Fact]
        public void TruncatedResultsExplainHowToPageThem() {
            var compact = PyRevitMcpRunResults.Compact(Run(extra: new JObject { ["result"] = "x", ["result_truncated"] = true }));

            Assert.True(compact.Value<bool>("result_truncated"));
            Assert.Contains("get_run", compact.Value<string>("result_note"));
        }

        [Fact]
        public void OutputIsKeptOnlyWhenPresentAndFlagsTruncation() {
            var compact = PyRevitMcpRunResults.Compact(Run(extra: new JObject { ["output"] = "hello", ["output_truncated"] = true }));

            Assert.Equal("hello", compact.Value<string>("output"));
            Assert.True(compact.Value<bool>("output_truncated"));
        }

        [Fact]
        public void NullResultsAreOmitted() {
            Assert.Null(PyRevitMcpRunResults.Compact(Run(extra: new JObject { ["result"] = JValue.CreateNull() }))["result"]);
        }

        [Fact]
        public void EngineBecomesImplementationAndVersion() {
            var compact = PyRevitMcpRunResults.Compact(Run(extra: new JObject {
                ["engine"] = new JObject { ["implementation"] = "ironpython", ["python"] = "3.4.2" },
            }));

            Assert.Equal("ironpython 3.4.2", compact.Value<string>("engine"));
        }

        [Fact]
        public void ErrorsKeepTypeMessageTracebackAndAHint() {
            var run = Run(extra: new JObject {
                ["status"] = "error",
                ["error"] = Error("AttributeError", "'Autodesk.Revit.DB' object has no attribute 'Wal'", "x = DB.Wal"),
            });

            var error = PyRevitMcpRunResults.Compact(run)["error"];

            Assert.Equal("AttributeError", error.Value<string>("type"));
            Assert.NotNull(error["traceback"]);
            Assert.Contains("lookup_revit_api(name='Wal')", error.Value<string>("hint"));
        }

        [Fact]
        public void ANonTextTracebackIsDropped() {
            var error = new JObject { ["type"] = "timeout", ["message"] = "slow", ["traceback"] = JValue.CreateNull() };

            var shaped = PyRevitMcpRunResults.Compact(Run(extra: new JObject { ["error"] = error }))["error"];

            Assert.Null(shaped["traceback"]);
            Assert.Null(shaped["hint"]);
        }
    }

    public class HintTests {
        [Fact]
        public void ChangingTheDocumentOutsideATransactionPointsToShowElements() {
            var hint = PyRevitMcpRunResults.HintFor(Error("InvalidOperationException", "Modification of the document outside of transaction"));

            Assert.Contains("show_elements", hint);
            Assert.Contains("run_modify", hint);
        }

        [Fact]
        public void ImportingDbOrUiIsExplained() {
            Assert.Contains("already injected", PyRevitMcpRunResults.HintFor(Error("ImportError", "No module named 'DB'")));
            Assert.Contains("already injected", PyRevitMcpRunResults.HintFor(Error("ImportError", "No module named UI")));
        }

        [Fact]
        public void ANameThatCannotBeImportedPointsToTheLookup() {
            var hint = PyRevitMcpRunResults.HintFor(Error("ImportError", "cannot import name Wall"));

            Assert.Contains("lookup_revit_api(name='Wall')", hint);
        }

        [Fact]
        public void OtherImportErrorsGetNoHint() {
            Assert.Null(PyRevitMcpRunResults.HintFor(Error("ImportError", "No module named 'numpy'")));
        }

        [Fact]
        public void ATypeWithoutAPublicConstructorNamesItsFactories() {
            var hint = PyRevitMcpRunResults.HintFor(Error("TypeError", "cannot create instances of Room because it has no public constructors"));

            Assert.Contains("Room.Create", hint);
            Assert.Contains("doc.Create.NewRoom", hint);
        }

        [Fact]
        public void AReadOnlyAttributeIsExplained() {
            var hint = PyRevitMcpRunResults.HintFor(Error("AttributeError", "attribute 'Name' of 'Room' object is read-only"));

            Assert.Contains("Room.Name is read-only", hint);
        }

        [Fact]
        public void ApiOnlyClassesInCollectorsPointToCategories() {
            var hint = PyRevitMcpRunResults.HintFor(Error("Exception", "Room is not in Revit's native object model"));

            Assert.Contains("OfCategory", hint);
        }

        [Fact]
        public void AManagedExceptionPointsAtTheNetDetails() {
            var hint = PyRevitMcpRunResults.HintFor(Error("Exception", "A managed exception was thrown by the method"));

            Assert.Contains("[.NET: ...]", hint);
        }

        [Fact]
        public void AMissingRevitNamePointsToTheLookup() {
            var hint = PyRevitMcpRunResults.HintFor(Error("AttributeError", "'Autodesk.Revit.DB' object has no attribute 'Wal'", "x = DB.Wal"));

            Assert.Equal("'Wal' does not exist in Autodesk.Revit.DB. Find the right name with lookup_revit_api(name='Wal') before retrying.", hint);
        }

        [Fact]
        public void AMissingFactoryOnATypeNamesTheTypeFromTheFailingLine() {
            var hint = PyRevitMcpRunResults.HintFor(Error("AttributeError", "'type' object has no attribute 'CreateWall'", "w = Wall.CreateWall(doc)"));

            Assert.Contains("Wall has no CreateWall", hint);
            Assert.Contains("doc.Create.New", hint);
        }

        [Fact]
        public void AMissingMemberOnATypeNamesTheTypeOrAdmitsItDoesNotKnow() {
            var named = PyRevitMcpRunResults.HintFor(Error("AttributeError", "'type' object has no attribute 'Purple'", "c = Color.Purple"));
            var unknown = PyRevitMcpRunResults.HintFor(Error("AttributeError", "'type' object has no attribute 'Purple'"));

            Assert.Contains("Color has no member 'Purple'", named);
            Assert.Contains("No class or enum on the failing line has a member 'Purple'", unknown);
        }

        [Fact]
        public void AMissingMemberOnAnObjectSuggestsFilteringByClass() {
            var hint = PyRevitMcpRunResults.HintFor(Error("AttributeError", "'Element' object has no attribute 'Width'"));

            Assert.Contains("Element has no 'Width'", hint);
            Assert.Contains("isinstance()", hint);
        }

        [Fact]
        public void AWrongArgumentCountNamesTheCallFromTheFailingLine() {
            var hint = PyRevitMcpRunResults.HintFor(Error("TypeError", "Create() takes exactly 4 arguments (2 given)", "w = Wall.Create(doc, line)"));

            Assert.Contains("Wrong number of arguments for Create", hint);
            Assert.Contains("lookup_revit_api(name='Wall.Create')", hint);
        }

        [Fact]
        public void APythonListWhereANetCollectionIsExpectedGetsTheConversion() {
            var hint = PyRevitMcpRunResults.HintFor(Error("TypeError", "expected ICollection[ElementId], got list"));

            Assert.Contains("List[DB.ElementId](python_items)", hint);
        }

        [Fact]
        public void ACollectionWithoutAnItemTypeDefaultsToElementId() {
            var hint = PyRevitMcpRunResults.HintFor(Error("TypeError", "expected IList, got tuple"));

            Assert.Contains("List[DB.ElementId](python_items)", hint);
        }

        [Fact]
        public void AnyOtherWrongTypeListsTheCallsOnTheFailingLine() {
            var withCalls = PyRevitMcpRunResults.HintFor(Error("TypeError", "expected Level, got str", "w = Wall.Create(doc, line, 'L1')"));
            var withoutCalls = PyRevitMcpRunResults.HintFor(Error("TypeError", "expected Level, got str"));

            Assert.Contains("expected Level, got str", withCalls);
            Assert.Contains("'Wall.Create'", withCalls);
            Assert.Contains("Check the called method's overloads", withoutCalls);
        }

        [Fact]
        public void ATypeErrorWithNoRecognizedShapeStillGetsTheGenericHint() {
            var hint = PyRevitMcpRunResults.HintFor(Error("TypeError", "something odd"));

            Assert.Contains("Check the Revit API names and signatures", hint);
        }

        [Fact]
        public void OtherErrorTypesGetNoHint() {
            Assert.Null(PyRevitMcpRunResults.HintFor(Error("ValueError", "bad value")));
            Assert.Null(PyRevitMcpRunResults.HintFor(Error("timeout", "too slow")));
        }
    }

    public class LookupTests {
        [Theory]
        [InlineData("AttributeError", "'Autodesk.Revit.DB' object has no attribute 'Wal'", "Wal")]
        [InlineData("AttributeError", "'Autodesk.Revit.UI' object has no attribute 'TaskDialogX'", "TaskDialogX")]
        [InlineData("AttributeError", "'Element' object has no attribute 'Width'", null)]
        [InlineData("TypeError", "'Autodesk.Revit.DB' object has no attribute 'Wal'", null)]
        [InlineData("AttributeError", "something else", null)]
        public void OnlyAMissingNameOnTheInjectedNamespacesIsReported(string type, string message, string expected) {
            Assert.Equal(expected, PyRevitMcpRunResults.MissingRevitApiName(Error(type, message)));
        }

        [Fact]
        public void AFoundNameBecomesTheScriptSpelling() {
            var hint = PyRevitMcpRunResults.HintFromLookup("Room", new JObject {
                ["found"] = true,
                ["full_name"] = "Autodesk.Revit.DB.Architecture.Room",
            });

            Assert.Equal("'Room' is Autodesk.Revit.DB.Architecture.Room: use DB.Architecture.Room in the script.", hint);
        }

        [Fact]
        public void AnAmbiguousNameListsAtMostSixCandidates() {
            var lookup = new JObject {
                ["ambiguous"] = true,
                ["matches"] = new JArray(Enumerable.Range(1, 8).Select(index => "Autodesk.Revit.DB.Space" + index)),
            };

            var hint = PyRevitMcpRunResults.HintFromLookup("Space", lookup);

            Assert.Contains("DB.Space1", hint);
            Assert.Contains("DB.Space6", hint);
            Assert.DoesNotContain("DB.Space7", hint);
        }

        [Fact]
        public void SuggestionsKeepOnlyRevitTypesAndSkipNestedOnes() {
            var lookup = new JObject {
                ["found"] = false,
                ["suggestions"] = new JArray("Autodesk.Revit.DB.Wall", "Autodesk.Revit.DB.Wall+Nested", "System.Object"),
            };

            var hint = PyRevitMcpRunResults.HintFromLookup("Wal", lookup);

            Assert.Equal("There is no Revit API type named 'Wal'. Similar types: DB.Wall.", hint);
        }

        [Fact]
        public void WithoutSuggestionsTheHintOnlyStatesTheMiss() {
            var hint = PyRevitMcpRunResults.HintFromLookup("Zzz", new JObject { ["found"] = false, ["suggestions"] = new JArray() });

            Assert.Equal("There is no Revit API type named 'Zzz'.", hint);
        }

        [Fact]
        public void ANullLookupGivesNoHint() {
            Assert.Null(PyRevitMcpRunResults.HintFromLookup("Zzz", null));
        }
    }
}
