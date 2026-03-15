#nullable enable
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.UIManager.Icons;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Buttons
{
    /// <summary>
    /// Interface for post-processing ribbon buttons after creation.
    /// Consolidates icon application, tooltip setup, and highlight management.
    /// </summary>
    public interface IButtonPostProcessor
    {
        /// <summary>
        /// Gets the icon manager for direct icon operations (preloading, ComboBox icons).
        /// </summary>
        IIconManager IconManager { get; }

        /// <summary>
        /// Processes a ribbon item by applying icon, tooltip, and highlight.
        /// </summary>
        /// <param name="ribbonItem">The ribbon item to process.</param>
        /// <param name="component">The component containing configuration.</param>
        void Process(RibbonItem ribbonItem, ParsedComponent component);

        /// <summary>
        /// Processes a ribbon item with a parent component for icon fallback.
        /// Used for sub-buttons where icons may be inherited from parent.
        /// </summary>
        /// <param name="ribbonItem">The ribbon item to process.</param>
        /// <param name="component">The component containing configuration.</param>
        /// <param name="parentComponent">The parent component for icon fallback.</param>
        void Process(RibbonItem ribbonItem, ParsedComponent component, ParsedComponent? parentComponent);

        /// <summary>
        /// Processes a ribbon item with specific icon mode.
        /// Used for sub-buttons in pulldowns/splits where small icons go to both properties.
        /// </summary>
        /// <param name="ribbonItem">The ribbon item to process.</param>
        /// <param name="component">The component containing configuration.</param>
        /// <param name="parentComponent">The parent component for icon fallback.</param>
        /// <param name="iconMode">The icon application mode.</param>
        void Process(RibbonItem ribbonItem, ParsedComponent component, ParsedComponent? parentComponent, IconMode iconMode);

        /// <summary>
        /// Applies highlight to a ribbon item based on the component's Highlight property.
        /// </summary>
        /// <param name="ribbonItem">The ribbon item to highlight.</param>
        /// <param name="component">The component containing highlight configuration.</param>
        void ApplyHighlight(RibbonItem ribbonItem, ParsedComponent component);

        /// <summary>
        /// Gets the button text with config script indicator if applicable.
        /// Used when creating button data before adding to ribbon.
        /// </summary>
        /// <param name="component">The component to get text for.</param>
        /// <returns>The button text, with dot indicator if applicable.</returns>
        string GetButtonText(ParsedComponent component);
    }
}
