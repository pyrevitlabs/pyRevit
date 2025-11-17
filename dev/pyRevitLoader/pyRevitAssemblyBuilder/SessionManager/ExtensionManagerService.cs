using System.Collections.Generic;
using System.Linq;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Service for managing and querying installed pyRevit extensions.
    /// </summary>
    public class ExtensionManagerService
    {
        /// <summary>
        /// Gets all installed extensions that are not disabled.
        /// </summary>
        /// <returns>An enumerable collection of parsed extensions.</returns>
        public IEnumerable<ParsedExtension> GetInstalledExtensions()
        {
            var installedExtensions = ExtensionParser.ParseInstalledExtensions();
            return installedExtensions.Where(ext => ext.Config?.Disabled != true);
        }

        private void ReorderChildren(ParsedExtension parsedExtension)
        {
            // If LayoutOrder is null for the entire extension, no reordering for top-level children
            if (parsedExtension.LayoutOrder == null)
            {
                // Continue checking for children that may have their own LayoutOrder
                foreach (var child in parsedExtension.Children)
                {
                    // Reorder this component's children if they have their own LayoutOrder
                    if (child.LayoutOrder != null)
                    {
                        ReorderChildrenForComponent(child);
                    }
                }
                return;
            }

            // Otherwise, reorder top-level children based on LayoutOrder
            parsedExtension.Children.Sort((x, y) =>
            {
                // Compare based on LayoutOrder index, or place items not found at the end
                var indexX = parsedExtension.LayoutOrder.IndexOf(x.Name);
                var indexY = parsedExtension.LayoutOrder.IndexOf(y.Name);

                // Handle missing LayoutOrder by placing them at the end
                return indexX.CompareTo(indexY);
            });

            // Recurse through children to reorder them if they have LayoutOrder defined
            foreach (var child in parsedExtension.Children)
            {
                if (child.Children != null)
                {
                    ReorderChildren(new ParsedExtension
                    {
                        Children = child.Children,
                        LayoutOrder = child.LayoutOrder // Pass LayoutOrder for child components
                    });
                }
            }
        }

        private void ReorderChildrenForComponent(ParsedComponent component)
        {
            // Only reorder if this component has its own LayoutOrder
            if (component.LayoutOrder == null) return;

            component.Children.Sort((x, y) =>
            {
                var indexX = component.LayoutOrder.IndexOf(x.Name);
                var indexY = component.LayoutOrder.IndexOf(y.Name);

                // Handle missing LayoutOrder by placing them at the end
                return indexX.CompareTo(indexY);
            });

            // Recurse for nested components (children of this component)
            foreach (var child in component.Children)
            {
                if (child.Children != null)
                {
                    ReorderChildren(new ParsedExtension
                    {
                        Children = child.Children,
                        LayoutOrder = child.LayoutOrder // Pass LayoutOrder for nested components
                    });
                }
            }
        }

        private void FlattenAndEnrich(IEnumerable<ParsedComponent> components)
        {
            foreach (var component in components)
            {
                if (!string.IsNullOrEmpty(component.ScriptPath))
                    yield return component;

        private void FlattenAndEnrich(IEnumerable<ParsedComponent> components)
        {
            foreach (var component in components)
            {
                // Custom logic if needed, e.g., enrich tooltip or validate UniqueId
                if (component.Children != null)
                    FlattenAndEnrich(component.Children);
            }
        }
    }
}
