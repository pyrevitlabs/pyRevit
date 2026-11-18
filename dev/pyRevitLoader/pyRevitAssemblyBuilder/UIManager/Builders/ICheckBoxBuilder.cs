#nullable enable
using System.Collections.Generic;
using Autodesk.Revit.UI;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Builders
{
    /// <summary>
    /// Builds ribbon checkboxes for .checkbox bundles.
    /// </summary>
    public interface ICheckBoxBuilder
    {
        /// <summary>
        /// Adds the component's checkbox to the panel, or refreshes the one a previous load added.
        /// </summary>
        /// <param name="tabName">The tab that contains the panel, used to find the panel's AdWindows counterpart.</param>
        /// <returns>The checkbox's AdWindows id, which the caller marks as touched in the ribbon scanner
        /// so reloads keep it; null when the checkbox could not be built.</returns>
        string? CreateOrUpdateCheckBox(ParsedComponent component, RibbonPanel parentPanel, string tabName);

        /// <summary>
        /// Adds a stack's checkboxes to the panel as the rows of one AdWindows row panel, or refreshes
        /// the rows a previous load added.
        /// </summary>
        /// <param name="stackComponent">The .stack bundle; its display name is part of the ids of the row panel and of each checkbox in it.</param>
        /// <param name="checkBoxComponents">The stack's visible children, all checkboxes, in layout order. Only the first three are shown; any other checkbox a previous load left in the stack is hidden.</param>
        /// <param name="tabName">The tab that contains the panel, used to find the panel's AdWindows counterpart.</param>
        /// <returns>The AdWindows ids of the checkboxes it shows, including a row whose build failed, which
        /// the caller marks as touched in the ribbon scanner so reloads keep them.</returns>
        IReadOnlyCollection<string> CreateOrUpdateCheckBoxStack(
            ParsedComponent stackComponent,
            IReadOnlyList<ParsedComponent> checkBoxComponents,
            RibbonPanel parentPanel,
            string tabName);
    }
}
