#nullable enable
using System;
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
    /// Base class for button builders providing common functionality.
    /// </summary>
    public abstract class ButtonBuilderBase : IButtonBuilder
    {
        protected readonly ILogger Logger;
        protected readonly IButtonPostProcessor ButtonPostProcessor;

        /// <inheritdoc/>
        public abstract CommandComponentType[] SupportedTypes { get; }

        /// <summary>
        /// Initializes a new instance of the button builder base.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor.</param>
        protected ButtonBuilderBase(ILogger logger, IButtonPostProcessor buttonPostProcessor)
        {
            Logger = logger ?? throw new ArgumentNullException(nameof(logger));
            ButtonPostProcessor = buttonPostProcessor ?? throw new ArgumentNullException(nameof(buttonPostProcessor));
        }

        /// <inheritdoc/>
        public bool CanHandle(CommandComponentType componentType)
        {
            return SupportedTypes.Contains(componentType);
        }

        /// <inheritdoc/>
        public abstract void Build(ParsedComponent component, RibbonPanel parentPanel, string tabName, ExtensionAssemblyInfo assemblyInfo);

        /// <summary>
        /// Creates a PushButtonData for a standard push button.
        /// </summary>
        protected PushButtonData CreatePushButtonData(ParsedComponent component, ExtensionAssemblyInfo assemblyInfo)
        {
            // Use Title from bundle.yaml if available, otherwise fall back to DisplayName
            var buttonText = ButtonPostProcessor.GetButtonText(component);

            // Ensure the class name matches what the CommandTypeGenerator creates
            var className = SanitizeClassName(component.UniqueId);

            // Use DisplayName as the button's internal name to match control ID format.
            var pushButtonData = new PushButtonData(
                component.DisplayName,
                buttonText,
                assemblyInfo.Location,
                className);

            // Set availability class if context is defined
            if (!string.IsNullOrEmpty(component.Context))
            {
                var availabilityClassName = className + "_avail";
                pushButtonData.AvailabilityClassName = availabilityClassName;
            }

            return pushButtonData;
        }

        /// <summary>
        /// Sanitizes a class name to match the CommandTypeGenerator logic.
        /// </summary>
        protected static string SanitizeClassName(string name)
        {
            var sb = new System.Text.StringBuilder();
            foreach (char c in name)
                sb.Append(char.IsLetterOrDigit(c) ? c : '_');
            return sb.ToString();
        }

        /// <summary>
        /// Checks if a ribbon item with the specified name already exists in the panel.
        /// </summary>
        protected bool ItemExistsInPanel(RibbonPanel? panel, string itemName)
        {
            if (panel == null || string.IsNullOrEmpty(itemName))
                return false;

            try
            {
                var existingItems = panel.GetItems();
                return existingItems.Any(item => item.Name == itemName);
            }
            catch (Exception ex)
            {
                Logger.Debug($"Error checking if item '{itemName}' exists in panel. Exception: {ex.Message}");
                return false;
            }
        }
    }
}
