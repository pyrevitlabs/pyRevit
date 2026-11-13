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
        private readonly BuildContext _buildContext;

        /// <inheritdoc/>
        public override CommandComponentType[] SupportedTypes => new[]
        {
            CommandComponentType.LinkButton
        };

        /// <summary>
        /// Initializes a new instance of the <see cref="LinkButtonBuilder"/> class.
        /// </summary>
        /// <param name="buildContext">Shared build context that carries the extension being built.</param>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor.</param>
        public LinkButtonBuilder(BuildContext buildContext, ILogger logger, IButtonPostProcessor buttonPostProcessor)
            : base(logger, buttonPostProcessor)
        {
            _buildContext = buildContext ?? throw new ArgumentNullException(nameof(buildContext));
        }

        /// <inheritdoc/>
        public override void Build(ParsedComponent component, RibbonPanel parentPanel, string tabName, ExtensionAssemblyInfo assemblyInfo)
        {
            if (parentPanel == null)
            {
                Logger.Warning($"Cannot create link button '{component.DisplayName}': parent panel is null.");
                return;
            }

            var existingBtn = GetExistingButton(parentPanel, component.DisplayName);
            if (existingBtn != null)
            {
                UpdateExistingLinkButton(existingBtn, component);
                return;
            }

            try
            {
                var linkData = CreateLinkButtonData(component);
                if (linkData != null)
                {
                    var linkBtn = TimedAddItem(() => parentPanel.AddItem(linkData) as PushButton);
                    if (linkBtn != null)
                    {
                        ButtonPostProcessor.Process(linkBtn, component);
                    }
                }
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to create link button '{component.DisplayName}'. Exception: {ex.Message}");
            }
        }

        /// <summary>
        /// Gets an existing link button from the panel by name.
        /// </summary>
        private PushButton? GetExistingButton(RibbonPanel panel, string buttonName)
        {
            try
            {
                var items = panel.GetItems();
                foreach (var item in items)
                {
                    if (item.Name == buttonName && item is PushButton pb)
                        return pb;
                }
            }
            catch (Exception ex)
            {
                Logger.Debug($"Error getting existing link button '{buttonName}': {ex.Message}");
            }
            return null;
        }

        /// <summary>
        /// Updates an existing link button's properties and command binding.
        /// </summary>
        internal void UpdateExistingLinkButton(
            PushButton linkBtn,
            ParsedComponent component,
            ParsedComponent? parentComponent = null,
            IconMode iconMode = IconMode.LargeAndSmall)
        {
            try
            {
                if (TryResolveLinkBinding(component, out var assemblyPath, out var className, out var availabilityClassName, out var buttonText))
                {
                    linkBtn.AssemblyName = assemblyPath;
                    linkBtn.ClassName = className;
                    AvailabilityBinding.Apply(linkBtn, AvailabilityBinding.ForResolved(availabilityClassName));

                    linkBtn.ItemText = buttonText;
                    ButtonPostProcessor.Process(linkBtn, component, parentComponent, iconMode);

                    linkBtn.Enabled = true;
                    linkBtn.Visible = true;
                }
            }
            catch (Exception ex)
            {
                Logger.Warning($"Failed to update link button '{component.DisplayName}': {ex.Message}");
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
                if (!TryResolveLinkBinding(component, out var assemblyPath, out var fullCommandClass, out var fullAvailClass, out var buttonText))
                    return null;

                var pushButtonData = new PushButtonData(component.DisplayName, buttonText, assemblyPath, fullCommandClass);
                if (!string.IsNullOrEmpty(fullAvailClass))
                    pushButtonData.AvailabilityClassName = fullAvailClass;

                return pushButtonData;
            }
            catch (Exception ex)
            {
                Logger.Debug($"Failed to resolve assembly path for LinkButton '{component.DisplayName}'. Exception: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Resolves assembly/class bindings and button text for a LinkButton.
        /// </summary>
        private bool TryResolveLinkBinding(ParsedComponent component, out string assemblyPath, out string fullCommandClass, out string? fullAvailClass, out string buttonText)
        {
            assemblyPath = string.Empty;
            fullCommandClass = string.Empty;
            fullAvailClass = null;
            buttonText = string.Empty;

            if (string.IsNullOrEmpty(component.TargetAssembly))
            {
                Logger.Debug($"LinkButton '{component.DisplayName}' has no target assembly specified.");
                return false;
            }

            if (string.IsNullOrEmpty(component.CommandClass))
            {
                Logger.Debug($"LinkButton '{component.DisplayName}' has no command class specified.");
                return false;
            }

            assemblyPath = LinkAssemblyPathResolver.Resolve(component, _buildContext.CurrentExtension) ?? string.Empty;
            if (string.IsNullOrEmpty(assemblyPath) || !File.Exists(assemblyPath))
            {
                Logger.Debug($"LinkButton '{component.DisplayName}' assembly not found at resolved path.");
                return false;
            }

            buttonText = ButtonPostProcessor.GetButtonText(component);

            var assemblyName = Path.GetFileNameWithoutExtension(assemblyPath);

            fullCommandClass = component.CommandClass.Contains(".")
                ? component.CommandClass
                : $"{assemblyName}.{component.CommandClass}";

            if (!string.IsNullOrEmpty(component.AvailabilityClass))
            {
                fullAvailClass = component.AvailabilityClass.Contains(".")
                    ? component.AvailabilityClass
                    : $"{assemblyName}.{component.AvailabilityClass}";
            }

            return true;
        }
    }
}
