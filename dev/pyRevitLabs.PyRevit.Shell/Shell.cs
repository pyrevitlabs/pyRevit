using System;
using System.IO;
using System.Reflection;
using System.Threading;
using Autodesk.Revit.UI;

namespace PyRevitLabs.PyRevit.Shell {
    /// <summary>
    /// Public launch entry points for the interactive shell.
    ///
    /// These are deliberately thin and free of IronPython/AvalonEdit references so the assembly
    /// resolver is installed *before* the JIT has to load those dependencies (which live next to
    /// this DLL in engines/IPY342, not on Revit's probing path). The heavy work happens in
    /// <see cref="ShellLauncher"/>, whose methods are only JIT-compiled once these run.
    /// </summary>
    public static class Shell {
        public static void Modal(UIApplication uiapp) {
            ShellAssemblyResolver.Install();
            ShellLauncher.ShowModal(uiapp);
        }

        public static void Modeless(UIApplication uiapp) {
            ShellAssemblyResolver.Install();
            ShellLauncher.ShowModeless(uiapp);
        }
    }

    /// <summary>
    /// Resolves the shell's private dependencies (IronPython 3.4, the DLR and AvalonEdit) from the
    /// folder this assembly was loaded from. The shell ships into engines/IPY342, which Revit does
    /// not probe, and pyRevit may be running a different engine entirely, so explicit resolution is
    /// required for the shell to load regardless of the active engine.
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
