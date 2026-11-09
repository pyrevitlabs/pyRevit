using Python.Runtime;

namespace PyRevitLabs.PyRevit.Runtime.EnvVars.Tests;

/// <summary>
/// Groups the suites sharing the process-wide CPython engine and its <c>sys.modules</c>, so they
/// never run in parallel.
/// </summary>
[CollectionDefinition(Name, DisableParallelization = true)]
public sealed class CPythonEngineCollection {
    /// <summary>Collection name shared by the CPython engine suites.</summary>
    public const string Name = "CPython engine";
}

/// <summary>
/// Pins that <c>pyrevit.revit.events</c> detaches handlers under CPython although Revit hands
/// back a new <c>Application</c> wrapper on every access, which pythonnet's own <c>-=</c> cannot
/// handle.
/// </summary>
[Collection(CPythonEngineCollection.Name)]
public class CPythonEventsTests {
    /// <summary>Starts the CPython engine with <c>events.py</c> loaded.</summary>
    public CPythonEventsTests() {
        CPythonEventsHost.Exec("pass");
    }

    /// <summary>
    /// A handler added and removed through two different wrappers is really detached, so the
    /// event stops calling it and holds no subscription.
    /// </summary>
    [Fact]
    public void RemoveHandler_DetachesThroughAFreshWrapper() {
        SharedEventSource source = CPythonEventsHost.NewSource();
        CPythonEventsHost.Exec(
            "calls = []\n"
            + "handler = events.add_handler('doc-changed', lambda sender, args: calls.append(1))");

        source.Raise();
        Assert.Equal(1, CPythonEventsHost.EvalInt("len(calls)"));

        CPythonEventsHost.Exec("events.remove_handler('doc-changed', handler)");
        source.Raise();

        Assert.Equal(1, CPythonEventsHost.EvalInt("len(calls)"));
        Assert.Equal(0, source.SubscriberCount);
    }

    /// <summary>
    /// Why <c>remove_handler</c> must not use <c>-=</c>: pythonnet records each handler under the
    /// wrapper it was added through, so removing it through a fresh wrapper fails and the
    /// subscription leaks. If pythonnet starts matching handlers across wrappers, this fails and
    /// the <c>EventInfo</c> path can be dropped.
    /// </summary>
    [Fact]
    public void AttributeUnsubscribe_ThroughAFreshWrapper_LeavesTheHandlerSubscribed() {
        SharedEventSource source = CPythonEventsHost.NewSource();
        CPythonEventsHost.Exec(
            "leaked = events.create_handler(lambda sender, args: None, EventArgs)\n"
            + "HOST_APP.app.DocumentChanged += leaked");

        Exception? failure = Record.Exception(
            () => CPythonEventsHost.Exec("HOST_APP.app.DocumentChanged -= leaked"));

        Assert.IsType<PythonException>(failure);
        Assert.Equal(1, source.SubscriberCount);
    }

    /// <summary>
    /// <c>execute_in_revit_context</c> hands the queue a delegate pythonnet accepts for an
    /// <see cref="Action"/> parameter, and the callback runs once with its arguments when the
    /// queue drains; a raising callback is logged and does not stop the next one.
    /// </summary>
    [Fact]
    public void ExecuteInRevitContext_SchedulesThroughAnActionParameter() {
        CPythonEventsHost.Exec(
            "ran = []\n"
            + "def failing():\n"
            + "    raise ValueError('boom')\n"
            + "queued = [events.execute_in_revit_context(failing),\n"
            + "          events.execute_in_revit_context(lambda v, key=None: ran.append((v, key)), 1, key=2)]");

        Assert.Equal(1, CPythonEventsHost.EvalInt("int(queued == [True, True])"));
        Assert.Equal(0, CPythonEventsHost.EvalInt("len(ran)"));

        ApiContextQueueDouble.RunPending();

        Assert.Equal(1, CPythonEventsHost.EvalInt("int(ran == [(1, 2)])"));
    }

    /// <summary>
    /// A second execution of <c>events.py</c> in the same interpreter, as <c>importlib.reload</c>
    /// or a runner unloading its modules causes, defines its CLR handler types again without
    /// colliding with the types the first execution emitted.
    /// </summary>
    [Fact]
    public void Module_ExecutesAgainInTheSameInterpreter() {
        CPythonEventsHost.Exec(
            "reloaded = importlib.util.module_from_spec(_spec)\n"
            + "_spec.loader.exec_module(reloaded)");

        Assert.Equal(
            1,
            CPythonEventsHost.EvalInt("int(reloaded.FuncAsEventHandler(None).GetName() == 'FuncAsEventHandler')"));
    }
}
