using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Runtime.InteropServices;

namespace pyRevitLoader.Tests.TestSupport
{
    /// <summary>
    /// Loads AdWindows.dll from an installed Revit for tests that build real AdWindows ribbon items.
    /// </summary>
    /// <remarks>
    /// The build references AdWindows as a reference assembly only, so the test output holds no
    /// AdWindows that can run. <see cref="Register"/> picks the newest installed Revit whose
    /// AdWindows.dll targets the runtime the tests run on, and resolves AdWindows to it until
    /// <see cref="Unregister"/>.
    /// Note: AdWindows stays loaded after <see cref="Unregister"/>, because the default load context
    /// cannot unload it.
    /// </remarks>
    internal static class InstalledAdWindows
    {
        private const string AdWindowsAssemblyName = "AdWindows";

        private static Assembly? _adWindows;

        /// <returns>The path of the AdWindows.dll it loaded; null when no installed Revit has one that
        /// runs on this runtime.</returns>
        internal static string? Register()
        {
            var path = FindRunnableAdWindows();
            if (path == null)
                return null;

            _adWindows = Assembly.LoadFrom(path);
            AppDomain.CurrentDomain.AssemblyResolve += ResolveAdWindows;
            return path;
        }

        internal static void Unregister()
        {
            AppDomain.CurrentDomain.AssemblyResolve -= ResolveAdWindows;
        }

        private static Assembly? ResolveAdWindows(object? sender, ResolveEventArgs args)
        {
            return new AssemblyName(args.Name).Name == AdWindowsAssemblyName ? _adWindows : null;
        }

        private static string? FindRunnableAdWindows()
        {
            var autodeskDirectory = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "Autodesk");
            if (!Directory.Exists(autodeskDirectory))
                return null;

            return Directory.GetDirectories(autodeskDirectory, "Revit 20??")
                .OrderByDescending(directory => directory, StringComparer.OrdinalIgnoreCase)
                .Select(directory => Path.Combine(directory, AdWindowsAssemblyName + ".dll"))
                .FirstOrDefault(path => File.Exists(path) && RunsOnThisRuntime(path));
        }

        private static bool RunsOnThisRuntime(string assemblyPath)
        {
            var onNetFramework = RuntimeInformation.FrameworkDescription.StartsWith(".NET Framework", StringComparison.Ordinal);
            using (var stream = File.OpenRead(assemblyPath))
            using (var peReader = new PEReader(stream))
            {
                var metadata = peReader.GetMetadataReader();
                foreach (var handle in metadata.AssemblyReferences)
                {
                    var reference = metadata.GetAssemblyReference(handle);
                    var name = metadata.GetString(reference.Name);
                    if (name == "mscorlib")
                        return onNetFramework;
                    if (name == "System.Runtime")
                        return !onNetFramework && reference.Version.Major <= Environment.Version.Major;
                }
            }

            return false;
        }
    }
}
