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
using Autodesk.Internal.Windows;
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
                case CommandComponentType.Separator:
                    // Add separator to panel or pulldown
                    if (parentPanel != null)
                    {
                        try { parentPanel.AddSeparator(); } catch { }
                    }
                    break;
                    
                case CommandComponentType.Stack:
                    BuildStack(component, parentPanel, assemblyInfo);
                    break;
                case CommandComponentType.PanelButton:
                    var panelBtnData = CreatePushButton(component, assemblyInfo);
                    var panelBtn = parentPanel.AddItem(panelBtnData) as PushButton;
                    if (panelBtn != null)
                    {
                        ApplyIconToPushButtonThemeAware(panelBtn, component);
                        if (!string.IsNullOrEmpty(component.Tooltip))
                            panelBtn.ToolTip = component.Tooltip;
                        ApplyHighlightToButton(panelBtn, component);
                        ModifyToPanelButton(tabName, parentPanel, panelBtn);
                    }
                    break;
                case CommandComponentType.PushButton:
                case CommandComponentType.SmartButton:
                case CommandComponentType.UrlButton:
                    var pbData = CreatePushButton(component, assemblyInfo);
                    var btn = parentPanel.AddItem(pbData) as PushButton;
                    if (btn != null)
                    {
                        ApplyIconToPushButtonThemeAware(btn, component);
                        if (!string.IsNullOrEmpty(component.Tooltip))
                            btn.ToolTip = component.Tooltip;
                        ApplyHighlightToButton(btn, component);
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
                        ApplyIconToSplitButtonThemeAware(splitBtn, component);
                        
                        // Assign tooltip to the split button itself
                        if (!string.IsNullOrEmpty(component.Tooltip))
                            splitBtn.ToolTip = component.Tooltip;
                        
                        // Apply highlight to the split button itself
                        ApplyHighlightToButton(splitBtn, component);

                        foreach (var sub in component.Children ?? Enumerable.Empty<ParsedComponent>())
                        {
                            if (sub.Type == CommandComponentType.Separator)
                            {
                                // Add separator to split button
                                try { splitBtn.AddSeparator(); } catch { }
                            }
                            else if (sub.Type == CommandComponentType.PushButton ||
                                     sub.Type == CommandComponentType.UrlButton)
                            {
                                var subBtn = splitBtn.AddPushButton(CreatePushButton(sub, assemblyInfo));
                                if (subBtn != null)
                                {
                                    ApplyIconToPushButtonThemeAware(subBtn, sub);
                                    if (!string.IsNullOrEmpty(sub.Tooltip))
                                        subBtn.ToolTip = sub.Tooltip;
                                    ApplyHighlightToButton(subBtn, sub);
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
                    child.Type == CommandComponentType.SmartButton ||
                    child.Type == CommandComponentType.UrlButton)
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
                            ApplyIconToPushButtonThemeAware(pushBtn, origComponent);
                            if (!string.IsNullOrEmpty(origComponent.Tooltip))
                                pushBtn.ToolTip = origComponent.Tooltip;
                            ApplyHighlightToButton(pushBtn, origComponent);
                        }
                        
                        if (ribbonItem is PulldownButton pdBtn)
                        {
                            // Apply icon and tooltip to the pulldown button itself in stack
                            ApplyIconToPulldownButtonThemeAware(pdBtn, origComponent);
                            if (!string.IsNullOrEmpty(origComponent.Tooltip))
                                pdBtn.ToolTip = origComponent.Tooltip;
                            
                            // Apply highlight to the pulldown button itself in stack
                            ApplyHighlightToButton(pdBtn, origComponent);

                            foreach (var sub in origComponent.Children ?? Enumerable.Empty<ParsedComponent>())
                            {
                                if (sub.Type == CommandComponentType.Separator)
                                {
                                    // Add separator to pulldown in stack
                                    try { pdBtn.AddSeparator(); } catch { }
                                }
                                else if (sub.Type == CommandComponentType.PushButton ||
                                         sub.Type == CommandComponentType.UrlButton)
                                {
                                    var subBtn = pdBtn.AddPushButton(CreatePushButton(sub, assemblyInfo));
                                    if (subBtn != null)
                                    {
                                        ApplyIconToPulldownSubButtonThemeAware(subBtn, sub);
                                        if (!string.IsNullOrEmpty(sub.Tooltip))
                                            subBtn.ToolTip = sub.Tooltip;
                                        ApplyHighlightToButton(subBtn, sub);
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
            ApplyIconToPulldownButtonThemeAware(pdBtn, component);
            if (!string.IsNullOrEmpty(component.Tooltip))
                pdBtn.ToolTip = component.Tooltip;
            
            // Apply highlight to the pulldown button itself
            ApplyHighlightToButton(pdBtn, component);

            foreach (var sub in component.Children ?? Enumerable.Empty<ParsedComponent>())
            {
                if (sub.Type == CommandComponentType.Separator)
                {
                    // Add separator to pulldown
                    try { pdBtn.AddSeparator(); } catch { }
                }
                else if (sub.Type == CommandComponentType.PushButton ||
                         sub.Type == CommandComponentType.UrlButton)
                {
                    var subBtn = pdBtn.AddPushButton(CreatePushButton(sub, assemblyInfo));
                    if (subBtn != null)
                    {
                        ApplyIconToPulldownSubButtonThemeAware(subBtn, sub);
                        if (!string.IsNullOrEmpty(sub.Tooltip))
                            subBtn.ToolTip = sub.Tooltip;
                        ApplyHighlightToButton(subBtn, sub);
                    }
                }
            }
            return pdData;
        }

        private PushButtonData CreatePushButton(ParsedComponent component, ExtensionAssemblyInfo assemblyInfo)
        {
            // Use Title from bundle.yaml if available, otherwise fall back to DisplayName
            var buttonText = !string.IsNullOrEmpty(component.Title) ? component.Title : component.DisplayName;
            
            // Ensure the class name matches what the CommandTypeGenerator creates
            var className = SanitizeClassName(component.UniqueId);
            
            var pushButtonData = new PushButtonData(
                component.UniqueId,
                buttonText,
                assemblyInfo.Location,
                className);

            // Set availability class if context is defined
            if (!string.IsNullOrEmpty(component.Context))
            {
                var availabilityClassName = className + "_avail";
                pushButtonData.AvailabilityClassName = availabilityClassName;
            }

            return pushButtonData;
        }

        /// <summary>
        /// Sanitizes a class name to match the CommandTypeGenerator logic
        /// </summary>
        private static string SanitizeClassName(string name)
        {
            var sb = new System.Text.StringBuilder();
            foreach (char c in name)
                sb.Append(char.IsLetterOrDigit(c) ? c : '_');
            return sb.ToString();
        }

        #region Icon Management

        /// <summary>
        /// Applies icons from the component to a PushButton with theme awareness (primary method)
        /// </summary>
        private void ApplyIconToPushButtonThemeAware(PushButton button, ParsedComponent component)
        {
            if (!component.HasValidIcons)
                return;

            try
            {
                var isDarkTheme = RevitThemeDetector.IsDarkTheme();
                Console.WriteLine($"Applying theme-aware icons to PushButton '{component.DisplayName}' - Current theme: {(isDarkTheme ? "Dark" : "Light")}");
                Console.WriteLine($"Component has {component.Icons.Count} total icons, {component.Icons.DarkIcons.Count()} dark icons, {component.Icons.LightIcons.Count()} light icons");

                // Get the best icons for large and small sizes with theme awareness
                var largeIcon = GetBestIconForSizeWithTheme(component, 32, isDarkTheme);
                var smallIcon = GetBestIconForSizeWithTheme(component, 16, isDarkTheme);

                if (largeIcon != null)
                {
                    var largeBitmap = LoadBitmapSource(largeIcon.FilePath, 32);
                    if (largeBitmap != null)
                    {
                        button.LargeImage = largeBitmap;
                        Console.WriteLine($"Applied large icon: {largeIcon.FileName} (Dark: {largeIcon.IsDark}, Theme: {(isDarkTheme ? "Dark" : "Light")})");
                    }
                }

                if (smallIcon != null)
                {
                    var smallBitmap = LoadBitmapSource(smallIcon.FilePath, 16);
                    if (smallBitmap != null)
                    {
                        button.Image = smallBitmap;
                        Console.WriteLine($"Applied small icon: {smallIcon.FileName} (Dark: {smallIcon.IsDark}, Theme: {(isDarkTheme ? "Dark" : "Light")})");
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Failed to apply theme-aware icon to PushButton {component.DisplayName}: {ex.Message}");
            }
        }

        /// <summary>
        /// Applies icons from the component to a PulldownButton with theme awareness
        /// Uses fixed 16x16 size for pulldown button icons to ensure consistent appearance
        /// </summary>
        private void ApplyIconToPulldownButtonThemeAware(PulldownButton button, ParsedComponent component)
        {
            if (!component.HasValidIcons)
                return;

            try
            {
                var isDarkTheme = RevitThemeDetector.IsDarkTheme();
                Console.WriteLine($"Applying theme-aware icons to PulldownButton '{component.DisplayName}' - Current theme: {(isDarkTheme ? "Dark" : "Light")}");

                // For pulldown buttons, use fixed 16x16 size for consistent appearance
                // This ensures pulldown icons remain at the expected size regardless of DPI scaling
                const int pulldownIconSize = 16;
                
                // Get the best icons for pulldown buttons with fixed 16x16 size
                var smallIcon = GetBestIconForSizeWithTheme(component, pulldownIconSize, isDarkTheme);
                // For the main pulldown button, also get a larger icon for LargeImage property
                var largeIcon = GetBestIconForSizeWithTheme(component, 32, isDarkTheme);

                // Set the large image (32x32) for the main pulldown button
                if (largeIcon != null)
                {
                    var largeBitmap = LoadBitmapSource(largeIcon.FilePath, 32);
                    if (largeBitmap != null)
                    {
                        button.LargeImage = largeBitmap;
                        Console.WriteLine($"Applied pulldown large icon (32x32): {largeIcon.FileName} (Dark: {largeIcon.IsDark}, Theme: {(isDarkTheme ? "Dark" : "Light")})");
                    }
                }

                // Set the small image (16x16) for the main pulldown button
                if (smallIcon != null)
                {
                    var smallBitmap = LoadBitmapSource(smallIcon.FilePath, pulldownIconSize);
                    if (smallBitmap != null)
                    {
                        button.Image = smallBitmap;
                        Console.WriteLine($"Applied pulldown small icon (16x16): {smallIcon.FileName} (Dark: {smallIcon.IsDark}, Theme: {(isDarkTheme ? "Dark" : "Light")})");
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Failed to apply theme-aware icon to PulldownButton {component.DisplayName}: {ex.Message}");
            }
        }

        /// <summary>
        /// Applies icons from the component to a PushButton within a pulldown with theme awareness
        /// Uses fixed 16x16 size for consistency with pulldown button appearance
        /// </summary>
        private void ApplyIconToPulldownSubButtonThemeAware(PushButton button, ParsedComponent component)
        {
            if (!component.HasValidIcons)
                return;

            try
            {
                var isDarkTheme = RevitThemeDetector.IsDarkTheme();
                Console.WriteLine($"Applying theme-aware icons to pulldown sub-button '{component.DisplayName}' - Current theme: {(isDarkTheme ? "Dark" : "Light")}");

                // For pulldown sub-buttons, use fixed 16x16 size for consistency with pulldown appearance
                const int pulldownSubButtonIconSize = 16;
                
                // Get the best icon for pulldown sub-buttons with fixed 16x16 size
                var smallIcon = GetBestIconForSizeWithTheme(component, pulldownSubButtonIconSize, isDarkTheme);

                if (smallIcon != null)
                {
                    var smallBitmap = LoadBitmapSource(smallIcon.FilePath, pulldownSubButtonIconSize);
                    if (smallBitmap != null)
                    {
                        // For pulldown sub-buttons, set both properties to ensure visibility
                        // Some Revit contexts require both Image and LargeImage to be set
                        button.Image = smallBitmap;
                        button.LargeImage = smallBitmap;
                        Console.WriteLine($"Applied pulldown sub-button icon (16x16): {smallIcon.FileName} (Dark: {smallIcon.IsDark}, Theme: {(isDarkTheme ? "Dark" : "Light")})");
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Failed to apply theme-aware icon to pulldown sub-button {component.DisplayName}: {ex.Message}");
            }
        }

        /// <summary>
        /// Applies icons from the component to a SplitButton with theme awareness
        /// </summary>
        private void ApplyIconToSplitButtonThemeAware(SplitButton button, ParsedComponent component)
        {
            if (!component.HasValidIcons)
                return;

            try
            {
                var isDarkTheme = RevitThemeDetector.IsDarkTheme();
                Console.WriteLine($"Applying theme-aware icons to SplitButton '{component.DisplayName}' - Current theme: {(isDarkTheme ? "Dark" : "Light")}");

                // Get the best icons for large and small sizes with theme awareness
                var largeIcon = GetBestIconForSizeWithTheme(component, 32, isDarkTheme);
                var smallIcon = GetBestIconForSizeWithTheme(component, 16, isDarkTheme);

                if (largeIcon != null)
                {
                    var largeBitmap = LoadBitmapSource(largeIcon.FilePath, 32);
                    if (largeBitmap != null)
                    {
                        button.LargeImage = largeBitmap;
                        Console.WriteLine($"Applied large icon to split button: {largeIcon.FileName} (Dark: {largeIcon.IsDark}, Theme: {(isDarkTheme ? "Dark" : "Light")})");
                    }
                }

                if (smallIcon != null)
                {
                    var smallBitmap = LoadBitmapSource(smallIcon.FilePath, 16);
                    if (smallBitmap != null)
                    {
                        button.Image = smallBitmap;
                        Console.WriteLine($"Applied small icon to split button: {smallIcon.FileName} (Dark: {smallIcon.IsDark}, Theme: {(isDarkTheme ? "Dark" : "Light")})");
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Failed to apply theme-aware icon to SplitButton {component.DisplayName}: {ex.Message}");
            }
        }

        /// <summary>
        /// Gets the best icon for a specific size with theme preference - IMPROVED LOGIC
        /// </summary>
        private ComponentIcon GetBestIconForSizeWithTheme(ParsedComponent component, int preferredSize, bool isDarkTheme)
        {
            if (!component.HasValidIcons)
                return null;

            // Step 1: Try to find exact size match with theme preference
            var exactSizeThemeIcon = component.Icons.GetBySize(preferredSize, isDarkTheme);
            if (exactSizeThemeIcon?.IsValid == true)
            {
                Console.WriteLine($"Found exact size+theme icon for size {preferredSize}: {exactSizeThemeIcon.FileName} (Dark: {isDarkTheme})");
                return exactSizeThemeIcon;
            }

            // Step 2: Try to find icon type based on size with theme preference
            ComponentIcon typeBasedIcon = null;
            if (preferredSize <= 16)
            {
                typeBasedIcon = GetIconByTypeWithTheme(component, IconType.Size16, IconType.DarkSize16, isDarkTheme) ?? 
                               GetIconByTypeWithTheme(component, IconType.Small, IconType.DarkSmall, isDarkTheme);
            }
            else if (preferredSize <= 32)
            {
                typeBasedIcon = GetIconByTypeWithTheme(component, IconType.Size32, IconType.DarkSize32, isDarkTheme) ?? 
                               GetIconByTypeWithTheme(component, IconType.Standard, IconType.DarkStandard, isDarkTheme);
            }
            else
            {
                typeBasedIcon = GetIconByTypeWithTheme(component, IconType.Size64, IconType.DarkSize64, isDarkTheme) ?? 
                               GetIconByTypeWithTheme(component, IconType.Large, IconType.DarkLarge, isDarkTheme);
            }
            
            if (typeBasedIcon?.IsValid == true)
            {
                Console.WriteLine($"Found type-based theme icon for size {preferredSize}: {typeBasedIcon.FileName} (Dark: {isDarkTheme})");
                return typeBasedIcon;
            }

            // Step 3: Fallback to primary icon with theme preference
            var primaryIcon = GetPrimaryIconWithTheme(component, isDarkTheme);
            if (primaryIcon?.IsValid == true)
            {
                Console.WriteLine($"Fallback to primary theme icon for size {preferredSize}: {primaryIcon.FileName} (Dark: {isDarkTheme})");
                return primaryIcon;
            }

            // Step 4: Final fallback - use any valid icon
            var fallbackIcon = component.Icons.FirstOrDefault(i => i.IsValid);
            if (fallbackIcon != null)
            {
                Console.WriteLine($"Final fallback icon for size {preferredSize}: {fallbackIcon.FileName} (Dark: {fallbackIcon.IsDark})");
            }
            return fallbackIcon;
        }

        /// <summary>
        /// Gets an icon by type with theme preference - IMPROVED
        /// </summary>
        private ComponentIcon GetIconByTypeWithTheme(ParsedComponent component, IconType lightType, IconType darkType, bool isDarkTheme)
        {
            if (isDarkTheme)
            {
                // In dark theme, prefer dark icons
                var darkIcon = component.Icons.GetByType(darkType);
                if (darkIcon?.IsValid == true)
                {
                    Console.WriteLine($"Found dark icon of type {darkType}: {darkIcon.FileName}");
                    return darkIcon;
                }
                
                // If no dark icon of this type, log it but continue to light fallback
                Console.WriteLine($"No dark icon found for type {darkType}, falling back to light type {lightType}");
            }
            
            // Use light icon (either because we're in light theme, or as fallback in dark theme)
            var lightIcon = component.Icons.GetByType(lightType);
            if (lightIcon?.IsValid == true)
            {
                Console.WriteLine($"Using light icon of type {lightType}: {lightIcon.FileName} (requested dark: {isDarkTheme})");
                return lightIcon;
            }
            
            return null;
        }

        /// <summary>
        /// Gets the primary icon for a component with theme preference - IMPROVED
        /// </summary>
        private ComponentIcon GetPrimaryIconWithTheme(ParsedComponent component, bool isDarkTheme)
        {
            if (!component.HasValidIcons)
                return null;

            if (isDarkTheme)
            {
                // In dark theme, prefer primary dark icon
                var primaryDarkIcon = component.Icons.PrimaryDarkIcon;
                if (primaryDarkIcon?.IsValid == true)
                {
                    Console.WriteLine($"Using primary dark icon: {primaryDarkIcon.FileName}");
                    return primaryDarkIcon;
                }
                
                Console.WriteLine($"No primary dark icon found, falling back to light primary (Dark theme: {isDarkTheme}, Has dark icons: {component.Icons.HasDarkIcons})");
            }
            
            // Use primary light icon (either because we're in light theme, or as fallback)
            var primaryIcon = component.Icons.PrimaryIcon;
            if (primaryIcon?.IsValid == true)
            {
                Console.WriteLine($"Using primary light icon: {primaryIcon.FileName} (requested dark: {isDarkTheme})");
                return primaryIcon;
            }

            return null;
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
                    context.DrawImage(source, new Rect(0, 0, width, height));
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
        /// Enhanced icon application that considers system DPI and UI theme
        /// </summary>
        private void ApplyIconToPushButtonWithDpiAwareness(PushButton button, ParsedComponent component)
        {
            if (!component.HasValidIcons)
                return;

            try
            {
                var (smallSize, largeSize) = GetOptimalIconSizes();
                var isDarkTheme = RevitThemeDetector.IsDarkTheme();
                
                Console.WriteLine($"Applying DPI-aware icons to PushButton '{component.DisplayName}' - Theme: {(isDarkTheme ? "Dark" : "Light")}, Sizes: {smallSize}x{smallSize}, {largeSize}x{largeSize}");
                
                // Get the best icons for the calculated sizes with theme awareness
                var largeIcon = GetBestIconForSizeWithTheme(component, largeSize, isDarkTheme);
                var smallIcon = GetBestIconForSizeWithTheme(component, smallSize, isDarkTheme);

                if (largeIcon != null)
                {
                    var largeBitmap = LoadBitmapSource(largeIcon.FilePath, largeSize);
                    if (largeBitmap != null)
                    {
                        button.LargeImage = largeBitmap;
                        Console.WriteLine($"Applied DPI-aware large icon: {largeIcon.FileName} (Dark: {largeIcon.IsDark})");
                    }
                }

                if (smallIcon != null)
                {
                    var smallBitmap = LoadBitmapSource(smallIcon.FilePath, smallSize);
                    if (smallBitmap != null)
                    {
                        button.Image = smallBitmap;
                        Console.WriteLine($"Applied DPI-aware small icon: {smallIcon.FileName} (Dark: {smallIcon.IsDark})");
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Failed to apply DPI-aware icon to PushButton {component.DisplayName}: {ex.Message}");
                // Fallback to standard method
                ApplyIconToPushButtonThemeAware(button, component);
            }
        }

        #endregion

        #region Highlight Management

        /// <summary>
        /// Applies highlight to a Revit UI button based on the component's Highlight property
        /// </summary>
        private void ApplyHighlightToButton(RibbonItem revitButton, ParsedComponent component)
        {
            if (string.IsNullOrEmpty(component.Highlight))
                return;

            try
            {
                // Get the Autodesk.Windows.RibbonButton from the Revit RibbonItem
                var adwButton = GetAutodeskWindowsButton(revitButton);
                if (adwButton == null)
                    return;

                // Apply highlight based on the component's Highlight value
                // Use reflection to access the Highlight property since it's in Autodesk.Internal namespace
                var highlightValue = component.Highlight.ToLowerInvariant();
                var highlightProperty = adwButton.GetType().GetProperty("Highlight");
                
                if (highlightProperty != null)
                {
                    var highlightModeType = highlightProperty.PropertyType;
                    object highlightModeValue = null;

                    if (highlightValue == "new")
                    {
                        highlightModeValue = Enum.Parse(highlightModeType, "New");
                        Console.WriteLine($"Applied 'new' highlight to button: {component.DisplayName}");
                    }
                    else if (highlightValue == "updated")
                    {
                        highlightModeValue = Enum.Parse(highlightModeType, "Updated");
                        Console.WriteLine($"Applied 'updated' highlight to button: {component.DisplayName}");
                    }

                    if (highlightModeValue != null)
                    {
                        highlightProperty.SetValue(adwButton, highlightModeValue);
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Failed to apply highlight to button {component.DisplayName}: {ex.Message}");
            }
        }

        /// <summary>
        /// Gets the Autodesk.Windows.RibbonButton from a Revit UI RibbonItem
        /// </summary>
        private RibbonButton GetAutodeskWindowsButton(RibbonItem revitButton)
        {
            if (revitButton == null)
                return null;

            try
            {
                // Search for the button in the Autodesk.Windows.ComponentManager.Ribbon
                var ribbon = ComponentManager.Ribbon;
                if (ribbon?.Tabs == null)
                    return null;

                foreach (var tab in ribbon.Tabs)
                {
                    if (tab?.Panels == null)
                        continue;

                    foreach (var panel in tab.Panels)
                    {
                        if (panel?.Source?.Items == null)
                            continue;

                        var found = FindButtonInItems(panel.Source.Items, revitButton.ItemText);
                        if (found != null)
                            return found;
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error getting Autodesk.Windows.RibbonButton: {ex.Message}");
            }

            return null;
        }

        /// <summary>
        /// Recursively searches for a RibbonButton by AutomationName in a collection of ribbon items
        /// </summary>
        private RibbonButton FindButtonInItems(System.Collections.IEnumerable items, string automationName)
        {
            if (items == null)
                return null;

            foreach (var item in items)
            {
                // Check if this item is the button we're looking for
                if (item is RibbonButton button && button.AutomationName == automationName)
                {
                    return button;
                }
                
                // Check in split buttons
                if (item is Autodesk.Windows.RibbonSplitButton splitButton && splitButton.Items != null)
                {
                    var found = FindButtonInItems(splitButton.Items, automationName);
                    if (found != null)
                        return found;
                }
            }

            return null;
        }

        #endregion
    }
}
