using System;
using System.Collections.Generic;
using System.IO;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Search paths for type:lib extensions. Packages live at the .lib root
    /// (Foo.lib/Pkg); nested Foo.lib/lib/ is optional compatibility only.
    /// </summary>
    internal static class LibraryExtensionSearchPaths
    {
        /// <summary>
        /// Returns each library-extension directory, then nested lib/ when it exists.
        /// Used by startup, hooks, and command-type generation so the three
        /// runtimes cannot drift. Also hashed into the rocket-mode cache key so
        /// adding or removing a .lib (or its nested lib/) rebuilds command assemblies.
        /// </summary>
        public static List<string> Collect(IEnumerable<ParsedExtension> libraryExtensions)
        {
            var paths = new List<string>();
            if (libraryExtensions == null)
                return paths;

            foreach (var libExt in libraryExtensions)
            {
                if (string.IsNullOrEmpty(libExt?.Directory))
                    continue;
                paths.Add(libExt.Directory);
                var nestedLib = Path.Combine(libExt.Directory, "lib");
                if (Directory.Exists(nestedLib))
                    paths.Add(nestedLib);
            }

            return paths;
        }

        /// <summary>
        /// Defers <paramref name="provider"/> until the returned value is first read, then keeps the paths it gave.
        /// </summary>
        /// <param name="onError">Receives the exception when <paramref name="provider"/> throws.</param>
        /// <remarks>
        /// Important: when <paramref name="provider"/> throws, the value is an empty list and the provider is not
        /// called again. A plain <see cref="Lazy{T}"/> caches the exception instead and rethrows it on every read,
        /// which would fail the setup of every later smart button, ComboBox and checkbox rather than only their
        /// imports from library extensions.
        /// </remarks>
        public static Lazy<List<string>> ReadOnFirstUse(Func<IEnumerable<string>> provider, Action<Exception> onError)
        {
            return new Lazy<List<string>>(() =>
            {
                try
                {
                    return new List<string>(provider?.Invoke() ?? Array.Empty<string>());
                }
                catch (Exception ex)
                {
                    onError(ex);
                    return new List<string>();
                }
            });
        }

        /// <summary>
        /// Order-stable fragment for the command-assembly cache seed.
        /// Sorted so enumeration order of library extensions cannot miss the cache.
        /// </summary>
        public static string CacheSeed(IEnumerable<ParsedExtension> libraryExtensions)
        {
            var paths = Collect(libraryExtensions);
            paths.Sort(StringComparer.OrdinalIgnoreCase);
            return string.Join(";", paths);
        }
    }
}
