using System.IO;
using Python.Runtime;
using Xunit;

namespace PyRevitLabs.PyRevit.Forms.Tests;

/// <summary>Exercise real WPF and the shipped pythonnet without starting Revit.</summary>
public class FormsBackendTests {
    /// <summary>Modal inputs retain names, callbacks, resources and results across repeated runs.</summary>
    [Fact]
    public void InputDialogsWorkOnAnStaThread() {
        string? failure = null;
        var thread = new Thread(() => {
            try {
                GC.KeepAlive(typeof(System.Windows.Window).Assembly);
                GC.KeepAlive(typeof(System.Windows.Media.Visual).Assembly);
                GC.KeepAlive(typeof(System.Windows.DependencyObject).Assembly);
                Python.Runtime.Runtime.PythonDLL = Path.Combine(AppContext.BaseDirectory, "CPY3123", "python312.dll");
                PythonEngine.Initialize();
                PythonEngine.BeginAllowThreads();
                using var gil = Py.GIL();
                using var scope = Py.CreateScope();
                scope.Set("fixture_root", AppContext.BaseDirectory);
                scope.Exec(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "FormsProbe.py")));
            }
            catch (Exception ex) {
                failure = ex.ToString();
            }
        }) { IsBackground = true };
        thread.SetApartmentState(ApartmentState.STA);
        thread.Start();
        Assert.True(thread.Join(TimeSpan.FromSeconds(45)), "WPF/pythonnet modal probe deadlocked.");
        Assert.True(failure is null, failure);
    }
}
