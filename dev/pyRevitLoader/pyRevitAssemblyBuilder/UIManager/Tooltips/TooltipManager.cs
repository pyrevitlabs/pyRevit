#nullable enable
using System;
using System.Windows.Controls;
using System.Windows.Media.Imaging;
using Autodesk.Revit.UI;
using Autodesk.Windows;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitExtensionParser;
using RibbonItem = Autodesk.Revit.UI.RibbonItem;

namespace pyRevitAssemblyBuilder.UIManager.Tooltips
{
    /// <summary>
    /// Manages tooltip creation and media handling for Revit ribbon items.
    /// Consolidates all tooltip-related functionality including text building and media (image/video) support.
    /// </summary>
    public class TooltipManager : ITooltipManager
    {
        private readonly ILogger _logger;

        /// <summary>
        /// Initializes a new instance of the <see cref="TooltipManager"/> class.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        public TooltipManager(ILogger logger)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        }

        /// <inheritdoc/>
        public string BuildButtonTooltip(ParsedComponent component)
        {
            var tooltip = string.Empty;

            // Add localized tooltip if present
            var localizedTooltip = ExtensionParser.GetComponentTooltip(component);
            if (!string.IsNullOrEmpty(localizedTooltip))
            {
                tooltip = localizedTooltip + "\n\n";
            }

            // Add Bundle Name with type (matching Python: button.name, button.type_id.replace(".", ""))
            var typeId = component.Type.ToExtension().Replace(".", "");
            tooltip += $"Bundle Name:\n{component.Name} ({typeId})";

            // Add Author(s) if present
            if (!string.IsNullOrEmpty(component.Author))
            {
                tooltip += $"\n\nAuthor(s):\n{component.Author}";
            }

            return tooltip;
        }

        /// <inheritdoc/>
        public void ApplyTooltip(RibbonItem ribbonItem, ParsedComponent component)
        {
            // Set the text tooltip
            ribbonItem.ToolTip = BuildButtonTooltip(component);
            
            // Set media if available
            SetTooltipMedia(ribbonItem, component);
        }

        /// <inheritdoc/>
        public void SetTooltipMedia(RibbonItem ribbonItem, ParsedComponent component)
        {
            if (!component.HasMediaFile || string.IsNullOrEmpty(component.MediaFile))
                return;

            try
            {
                var extension = System.IO.Path.GetExtension(component.MediaFile).ToLowerInvariant();
                
                if (extension == UIManagerConstants.TOOLTIP_IMAGE_FORMAT)
                {
                    SetTooltipImage(ribbonItem, component);
                }
                else if (extension == UIManagerConstants.TOOLTIP_VIDEO_FORMAT_MP4 || 
                         extension == UIManagerConstants.TOOLTIP_VIDEO_FORMAT_SWF)
                {
                    SetTooltipVideo(ribbonItem, component);
                }
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to set tooltip media for '{component.DisplayName}'. Exception: {ex.Message}");
            }
        }

        /// <inheritdoc/>
        public string GetButtonTextWithConfigIndicator(ParsedComponent component)
        {
            // Use centralized localized title method
            var baseText = ExtensionParser.GetComponentTitle(component);
            
            // Add dot indicator if component has a separate config script
            if (component.HasConfigScript)
            {
                return $"{baseText} {UIManagerConstants.ConfigScriptTitlePostfix}";
            }
            
            return baseText;
        }

        /// <summary>
        /// Sets a tooltip image on a RibbonItem using AdWindows API.
        /// Matches the Python set_tooltip_image implementation.
        /// </summary>
        private void SetTooltipImage(RibbonItem ribbonItem, ParsedComponent component)
        {
            try
            {
                // Get AdWindows object using reflection-like approach
                var adWindowsRibbonItem = AdWindowsHelper.GetAdWindowsRibbonItem(ribbonItem, _logger);
                if (adWindowsRibbonItem == null)
                    return;

                // Get button title for tooltip
                var buttonTitle = GetButtonTextWithConfigIndicator(component);
                var existingTooltip = ribbonItem.ToolTip as string;

                // Create RibbonToolTip
                var ribbonToolTip = new RibbonToolTip
                {
                    Title = buttonTitle,
                    Content = existingTooltip
                };

                // Create StackPanel with image
                var stackPanel = new StackPanel();
                var image = new Image();
                
                // Load the image
                var bitmapImage = new BitmapImage();
                bitmapImage.BeginInit();
                bitmapImage.UriSource = new Uri(component.MediaFile);
                bitmapImage.CacheOption = BitmapCacheOption.OnLoad;
                bitmapImage.EndInit();
                bitmapImage.Freeze();
                
                image.Source = bitmapImage;
                stackPanel.Children.Add(image);

                ribbonToolTip.ExpandedContent = stackPanel;
                adWindowsRibbonItem.ToolTip = ribbonToolTip;
                
                // Resolve the tooltip to apply changes
                AdWindowsHelper.ResolveToolTip(adWindowsRibbonItem);
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to set tooltip image for '{component.DisplayName}'. Exception: {ex.Message}");
            }
        }

        /// <summary>
        /// Sets a tooltip video on a RibbonItem using AdWindows API.
        /// Matches the Python set_tooltip_video implementation.
        /// Video loops automatically when it ends.
        /// </summary>
        private void SetTooltipVideo(RibbonItem ribbonItem, ParsedComponent component)
        {
            try
            {
                // Get AdWindows object
                var adWindowsRibbonItem = AdWindowsHelper.GetAdWindowsRibbonItem(ribbonItem, _logger);
                if (adWindowsRibbonItem == null)
                    return;

                // Get button title for tooltip
                var buttonTitle = GetButtonTextWithConfigIndicator(component);
                var existingTooltip = ribbonItem.ToolTip as string;

                // Create RibbonToolTip
                var ribbonToolTip = new RibbonToolTip
                {
                    Title = buttonTitle,
                    Content = existingTooltip
                };

                // Create StackPanel with MediaElement (video player)
                var stackPanel = new StackPanel();
                var mediaElement = new MediaElement
                {
                    Source = new Uri(component.MediaFile),
                    LoadedBehavior = MediaState.Manual,
                    UnloadedBehavior = MediaState.Manual
                };

                // Set up event handlers for looping and auto-play
                mediaElement.MediaEnded += (sender, args) =>
                {
                    var me = sender as MediaElement;
                    if (me != null)
                    {
                        me.Position = TimeSpan.Zero;
                        me.Play();
                    }
                };

                mediaElement.Loaded += (sender, args) =>
                {
                    var me = sender as MediaElement;
                    me?.Play();
                };

                stackPanel.Children.Add(mediaElement);

                ribbonToolTip.ExpandedContent = stackPanel;
                adWindowsRibbonItem.ToolTip = ribbonToolTip;
                
                // Resolve the tooltip to apply changes
                AdWindowsHelper.ResolveToolTip(adWindowsRibbonItem);
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to set tooltip video for '{component.DisplayName}'. Exception: {ex.Message}");
            }
        }
    }
}
