#nullable enable
using Autodesk.Revit.UI;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Builders
{
    /// <summary>
    /// Interface for building ComboBox controls.
    /// </summary>
    public interface IComboBoxBuilder
    {
        /// <summary>
        /// Creates a ComboBox control in the ribbon panel.
        /// </summary>
        /// <param name="component">The ComboBox component definition.</param>
        /// <param name="parentPanel">The panel to add the ComboBox to.</param>
        void CreateComboBox(ParsedComponent component, RibbonPanel parentPanel);

        /// <summary>
        /// Updates an existing ComboBox control in the ribbon panel.
        /// </summary>
        /// <param name="component">The ComboBox component definition.</param>
        /// <param name="parentPanel">The panel containing the ComboBox.</param>
        void UpdateComboBox(ParsedComponent component, RibbonPanel parentPanel);
    }
}
