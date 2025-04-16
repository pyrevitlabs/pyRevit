using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.UI;
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

        public void BuildUI(IExtension extension, ExtensionAssemblyInfo assemblyInfo)
        {
            if (extension?.Children == null)
                return;

            foreach (var obj in extension.Children as IEnumerable<object> ?? Enumerable.Empty<object>())
                RecursivelyBuildUI(obj, null, null, extension.Name, assemblyInfo);
        }

        private void RecursivelyBuildUI(object obj, object parentComponent, RibbonPanel parentPanel, string tabName, ExtensionAssemblyInfo assemblyInfo)
        {
            var component = obj as ICommandComponent;
            if (component == null)
                return;

            var type = CommandComponentTypeExtensions.FromExtension(component.Type);

            switch (type)
            {
                case CommandComponentType.Tab:
                    try { _uiApp.CreateRibbonTab(component.Name); } catch { }
                    foreach (var child in component.Children ?? Enumerable.Empty<object>())
                        RecursivelyBuildUI(child, component, null, component.Name, assemblyInfo);
                    break;

                case CommandComponentType.Panel:
                    var panel = _uiApp.GetRibbonPanels(tabName).FirstOrDefault(p => p.Name == component.Name)
                             ?? _uiApp.CreateRibbonPanel(tabName, component.Name);
                    foreach (var child in component.Children ?? Enumerable.Empty<object>())
                        RecursivelyBuildUI(child, component, panel, tabName, assemblyInfo);
                    break;

                case CommandComponentType.Stack:
                    var itemDataList = new List<RibbonItemData>();
                    var originalItems = new List<ICommandComponent>();

                    foreach (var child in component.Children as IEnumerable<object> ?? Enumerable.Empty<object>())
                    {
                        var subCmd = child as ICommandComponent;
                        if (subCmd == null)
                            continue;

                        var subType = CommandComponentTypeExtensions.FromExtension(subCmd.Type);

                        if (subType == CommandComponentType.PushButton)
                        {
                            itemDataList.Add(new PushButtonData(subCmd.UniqueId, subCmd.Name, assemblyInfo.Location, subCmd.UniqueId));
                            originalItems.Add(subCmd);
                        }
                        else if (subType == CommandComponentType.PullDown)
                        {
                            var pdData = new PulldownButtonData(subCmd.UniqueId, subCmd.Name);
                            itemDataList.Add(pdData);
                            originalItems.Add(subCmd); // to match later
                        }
                    }

                    if (itemDataList.Count >= 2)
                    {
                        IList<RibbonItem> stackedItems = null;
                        if (itemDataList.Count == 2)
                            stackedItems = parentPanel?.AddStackedItems(itemDataList[0], itemDataList[1]);
                        else if (itemDataList.Count >= 3)
                            stackedItems = parentPanel?.AddStackedItems(itemDataList[0], itemDataList[1], itemDataList[2]);

                        // Now post-process pulldowns to add nested pushbuttons
                        if (stackedItems != null)
                        {
                            for (int i = 0; i < stackedItems.Count; i++)
                            {
                                var ribbonItem = stackedItems[i];
                                var origComponent = originalItems[i];

                                if (ribbonItem is PulldownButton pdBtn)
                                {
                                    foreach (var child in origComponent.Children ?? Enumerable.Empty<object>())
                                    {
                                        if (child is ICommandComponent subCmd &&
                                            CommandComponentTypeExtensions.FromExtension(subCmd.Type) == CommandComponentType.PushButton)
                                        {
                                            var subData = new PushButtonData(subCmd.UniqueId, subCmd.Name, assemblyInfo.Location, subCmd.UniqueId);
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
                    var pbData = new PushButtonData(component.UniqueId, component.Name, assemblyInfo.Location, component.UniqueId);
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

                    foreach (var child in component.Children ?? Enumerable.Empty<object>())
                    {
                        if (child is ICommandComponent subCmd &&
                            CommandComponentTypeExtensions.FromExtension(subCmd.Type) == CommandComponentType.PushButton)
                        {
                            var subData = new PushButtonData(subCmd.UniqueId, subCmd.Name, assemblyInfo.Location, subCmd.UniqueId);
                            splitBtn.AddPushButton(subData);
                        }
                    }
                    break;
            }
        }

        private PulldownButtonData CreatePulldown(
            ICommandComponent component,
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


            foreach (var child in component.Children ?? Enumerable.Empty<object>())
            {
                if (child is ICommandComponent subCmd &&
                    CommandComponentTypeExtensions.FromExtension(subCmd.Type) == CommandComponentType.PushButton)
                {
                    var subData = new PushButtonData(subCmd.UniqueId, subCmd.Name, assemblyInfo.Location, subCmd.UniqueId);
                    pdBtn.AddPushButton(subData);
                }
            }

            return pdData;
        }
    }
}
