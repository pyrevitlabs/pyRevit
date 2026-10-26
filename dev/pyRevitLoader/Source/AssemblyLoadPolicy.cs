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
    /// Invariant: on .NET Framework nothing is skipped. That runtime has no
    /// isolated load context, and the renderer runs in the host process.
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
