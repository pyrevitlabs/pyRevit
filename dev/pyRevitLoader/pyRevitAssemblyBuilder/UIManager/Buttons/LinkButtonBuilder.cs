#nullable enable
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitAssemblyBuilder.UIManager.Icons;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Buttons
{
    /// <summary>
    /// Builder for link buttons that reference external assemblies.
    /// </summary>
    public class LinkButtonBuilder : ButtonBuilderBase
    {
        private ParsedExtension? _currentExtension;

        /// <inheritdoc/>
        public override CommandComponentType[] SupportedTypes => new[]
        {
            CommandComponentType.LinkButton
        };

        /// <summary>
        /// Initializes a new instance of the <see cref="LinkButtonBuilder"/> class.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor.</param>
        public LinkButtonBuilder(ILogger logger, IButtonPostProcessor buttonPostProcessor)
            : base(logger, buttonPostProcessor)
        {
        }

        /// <summary>
        /// Sets the current extension for assembly path resolution.
        /// </summary>
        /// <param name="extension">The current extension being processed.</param>
        public void SetCurrentExtension(ParsedExtension? extension)
        {
            _currentExtension = extension;
        }

        /// <inheritdoc/>
        public override void Build(ParsedComponent component, RibbonPanel parentPanel, string tabName, ExtensionAssemblyInfo assemblyInfo)
        {
            if (parentPanel == null)
            {
                Logger.Warning($"Cannot create link button '{component.DisplayName}': parent panel is null.");
                return;
            }

            if (ItemExistsInPanel(parentPanel, component.DisplayName))
            {
                Logger.Debug($"Link button '{component.DisplayName}' already exists in panel.");
                return;
            }

            try
            {
                var linkData = CreateLinkButtonData(component);
                if (linkData != null)
                {
                    var linkBtn = parentPanel.AddItem(linkData) as PushButton;
                    if (linkBtn != null)
                    {
                        ButtonPostProcessor.Process(linkBtn, component);
                        Logger.Debug($"Created link button '{component.DisplayName}'.");
                    }
                }
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to create link button '{component.DisplayName}'. Exception: {ex.Message}");
            }
        }

        /// <summary>
        /// Creates a PushButtonData for a LinkButton that directly references an external assembly.
        /// </summary>
        public PushButtonData? CreateLinkButtonData(ParsedComponent component)
        {
            if (string.IsNullOrEmpty(component.TargetAssembly))
            {
                Logger.Debug($"LinkButton '{component.DisplayName}' has no target assembly specified.");
                return null;
            }

            if (string.IsNullOrEmpty(component.CommandClass))
            {
                Logger.Debug($"LinkButton '{component.DisplayName}' has no command class specified.");
                return null;
            }

            try
            {
                // Resolve the assembly path
                var assemblyPath = ResolveAssemblyPath(component);
                if (string.IsNullOrEmpty(assemblyPath) || !File.Exists(assemblyPath))
                {
                    Logger.Debug($"LinkButton '{component.DisplayName}' assembly not found at resolved path.");
                    return null;
                }

                // Use Title from bundle.yaml if available, with config script indicator
                var buttonText = ButtonPostProcessor.GetButtonText(component);

                // Get assembly name to construct fully qualified class names
                var assemblyName = Path.GetFileNameWithoutExtension(assemblyPath);

                // Construct fully qualified class name (Namespace.ClassName)
                var fullCommandClass = component.CommandClass.Contains(".")
                    ? component.CommandClass
                    : $"{assemblyName}.{component.CommandClass}";

                var pushButtonData = new PushButtonData(
                    component.DisplayName,
                    buttonText,
                    assemblyPath,
                    fullCommandClass);

                // Set availability class if specified
                if (!string.IsNullOrEmpty(component.AvailabilityClass))
                {
                    var fullAvailClass = component.AvailabilityClass.Contains(".")
                        ? component.AvailabilityClass
                        : $"{assemblyName}.{component.AvailabilityClass}";
                    pushButtonData.AvailabilityClassName = fullAvailClass;
                }

                return pushButtonData;
            }
            catch (Exception ex)
            {
                Logger.Debug($"Failed to resolve assembly path for LinkButton '{component.DisplayName}'. Exception: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Resolves the full path to an assembly specified in a LinkButton or InvokeButton.
        /// </summary>
        private string? ResolveAssemblyPath(ParsedComponent component)
        {
            if (string.IsNullOrWhiteSpace(component.TargetAssembly))
                return null;

            var assemblyValue = component.TargetAssembly.Trim();

            // If it's already a rooted path and exists, return it
            if (Path.IsPathRooted(assemblyValue) && File.Exists(assemblyValue))
                return Path.GetFullPath(assemblyValue);

            // Ensure the assembly has a .dll extension
            var baseFileName = assemblyValue;
            if (!assemblyValue.EndsWith(".dll", StringComparison.OrdinalIgnoreCase))
                baseFileName += ".dll";

            // Check if path includes directories (relative path)
            var includesDirectories = assemblyValue.Contains(Path.DirectorySeparatorChar) ||
                                      assemblyValue.Contains(Path.AltDirectorySeparatorChar);

            // Try relative path from component directory
            if (!Path.IsPathRooted(assemblyValue) && includesDirectories && !string.IsNullOrEmpty(component.Directory))
            {
                var relativePath = Path.GetFullPath(Path.Combine(component.Directory, assemblyValue));
                if (File.Exists(relativePath))
                    return relativePath;
            }

            // Search in component directory and binary paths
            var searchPaths = new List<string>();

            // Only use expensive CollectBinaryPaths for LinkButton and InvokeButton types
            if (_currentExtension != null &&
                (component.Type == CommandComponentType.LinkButton || component.Type == CommandComponentType.InvokeButton))
            {
                searchPaths.AddRange(_currentExtension.CollectBinaryPaths(component));
            }
            else if (!string.IsNullOrEmpty(component.Directory))
            {
                searchPaths.Add(component.Directory);

                // Also check bin subdirectory
                var binPath = Path.Combine(component.Directory, "bin");
                if (Directory.Exists(binPath))
                    searchPaths.Add(binPath);
            }

            // Search in all paths
            foreach (var searchPath in searchPaths)
            {
                var candidatePath = Path.Combine(searchPath, baseFileName);
                if (File.Exists(candidatePath))
                    return candidatePath;
            }

            // Search for loaded assembly in AppDomain
            try
            {
                var loadedAssemblies = AppDomain.CurrentDomain.GetAssemblies();
                var assemblyName = Path.GetFileNameWithoutExtension(baseFileName);
                var loadedAssembly = loadedAssemblies.FirstOrDefault(a =>
                    a.GetName().Name?.Equals(assemblyName, StringComparison.OrdinalIgnoreCase) == true);

                if (loadedAssembly != null && !string.IsNullOrEmpty(loadedAssembly.Location))
                    return loadedAssembly.Location;
            }
            catch
            {
                // Ignore errors searching loaded assemblies
            }

            return null;
        }
    }
}
