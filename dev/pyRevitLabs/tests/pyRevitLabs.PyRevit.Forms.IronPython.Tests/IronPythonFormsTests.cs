using System.IO;
using IronPython.Hosting;
using Microsoft.Scripting.Hosting;
using Xunit;

namespace PyRevitLabs.PyRevit.Forms.IronPython.Tests;

/// <summary>Run the same shared WPF contracts using the attached IronPython engine.</summary>
public class IronPythonFormsTests {
    /// <summary>Exercise real modal events without risking a Revit process during diagnosis.</summary>
    [Fact]
    public void SharedFormsWorkUnderIronPython() {
        string? failure = null;
        var thread = new Thread(() => {
            ScriptEngine? engine = null;
            try {
                engine = Python.CreateEngine();
                engine.SetSearchPaths([AppContext.BaseDirectory, Path.Combine(AppContext.BaseDirectory, "stdlib.zip")]);
                var scope = engine.CreateScope();
                scope.SetVariable("fixture_root", AppContext.BaseDirectory);
                scope.SetVariable("ironpython_probe", true);
                engine.Execute("import clr\nfor assembly in ['System.Runtime', 'System.Private.Uri', 'System.ComponentModel', 'System.ObjectModel', 'System.Drawing.Primitives', 'System.Threading', 'System.Console']:\n    clr.AddReference(assembly)", scope);
                var bootstrap = File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "FormsProbe.py"));
                bootstrap = bootstrap.Substring(0, bootstrap.IndexOf("from pyrevit import forms", StringComparison.Ordinal));
                engine.Execute(bootstrap, scope);
                engine.Execute(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "IronPythonProbe.py")), scope);
            }
            catch (Exception ex) {
                failure = engine?.GetService<ExceptionOperations>().FormatException(ex) ?? ex.ToString();
            }
        }) { IsBackground = true };
        thread.SetApartmentState(ApartmentState.STA);
        thread.Start();
        Assert.True(thread.Join(TimeSpan.FromSeconds(45)), "IronPython WPF probe deadlocked.");
        Assert.True(failure is null, failure);
    }
}
