using System.IO;
using Xunit;
using PyRevitLabs.PyRevit.Forms.Binding;
using Python.Runtime;
using Dispatcher = System.Windows.Threading.Dispatcher;

namespace PyRevitLabs.PyRevit.Forms.Binding.Tests;

/// <summary>
/// Runs every test on one STA dispatcher thread with the shipped CPython interpreter, because
/// the interpreter and WPF are process-wide.
/// </summary>
/// <remarks>
/// Before registering the codecs the host converts a Python class instance to a CLR object and
/// fails to pass a Python list as <c>IEnumerable</c>, so the tests also prove that codecs
/// registered late replace pythonnet's cached conversions.
/// </remarks>
public sealed class PythonWpfHost : IDisposable {
    private const string Prelude = @"
import clr
for name in ('PresentationFramework', 'PresentationCore', 'WindowsBase', 'System.Xaml'):
    clr.AddReference(name)
import System
from System.Collections import ArrayList

class Early(object):
    def __init__(self):
        self.name = 'early'

early = Early()
early_holder = ArrayList()
early_holder.Add(early)
early_list_failed = False
try:
    System.Windows.Controls.ListBox().ItemsSource = [early]
except TypeError:
    early_list_failed = True
";

    private readonly Thread thread;
    private readonly Dispatcher dispatcher;

    public PythonWpfHost() {
        using var ready = new ManualResetEventSlim();
        Dispatcher? created = null;
        Exception? failure = null;
        thread = new Thread(() => {
            try {
                created = Dispatcher.CurrentDispatcher;
                Start();
            }
            catch (Exception ex) {
                failure = ex;
            }
            ready.Set();
            if (failure is null)
                Dispatcher.Run();
        }) { IsBackground = true };
        thread.SetApartmentState(ApartmentState.STA);
        thread.Start();
        ready.Wait();
        if (failure is not null)
            throw new InvalidOperationException("Python/WPF host failed to start.", failure);
        dispatcher = created!;
    }

    /// <summary>The early Python object converted before the codecs were registered.</summary>
    public object? EarlyHolderItem { get; private set; }

    /// <summary>Whether passing a list as IEnumerable failed before registration.</summary>
    public bool EarlyListFailed { get; private set; }

    private void Start() {
        GC.KeepAlive(typeof(System.Windows.Window).Assembly);
        Runtime.PythonDLL = Path.Combine(AppContext.BaseDirectory, "CPY3123", "python312.dll");
        PythonEngine.Initialize();
        PythonEngine.BeginAllowThreads();
        using (Py.GIL()) {
            using var scope = Py.CreateScope();
            scope.Exec(Prelude);
            EarlyListFailed = scope.Get<bool>("early_list_failed");
            PythonBinding.Register(null!, null!);
            scope.Exec("early_holder.Add(early)");
            var holder = (System.Collections.ArrayList)scope.Get("early_holder").AsManagedObject(typeof(System.Collections.ArrayList));
            EarlyHolderItem = holder[1];
        }
    }

    /// <summary>Runs <paramref name="action"/> on the STA thread without holding the GIL.</summary>
    public void Run(Action action) {
        dispatcher.Invoke(action);
    }

    /// <summary>Runs Python <paramref name="code"/> on the STA thread in a fresh scope.</summary>
    public void Exec(string code) {
        Run(() => {
            using (Py.GIL()) {
                using var scope = Py.CreateScope();
                scope.Exec(code);
            }
        });
    }

    public void Dispose() {
        dispatcher.InvokeShutdown();
    }
}

[CollectionDefinition(Name)]
public sealed class PythonWpfCollection : ICollectionFixture<PythonWpfHost> {
    public const string Name = "Python WPF host";
}
