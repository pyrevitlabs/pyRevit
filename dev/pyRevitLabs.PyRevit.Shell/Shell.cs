using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Threading;
using Autodesk.Revit.UI;

namespace PyRevitLabs.PyRevit.Shell {
    /// <summary>
    /// Public launch entry points for the interactive shell, called from the launcher script.
    ///
    /// These are deliberately thin and free of IronPython/AvalonEdit references so the assembly
    /// resolver is installed *before* the JIT has to load those dependencies (which live next to
    /// this DLL in its engine folder, not on Revit's probing path). The heavy work happens in
    /// <see cref="ShellLauncher"/>, whose methods are only JIT-compiled once these run.
    ///
    /// <paramref name="searchPaths"/> is the launcher's sys.path, forwarded to the REPL engine so
    /// <c>from pyrevit import ...</c> resolves exactly as in a normal script.
    /// </summary>
    public static class Shell {
        public static void Modal(UIApplication uiapp, IList<string> searchPaths) {
            ShellAssemblyResolver.Install();
            ShellLauncher.ShowModal(uiapp, searchPaths);
        }

        public static void Modeless(UIApplication uiapp, IList<string> searchPaths) {
            ShellAssemblyResolver.Install();
            ShellLauncher.ShowModeless(uiapp, searchPaths);
        }
    }

    /// <summary>
    /// Resolves the shell's private dependencies (AvalonEdit, and the forked IronPython/DLR) from
    /// the engine folder this assembly was loaded from, which Revit does not probe.
    /// </summary>
    internal static class ShellAssemblyResolver {
        static int _installed;

        public static void Install() {
            if (Interlocked.Exchange(ref _installed, 1) == 1)
                return;
            AppDomain.CurrentDomain.AssemblyResolve += Resolve;
        }

        static Assembly Resolve(object sender, ResolveEventArgs args) {
            var probeDir = Path.GetDirectoryName(typeof(ShellAssemblyResolver).Assembly.Location);
            if (string.IsNullOrEmpty(probeDir))
                return null;

            var candidate = Path.Combine(probeDir, new AssemblyName(args.Name).Name + ".dll");
            return File.Exists(candidate) ? Assembly.LoadFrom(candidate) : null;
        }
    }
}
