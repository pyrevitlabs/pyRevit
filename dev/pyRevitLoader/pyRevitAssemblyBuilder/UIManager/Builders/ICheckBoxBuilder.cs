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
        void CreateOrUpdateCheckBox(ParsedComponent component, RibbonPanel parentPanel, string tabName);

        /// <summary>
        /// Adds a stack's checkboxes to the panel as the rows of one AdWindows row panel, or refreshes
        /// the rows a previous load added.
        /// </summary>
        /// <param name="stackComponent">The .stack bundle; its display name identifies the row panel across reloads.</param>
        /// <param name="checkBoxComponents">The stack's visible children, all checkboxes, in layout order. Only the first three are shown; any other checkbox a previous load left in the stack is hidden.</param>
        /// <param name="tabName">The tab that contains the panel, used to find the panel's AdWindows counterpart.</param>
        void CreateOrUpdateCheckBoxStack(
            ParsedComponent stackComponent,
            IReadOnlyList<ParsedComponent> checkBoxComponents,
            RibbonPanel parentPanel,
            string tabName);
    }
}
