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
    /// Public entry points for the interactive shell.
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
        /// Opens the interactive shell with a code editor in a modal window.
        /// </summary>
        public static void ModalEditor(UIApplication uiapp, IList<string> searchPaths) {
            ShellAssemblyResolver.Install();
            ShellLauncher.ShowModalEditor(uiapp, searchPaths);
        }

        /// <summary>
        /// Opens the interactive shell with a code editor in a modeless window.
        /// </summary>
        public static void ModelessEditor(UIApplication uiapp, IList<string> searchPaths) {
            ShellAssemblyResolver.Install();
            ShellLauncher.ShowModelessEditor(uiapp, searchPaths);
        }

        /// <summary>
        /// Creates an interactive console for a Revit dockable pane.
        /// </summary>
        public static UserControl CreateDockableConsole(UIApplication uiapp, IList<string> searchPaths) {
            ShellAssemblyResolver.Install();
            return ShellLauncher.CreateConfiguredConsole(uiapp, searchPaths);
        }

        /// <summary>
        /// Creates an interactive editor and console for a Revit dockable pane.
        /// </summary>
        public static UserControl CreateDockableEditor(UIApplication uiapp, IList<string> searchPaths) {
            ShellAssemblyResolver.Install();
            return ShellLauncher.CreateConfiguredEditor(uiapp, searchPaths);
        }

        /// <summary>
        /// Registers the dockable shell without loading pyRevit's Python UI modules.
        /// </summary>
        public static bool RegisterDockablePane(
            UIApplication uiapp,
            IList<string> searchPaths,
            bool useEditor
        ) {
            ShellAssemblyResolver.Install();
            return ShellDockablePaneRegistration.Register(uiapp, searchPaths, useEditor);
        }
    }

    /// <summary>
    /// Resolves private dependencies from the shell assembly directory, which Revit does not probe.
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
