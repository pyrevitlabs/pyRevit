#nullable enable
using Autodesk.Revit.UI;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Tooltips
{
    /// <summary>
    /// Interface for managing tooltip creation and media handling for Revit ribbon items.
    /// </summary>
    public interface ITooltipManager
    {
        /// <summary>
        /// Builds a tooltip string with bundle metadata.
        /// The tooltip includes the original tooltip text, bundle name with type, and author(s).
        /// </summary>
        /// <param name="component">The component to build tooltip for.</param>
        /// <returns>The formatted tooltip string with bundle metadata.</returns>
        string BuildButtonTooltip(ParsedComponent component);

        /// <summary>
        /// Applies tooltip text and media (image or video) to a RibbonItem.
        /// </summary>
        /// <param name="ribbonItem">The Revit ribbon item to set tooltip on.</param>
        /// <param name="component">The component containing tooltip and media file info.</param>
        void ApplyTooltip(RibbonItem ribbonItem, ParsedComponent component);

        /// <summary>
        /// Sets tooltip media (image or video) on a RibbonItem using AdWindows API.
        /// </summary>
        /// <param name="ribbonItem">The Revit ribbon item to set media on.</param>
        /// <param name="component">The component containing media file info.</param>
        void SetTooltipMedia(RibbonItem ribbonItem, ParsedComponent component);

        /// <summary>
        /// Gets the button text with config script indicator if applicable.
        /// </summary>
        /// <param name="component">The component to get text for.</param>
        /// <returns>The button text, with dot indicator if applicable.</returns>
        string GetButtonTextWithConfigIndicator(ParsedComponent component);
    }
}
