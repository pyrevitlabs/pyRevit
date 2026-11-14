#nullable enable
using System;
using AdwRibbonPanel = Autodesk.Windows.RibbonPanel;

namespace pyRevitAssemblyBuilder.UIManager
{
    /// <summary>
    /// Identifies ribbon panels by their stable name instead of their displayed title.
    /// </summary>
    /// <remarks>
    /// Invariant: a panel is created under its bundle folder name. Revit bakes that name into the panel id
    /// (<c>CustomCtrl_%tab%name</c>) and into the id of every item inside it, which is what a command's
    /// control id has to equal. The localized title is display text only: finding or registering a panel by
    /// it makes control ids depend on the UI locale.
    /// </remarks>
    internal static class RibbonPanelNaming
    {
        /// <summary>
        /// The panel name the ribbon id was built from, falling back to the displayed title for a panel
        /// whose id carries no name segment.
        /// </summary>
        internal static string GetStableName(AdwRibbonPanel panel)
        {
            var id = panel.Source?.Id;
            if (!string.IsNullOrEmpty(id))
            {
                var separator = id!.LastIndexOf('%');
                if (separator >= 0 && separator < id.Length - 1)
                    return id.Substring(separator + 1);
            }

            return panel.Source?.Title ?? string.Empty;
        }

        /// <summary>
        /// True when <paramref name="name"/> is the panel's stable name or its current displayed title.
        /// </summary>
        internal static bool IsNamed(AdwRibbonPanel panel, string name)
        {
            return string.Equals(GetStableName(panel), name, StringComparison.OrdinalIgnoreCase)
                || string.Equals(panel.Source?.Title, name, StringComparison.OrdinalIgnoreCase);
        }
    }
}
