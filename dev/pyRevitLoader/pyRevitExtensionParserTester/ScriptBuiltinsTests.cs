using System.Collections.Generic;

using NUnit.Framework;
using PyRevitLabs.PyRevit.Runtime;

namespace pyRevitExtensionParserTester
{
    /// <summary>
    /// Covers the reserved-builtin filter that keeps caller-supplied variables from
    /// overwriting what the engines inject. IronPython already filtered; CPython did
    /// not, so the same dictionary had two meanings depending on the engine.
    /// </summary>
    [TestFixture]
    public class ScriptBuiltinsTests
    {
        private static readonly string[] AllReservedNames = {
            "__execid__",
            "__timestamp__",
            "__cachedengine__",
            "__cachedengineid__",
            "__scriptruntime__",
            "__revit__",
            "__commanddata__",
            "__elements__",
            "__uibutton__",
            "__commandpath__",
            "__configcommandpath__",
            "__commandname__",
            "__commandbundle__",
            "__commandextension__",
            "__commanduniqueid__",
            "__commandcontrolid__",
            "__forceddebugmode__",
            "__shiftclick__",
            "__result__",
            "__eventsender__",
            "__eventargs__",
        };

        [Test]
        public void EveryInjectedBuiltinIsReserved()
        {
            foreach (var name in AllReservedNames)
            {
                Assert.That(ScriptBuiltins.IsReserved(name), Is.True, name + " must stay reserved");
            }
        }

        [Test]
        public void OrdinaryScriptVariablesAreNotReserved()
        {
            foreach (var name in new[] { "MY_VAR", "__revit", "revit", "__result", "REVIT__", "" })
            {
                Assert.That(ScriptBuiltins.IsReserved(name), Is.False, name + " must not be reserved");
            }
        }

        [Test]
        public void FilterUserVariablesDropsReservedNamesAndKeepsTheRest()
        {
            var variables = new Dictionary<string, object> {
                { "__revit__", "hijacked handle" },
                { "__eventsender__", "hijacked sender" },
                { "__result__", "hijacked result" },
                { "__revit", "near miss" },
                { "MY_VAR", 42 },
            };

            var kept = new List<string>();
            foreach (var variable in ScriptBuiltins.FilterUserVariables(variables))
                kept.Add(variable.Key);

            Assert.That(kept, Is.EqualTo(new[] { "__revit", "MY_VAR" }));
        }

        [Test]
        public void FilterUserVariablesToleratesAMissingDictionary()
        {
            var kept = new List<string>();
            foreach (var variable in ScriptBuiltins.FilterUserVariables(null))
                kept.Add(variable.Key);

            Assert.That(kept, Is.Empty);
        }
    }
}
