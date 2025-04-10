using System;
using Autodesk.Revit.UI;
using Autodesk.Revit.ApplicationServices;
using pyRevitAssemblyBuilder.Shared;
using static System.Net.Mime.MediaTypeNames;
using pyRevitAssemblyBuilder.AssemblyMaker;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class UIManagerService : IUIManager
    {
        private readonly UIApplication _uiApplication;

        public UIManagerService(UIApplication uiApplication)
        {
            _uiApplication = uiApplication;
        }

        public void BuildUI(IExtension extension, ExtensionAssemblyInfo assemblyInfo)
        {
            string tabName = extension.Name;
            string panelName = "Commands";

            try
            {
                _uiApplication.CreateRibbonTab(tabName);
            }
            catch { }

            RibbonPanel panel = null;
            foreach (var existingPanel in _uiApplication.GetRibbonPanels(tabName))
            {
                if (existingPanel.Name == panelName)
                {
                    panel = existingPanel;
                    break;
                }
            }
            if (panel == null)
            {
                panel = _uiApplication.CreateRibbonPanel(tabName, panelName);
            }

            foreach (var cmd in extension.GetAllCommands())
            {
                var pushButtonData = new PushButtonData(
                    name: cmd.Name,
                    text: cmd.Name,
                    assemblyName: assemblyInfo.Location,
                    className: cmd.UniqueId);

                var button = panel.AddItem(pushButtonData) as PushButton;
                if (!string.IsNullOrEmpty(cmd.Tooltip))
                {
                    button.ToolTip = cmd.Tooltip;
                }
            }
        }

    }
}