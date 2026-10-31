using System.IO;
using PyRevitLabs.PyRevit.Forms.Testing;
using Python.Runtime;
using Xunit;
using Xunit.Abstractions;

namespace PyRevitLabs.PyRevit.Forms.Tests;

/// <summary>Exercise real WPF and the shipped pythonnet without starting Revit.</summary>
/// <remarks>
/// One CPython interpreter runs every probe and parity test once per process; each case is a
/// separate theory row so one failure does not hide the others.
/// </remarks>
public class FormsBackendTests(ITestOutputHelper output) {
    const string UnownedCallbackProbe = "probe:UnownedCallbackProbe";

    static readonly string[] Probes = ["probe:FormsProbe", "probe:BindingProbe", "probe:SelectionProbe", UnownedCallbackProbe];

    static readonly Lazy<ParitySession> Session = new(() => ParitySession.Run(RunAll, TimeSpan.FromMinutes(5)));

    public static IEnumerable<object[]> Cases => ParitySession.Cases(Probes);

    static void RunAll(CaseLog log) {
        GC.KeepAlive(typeof(System.Windows.Window).Assembly);
        GC.KeepAlive(typeof(System.Windows.Media.Visual).Assembly);
        GC.KeepAlive(typeof(System.Windows.DependencyObject).Assembly);
        Runtime.PythonDLL = Path.Combine(AppContext.BaseDirectory, "CPY3123", "python312.dll");
        PythonEngine.Initialize();
        PythonEngine.BeginAllowThreads();
        using var gil = Py.GIL();
        using var scope = Py.CreateScope();
        scope.Set("fixture_root", AppContext.BaseDirectory);
        scope.Set("case_log", log);
        scope.Set("revit_only_classes", string.Join(",", ParitySession.RevitOnlyClasses));
        scope.Exec("import sys\ncase_log.Engine = sys.version");
        scope.Exec(ParitySession.Script("HostStubs.py"));
        foreach (var probe in Probes) {
            var file = probe.Substring("probe:".Length) + ".py";
            ParitySession.RunCase(log, probe, () => {
                scope.Exec(ParitySession.Script(file));
                if (probe == UnownedCallbackProbe) {
                    PumpWithoutPythonCaller();
                    scope.Exec("check_unowned_callbacks()");
                }
            });
        }
        scope.Exec(ParitySession.Script("ParityRunner.py"));
    }

    /// <summary>Run the dispatcher work a probe queued while no Python frame is executing.</summary>
    /// <remarks>Revit delivers input to a modeless window or a dockable page the same way.</remarks>
    static void PumpWithoutPythonCaller() {
        System.Windows.Threading.Dispatcher.CurrentDispatcher.Invoke(
            System.Windows.Threading.DispatcherPriority.Background, new Action(() => { }));
    }

    /// <summary>Each probe script and parity test passes under CPython.</summary>
    [Theory]
    [MemberData(nameof(Cases))]
    public void Case(string name) {
        var outcome = Session.Value.Outcome(name);
        output.WriteLine("CPython {0}: {1} {2}", Session.Value.Log.Engine, outcome.Status, outcome.Detail);
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
