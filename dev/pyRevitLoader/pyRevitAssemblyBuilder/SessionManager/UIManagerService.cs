using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using Autodesk.Windows;
using RibbonPanel = Autodesk.Revit.UI.RibbonPanel;
using RibbonButton = Autodesk.Windows.RibbonButton;
using RibbonItem = Autodesk.Revit.UI.RibbonItem;
using static pyRevitExtensionParser.ExtensionParser;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class UIManagerService
    {
        private readonly UIApplication _uiApp;

        public UIManagerService(UIApplication uiApp)
        {
            _uiApp = uiApp;
        }

        public void BuildUI(ParsedExtension extension, ExtensionAssemblyInfo assemblyInfo)
        {
            if (extension?.Children == null)
                return;

            foreach (var component in extension.Children)
                RecursivelyBuildUI(component, null, null, extension.Name, assemblyInfo);
        }

        private void RecursivelyBuildUI(
            ParsedComponent component,
            ParsedComponent parentComponent,
            RibbonPanel parentPanel,
            string tabName,
            ExtensionAssemblyInfo assemblyInfo)
        {
            switch (component.Type)
            {
                case CommandComponentType.Tab:
                    // Use Title from bundle.yaml if available, otherwise fall back to DisplayName
                    var tabText = !string.IsNullOrEmpty(component.Title) ? component.Title : component.DisplayName;
                    try { _uiApp.CreateRibbonTab(tabText); } catch { }
                    foreach (var child in component.Children ?? Enumerable.Empty<ParsedComponent>())
                        RecursivelyBuildUI(child, component, null, tabText, assemblyInfo);
                    break;

                case CommandComponentType.Panel:
                    // Use Title from bundle.yaml if available, otherwise fall back to DisplayName
                    var panelText = !string.IsNullOrEmpty(component.Title) ? component.Title : component.DisplayName;
                    var panel = _uiApp.GetRibbonPanels(tabName)
                        .FirstOrDefault(p => p.Name == panelText)
                        ?? _uiApp.CreateRibbonPanel(tabName, panelText);
                    foreach (var child in component.Children ?? Enumerable.Empty<ParsedComponent>())
                        RecursivelyBuildUI(child, component, panel, tabName, assemblyInfo);
                    break;

                default:
                    if (component.HasSlideout)
                    {
                        EnsureSlideOutApplied(parentComponent, parentPanel);
                    }
                    HandleComponentBuilding(component, parentPanel, tabName, assemblyInfo);
                    break;
            }
        }

        private void EnsureSlideOutApplied(ParsedComponent parentComponent,RibbonPanel parentPanel)
        {
            if (parentPanel != null && parentComponent.Type == CommandComponentType.Panel)
            {
                try { parentPanel.AddSlideOut(); } catch { }
            }
        }

        private void HandleComponentBuilding(
            ParsedComponent component,
            RibbonPanel parentPanel,
            string tabName,
            ExtensionAssemblyInfo assemblyInfo)
        {
            switch (component.Type)
            {
                case CommandComponentType.Stack:
                    BuildStack(component, parentPanel, assemblyInfo);
                    break;
                case CommandComponentType.PanelButton:
                    var panelBtnData = CreatePushButton(component, assemblyInfo);
                    var panelBtn = parentPanel.AddItem(panelBtnData) as PushButton;
                    if (!string.IsNullOrEmpty(component.Tooltip))
                        panelBtn.ToolTip = component.Tooltip;
                    ModifyToPanelButton(tabName, parentPanel, panelBtn);
                    break;
                case CommandComponentType.PushButton:
                case CommandComponentType.SmartButton:
                    var pbData = CreatePushButton(component, assemblyInfo);
                    var btn = parentPanel.AddItem(pbData) as PushButton;
                    if (!string.IsNullOrEmpty(component.Tooltip))
                        btn.ToolTip = component.Tooltip;
                    break;

                case CommandComponentType.PullDown:
                    CreatePulldown(component, parentPanel, tabName, assemblyInfo, true);
                    break;

                case CommandComponentType.SplitButton:
                case CommandComponentType.SplitPushButton:
                    // Use Title from bundle.yaml if available, otherwise fall back to DisplayName
                    var splitButtonText = !string.IsNullOrEmpty(component.Title) ? component.Title : component.DisplayName;
                    var splitData = new SplitButtonData(component.UniqueId, splitButtonText);
                    var splitBtn = parentPanel.AddItem(splitData) as SplitButton;
                    if (splitBtn != null)
                    {
                        // Assign tooltip to the split button itself
                        if (!string.IsNullOrEmpty(component.Tooltip))
                            splitBtn.ToolTip = component.Tooltip;

                        foreach (var sub in component.Children ?? Enumerable.Empty<ParsedComponent>())
                        {
                            if (sub.Type == CommandComponentType.PushButton)
                            {
                                var subBtn = splitBtn.AddPushButton(CreatePushButton(sub, assemblyInfo));
                                if (!string.IsNullOrEmpty(sub.Tooltip))
                                    subBtn.ToolTip = sub.Tooltip;
                            }
                        }
                    }
                    break;
            }
        }

        private void ModifyToPanelButton(string tabName, RibbonPanel parentPanel, PushButton panelBtn)
        {
            try
            {
                var adwTab = ComponentManager
                    .Ribbon
                    .Tabs
                    .FirstOrDefault(t => t.Id == tabName);
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
                Console.WriteLine("Failed modify PushButton to PanelButton");
                Console.WriteLine(ex.Message);
            }
        }

        private void BuildStack(
            ParsedComponent component,
            RibbonPanel parentPanel,
            ExtensionAssemblyInfo assemblyInfo)
        {
            var itemDataList = new List<RibbonItemData>();
            var originalItems = new List<ParsedComponent>();

            foreach (var child in component.Children ?? Enumerable.Empty<ParsedComponent>())
            {
                if (child.Type == CommandComponentType.PushButton ||
                    child.Type == CommandComponentType.SmartButton)
                {
                    itemDataList.Add(CreatePushButton(child, assemblyInfo));
                    originalItems.Add(child);
                }
                else if (child.Type == CommandComponentType.PullDown)
                {
                    // Use Title from bundle.yaml if available, otherwise fall back to DisplayName
                    var pulldownText = !string.IsNullOrEmpty(child.Title) ? child.Title : child.DisplayName;
                    var pdData = new PulldownButtonData(child.UniqueId, pulldownText);
                    itemDataList.Add(pdData);
                    originalItems.Add(child);
                }
            }

            if (itemDataList.Count >= 2)
            {
                IList<RibbonItem> stackedItems = null;
                if (itemDataList.Count == 2)
                    stackedItems = parentPanel.AddStackedItems(itemDataList[0], itemDataList[1]);
                else
                    stackedItems = parentPanel.AddStackedItems(itemDataList[0], itemDataList[1], itemDataList[2]);

                if (stackedItems != null)
                {
                    for (int i = 0; i < stackedItems.Count; i++)
                    {
                        var ribbonItem = stackedItems[i];
                        var origComponent = originalItems[i];
                        
                        // Assign tooltip to push buttons in stack
                        if (ribbonItem is PushButton pushBtn && !string.IsNullOrEmpty(origComponent.Tooltip))
                        {
                            pushBtn.ToolTip = origComponent.Tooltip;
                        }
                        
                        if (ribbonItem is PulldownButton pdBtn)
                        {
                            // Assign tooltip to the pulldown button itself in stack
                            if (!string.IsNullOrEmpty(origComponent.Tooltip))
                                pdBtn.ToolTip = origComponent.Tooltip;

                            foreach (var sub in origComponent.Children ?? Enumerable.Empty<ParsedComponent>())
                            {
                                if (sub.Type == CommandComponentType.PushButton)
                                {
                                    var subBtn = pdBtn.AddPushButton(CreatePushButton(sub, assemblyInfo));
                                    if (!string.IsNullOrEmpty(sub.Tooltip))
                                        subBtn.ToolTip = sub.Tooltip;
                                }
                            }
                        }
                    }
                }
            }
        }

        private PulldownButtonData CreatePulldown(
            ParsedComponent component,
            RibbonPanel parentPanel,
            string tabName,
            ExtensionAssemblyInfo assemblyInfo,
            bool addToPanel)
        {
            // Use Title from bundle.yaml if available, otherwise fall back to DisplayName
            var pulldownText = !string.IsNullOrEmpty(component.Title) ? component.Title : component.DisplayName;
            var pdData = new PulldownButtonData(component.UniqueId, pulldownText);
            if (!addToPanel) return pdData;

            var pdBtn = parentPanel.AddItem(pdData) as PulldownButton;
            if (pdBtn == null) return null;

            // Assign tooltip to the pulldown button itself
            if (!string.IsNullOrEmpty(component.Tooltip))
                pdBtn.ToolTip = component.Tooltip;

            foreach (var sub in component.Children ?? Enumerable.Empty<ParsedComponent>())
            {
                if (sub.Type == CommandComponentType.PushButton)
                {
                    var subBtn = pdBtn.AddPushButton(CreatePushButton(sub, assemblyInfo));
                    if (!string.IsNullOrEmpty(sub.Tooltip))
                        subBtn.ToolTip = sub.Tooltip;
                }
            }
            return pdData;
        }

        private PushButtonData CreatePushButton(ParsedComponent component, ExtensionAssemblyInfo assemblyInfo)
        {
            // Use Title from bundle.yaml if available, otherwise fall back to DisplayName
            var buttonText = !string.IsNullOrEmpty(component.Title) ? component.Title : component.DisplayName;
            
            return new PushButtonData(
                component.UniqueId,
                buttonText,
                assemblyInfo.Location,
                component.UniqueId);
        }
    }
}
