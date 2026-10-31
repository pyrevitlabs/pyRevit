using System.IO;
using System.Reflection;
using IronPython.Hosting;
using Microsoft.Scripting.Hosting;
using PyRevitLabs.PyRevit.Forms.Testing;
using Xunit;
using Xunit.Abstractions;

namespace PyRevitLabs.PyRevit.Forms.IronPython.Tests;

/// <summary>Run the same shared WPF contracts using the attached IronPython engine.</summary>
/// <remarks>
/// IronPython is the parity reference. Build with <c>-p:IronPythonVersion=IPY2712PR</c> for Revit's
/// default engine; the default is IPY342. Each version builds into its own <c>bin\&lt;version&gt;</c>
/// and <c>obj\&lt;version&gt;</c>, so both can be run back to back:
/// <code>
/// dotnet test ... -p:SkipPyRevitDeploy=true
/// dotnet test ... -p:SkipPyRevitDeploy=true -p:IronPythonVersion=IPY2712PR
/// </code>
/// </remarks>
public class IronPythonFormsTests(ITestOutputHelper output) {
    static readonly string[] Probes = ["probe:SelectionProbe", "probe:IronPythonDockableProbe"];

    static readonly string ExpectedVersion = typeof(IronPythonFormsTests).Assembly
        .GetCustomAttributes<AssemblyMetadataAttribute>()
        .Single(attribute => attribute.Key == "IronPythonVersion").Value!;

    static readonly Lazy<ParitySession> Session = new(() => ParitySession.Run(RunAll, TimeSpan.FromMinutes(5)));

    public static IEnumerable<object[]> Cases => ParitySession.Cases(Probes);

    static void RunAll(CaseLog log) {
        var engine = Python.CreateEngine();
        string Format(Exception ex) => engine.GetService<ExceptionOperations>().FormatException(ex);
        try {
            engine.SetSearchPaths([AppContext.BaseDirectory, Path.Combine(AppContext.BaseDirectory, "stdlib.zip")]);
            var scope = engine.CreateScope();
            scope.SetVariable("fixture_root", AppContext.BaseDirectory);
            scope.SetVariable("ironpython_probe", true);
            scope.SetVariable("case_log", log);
            scope.SetVariable("revit_only_classes", string.Join(",", ParitySession.RevitOnlyClasses));
            engine.Execute("import clr, sys\ncase_log.Engine = sys.version\nfor assembly in ['System.Runtime', 'System.Private.Uri', 'System.ComponentModel', 'System.ObjectModel', 'System.Drawing.Primitives', 'System.Threading', 'System.Console']:\n    clr.AddReference(assembly)", scope);
            engine.Execute(ParitySession.Script("HostStubs.py"), scope);
            engine.Execute(ParitySession.Script("IronPythonProbe.py"), scope);
            ParitySession.RunCase(log, Probes[0], () => engine.Execute(ParitySession.Script("SelectionProbe.py"), scope), Format);
            engine.Execute(ParitySession.Script("ParityRunner.py"), scope);
            ParitySession.RunCase(log, Probes[1], () => engine.Execute(ParitySession.Script("IronPythonDockableProbe.py"), scope), Format);
        }
        catch (Exception ex) {
            throw new InvalidOperationException(Format(ex), ex);
        }
    }

    /// <summary>The engine that ran matches the <c>IronPythonVersion</c> this assembly was built for.</summary>
    [Fact]
    public void EngineMatchesBuildConfiguration() {
        var engine = Session.Value.Log.Engine;
        output.WriteLine("{0}: {1}", ExpectedVersion, engine);
        var prefix = ExpectedVersion switch {
            "IPY2712PR" => "2.7.12",
            "IPY342" => "3.4.2",
            _ => throw new InvalidOperationException("Unknown IronPythonVersion " + ExpectedVersion),
        };
        Assert.StartsWith(prefix, engine);
    }

    /// <summary>Each probe script and parity test passes under IronPython.</summary>
    [Theory]
    [MemberData(nameof(Cases))]
    public void Case(string name) {
        var outcome = Session.Value.Outcome(name);
        output.WriteLine("{0} {1}: {2} {3}", ExpectedVersion, Session.Value.Log.Engine, outcome.Status, outcome.Detail);
        Assert.True(outcome.Succeeded, outcome.Detail);
    }

    /// <summary>Every case the interpreter ran has its own theory row.</summary>
    [Fact]
    public void EveryExecutedCaseIsDiscovered() {
        var discovered = Cases.Select(row => (string)row[0]).ToHashSet();
        var unlisted = Session.Value.Log.Order.Where(name => !discovered.Contains(name)).ToList();
        Assert.True(unlisted.Count == 0, "Cases ran without a theory row: " + string.Join(", ", unlisted));
    }
}
