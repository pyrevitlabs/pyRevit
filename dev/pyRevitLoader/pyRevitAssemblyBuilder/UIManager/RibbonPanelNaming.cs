#nullable enable
using System;
using System.Collections.Generic;
using System.Linq;
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
            return GetIdName(panel) ?? panel.Source?.Title ?? string.Empty;
        }

        private static string? GetIdName(AdwRibbonPanel panel)
        {
            var id = panel.Source?.Id;
            if (string.IsNullOrEmpty(id))
                return null;

            var separator = id!.LastIndexOf('%');
            return separator >= 0 && separator < id.Length - 1 ? id.Substring(separator + 1) : null;
        }

        /// <summary>
        /// Finds the panel whose id carries the name <paramref name="name"/>, falling back to a panel whose
        /// displayed title is <paramref name="name"/> only when no id carries it.
        /// </summary>
        /// <remarks>
        /// Important: a title must never outrank a name taken from a panel id. Another panel may display
        /// the title <paramref name="name"/> and come first in the tab.
        /// </remarks>
        internal static AdwRibbonPanel? FindByName(IEnumerable<AdwRibbonPanel> panels, string name)
        {
            var candidates = panels.Where(panel => panel != null).ToList();
            return candidates.FirstOrDefault(panel =>
                    string.Equals(GetIdName(panel), name, StringComparison.OrdinalIgnoreCase))
                ?? candidates.FirstOrDefault(panel =>
                    string.Equals(panel.Source?.Title, name, StringComparison.OrdinalIgnoreCase));
        }
    }
}
