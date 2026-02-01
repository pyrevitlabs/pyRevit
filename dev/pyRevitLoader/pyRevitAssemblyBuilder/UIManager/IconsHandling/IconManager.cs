using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Icons
{
    /// <summary>
    /// Manages icon loading, caching, and application to Revit UI elements.
    /// Consolidates all icon-related functionality with theme awareness.
    /// </summary>
    public class IconManager : IIconManager
    {
        private readonly ILogger _logger;
        private readonly RevitThemeDetector _themeDetector;
        private readonly BitmapCache _cache;

        /// <summary>
        /// Initializes a new instance of the <see cref="IconManager"/> class.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        public IconManager(ILogger logger)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _themeDetector = new RevitThemeDetector(logger);
            _cache = new BitmapCache();
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="IconManager"/> class with a custom theme detector.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <param name="themeDetector">The theme detector for dark/light mode awareness.</param>
        public IconManager(ILogger logger, RevitThemeDetector themeDetector)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _themeDetector = themeDetector ?? throw new ArgumentNullException(nameof(themeDetector));
            _cache = new BitmapCache();
        }

        /// <inheritdoc/>
        public void ApplyIcon(object item, ParsedComponent component, ParsedComponent parentComponent = null, IconMode iconMode = IconMode.LargeAndSmall)
        {
            // If the component doesn't have icons, try to use parent's icons
            var sourceComponent = component;
            if (!component.HasValidIcons)
            {
                if (parentComponent != null && parentComponent.HasValidIcons)
                {
                    sourceComponent = parentComponent;
                }
                else
                {
                    return;
                }
            }

            try
            {
                var isDarkTheme = _themeDetector.IsDarkTheme();
                var largeIcon = GetBestIconForSizeWithTheme(sourceComponent, UIManagerConstants.ICON_LARGE, isDarkTheme);
                var smallIcon = GetBestIconForSizeWithTheme(sourceComponent, UIManagerConstants.ICON_SMALL, isDarkTheme);

                switch (iconMode)
                {
                    case IconMode.LargeAndSmall:
                        ApplyLargeAndSmallIcons(item, largeIcon, smallIcon, sourceComponent.DisplayName);
                        break;

                    case IconMode.SmallOnly:
                        ApplySmallIconOnly(item, smallIcon, sourceComponent.DisplayName);
                        break;

                    case IconMode.SmallToBoth:
                        ApplySmallIconToBoth(item, smallIcon, sourceComponent.DisplayName);
                        break;
                }
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to apply icon to '{component.DisplayName}'. Exception: {ex.Message}");
            }
        }

        /// <summary>
        /// Applies both large and small icons to the item.
        /// </summary>
        private void ApplyLargeAndSmallIcons(object item, ComponentIcon largeIcon, ComponentIcon smallIcon, string displayName)
        {
            BitmapSource largeBitmap = null;
            BitmapSource smallBitmap = null;

            if (largeIcon != null)
            {
                largeBitmap = LoadBitmapSource(largeIcon.FilePath, UIManagerConstants.ICON_LARGE);
            }

            if (smallIcon != null)
            {
                smallBitmap = LoadBitmapSource(smallIcon.FilePath, UIManagerConstants.ICON_SMALL);
            }

            SetIconsOnItem(item, largeBitmap, smallBitmap);
        }

        /// <summary>
        /// Applies only the small icon to the item.
        /// </summary>
        private void ApplySmallIconOnly(object item, ComponentIcon smallIcon, string displayName)
        {
            if (smallIcon == null)
                return;

            var smallBitmap = LoadBitmapSource(smallIcon.FilePath, UIManagerConstants.ICON_SMALL);
            SetIconsOnItem(item, null, smallBitmap);
        }

        /// <summary>
        /// Applies the small icon to both Image and LargeImage properties.
        /// Used for pulldown sub-buttons where both properties need the same small icon.
        /// </summary>
        private void ApplySmallIconToBoth(object item, ComponentIcon smallIcon, string displayName)
        {
            if (smallIcon == null)
                return;

            var smallBitmap = LoadBitmapSource(smallIcon.FilePath, UIManagerConstants.ICON_SMALL);
            if (smallBitmap != null)
            {
                SetIconsOnItem(item, smallBitmap, smallBitmap);
            }
        }

        /// <summary>
        /// Sets icons on the ribbon item using dynamic dispatch based on item type.
        /// </summary>
        private void SetIconsOnItem(object item, BitmapSource largeImage, BitmapSource smallImage)
        {
            switch (item)
            {
                // SplitButton must come before PulldownButton because SplitButton derives from PulldownButton
                case SplitButton splitButton:
                    if (largeImage != null) splitButton.LargeImage = largeImage;
                    if (smallImage != null) splitButton.Image = smallImage;
                    break;

                case PulldownButton pulldownButton:
                    if (largeImage != null) pulldownButton.LargeImage = largeImage;
                    if (smallImage != null) pulldownButton.Image = smallImage;
                    break;

                case PushButton pushButton:
                    if (largeImage != null) pushButton.LargeImage = largeImage;
                    if (smallImage != null) pushButton.Image = smallImage;
                    break;

                case ComboBox comboBox:
                    // ComboBox only has Image property (small icon)
                    if (smallImage != null) comboBox.Image = smallImage;
                    break;

                case Autodesk.Revit.UI.ComboBoxMember comboBoxMember:
                    // ComboBoxMember only has Image property (small icon)
                    if (smallImage != null) comboBoxMember.Image = smallImage;
                    break;

                default:
                    _logger.Debug($"Unknown ribbon item type: {item?.GetType().Name ?? "null"}");
                    break;
            }
        }

        /// <inheritdoc/>
        public BitmapSource LoadBitmapSource(string imagePath, int targetSize = 0)
        {
            if (string.IsNullOrEmpty(imagePath) || !File.Exists(imagePath))
                return null;

            // Check cache first
            if (_cache.TryGet(imagePath, targetSize, out var cachedBitmap))
                return cachedBitmap;

            try
            {
                var bitmap = new BitmapImage();
                bitmap.BeginInit();
                bitmap.UriSource = new Uri(imagePath, UriKind.Absolute);
                bitmap.CacheOption = BitmapCacheOption.OnLoad;

                // If target size is specified, resize the image
                if (targetSize > 0)
                {
                    bitmap.DecodePixelWidth = targetSize;
                    bitmap.DecodePixelHeight = targetSize;
                }

                bitmap.EndInit();
                bitmap.Freeze(); // Make it thread-safe for cross-thread access

                // Ensure proper DPI for Revit (96 DPI is standard)
                var result = EnsureProperDpi(bitmap, targetSize);

                // Cache the result
                if (result != null)
                    _cache.Set(imagePath, targetSize, result);

                return result;
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to load bitmap source from '{imagePath}'. Exception: {ex.Message}");
                return null;
            }
        }

        /// <inheritdoc/>
        public ComponentIcon GetBestIconForSize(ParsedComponent component, int preferredSize)
        {
            var isDarkTheme = _themeDetector.IsDarkTheme();
            return GetBestIconForSizeWithTheme(component, preferredSize, isDarkTheme);
        }

        /// <summary>
        /// Gets the best icon for a specific size with theme preference.
        /// Only icon.png (Standard) and icon.dark.png (DarkStandard) are supported.
        /// </summary>
        private ComponentIcon GetBestIconForSizeWithTheme(ParsedComponent component, int preferredSize, bool isDarkTheme)
        {
            if (!component.HasValidIcons)
                return null;

            // Return the appropriate icon based on theme preference
            if (isDarkTheme)
            {
                // In dark theme, prefer dark icon, fall back to light
                var darkIcon = component.Icons.PrimaryDarkIcon;
                if (darkIcon?.IsValid == true)
                    return darkIcon;
            }

            // Use light icon (either because we're in light theme, or as fallback)
            var lightIcon = component.Icons.PrimaryIcon;
            if (lightIcon?.IsValid == true)
                return lightIcon;

            // Final fallback - use any valid icon
            return component.Icons.FirstOrDefault(i => i.IsValid);
        }

        /// <inheritdoc/>
        public void PreloadExtensionIcons(ParsedExtension extension)
        {
            try
            {
                var isDarkTheme = _themeDetector.IsDarkTheme();

                // Collect all unique icon paths we'll need
                var iconPaths = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

                CollectIconPaths(extension.Children, iconPaths, isDarkTheme);

                if (iconPaths.Count == 0)
                    return;

                _logger.Debug($"Pre-reading {iconPaths.Count} icon files for {extension.Name}...");

                // Read all icon file bytes in parallel to warm OS file cache
                // This makes subsequent bitmap loading much faster
                Parallel.ForEach(iconPaths, new ParallelOptions { MaxDegreeOfParallelism = Environment.ProcessorCount },
                    iconPath =>
                    {
                        try
                        {
                            // Just read the file to warm the OS file cache
                            // The actual bitmap loading will use BitmapImage with UriSource
                            // which benefits from the warm cache
                            File.ReadAllBytes(iconPath);
                        }
                        catch
                        {
                            // Ignore read errors - bitmap loading will handle them
                        }
                    });

                _logger.Debug($"Pre-read {iconPaths.Count} icon files for {extension.Name}");
            }
            catch (Exception ex)
            {
                _logger.Debug($"Error pre-reading icons: {ex.Message}");
                // Continue without pre-loading - icons will load on demand
            }
        }

        /// <summary>
        /// Recursively collects icon paths from components.
        /// </summary>
        private void CollectIconPaths(IEnumerable<ParsedComponent> components, HashSet<string> iconPaths, bool isDarkTheme)
        {
            if (components == null)
                return;

            foreach (var component in components)
            {
                if (component == null)
                    continue;

                // Get the best icons for this component
                var largeIcon = GetBestIconForSizeWithTheme(component, UIManagerConstants.ICON_LARGE, isDarkTheme);
                var smallIcon = GetBestIconForSizeWithTheme(component, UIManagerConstants.ICON_SMALL, isDarkTheme);

                if (largeIcon != null && !string.IsNullOrEmpty(largeIcon.FilePath) && File.Exists(largeIcon.FilePath))
                {
                    iconPaths.Add(largeIcon.FilePath);
                }
                if (smallIcon != null && !string.IsNullOrEmpty(smallIcon.FilePath) && File.Exists(smallIcon.FilePath))
                {
                    iconPaths.Add(smallIcon.FilePath);
                }

                // Recurse into children
                CollectIconPaths(component.Children, iconPaths, isDarkTheme);
            }
        }

        /// <inheritdoc/>
        public void ClearCache()
        {
            _cache.Clear();
        }

        /// <summary>
        /// Ensures the bitmap has proper DPI and size for Revit UI.
        /// </summary>
        private BitmapSource EnsureProperDpi(BitmapSource source, int targetSize)
        {
            if (source == null) return null;

            try
            {
                const double targetDpi = 96.0;

                // Check if we need to adjust DPI or size
                bool needsDpiAdjustment = Math.Abs(source.DpiX - targetDpi) > 1.0 || Math.Abs(source.DpiY - targetDpi) > 1.0;
                bool needsSizeAdjustment = targetSize > 0 && (source.PixelWidth != targetSize || source.PixelHeight != targetSize);

                if (!needsDpiAdjustment && !needsSizeAdjustment)
                {
                    return source;
                }

                // Calculate the target dimensions
                int width = targetSize > 0 ? targetSize : source.PixelWidth;
                int height = targetSize > 0 ? targetSize : source.PixelHeight;

                // Create a properly sized and DPI-adjusted bitmap
                var targetBitmap = new RenderTargetBitmap(
                    width,
                    height,
                    targetDpi,
                    targetDpi,
                    PixelFormats.Pbgra32);

                var visual = new DrawingVisual();
                using (var context = visual.RenderOpen())
                {
                    // Draw the source image scaled to fit the target size
                    context.DrawImage(source, new Rect(0, 0, width, height));
                }

                targetBitmap.Render(visual);
                targetBitmap.Freeze();

                return targetBitmap;
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to adjust DPI for bitmap source. Exception: {ex.Message}");
                return source; // Return original if adjustment fails
            }
        }
    }
}
