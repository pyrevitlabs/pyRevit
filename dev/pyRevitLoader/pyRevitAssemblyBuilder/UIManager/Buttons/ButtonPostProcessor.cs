#nullable enable
using System;
using System.Collections;
using Autodesk.Revit.UI;
using Autodesk.Windows;
using pyRevitAssemblyBuilder.UIManager.Icons;
using pyRevitAssemblyBuilder.UIManager.Tooltips;
using pyRevitExtensionParser;
using RibbonItem = Autodesk.Revit.UI.RibbonItem;
using RibbonButton = Autodesk.Windows.RibbonButton;
using pyRevitAssemblyBuilder.SessionManager;

namespace pyRevitAssemblyBuilder.UIManager.Buttons
{
    /// <summary>
    /// Handles post-processing of ribbon buttons after creation.
    /// Consolidates icon application, tooltip setup, and highlight management into a single service.
    /// </summary>
    public class ButtonPostProcessor : IButtonPostProcessor
    {
        private readonly ILogger _logger;
        private readonly IIconManager _iconManager;
        private readonly ITooltipManager _tooltipManager;

        /// <summary>
        /// Initializes a new instance of the <see cref="ButtonPostProcessor"/> class.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <param name="iconManager">The icon manager for applying icons.</param>
        /// <param name="tooltipManager">The tooltip manager for applying tooltips.</param>
        public ButtonPostProcessor(ILogger logger, IIconManager iconManager, ITooltipManager tooltipManager)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _iconManager = iconManager ?? throw new ArgumentNullException(nameof(iconManager));
            _tooltipManager = tooltipManager ?? throw new ArgumentNullException(nameof(tooltipManager));
        }

        /// <inheritdoc/>
        public IIconManager IconManager => _iconManager;

        /// <inheritdoc/>
        public void Process(RibbonItem ribbonItem, ParsedComponent component)
        {
            Process(ribbonItem, component, null, IconMode.LargeAndSmall);
        }

        /// <inheritdoc/>
        public void Process(RibbonItem ribbonItem, ParsedComponent component, ParsedComponent? parentComponent)
        {
            Process(ribbonItem, component, parentComponent, IconMode.LargeAndSmall);
        }

        /// <inheritdoc/>
        public void Process(RibbonItem ribbonItem, ParsedComponent component, ParsedComponent? parentComponent, IconMode iconMode)
        {
            if (ribbonItem == null || component == null)
                return;

            try
            {
                // Apply icon (with optional parent fallback)
                _iconManager.ApplyIcon(ribbonItem, component, parentComponent, iconMode);

                // Apply tooltip (text + media)
                _tooltipManager.ApplyTooltip(ribbonItem, component);

                // Apply highlight (new/updated badge)
                ApplyHighlight(ribbonItem, component);
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to process button '{component.DisplayName}'. Exception: {ex.Message}");
            }
        }

        /// <inheritdoc/>
        public string GetButtonText(ParsedComponent component)
        {
            return _tooltipManager.GetButtonTextWithConfigIndicator(component);
        }

        /// <inheritdoc/>
        public void ApplyHighlight(RibbonItem ribbonItem, ParsedComponent component)
        {
            if (string.IsNullOrEmpty(component.Highlight))
                return;

            try
            {
                // Get the Autodesk.Windows.RibbonButton from the Revit RibbonItem
                var adwButton = GetAutodeskWindowsButton(ribbonItem);
                if (adwButton == null)
                    return;

                // Apply highlight based on the component's Highlight value
                // Use reflection to access the Highlight property since it's in Autodesk.Internal namespace
                var highlightValue = component.Highlight.ToLowerInvariant();
                var highlightProperty = adwButton.GetType().GetProperty("Highlight");
                
                if (highlightProperty != null)
                {
                    var highlightModeType = highlightProperty.PropertyType;
                    object? highlightModeValue = null;

                    if (highlightValue == "new")
                    {
                        highlightModeValue = FindEnumValue(highlightModeType, "New");
                    }
                    else if (highlightValue == "updated")
                    {
                        highlightModeValue = FindEnumValue(highlightModeType, "Updated");
                    }

                    if (highlightModeValue != null)
                        highlightProperty.SetValue(adwButton, highlightModeValue);
                }
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to apply highlight to button '{ribbonItem?.ItemText ?? "unknown"}'. Exception: {ex.Message}");
            }
        }

        /// <summary>
        /// Finds an enum value by name from a given enum type.
        /// </summary>
        private static object? FindEnumValue(Type enumType, string valueName)
        {
            var enumValues = Enum.GetValues(enumType);
            foreach (var enumValue in enumValues)
            {
                if (enumValue.ToString() == valueName)
                    return enumValue;
            }
            return null;
        }

        /// <summary>
        /// Gets the Autodesk.Windows.RibbonButton from a Revit UI RibbonItem.
        /// Uses reflection to access the internal getRibbonItem method.
        /// </summary>
        private RibbonButton? GetAutodeskWindowsButton(RibbonItem ribbonItem)
        {
            if (ribbonItem == null)
                return null;

            try
            {
                // Use reflection to call the internal getRibbonItem method
                // This is the same approach used by pyrevit.coreutils.ribbon.py
                var getRibbonItemMethod = ribbonItem.GetType().GetMethod(
                    "getRibbonItem",
                    System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
                    
                if (getRibbonItemMethod != null)
                {
                    var result = getRibbonItemMethod.Invoke(ribbonItem, null);
                    return result as RibbonButton;
                }
                
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

                        var found = FindButtonInItems(panel.Source.Items, ribbonItem.ItemText);
                        if (found != null)
                            return found;
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to get Autodesk.Windows button for '{ribbonItem?.ItemText ?? "unknown"}'. Exception: {ex.Message}");
            }

            return null;
        }

        /// <summary>
        /// Recursively searches for a RibbonButton by AutomationName in a collection of ribbon items.
        /// </summary>
        private RibbonButton? FindButtonInItems(IEnumerable? items, string? automationName)
        {
            if (items == null || string.IsNullOrEmpty(automationName))
                return null;

            foreach (var item in items)
            {
                // Check if this item is the button we're looking for
                if (item is RibbonButton button && button.AutomationName == automationName)
                {
                    return button;
                }
                
                // Check in split buttons
                if (item is RibbonSplitButton splitButton && splitButton.Items != null)
                {
                    var found = FindButtonInItems(splitButton.Items, automationName);
                    if (found != null)
                        return found;
                }
            }

            return null;
        }
    }
}
