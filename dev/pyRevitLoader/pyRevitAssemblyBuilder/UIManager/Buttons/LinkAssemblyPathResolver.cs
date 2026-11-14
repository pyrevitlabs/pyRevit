#nullable enable
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Buttons
{
    /// <summary>
    /// Locates the assembly a LinkButton or InvokeButton points at.
    /// </summary>
    internal static class LinkAssemblyPathResolver
    {
        /// <summary>
        /// Resolves <see cref="ParsedComponent.TargetAssembly"/> to a full path, or null when not found.
        /// </summary>
        /// <param name="component">The link or invoke button component.</param>
        /// <param name="extension">
        /// The owning extension. Link and invoke buttons search the button's own folder,
        /// <c>bin/</c> and <c>lib/</c>, then those of each ancestor up to the extension, nearest
        /// first. A sibling bundle's folders are never searched. Without the extension only the
        /// component folder and its <c>bin/</c> are searched.
        /// </param>
        public static string? Resolve(ParsedComponent component, ParsedExtension? extension)
        {
            if (string.IsNullOrWhiteSpace(component.TargetAssembly))
                return null;

            var assemblyValue = component.TargetAssembly.Trim();

            if (Path.IsPathRooted(assemblyValue) && File.Exists(assemblyValue))
                return Path.GetFullPath(assemblyValue);

            var baseFileName = assemblyValue;
            if (!assemblyValue.EndsWith(".dll", StringComparison.OrdinalIgnoreCase))
                baseFileName += ".dll";

            var includesDirectories = assemblyValue.Contains(Path.DirectorySeparatorChar) ||
                                      assemblyValue.Contains(Path.AltDirectorySeparatorChar);

            if (!Path.IsPathRooted(assemblyValue) && includesDirectories && !string.IsNullOrEmpty(component.Directory))
            {
                var relativePath = Path.GetFullPath(Path.Combine(component.Directory, assemblyValue));
                if (File.Exists(relativePath))
                    return relativePath;
            }

            var searchPaths = new List<string>();

            if (extension != null &&
                (component.Type == CommandComponentType.LinkButton || component.Type == CommandComponentType.InvokeButton))
            {
                searchPaths.AddRange(CollectOwnAndAncestorPaths(component, extension));
            }
            else if (!string.IsNullOrEmpty(component.Directory))
            {
                searchPaths.Add(component.Directory);

                var binPath = Path.Combine(component.Directory, "bin");
                if (Directory.Exists(binPath))
                    searchPaths.Add(binPath);
            }

            foreach (var searchPath in searchPaths)
            {
                var candidatePath = Path.Combine(searchPath, baseFileName);
                if (File.Exists(candidatePath))
                    return candidatePath;
            }

            try
            {
                var assemblyName = Path.GetFileNameWithoutExtension(baseFileName);
                var loadedAssembly = AppDomain.CurrentDomain.GetAssemblies().FirstOrDefault(a =>
                    a.GetName().Name?.Equals(assemblyName, StringComparison.OrdinalIgnoreCase) == true);

                if (loadedAssembly != null && IsInSearchPaths(loadedAssembly.Location, searchPaths))
                    return loadedAssembly.Location;
            }
            catch
            {
            }

            return null;
        }

        private static bool IsInSearchPaths(string assemblyLocation, IEnumerable<string> searchPaths)
        {
            if (string.IsNullOrEmpty(assemblyLocation))
                return false;

            var assemblyDirectory = Path.GetDirectoryName(Path.GetFullPath(assemblyLocation));
            return searchPaths.Any(searchPath => string.Equals(
                Path.GetFullPath(searchPath).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar),
                assemblyDirectory?.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar),
                StringComparison.OrdinalIgnoreCase));
        }

        private static IEnumerable<string> CollectOwnAndAncestorPaths(ParsedComponent component, ParsedExtension extension)
        {
            var paths = new List<string>();
            if (string.IsNullOrEmpty(component.Directory))
                return paths;

            paths.Add(component.Directory);

            var stop = extension.Directory?.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            var current = component.Directory.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            while (!string.IsNullOrEmpty(current))
            {
                paths.Add(Path.Combine(current, "bin"));
                paths.Add(Path.Combine(current, "lib"));
                if (string.Equals(current, stop, StringComparison.OrdinalIgnoreCase))
                    break;
                current = Path.GetDirectoryName(current);
            }

            return paths;
        }
    }
}
