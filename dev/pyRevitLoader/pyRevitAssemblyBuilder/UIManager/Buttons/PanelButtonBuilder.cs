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

            if (ItemExistsInPanel(parentPanel, component.DisplayName))
            {
                Logger.Debug($"Panel button '{component.DisplayName}' already exists in panel.");
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
                    Logger.Debug($"Created panel button '{component.DisplayName}'.");
                }
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to create panel button '{component.DisplayName}'. Exception: {ex.Message}");
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
