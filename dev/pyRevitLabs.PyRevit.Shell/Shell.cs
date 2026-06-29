using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Threading;
using System.Windows.Controls;
using Autodesk.Revit.UI;
using PythonConsoleControl;

namespace PyRevitLabs.PyRevit.Shell {
    /// <summary>
    /// Public launch entry points for the interactive shell, called from the launcher script.
    ///
    /// These are deliberately thin and free of IronPython/AvalonEdit references in their
    /// parameter lists so the assembly resolver is installed *before* the JIT has to load those
    /// dependencies (which live next to this DLL in its engine folder, not on Revit's probing
    /// path). The heavy work happens in <see cref="ShellLauncher"/>, whose methods are only
    /// JIT-compiled once these run.
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

        /// <summary>
        /// Open the interactive shell with a code editor panel (AvalonEdit) above the REPL, in a
        /// modal window. Same engine environment and dispatch as <see cref="Modal"/>; the editor's
        /// Run sends the selection (or whole file) to the REPL.
        /// </summary>
        public static void ModalEditor(UIApplication uiapp, IList<string> searchPaths) {
            ShellAssemblyResolver.Install();
            ShellLauncher.ShowModalEditor(uiapp, searchPaths);
        }

        /// <summary>
        /// Open the interactive shell with a code editor panel above the REPL, in a modeless
        /// window that keeps Revit interactive (statements run through an ExternalEvent).
        /// </summary>
        public static void ModelessEditor(UIApplication uiapp, IList<string> searchPaths) {
            ShellAssemblyResolver.Install();
            ShellLauncher.ShowModelessEditor(uiapp, searchPaths);
        }

        /// <summary>
        /// Build a fully-wired interactive console control for hosting inside a Revit dockable
        /// pane (pyRevit registers the pane itself through <c>forms.register_dockable_panel</c>
        /// and places this control as the pane's framework element). The engine is configured with
        /// the full pyRevit environment and each statement is marshaled through an ExternalEvent so
        /// Revit stays interactive while the pane is open.
        /// </summary>
        public static UserControl CreateDockableConsole(UIApplication uiapp, IList<string> searchPaths) {
            ShellAssemblyResolver.Install();
            return ShellLauncher.CreateConfiguredConsole(uiapp, searchPaths);
        }
        /// <summary>
        /// Build a fully-wired Python editor (AvalonEdit + console) for hosting inside a Revit
        /// dockable pane, mirroring <see cref="CreateDockableConsole"/> but with the code editor
        /// surface on top. The editor's Run executes through the same ExternalEvent-driven dispatch
        /// so Revit stays interactive while the pane is open.
        /// </summary>
        public static UserControl CreateDockableEditor(UIApplication uiapp, IList<string> searchPaths) {
            ShellAssemblyResolver.Install();
            return ShellLauncher.CreateConfiguredEditor(uiapp, searchPaths);
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
