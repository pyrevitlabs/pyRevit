#nullable enable
using System;
using System.Linq;
using Autodesk.Revit.UI;
using Autodesk.Windows;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;
using RibbonPanel = Autodesk.Revit.UI.RibbonPanel;
using RibbonButton = Autodesk.Windows.RibbonButton;
using pyRevitAssemblyBuilder.SessionManager;

namespace pyRevitAssemblyBuilder.UIManager.Buttons
{
    /// <summary>
    /// Builder for panel buttons (dialog launcher buttons).
    /// </summary>
    public class PanelButtonBuilder : ButtonBuilderBase
    {
        /// <inheritdoc/>
        public override CommandComponentType[] SupportedTypes => new[]
        {
            CommandComponentType.PanelButton
        };

        /// <summary>
        /// Initializes a new instance of the <see cref="PanelButtonBuilder"/> class.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor.</param>
        public PanelButtonBuilder(ILogger logger, IButtonPostProcessor buttonPostProcessor)
            : base(logger, buttonPostProcessor)
        {
        }

        /// <inheritdoc/>
        public override void Build(ParsedComponent component, RibbonPanel parentPanel, string tabName, ExtensionAssemblyInfo assemblyInfo)
        {
            if (parentPanel == null)
            {
                Logger.Warning($"Cannot create panel button '{component.DisplayName}': parent panel is null.");
                return;
            }

            var existingBtn = GetExistingButton(parentPanel, component.DisplayName);
            if (existingBtn != null)
            {
                UpdateExistingPanelButton(existingBtn, component, assemblyInfo, tabName, parentPanel);
                return;
            }

            try
            {
                var panelBtnData = CreatePushButtonData(component, assemblyInfo);
                var panelBtn = parentPanel.AddItem(panelBtnData) as PushButton;

                if (panelBtn != null)
                {
                    ButtonPostProcessor.Process(panelBtn, component);
                    ModifyToPanelButton(tabName, parentPanel, panelBtn);
                    
                    // Note: We cannot re-apply contextual help after conversion because
                    // the DialogLauncher is a RibbonButton (Autodesk.Windows) which doesn't
                    // have the SetContextualHelp method. The contextual help applied
                    // in ButtonPostProcessor.Process() before conversion should remain.
                    
                    Logger.Debug($"Created panel button '{component.DisplayName}'.");
                }
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to create panel button '{component.DisplayName}'. Exception: {ex.Message}");
            }
        }

        /// <summary>
        /// Gets an existing panel button from the panel by name.
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
                Logger.Debug($"Error getting existing panel button '{buttonName}': {ex.Message}");
            }
            return null;
        }

        /// <summary>
        /// Updates an existing panel button's properties and binding.
        /// </summary>
        private void UpdateExistingPanelButton(PushButton panelBtn, ParsedComponent component, ExtensionAssemblyInfo assemblyInfo, string tabName, RibbonPanel parentPanel)
        {
            try
            {
                UpdatePushButtonCommandBinding(panelBtn, component, assemblyInfo);

                var buttonText = ButtonPostProcessor.GetButtonText(component);
                panelBtn.ItemText = buttonText;

                ButtonPostProcessor.Process(panelBtn, component);

                panelBtn.Enabled = true;
                panelBtn.Visible = true;

                // Ensure it is set as dialog launcher if needed
                ModifyToPanelButton(tabName, parentPanel, panelBtn);

                Logger.Debug($"Updated existing panel button '{component.DisplayName}'.");
            }
            catch (Exception ex)
            {
                Logger.Debug($"Failed to update panel button '{component.DisplayName}': {ex.Message}");
            }
        }

        /// <summary>
        /// Modifies a push button to be a panel dialog launcher button.
        /// </summary>
        private void ModifyToPanelButton(string tabName, RibbonPanel parentPanel, PushButton panelBtn)
        {
            try
            {
                var adwTab = ComponentManager
                    .Ribbon
                    .Tabs
                    .FirstOrDefault(t => t.Id == tabName);
                if (adwTab == null)
                    return;

                var adwPanel = adwTab
                    .Panels
                    .First(p => p.Source.Title == parentPanel.Name);
                var adwBtn = adwPanel
                    .Source
                    .Items
                    .First(i => i.AutomationName == panelBtn.ItemText);
                adwPanel.Source.Items.Remove(adwBtn);
                adwPanel.Source.DialogLauncher = (RibbonButton)adwBtn;
            }
            catch (Exception ex)
            {
                // Button modification is non-critical, but log for debugging
                Logger.Debug($"Failed to modify button '{panelBtn.ItemText}' to panel button in tab '{tabName}'. Exception: {ex.Message}");
            }
        }
    }
}
