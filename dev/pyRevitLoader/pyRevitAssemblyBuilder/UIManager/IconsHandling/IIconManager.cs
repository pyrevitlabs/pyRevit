using System.Windows.Media.Imaging;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Icons
{
    /// <summary>
    /// Interface for managing icon loading, caching, and application to Revit UI elements.
    /// </summary>
    public interface IIconManager
    {
        /// <summary>
        /// Applies icons to a Revit RibbonItem (PushButton, PulldownButton, SplitButton, etc.)
        /// with theme awareness and optional parent fallback.
        /// </summary>
        /// <param name="item">The Revit ribbon item to apply icons to.</param>
        /// <param name="component">The component containing icon definitions.</param>
        /// <param name="parentComponent">Optional parent component for icon fallback.</param>
        /// <param name="iconMode">The mode determining which icon sizes to apply.</param>
        void ApplyIcon(object item, ParsedComponent component, ParsedComponent parentComponent = null, IconMode iconMode = IconMode.LargeAndSmall);

        /// <summary>
        /// Loads a BitmapSource from an image file path with automatic resizing.
        /// </summary>
        /// <param name="imagePath">The path to the image file.</param>
        /// <param name="targetSize">The target size for the icon (0 for original size).</param>
        /// <returns>The loaded BitmapSource, or null if loading fails.</returns>
        BitmapSource LoadBitmapSource(string imagePath, int targetSize = 0);

        /// <summary>
        /// Gets the best icon for a specific size with theme preference.
        /// </summary>
        /// <param name="component">The component containing icons.</param>
        /// <param name="preferredSize">The preferred icon size.</param>
        /// <returns>The best matching ComponentIcon, or null if none available.</returns>
        ComponentIcon GetBestIconForSize(ParsedComponent component, int preferredSize);

        /// <summary>
        /// Pre-loads icon file bytes for an extension in parallel to warm the OS file cache.
        /// </summary>
        /// <param name="extension">The extension whose icons should be pre-loaded.</param>
        void PreloadExtensionIcons(ParsedExtension extension);

        /// <summary>
        /// Clears the bitmap cache.
        /// </summary>
        void ClearCache();
    }

    /// <summary>
    /// Specifies which icon sizes should be applied to a ribbon item.
    /// </summary>
    public enum IconMode
    {
        /// <summary>
        /// Apply both large (32x32) and small (16x16) icons.
        /// </summary>
        LargeAndSmall,

        /// <summary>
        /// Apply only the small (16x16) icon.
        /// </summary>
        SmallOnly,

        /// <summary>
        /// Apply only the small icon to both Image and LargeImage properties.
        /// Used for pulldown sub-buttons where both properties need the same small icon.
        /// </summary>
        SmallToBoth
    }
}
