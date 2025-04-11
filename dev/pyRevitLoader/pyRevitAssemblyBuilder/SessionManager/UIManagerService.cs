using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.UI;
using pyRevitExtensionParser;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.Shared;

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

        private void RecursivelyBuildUI(ParsedComponent component, ParsedComponent parentComponent, RibbonPanel parentPanel, string tabName, ExtensionAssemblyInfo assemblyInfo)
        {
            switch (component.Type)
            {
                case CommandComponentType.Tab:
                    try { _uiApp.CreateRibbonTab(component.Name); } catch { }
                    foreach (var child in component.Children ?? Enumerable.Empty<ParsedComponent>())
                        RecursivelyBuildUI(child, component, null, component.Name, assemblyInfo);
                    break;

                case CommandComponentType.Panel:
                    var panel = _uiApp.GetRibbonPanels(tabName).FirstOrDefault(p => p.Name == component.Name)
                             ?? _uiApp.CreateRibbonPanel(tabName, component.Name);
                    foreach (var child in component.Children ?? Enumerable.Empty<ParsedComponent>())
                        RecursivelyBuildUI(child, component, panel, tabName, assemblyInfo);
                    break;

                case CommandComponentType.Stack:
                    var itemDataList = new List<RibbonItemData>();
                    var originalItems = new List<ParsedComponent>();

                    foreach (var child in component.Children ?? Enumerable.Empty<ParsedComponent>())
                    {
                        if (child.Type == CommandComponentType.PushButton)
                        {
                            itemDataList.Add(CreatePushButton(child, assemblyInfo));
                            originalItems.Add(child);
                        }
                        else if (child.Type == CommandComponentType.PullDown)
                        {
                            var pdData = new PulldownButtonData(child.UniqueId, child.Name);
                            itemDataList.Add(pdData);
                            originalItems.Add(child);
                        }
                    }

                    if (itemDataList.Count >= 2)
                    {
                        IList<RibbonItem> stackedItems = null;
                        if (itemDataList.Count == 2)
                            stackedItems = parentPanel?.AddStackedItems(itemDataList[0], itemDataList[1]);
                        else if (itemDataList.Count >= 3)
                            stackedItems = parentPanel?.AddStackedItems(itemDataList[0], itemDataList[1], itemDataList[2]);

                        if (stackedItems != null)
                        {
                            for (int i = 0; i < stackedItems.Count; i++)
                            {
                                var ribbonItem = stackedItems[i];
                                var origComponent = originalItems[i];

                                if (ribbonItem is PulldownButton pdBtn)
                                {
                                    foreach (var sub in origComponent.Children ?? Enumerable.Empty<ParsedComponent>())
                                    {
                                        if (sub.Type == CommandComponentType.PushButton)
                                        {
                                            var subData = CreatePushButton(sub, assemblyInfo);
                                            pdBtn.AddPushButton(subData);
                                        }
                                    }
                                }
                            }
                        }
                    }
                    break;

                case CommandComponentType.PushButton:
                case CommandComponentType.SmartButton:
                    var pbData = CreatePushButton(component, assemblyInfo);
                    var btn = parentPanel?.AddItem(pbData) as PushButton;
                    if (!string.IsNullOrEmpty(component.Tooltip))
                        btn.ToolTip = component.Tooltip;
                    break;

                case CommandComponentType.PullDown:
                    CreatePulldown(component, parentPanel, tabName, assemblyInfo, true);
                    break;

                case CommandComponentType.SplitButton:
                case CommandComponentType.SplitPushButton:
                    var splitData = new SplitButtonData(component.UniqueId, component.Name);
                    var splitBtn = parentPanel?.AddItem(splitData) as SplitButton;
                    if (splitBtn == null) return;

                    foreach (var sub in component.Children ?? Enumerable.Empty<ParsedComponent>())
                    {
                        if (sub.Type == CommandComponentType.PushButton)
                        {
                            var subData = CreatePushButton(sub, assemblyInfo);
                            splitBtn.AddPushButton(subData);
                        }
                    }
                    break;
            }
        }

        private PulldownButtonData CreatePulldown(
            ParsedComponent component,
            RibbonPanel parentPanel,
            string tabName,
            ExtensionAssemblyInfo assemblyInfo,
            bool addToPanel)
        {
            var pdData = new PulldownButtonData(component.UniqueId, component.Name);

            if (!addToPanel)
                return pdData;

            PulldownButton pdBtn = parentPanel.AddItem(pdData) as PulldownButton;
            if (pdBtn == null)
                return null;

            foreach (var sub in component.Children ?? Enumerable.Empty<ParsedComponent>())
            {
                if (sub.Type == CommandComponentType.PushButton)
                {
                    var subData = CreatePushButton(sub, assemblyInfo);
                    pdBtn.AddPushButton(subData);
                }
            }

            return pdData;
        }

        private PushButtonData CreatePushButton(ParsedComponent component, ExtensionAssemblyInfo assemblyInfo)
        {
            return new PushButtonData(
                component.UniqueId,
                component.Name,
                assemblyInfo.Location,
                component.UniqueId
            );
        }
    }
}
