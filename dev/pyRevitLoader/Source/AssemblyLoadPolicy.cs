using System;
using System.IO;

namespace PyRevitLoader
{
    /// <summary>
    /// Decides which assemblies the loader may pull into the host process
    /// default load context.
    ///
    /// The WebView2 stack must never enter the default load context on .NET:
    /// the host process already carries its own WebView2 core, and binding
    /// pyRevit's newer wrapper against it takes the host down. The renderer
    /// loads the stack into an isolated load context instead, so the loader
    /// leaves those files alone and the renderer picks them up from the
    /// isolated folder.
    ///
    /// Invariant: on .NET Framework the WebView2 stack is never skipped. That
    /// runtime has no isolated load context, and the renderer runs in the host
    /// process.
    ///
    /// Independently of the runtime, callers that name a runtime year skip the
    /// pyRevit runtimes of every other Revit year.
    /// </summary>
    public static class AssemblyLoadPolicy
    {
        /// <summary>
        /// True when the WebView2 stack is deployed to an isolated folder and
        /// loaded into an isolated load context.
        /// </summary>
#if NETFRAMEWORK
        public const bool IsolatedOnNetCore = false;
#else
        public const bool IsolatedOnNetCore = true;
#endif

        private const string RuntimeAssemblyPrefix = "pyRevitLabs.PyRevit.Runtime.";

        private static readonly string[] IsolatedAssemblyFileNames = {
            "Microsoft.Web.WebView2.Core.dll",
            "Microsoft.Web.WebView2.Wpf.dll",
            "Microsoft.Web.WebView2.WinForms.dll",
            "pyRevitLabs.PyRevit.WebView2.dll",
            "WebView2Loader.dll",
        };

        /// <summary>
        /// Decides whether the loader must skip a file, for the runtime this
        /// assembly was built for.
        /// </summary>
        /// <param name="fileName">The file the loader is about to load.</param>
        public static AssemblyLoadDecision ShouldSkip(string fileName)
        {
            return ShouldSkip(fileName, IsolatedOnNetCore);
        }

        /// <summary>
        /// Decides whether the loader must skip a file, for a given isolation
        /// mode.
        /// </summary>
        /// <param name="fileName">The file the loader is about to load.</param>
        /// <param name="isolatedOnNetCore">
        /// True when the WebView2 stack is loaded into an isolated load
        /// context and must stay out of the host process.
        /// </param>
        public static AssemblyLoadDecision ShouldSkip(string fileName, bool isolatedOnNetCore)
        {
            var name = string.IsNullOrEmpty(fileName) ? null : Path.GetFileName(fileName);
            if (name == null)
                return AssemblyLoadDecision.Allow("The file has no name.");

            foreach (var isolated in IsolatedAssemblyFileNames)
            {
                if (!string.Equals(isolated, name, StringComparison.OrdinalIgnoreCase))
                    continue;

                return isolatedOnNetCore
                    ? AssemblyLoadDecision.Reject(
                        "The WebView2 stack is loaded into an isolated load context. Loading it "
                        + "here would bind it against the WebView2 core the host process carries.")
                    : AssemblyLoadDecision.Allow(
                        "The .NET Framework runtime has no isolated load context, so the renderer "
                        + "runs in the host process.");
            }

            return AssemblyLoadDecision.Allow("The file is not part of the isolated WebView2 stack.");
        }

        /// <summary>
        /// Decides whether the loader must skip a file when only one Revit
        /// year's pyRevit runtime may be loaded.
        /// </summary>
        /// <remarks>
        /// The engine folders ship one pyRevit runtime per Revit year, and all
        /// of them define the same types. CPython resolves a type from the
        /// first loaded assembly that defines it, so a runtime other than the
        /// one the caller executes through would shadow its types. The loader
        /// passes the host year; the runner passes the year it was compiled
        /// against, because its command binds to that runtime.
        /// </remarks>
        /// <param name="fileName">The file the loader is about to load.</param>
        /// <param name="runtimeYear">
        /// The Revit year of the runtime to keep, such as "2026". Null or empty
        /// keeps every runtime.
        /// </param>
        public static AssemblyLoadDecision ShouldSkip(string fileName, string runtimeYear)
        {
            var decision = ShouldSkip(fileName);
            if (decision.Skip || !IsRuntimeOfAnotherYear(fileName, runtimeYear))
                return decision;

            return AssemblyLoadDecision.Reject(
                "The file is the pyRevit runtime of another Revit year; its types would shadow "
                + "the runtime of year " + runtimeYear + ".");
        }

        /// <summary>
        /// Returns the Revit year of a per-year pyRevit runtime assembly, such
        /// as "2025" for "pyRevitLabs.PyRevit.Runtime.2025", or null for any
        /// other assembly, including "pyRevitLabs.PyRevit.Runtime.Shared".
        /// </summary>
        /// <param name="assemblyName">An assembly simple name or file name.</param>
        public static string GetRuntimeYear(string assemblyName)
        {
            if (string.IsNullOrEmpty(assemblyName))
                return null;

            var name = Path.GetFileName(assemblyName);
            if (name.EndsWith(".dll", StringComparison.OrdinalIgnoreCase))
                name = name.Substring(0, name.Length - 4);
            if (!name.StartsWith(RuntimeAssemblyPrefix, StringComparison.OrdinalIgnoreCase))
                return null;

            var year = name.Substring(RuntimeAssemblyPrefix.Length);
            if (year.Length == 0)
                return null;
            foreach (var character in year)
            {
                if (!char.IsDigit(character))
                    return null;
            }

            return year;
        }

        private static bool IsRuntimeOfAnotherYear(string fileName, string runtimeYear)
        {
            if (string.IsNullOrEmpty(runtimeYear))
                return false;

            var year = GetRuntimeYear(fileName);
            return year != null && !string.Equals(year, runtimeYear, StringComparison.Ordinal);
        }
    }

    /// <summary>
    /// The verdict of the assembly load policy, with the reason behind it.
    /// </summary>
    public readonly struct AssemblyLoadDecision
    {
        private AssemblyLoadDecision(bool skip, string reason)
        {
            Skip = skip;
            Reason = reason;
        }

        /// <summary>True when the loader must not load the file.</summary>
        public bool Skip { get; }

        /// <summary>Why the loader reached this verdict.</summary>
        public string Reason { get; }

        /// <summary>
        /// The file may be loaded into the host process.
        /// </summary>
        /// <param name="reason">Why the file may be loaded.</param>
        public static AssemblyLoadDecision Allow(string reason)
        {
            return new AssemblyLoadDecision(false, reason);
        }

        /// <summary>
        /// The file must be left out of the host process.
        /// </summary>
        /// <param name="reason">Why the file must be skipped.</param>
        public static AssemblyLoadDecision Reject(string reason)
        {
            return new AssemblyLoadDecision(true, reason);
        }
    }
}
