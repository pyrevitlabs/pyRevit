using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Threading;
using Microsoft.Scripting.Hosting;
using PyRevitLabs.PyRevit.Shell;
using PythonConsoleControl;

namespace PyRevitLabs.PyRevit.Shell.DevHost;

/// <summary>
/// Hosts the interactive shell outside Revit for development.
/// </summary>
internal static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        var root = FindRepositoryRoot();
        var engineDir = Path.Combine(root, "bin", "netcore", "engines", "IPY2712PR");

        if (!File.Exists(Path.Combine(engineDir, "pyRevitLabs.PyRevit.Shell.dll")))
        {
            var message =
                "The shell is not built yet. Build it first, e.g.:" + Environment.NewLine +
                "  cd build && dotnet run -c Release -- ci" + Environment.NewLine +
                "or just the shell:" + Environment.NewLine +
                "  dotnet build dev/pyRevitLabs.PyRevit.Shell/pyRevitLabs.PyRevit.Shell.csproj -c \"Release IPY2712PR\"";
            Console.Error.WriteLine(message);
            MessageBox.Show(
                message,
                "pyRevit Shell Dev Host",
                MessageBoxButton.OK,
                MessageBoxImage.Error);
            return 1;
        }

        var searchPaths = BuildSearchPaths(root, engineDir);
        var useDark = args.Contains("--dark", StringComparer.OrdinalIgnoreCase);
        var consoleOnly = args.Contains("--console", StringComparer.OrdinalIgnoreCase);

        Window window;
        IronPythonConsoleControl consoleControl;

        if (consoleOnly)
        {
            var shell = new InteractiveShellWindow();
            shell.ApplyTheme(useDark);
            window = shell;
            consoleControl = shell.ConsoleControl;
        }
        else
        {
            var editor = new InteractiveEditorWindow();
            editor.ApplyTheme(useDark);
            window = editor;
            consoleControl = editor.ConsoleControl;
        }

        var mainDispatcher = Dispatcher.CurrentDispatcher;

        consoleControl.WithConsoleHost(host =>
        {
            // Match modal shell execution semantics outside Revit.
            host.Console.SetCommandDispatcher(command => RunOnDispatcher(mainDispatcher, command));
            host.Editor.SetCompletionDispatcher(command => RunOnDispatcher(mainDispatcher, command));

            ConfigureStandaloneEngine(host.Engine, host.Console.ScriptScope, searchPaths);
            host.Console.ScriptScope.SetVariable("__window__", window);
        });

        window.ShowDialog();
        return 0;
    }

    private static IList<string> BuildSearchPaths(string root, string engineDir)
    {
        var paths = new List<string> { engineDir };

        var stdlibZip = Path.Combine(root, "dev", "libs", "IronPython", "python_2712pr_lib.zip");
        if (File.Exists(stdlibZip))
            paths.Add(stdlibZip);

        AddIfExists(paths, Path.Combine(root, "pyrevitlib"));
        AddIfExists(paths, Path.Combine(root, "site-packages"));
        AddIfExists(paths, Path.Combine(root, "extensions"));
        return paths;
    }

    private static void AddIfExists(List<string> paths, string dir)
    {
        if (Directory.Exists(dir))
            paths.Add(dir);
    }

    private static void ConfigureStandaloneEngine(ScriptEngine engine, ScriptScope scope, IList<string> searchPaths)
    {
        engine.SetSearchPaths(searchPaths);

        // Keep snippets that inspect reserved pyRevit values usable without Revit.
        try
        {
            engine.Execute(StubBuiltinsSnippet, scope);
        }
        catch
        {
            // The standalone REPL remains usable if defaults cannot be installed.
        }
    }

    // Poll the dispatcher operation so a Ctrl+C keyboard interrupt can break a long run.
    private static void RunOnDispatcher(Dispatcher dispatcher, Action command)
    {
        if (command == null)
            return;

        var operation = dispatcher.BeginInvoke(DispatcherPriority.Normal, command);
        while (operation.Status != DispatcherOperationStatus.Completed)
            operation.Wait(TimeSpan.FromSeconds(1));
    }

    private static string FindRepositoryRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current is not null)
        {
            if (File.Exists(Path.Combine(current.FullName, "pyRevitfile")))
                return current.FullName;
            current = current.Parent;
        }

        return Directory.GetCurrentDirectory();
    }

    private const string StubBuiltinsSnippet =
"try: __execid__\nexcept NameError: __execid__ = ''\n" +
"try: __timestamp__\nexcept NameError: __timestamp__ = ''\n" +
"try: __cachedengine__\nexcept NameError: __cachedengine__ = False\n" +
"try: __cachedengineid__\nexcept NameError: __cachedengineid__ = None\n" +
"try: __scriptruntime__\nexcept NameError: __scriptruntime__ = None\n" +
"try: __revit__\nexcept NameError: __revit__ = None\n" +
"try: __commanddata__\nexcept NameError: __commanddata__ = None\n" +
"try: __elements__\nexcept NameError: __elements__ = None\n" +
"try: __uibutton__\nexcept NameError: __uibutton__ = None\n" +
"try: __commandpath__\nexcept NameError: __commandpath__ = ''\n" +
"try: __configcommandpath__\nexcept NameError: __configcommandpath__ = ''\n" +
"try: __commandname__\nexcept NameError: __commandname__ = 'Interactive Shell (dev)'\n" +
"try: __commandbundle__\nexcept NameError: __commandbundle__ = 'pyRevit Shell'\n" +
"try: __commandextension__\nexcept NameError: __commandextension__ = 'pyRevitCore'\n" +
"try: __commanduniqueid__\nexcept NameError: __commanduniqueid__ = 'pyrevit-interactive-shell'\n" +
"try: __commandcontrolid__\nexcept NameError: __commandcontrolid__ = 'pyrevit-interactive-shell'\n" +
"try: __forceddebugmode__\nexcept NameError: __forceddebugmode__ = False\n" +
"try: __shiftclick__\nexcept NameError: __shiftclick__ = False\n" +
"try: __result__\nexcept NameError: __result__ = {}\n" +
"try: __eventsender__\nexcept NameError: __eventsender__ = None\n" +
"try: __eventargs__\nexcept NameError: __eventargs__ = None\n";
}
