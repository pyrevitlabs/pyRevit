using System.Collections.Concurrent;
using System.IO;
using System.Text.RegularExpressions;

namespace PyRevitLabs.PyRevit.Forms.Testing;

/// <summary>Outcome of one probe script or parity test inside a shared interpreter run.</summary>
public sealed class CaseOutcome {
    public CaseOutcome(string status, string detail) {
        Status = status;
        Detail = detail;
    }

    /// <summary><c>running</c>, <c>passed</c>, <c>failed</c> or <c>skipped</c>.</summary>
    public string Status { get; }

    public string Detail { get; }

    public bool Succeeded => Status is "passed" or "skipped";
}

/// <summary>Receives per-case results from Python; both engines call these methods directly.</summary>
public sealed class CaseLog {
    readonly ConcurrentDictionary<string, CaseOutcome> _outcomes = new();
    readonly ConcurrentQueue<string> _order = new();

    /// <summary>The interpreter's <c>sys.version</c>, set by the hosting fixture.</summary>
    public string Engine { get; set; } = "";

    public string? Running { get; private set; }

    public IReadOnlyDictionary<string, CaseOutcome> Outcomes => _outcomes;

    public IEnumerable<string> Order => _order;

    public void Start(string name) {
        Running = name;
        _order.Enqueue(name);
        _outcomes[name] = new CaseOutcome("running", "");
    }

    public void Pass(string name) => Finish(name, "passed", "");

    public void Fail(string name, string detail) => Finish(name, "failed", detail);

    public void Skip(string name, string reason) => Finish(name, "skipped", reason);

    void Finish(string name, string status, string detail) {
        _outcomes[name] = new CaseOutcome(status, detail);
        if (Running == name) {
            Running = null;
        }
    }
}

/// <summary>Runs one interpreter session on an STA thread and answers per-case queries.</summary>
/// <remarks>
/// The interpreter and the WPF dispatcher are process-scoped, so every case of a fixture shares one
/// session; one failing case is reported by its own theory row instead of hiding later cases.
/// A case still marked running when the timeout elapses is reported as deadlocked, and cases never
/// started are reported as not reached.
/// </remarks>
public sealed class ParitySession {
    /// <summary>Test classes that need the Revit acceptance fixture and never run in these processes.</summary>
    public static readonly string[] RevitOnlyClasses = ["DocumentFormsParityTests"];

    readonly CaseLog _log = new();
    string? _setupFailure;
    bool _timedOut;

    ParitySession() { }

    public CaseLog Log => _log;

    /// <summary>Run <paramref name="body"/> once on a background STA thread and wait up to <paramref name="timeout"/>.</summary>
    /// <param name="body">Initializes the engine and records every case through the given log.
    /// An exception it lets escape is reported as a setup failure for every case it did not record.</param>
    public static ParitySession Run(Action<CaseLog> body, TimeSpan timeout) {
        var session = new ParitySession();
        var thread = new Thread(() => {
            try {
                body(session._log);
            }
            catch (Exception ex) {
                session._setupFailure = ex.ToString();
            }
        }) { IsBackground = true };
        thread.SetApartmentState(ApartmentState.STA);
        thread.Start();
        session._timedOut = !thread.Join(timeout);
        return session;
    }

    /// <summary>Run one script as a named case and keep going if it fails.</summary>
    public static void RunCase(CaseLog log, string name, Action action, Func<Exception, string>? format = null) {
        log.Start(name);
        try {
            action();
            log.Pass(name);
        }
        catch (Exception ex) {
            log.Fail(name, format?.Invoke(ex) ?? ex.ToString());
        }
    }

    public CaseOutcome Outcome(string name) {
        if (_log.Outcomes.TryGetValue(name, out var outcome)) {
            if (outcome.Status == "running") {
                return new CaseOutcome("failed", _timedOut
                    ? "Deadlocked: the session timed out while this case was running."
                    : "Aborted: the session ended while this case was running. " + (_setupFailure ?? ""));
            }
            return outcome;
        }
        if (_setupFailure is not null) {
            return new CaseOutcome("failed", "Not reached; session failed: " + _setupFailure);
        }
        return new CaseOutcome("failed", _timedOut
            ? "Not reached: the session timed out while running " + (_log.Running ?? "<none>") + "."
            : "Not reached: the session never ran this case.");
    }

    /// <summary>Theory rows: the fixture's probe scripts followed by every parity test method.</summary>
    /// <remarks>Discovered by reading <c>test_forms_parity.py</c> so each test is its own xUnit row.</remarks>
    public static IEnumerable<object[]> Cases(params string[] probes) {
        foreach (var probe in probes) {
            yield return [probe];
        }
        foreach (var name in DiscoverParityTests()) {
            yield return [name];
        }
    }

    public static IEnumerable<string> DiscoverParityTests() {
        var path = Path.Combine(AppContext.BaseDirectory, "test_forms_parity.py");
        var classPattern = new Regex(@"^class (\w+)\(unittest\.TestCase\):");
        var testPattern = new Regex(@"^    def (test_\w+)\(");
        string? current = null;
        foreach (var line in File.ReadLines(path)) {
            var classMatch = classPattern.Match(line);
            if (classMatch.Success) {
                current = RevitOnlyClasses.Contains(classMatch.Groups[1].Value) ? null : classMatch.Groups[1].Value;
                continue;
            }
            if (line.StartsWith("class ", StringComparison.Ordinal)) {
                current = null;
                continue;
            }
            var testMatch = testPattern.Match(line);
            if (current is not null && testMatch.Success) {
                yield return current + "." + testMatch.Groups[1].Value;
            }
        }
    }

    public static string Script(string name) =>
        File.ReadAllText(Path.Combine(AppContext.BaseDirectory, name));
}
