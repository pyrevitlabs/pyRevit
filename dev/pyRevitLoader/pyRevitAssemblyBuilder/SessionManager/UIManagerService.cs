using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.Shared;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class UIManagerService : IUIManager
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
            {
                RecursivelyBuildUI(obj, null, null, extension.Name, assemblyInfo);
            }
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
                    foreach (var child in component.Children as IEnumerable<object> ?? Enumerable.Empty<object>())
                        RecursivelyBuildUI(child, component, null, component.Name, assemblyInfo);
                    break;

                case CommandComponentType.Panel:
                    var panel = _uiApp.GetRibbonPanels(tabName).FirstOrDefault(p => p.Name == component.Name)
                             ?? _uiApp.CreateRibbonPanel(tabName, component.Name);
                    foreach (var child in component.Children as IEnumerable<object> ?? Enumerable.Empty<object>())
                        RecursivelyBuildUI(child, component, panel, tabName, assemblyInfo);
                    break;

                case CommandComponentType.Stack:
                    var buttonDatas = new List<RibbonItemData>();

                    foreach (var child in component.Children as IEnumerable<object> ?? Enumerable.Empty<object>())
                    {
                        var subCmd = child as ICommandComponent;
                        if (subCmd == null) continue;

                        var subType = CommandComponentTypeExtensions.FromExtension(subCmd.Type);
                        switch (subType)
                        {
                            case CommandComponentType.PushButton:
                                buttonDatas.Add(new PushButtonData(subCmd.Name, subCmd.Name, assemblyInfo.Location, subCmd.UniqueId));
                                break;
                            case CommandComponentType.PullDown:
                                buttonDatas.Add(new PulldownButtonData(subCmd.Name, subCmd.Name));
                                break;
                        }
                    }

                    if (buttonDatas.Count == 2)
                        parentPanel?.AddStackedItems(buttonDatas[0], buttonDatas[1]);
                    else if (buttonDatas.Count >= 3)
                        parentPanel?.AddStackedItems(buttonDatas[0], buttonDatas[1], buttonDatas[2]);
                    break;

                case CommandComponentType.PushButton:
                case CommandComponentType.SmartButton:
                    var pbData = new PushButtonData(component.Name, component.Name, assemblyInfo.Location, component.UniqueId);
                    var btn = parentPanel?.AddItem(pbData) as PushButton;
                    if (!string.IsNullOrEmpty(component.Tooltip))
                        btn.ToolTip = component.Tooltip;
                    break;

                case CommandComponentType.PullDown:
                    var pdBtnData = new PulldownButtonData(component.Name, component.Name);
                    var pdBtn = parentPanel?.AddItem(pdBtnData) as PulldownButton;
                    if (pdBtn == null) return;

                    foreach (var child in component.Children as IEnumerable<object> ?? Enumerable.Empty<object>())
                    {
                        if (child is ICommandComponent subCmd &&
                            CommandComponentTypeExtensions.FromExtension(subCmd.Type) == CommandComponentType.PushButton)
                        {
                            var subData = new PushButtonData(subCmd.Name, subCmd.Name, assemblyInfo.Location, subCmd.UniqueId);
                            pdBtn.AddPushButton(subData);
                        }
                    }
                    break;

                case CommandComponentType.SplitButton:
                case CommandComponentType.SplitPushButton:
                    var splitData = new SplitButtonData(component.Name, component.Name);
                    var splitBtn = parentPanel?.AddItem(splitData) as SplitButton;
                    if (splitBtn == null) return;

                    foreach (var child in component.Children as IEnumerable<object> ?? Enumerable.Empty<object>())
                    {
                        if (child is ICommandComponent subCmd &&
                            CommandComponentTypeExtensions.FromExtension(subCmd.Type) == CommandComponentType.PushButton)
                        {
                            var subData = new PushButtonData(subCmd.Name, subCmd.Name, assemblyInfo.Location, subCmd.UniqueId);
                            splitBtn.AddPushButton(subData);
                        }
                    }
                    break;
            }
        }
    }
}