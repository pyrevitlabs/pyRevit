#nullable enable
using System;
using System.Collections;
using Autodesk.Revit.UI;
using Autodesk.Windows;
using pyRevitAssemblyBuilder.SessionManager;
using RibbonItem = Autodesk.Revit.UI.RibbonItem;

namespace pyRevitAssemblyBuilder.UIManager
{
    /// <summary>
    /// Helper class for working with Autodesk.Windows (AdWindows) API.
    /// Provides methods to access the underlying AdWindows ribbon objects from Revit API objects.
    /// </summary>
    public static class AdWindowsHelper
    {
        /// <summary>
        /// Gets the AdWindows RibbonItem from a Revit RibbonItem.
        /// Uses the internal 'getRibbonItem' method via reflection, matching the Python implementation
        /// in pyrevit.coreutils.ribbon.GenericPyRevitUIContainer.get_adwindows_object().
        /// </summary>
        /// <param name="ribbonItem">The Revit API RibbonItem.</param>
        /// <param name="logger">Optional logger for debugging.</param>
        /// <returns>The AdWindows RibbonItem, or null if not found.</returns>
        public static Autodesk.Windows.RibbonItem? GetAdWindowsRibbonItem(RibbonItem ribbonItem, ILogger? logger = null)
        {
            try
            {
                // Python implementation uses reflection to call the private 'getRibbonItem' method:
                // getRibbonItemMethod = rvtapi_obj.GetType().GetMethod(
                //     "getRibbonItem", BindingFlags.NonPublic | BindingFlags.Instance)
                // return getRibbonItemMethod.Invoke(rvtapi_obj, None)
                
                var getRibbonItemMethod = ribbonItem.GetType().GetMethod(
                    "getRibbonItem",
                    System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
                
                if (getRibbonItemMethod != null)
                {
                    return getRibbonItemMethod.Invoke(ribbonItem, null) as Autodesk.Windows.RibbonItem;
                }

                // Fallback: Search the ribbon for matching item (less reliable)
                logger?.Debug($"Could not find getRibbonItem method on {ribbonItem.GetType().Name}, falling back to ribbon search");
                var ribbon = ComponentManager.Ribbon;
                if (ribbon == null)
                    return null;

                foreach (var tab in ribbon.Tabs)
                {
                    foreach (var panel in tab.Panels)
                    {
                        var found = FindRibbonItemByName(panel.Source.Items, ribbonItem.Name);
                        if (found != null)
                            return found;
                    }
                }
            }
            catch (Exception ex)
            {
                logger?.Debug($"Failed to get AdWindows RibbonItem. Exception: {ex.Message}");
            }

            return null;
        }

        /// <summary>
        /// Recursively searches for a RibbonItem by name in a collection.
        /// </summary>
        /// <param name="items">The collection of items to search.</param>
        /// <param name="name">The name to search for.</param>
        /// <returns>The found RibbonItem, or null if not found.</returns>
        public static Autodesk.Windows.RibbonItem? FindRibbonItemByName(IEnumerable? items, string? name)
        {
            if (items == null || string.IsNullOrEmpty(name))
                return null;

            foreach (var item in items)
            {
                if (item is Autodesk.Windows.RibbonItem ribbonItem)
                {
                    if (ribbonItem.AutomationName == name || ribbonItem.Id == name)
                        return ribbonItem;

                    // Check children if it's a container (like RibbonRowPanel)
                    if (item is RibbonRowPanel rowPanel)
                    {
                        var found = FindRibbonItemByName(rowPanel.Items, name);
                        if (found != null)
                            return found;
                    }
                }
            }

            return null;
        }

        /// <summary>
        /// Resolves the tooltip on an AdWindows RibbonItem to apply changes.
        /// </summary>
        /// <param name="adWindowsRibbonItem">The AdWindows RibbonItem.</param>
        public static void ResolveToolTip(Autodesk.Windows.RibbonItem adWindowsRibbonItem)
        {
            typeof(Autodesk.Windows.RibbonItem).GetMethod("ResolveToolTip", 
                System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic)
                ?.Invoke(adWindowsRibbonItem, null);
        }
    }
}
