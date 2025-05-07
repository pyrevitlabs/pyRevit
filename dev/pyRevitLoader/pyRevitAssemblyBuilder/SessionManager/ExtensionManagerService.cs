using System;
using System.Collections.Generic;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class ExtensionManagerService
    {
        public IEnumerable<ParsedExtension> GetInstalledExtensions()
        {
            var installedExtensions = ExtensionParser.ParseInstalledExtensions();

            foreach (var parsedExtension in installedExtensions)
            {
                // Reorder children based on LayoutOrder inside the parsedExtension
                ReorderChildren(parsedExtension);

                yield return parsedExtension;
            }

            Console.WriteLine(installedExtensions);
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

    }
}
