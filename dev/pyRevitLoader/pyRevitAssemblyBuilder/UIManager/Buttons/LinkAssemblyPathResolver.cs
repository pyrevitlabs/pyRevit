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
        /// The owning extension. Link and invoke buttons search its extension-level,
        /// tab-level and component <c>bin/</c> and <c>lib/</c> folders; without it only the
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
                searchPaths.AddRange(extension.CollectBinaryPaths(component));
                foreach (var libPath in extension.CollectLibraryPaths(component))
                {
                    if (!searchPaths.Contains(libPath))
                        searchPaths.Add(libPath);
                }
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

                if (loadedAssembly != null && !string.IsNullOrEmpty(loadedAssembly.Location))
                    return loadedAssembly.Location;
            }
            catch
            {
            }

            return null;
        }
    }
}
