using System;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using Autodesk.Windows;
using RibbonPanel = Autodesk.Revit.UI.RibbonPanel;
using RibbonButton = Autodesk.Windows.RibbonButton;
using RibbonItem = Autodesk.Revit.UI.RibbonItem;
using static pyRevitExtensionParser.ExtensionParser;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class UIManagerService
    {
        private readonly UIApplication _uiApp;

        public UIManagerService(UIApplication uiApp)
        {
            _uiApp = uiApp;
        }

        public void BuildUI(ParsedExtension extension, ExtensionAssemblyInfo assemblyInfo)
        {
            if (extension?.Children == null)
                return;

            foreach (var component in extension.Children)
                RecursivelyBuildUI(component, null, null, extension.Name, assemblyInfo);
        }

        private void RecursivelyBuildUI(
            ParsedComponent component,
            ParsedComponent parentComponent,
            RibbonPanel parentPanel,
            string tabName,
            ExtensionAssemblyInfo assemblyInfo)
        {
            switch (component.Type)
            {
                case CommandComponentType.Tab:
                    // Use Title from bundle.yaml if available, otherwise fall back to DisplayName
                    var tabText = !string.IsNullOrEmpty(component.Title) ? component.Title : component.DisplayName;
                    try { _uiApp.CreateRibbonTab(tabText); } catch { }
                    foreach (var child in component.Children ?? Enumerable.Empty<ParsedComponent>())
                        RecursivelyBuildUI(child, component, null, tabText, assemblyInfo);
                    break;

                case CommandComponentType.Panel:
                    // Use Title from bundle.yaml if available, otherwise fall back to DisplayName
                    var panelText = !string.IsNullOrEmpty(component.Title) ? component.Title : component.DisplayName;
                    var panel = _uiApp.GetRibbonPanels(tabName)
                        .FirstOrDefault(p => p.Name == panelText)
                        ?? _uiApp.CreateRibbonPanel(tabName, panelText);
                    foreach (var child in component.Children ?? Enumerable.Empty<ParsedComponent>())
                        RecursivelyBuildUI(child, component, panel, tabName, assemblyInfo);
                    break;

                default:
                    if (component.HasSlideout)
                    {
                        EnsureSlideOutApplied(parentComponent, parentPanel);
                    }
                    HandleComponentBuilding(component, parentPanel, tabName, assemblyInfo);
                    break;
            }
        }

        private void EnsureSlideOutApplied(ParsedComponent parentComponent,RibbonPanel parentPanel)
        {
            if (parentPanel != null && parentComponent.Type == CommandComponentType.Panel)
            {
                try { parentPanel.AddSlideOut(); } catch { }
            }
        }

        private void HandleComponentBuilding(
            ParsedComponent component,
            RibbonPanel parentPanel,
            string tabName,
            ExtensionAssemblyInfo assemblyInfo)
        {
            switch (component.Type)
            {
                case CommandComponentType.Stack:
                    BuildStack(component, parentPanel, assemblyInfo);
                    break;

                        // Now post-process pulldowns to add nested pushbuttons
                        if (stackedItems != null)
                        {
                            for (int i = 0; i < stackedItems.Count; i++)
                            {
                                var ribbonItem = stackedItems[i];
                                var origComponent = originalItems[i];

                                if (ribbonItem is PulldownButton pdBtn)
                                {
                                    foreach (var child in origComponent.Children ?? Enumerable.Empty<object>())
                                    {
                                        if (sub.Type == CommandComponentType.PushButton)
                                        {
                                            var subData = CreatePushButton(sub, assemblyInfo);
                                            pdBtn.AddPushButton(subData);
                                        }
                                    }
                                }
                            }
                        }
                    }
                    break;

                case CommandComponentType.PushButton:
                case CommandComponentType.SmartButton:
                    var pbData = CreatePushButton(component, assemblyInfo);
                    var btn = parentPanel.AddItem(pbData) as PushButton;
                    if (btn != null)
                    {
                        ApplyIconToPushButton(btn, component);
                        if (!string.IsNullOrEmpty(component.Tooltip))
                            btn.ToolTip = component.Tooltip;
                    }
                    break;

                case CommandComponentType.PullDown:
                    CreatePulldown(component, parentPanel, tabName, assemblyInfo, true);
                    break;

                case CommandComponentType.SplitButton:
                case CommandComponentType.SplitPushButton:
                    // Use Title from bundle.yaml if available, otherwise fall back to DisplayName
                    var splitButtonText = !string.IsNullOrEmpty(component.Title) ? component.Title : component.DisplayName;
                    var splitData = new SplitButtonData(component.UniqueId, splitButtonText);
                    var splitBtn = parentPanel.AddItem(splitData) as SplitButton;
                    if (splitBtn != null)
                    {
                        // Apply icon to split button
                        ApplyIconToSplitButton(splitBtn, component);
                        
                        // Assign tooltip to the split button itself
                        if (!string.IsNullOrEmpty(component.Tooltip))
                            splitBtn.ToolTip = component.Tooltip;

                        foreach (var sub in component.Children ?? Enumerable.Empty<ParsedComponent>())
                        {
                            if (sub.Type == CommandComponentType.PushButton)
                            {
                                var subBtn = splitBtn.AddPushButton(CreatePushButton(sub, assemblyInfo));
                                if (subBtn != null)
                                {
                                    ApplyIconToPushButton(subBtn, sub);
                                    if (!string.IsNullOrEmpty(sub.Tooltip))
                                        subBtn.ToolTip = sub.Tooltip;
                                }
                            }
                        }
                    }
                    break;
            }
        }

        private void ModifyToPanelButton(string tabName, RibbonPanel parentPanel, PushButton panelBtn)
        {
            try
            {
                var adwTab = ComponentManager
                    .Ribbon
                    .Tabs
                    .FirstOrDefault(t => t.Id == tabName);
                var adwPanel = adwTab
                    .Panels
                    .First(p => p.Source.Title == parentPanel.Name);
                var adwBtn = adwPanel
                    .Source
                    .Items
                    .First(i => i.AutomationName == panelBtn.ItemText);
                adwPanel.Source.Items.Remove(adwBtn);
                adwPanel.Source.DialogLauncher = (RibbonButton)adwBtn;
            }
            catch (Exception ex)
            {
                Console.WriteLine("Failed modify PushButton to PanelButton");
                Console.WriteLine(ex.Message);
            }
        }

        private void BuildStack(
            ParsedComponent component,
            RibbonPanel parentPanel,
            ExtensionAssemblyInfo assemblyInfo)
        {
            var itemDataList = new List<RibbonItemData>();
            var originalItems = new List<ParsedComponent>();

            foreach (var child in component.Children ?? Enumerable.Empty<ParsedComponent>())
            {
                if (child.Type == CommandComponentType.PushButton ||
                    child.Type == CommandComponentType.SmartButton)
                {
                    itemDataList.Add(CreatePushButton(child, assemblyInfo));
                    originalItems.Add(child);
                }
                else if (child.Type == CommandComponentType.PullDown)
                {
                    // Use Title from bundle.yaml if available, otherwise fall back to DisplayName
                    var pulldownText = !string.IsNullOrEmpty(child.Title) ? child.Title : child.DisplayName;
                    var pdData = new PulldownButtonData(child.UniqueId, pulldownText);
                    itemDataList.Add(pdData);
                    originalItems.Add(child);
                }
            }

            if (itemDataList.Count >= 2)
            {
                IList<RibbonItem> stackedItems = null;
                if (itemDataList.Count == 2)
                    stackedItems = parentPanel.AddStackedItems(itemDataList[0], itemDataList[1]);
                else
                    stackedItems = parentPanel.AddStackedItems(itemDataList[0], itemDataList[1], itemDataList[2]);

                if (stackedItems != null)
                {
                    for (int i = 0; i < stackedItems.Count; i++)
                    {
                        var ribbonItem = stackedItems[i];
                        var origComponent = originalItems[i];
                        
                        // Apply icons and tooltips to push buttons in stack
                        if (ribbonItem is PushButton pushBtn)
                        {
                            ApplyIconToPushButton(pushBtn, origComponent);
                            if (!string.IsNullOrEmpty(origComponent.Tooltip))
                                pushBtn.ToolTip = origComponent.Tooltip;
                        }
                        
                        if (ribbonItem is PulldownButton pdBtn)
                        {
                            // Apply icon and tooltip to the pulldown button itself in stack
                            ApplyIconToPulldownButton(pdBtn, origComponent);
                            if (!string.IsNullOrEmpty(origComponent.Tooltip))
                                pdBtn.ToolTip = origComponent.Tooltip;

                            foreach (var sub in origComponent.Children ?? Enumerable.Empty<ParsedComponent>())
                            {
                                if (sub.Type == CommandComponentType.PushButton)
                                {
                                    var subBtn = pdBtn.AddPushButton(CreatePushButton(sub, assemblyInfo));
                                    if (subBtn != null)
                                    {
                                        ApplyIconToPushButton(subBtn, sub);
                                        if (!string.IsNullOrEmpty(sub.Tooltip))
                                            subBtn.ToolTip = sub.Tooltip;
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        private PulldownButtonData CreatePulldown(
            ParsedComponent component,
            RibbonPanel parentPanel,
            string tabName,
            ExtensionAssemblyInfo assemblyInfo,
            bool addToPanel)
        {
            // Use Title from bundle.yaml if available, otherwise fall back to DisplayName
            var pulldownText = !string.IsNullOrEmpty(component.Title) ? component.Title : component.DisplayName;
            var pdData = new PulldownButtonData(component.UniqueId, pulldownText);
            if (!addToPanel) return pdData;

            var pdBtn = parentPanel.AddItem(pdData) as PulldownButton;
            if (pdBtn == null) return null;

            // Apply icon and tooltip to the pulldown button itself
            ApplyIconToPulldownButton(pdBtn, component);
            if (!string.IsNullOrEmpty(component.Tooltip))
                pdBtn.ToolTip = component.Tooltip;

            foreach (var sub in component.Children ?? Enumerable.Empty<ParsedComponent>())
            {
                if (sub.Type == CommandComponentType.PushButton)
                {
                    var subBtn = pdBtn.AddPushButton(CreatePushButton(sub, assemblyInfo));
                    if (subBtn != null)
                    {
                        ApplyIconToPushButton(subBtn, sub);
                        if (!string.IsNullOrEmpty(sub.Tooltip))
                            subBtn.ToolTip = sub.Tooltip;
                    }
                }
            }
            return pdData;
        }

        private PushButtonData CreatePushButton(ParsedComponent component, ExtensionAssemblyInfo assemblyInfo)
        {
            // Use Title from bundle.yaml if available, otherwise fall back to DisplayName
            var buttonText = !string.IsNullOrEmpty(component.Title) ? component.Title : component.DisplayName;
            
            return new PushButtonData(
                component.UniqueId,
                buttonText,
                assemblyInfo.Location,
                component.UniqueId);
        }

        #region Icon Management

        /// <summary>
        /// Applies icons from the component to a PushButton
        /// </summary>
        private void ApplyIconToPushButton(PushButton button, ParsedComponent component)
        {
            if (!component.HasValidIcons)
                return;

            try
            {
                // Get the best icons for large and small sizes
                var largeIcon = GetBestIconForSize(component, 32) ?? component.PrimaryIcon;
                var smallIcon = GetBestIconForSize(component, 16) ?? largeIcon;

                if (largeIcon != null)
                {
                    var largeBitmap = LoadBitmapSource(largeIcon.FilePath, 32); // 32x32 for large icons
                    if (largeBitmap != null)
                        button.LargeImage = largeBitmap;
                }

                if (smallIcon != null)
                {
                    var smallBitmap = LoadBitmapSource(smallIcon.FilePath, 16); // 16x16 for small icons
                    if (smallBitmap != null)
                        button.Image = smallBitmap;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Failed to apply icon to PushButton {component.DisplayName}: {ex.Message}");
            }
        }

        /// <summary>
        /// Applies icons from the component to a PulldownButton
        /// </summary>
        private void ApplyIconToPulldownButton(PulldownButton button, ParsedComponent component)
        {
            if (!component.HasValidIcons)
                return;

            try
            {
                // Get the best icons for large and small sizes
                var largeIcon = GetBestIconForSize(component, 32) ?? component.PrimaryIcon;
                var smallIcon = GetBestIconForSize(component, 16) ?? largeIcon;

                if (largeIcon != null)
                {
                    var largeBitmap = LoadBitmapSource(largeIcon.FilePath, 32); // 32x32 for large icons
                    if (largeBitmap != null)
                        button.LargeImage = largeBitmap;
                }

                if (smallIcon != null)
                {
                    var smallBitmap = LoadBitmapSource(smallIcon.FilePath, 16); // 16x16 for small icons
                    if (smallBitmap != null)
                        button.Image = smallBitmap;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Failed to apply icon to PulldownButton {component.DisplayName}: {ex.Message}");
            }
        }

        /// <summary>
        /// Applies icons from the component to a SplitButton
        /// </summary>
        private void ApplyIconToSplitButton(SplitButton button, ParsedComponent component)
        {
            if (!component.HasValidIcons)
                return;

            try
            {
                // Get the best icons for large and small sizes
                var largeIcon = GetBestIconForSize(component, 32) ?? component.PrimaryIcon;
                var smallIcon = GetBestIconForSize(component, 16) ?? largeIcon;

                if (largeIcon != null)
                {
                    var largeBitmap = LoadBitmapSource(largeIcon.FilePath, 32); // 32x32 for large icons
                    if (largeBitmap != null)
                        button.LargeImage = largeBitmap;
                }

                if (smallIcon != null)
                {
                    var smallBitmap = LoadBitmapSource(smallIcon.FilePath, 16); // 16x16 for small icons
                    if (smallBitmap != null)
                        button.Image = smallBitmap;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Failed to apply icon to SplitButton {component.DisplayName}: {ex.Message}");
            }
        }

        /// <summary>
        /// Gets the best icon for a specific size from the component's icon collection
        /// </summary>
        private ComponentIcon GetBestIconForSize(ParsedComponent component, int preferredSize)
        {
            if (!component.HasValidIcons)
                return null;

            // First try to find an icon with the exact size specification
            var exactSizeIcon = component.Icons.GetBySize(preferredSize);
            if (exactSizeIcon?.IsValid == true)
                return exactSizeIcon;

            // Try to find icons with specific size types
            if (preferredSize <= 16)
            {
                var smallIcon = component.Icons.GetByType(IconType.Size16) ?? 
                               component.Icons.GetByType(IconType.Small);
                if (smallIcon?.IsValid == true)
                    return smallIcon;
            }
            else if (preferredSize <= 32)
            {
                var mediumIcon = component.Icons.GetByType(IconType.Size32) ?? 
                                component.Icons.GetByType(IconType.Standard);
                if (mediumIcon?.IsValid == true)
                    return mediumIcon;
            }
            else
            {
                var largeIcon = component.Icons.GetByType(IconType.Size64) ?? 
                               component.Icons.GetByType(IconType.Large);
                if (largeIcon?.IsValid == true)
                    return largeIcon;
            }

            // Fall back to any valid icon
            return component.Icons.FirstOrDefault(i => i.IsValid);
        }

        /// <summary>
        /// Loads a BitmapSource from an image file path with automatic resizing for Revit UI requirements
        /// </summary>
        private BitmapSource LoadBitmapSource(string imagePath, int targetSize = 0)
        {
            if (string.IsNullOrEmpty(imagePath) || !File.Exists(imagePath))
                return null;

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
                bitmap.Freeze(); // Make it thread-safe

                Console.WriteLine($"Loaded icon: {Path.GetFileName(imagePath)} " +
                                $"Original: {bitmap.PixelWidth}x{bitmap.PixelHeight} " +
                                $"DPI: {bitmap.DpiX:F1}x{bitmap.DpiY:F1} " +
                                $"Target: {targetSize}x{targetSize}");

                // Ensure proper DPI for Revit (96 DPI is standard)
                return EnsureProperDpi(bitmap, targetSize);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Failed to load image from {imagePath}: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Ensures the bitmap has proper DPI and size for Revit UI
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
                    Console.WriteLine($"Icon already at correct size and DPI: {source.PixelWidth}x{source.PixelHeight} @ {source.DpiX:F1} DPI");
                    return source;
                }

                // Calculate the target dimensions
                int width = targetSize > 0 ? targetSize : source.PixelWidth;
                int height = targetSize > 0 ? targetSize : source.PixelHeight;

                Console.WriteLine($"Adjusting icon: {source.PixelWidth}x{source.PixelHeight} @ {source.DpiX:F1} DPI → {width}x{height} @ {targetDpi} DPI");

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
                    context.DrawImage(source, new System.Windows.Rect(0, 0, width, height));
                }

                targetBitmap.Render(visual);
                targetBitmap.Freeze();
                
                Console.WriteLine($"Icon adjusted successfully to {targetBitmap.PixelWidth}x{targetBitmap.PixelHeight} @ {targetBitmap.DpiX:F1} DPI");
                return targetBitmap;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Failed to adjust image DPI/size: {ex.Message}");
                return source; // Return original if adjustment fails
            }
        }

        /// <summary>
        /// Gets the optimal icon sizes for Revit UI based on current DPI settings
        /// </summary>
        private (int smallSize, int largeSize) GetOptimalIconSizes()
        {
            try
            {
                // Get system DPI scaling factor
                var dpiScale = System.Windows.Media.VisualTreeHelper.GetDpi(System.Windows.Application.Current.MainWindow);
                var scaleFactor = dpiScale.DpiScaleX;
                
                // Base sizes for 96 DPI
                int baseSmallSize = 16;
                int baseLargeSize = 32;
                
                // Scale according to system DPI, but keep within reasonable bounds
                int smallSize = Math.Min(32, Math.Max(16, (int)(baseSmallSize * scaleFactor)));
                int largeSize = Math.Min(64, Math.Max(24, (int)(baseLargeSize * scaleFactor)));
                
                return (smallSize, largeSize);
            }
            catch
            {
                // Fallback to standard sizes if DPI detection fails
                return (16, 32);
            }
        }

        /// <summary>
        /// Enhanced icon application that considers system DPI
        /// </summary>
        private void ApplyIconToPushButtonWithDpiAwareness(PushButton button, ParsedComponent component)
        {
            if (!component.HasValidIcons)
                return;

            try
            {
                var (smallSize, largeSize) = GetOptimalIconSizes();
                
                // Get the best icons for the calculated sizes
                var largeIcon = GetBestIconForSize(component, largeSize) ?? component.PrimaryIcon;
                var smallIcon = GetBestIconForSize(component, smallSize) ?? largeIcon;

                if (largeIcon != null)
                {
                    var largeBitmap = LoadBitmapSource(largeIcon.FilePath, largeSize);
                    if (largeBitmap != null)
                        button.LargeImage = largeBitmap;
                }

                if (smallIcon != null)
                {
                    var smallBitmap = LoadBitmapSource(smallIcon.FilePath, smallSize);
                    if (smallBitmap != null)
                        button.Image = smallBitmap;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Failed to apply DPI-aware icon to PushButton {component.DisplayName}: {ex.Message}");
                // Fallback to standard method
                ApplyIconToPushButton(button, component);
            }
        }

        #endregion
    }
}
