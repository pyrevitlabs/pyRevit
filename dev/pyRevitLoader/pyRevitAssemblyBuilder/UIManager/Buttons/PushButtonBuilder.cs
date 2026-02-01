#nullable enable
using System;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Buttons
{
    /// <summary>
    /// Builder for standard push buttons including PushButton, UrlButton, InvokeButton, and ContentButton.
    /// </summary>
    public class PushButtonBuilder : ButtonBuilderBase
    {
        private readonly SmartButtonScriptInitializer? _smartButtonScriptInitializer;

        /// <inheritdoc/>
        public override CommandComponentType[] SupportedTypes => new[]
        {
            CommandComponentType.PushButton,
            CommandComponentType.UrlButton,
            CommandComponentType.InvokeButton,
            CommandComponentType.ContentButton,
            CommandComponentType.SmartButton
        };

        /// <summary>
        /// Initializes a new instance of the <see cref="PushButtonBuilder"/> class.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor.</param>
        /// <param name="smartButtonScriptInitializer">Optional SmartButton script initializer.</param>
        public PushButtonBuilder(
            ILogger logger,
            IButtonPostProcessor buttonPostProcessor,
            SmartButtonScriptInitializer? smartButtonScriptInitializer = null)
            : base(logger, buttonPostProcessor)
        {
            _smartButtonScriptInitializer = smartButtonScriptInitializer;
        }

        /// <inheritdoc/>
        public override void Build(ParsedComponent component, RibbonPanel parentPanel, string tabName, ExtensionAssemblyInfo assemblyInfo)
        {
            if (parentPanel == null)
            {
                Logger.Warning($"Cannot create push button '{component.DisplayName}': parent panel is null.");
                return;
            }

            // Check if button already exists - if so, update it instead of creating new
            var existingBtn = GetExistingButton(parentPanel, component.DisplayName);
            if (existingBtn != null)
            {
                UpdateExistingButton(existingBtn, component, assemblyInfo);
                return;
            }

            try
            {
                var pbData = CreatePushButtonData(component, assemblyInfo);
                var btn = parentPanel.AddItem(pbData) as PushButton;
                if (btn != null)
                {
                    ButtonPostProcessor.Process(btn, component);

                    // Handle SmartButton-specific initialization
                    if (component.Type == CommandComponentType.SmartButton && _smartButtonScriptInitializer != null)
                    {
                        var shouldActivate = _smartButtonScriptInitializer.ExecuteSelfInit(component, btn);
                        if (!shouldActivate)
                        {
                            btn.Enabled = false;
                            Logger.Debug($"SmartButton '{component.DisplayName}' deactivated by __selfinit__.");
                        }
                    }

                    Logger.Debug($"Created push button '{component.DisplayName}'.");
                }
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to create push button '{component.DisplayName}'. Exception: {ex.Message}");
            }
        }

        /// <summary>
        /// Gets an existing button from the panel by name.
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
                Logger.Debug($"Error getting existing button '{buttonName}': {ex.Message}");
            }
            return null;
        }

        /// <summary>
        /// Updates an existing button's properties (title, icon, tooltip) to match the component.
        /// Mirrors Python's existing_item.set_title() + existing_item.activate() behavior.
        /// </summary>
        private void UpdateExistingButton(PushButton btn, ParsedComponent component, ExtensionAssemblyInfo assemblyInfo)
        {
            try
            {
                // Update command binding to point at the latest assembly
                UpdatePushButtonCommandBinding(btn, component, assemblyInfo);

                // Update button text (title) - matches Python's existing_item.set_title(ui_title)
                var buttonText = ButtonPostProcessor.GetButtonText(component);
                btn.ItemText = buttonText;

                // Re-apply icon, tooltip, and other properties
                ButtonPostProcessor.Process(btn, component);

                // Activate the button (enable and show) - matches Python's existing_item.activate()
                btn.Enabled = true;
                btn.Visible = true;

                // Handle SmartButton-specific initialization on update
                if (component.Type == CommandComponentType.SmartButton && _smartButtonScriptInitializer != null)
                {
                    var shouldActivate = _smartButtonScriptInitializer.ExecuteSelfInit(component, btn);
                    if (!shouldActivate)
                    {
                        btn.Enabled = false;
                        Logger.Debug($"SmartButton '{component.DisplayName}' deactivated by __selfinit__ during update.");
                    }
                }

                Logger.Debug($"Updated existing push button '{component.DisplayName}'.");
            }
            catch (Exception ex)
            {
                Logger.Debug($"Failed to update push button '{component.DisplayName}': {ex.Message}");
            }
        }
    }
}
