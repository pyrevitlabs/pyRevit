#nullable enable
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitExtensionParser;
using System.Collections.Generic;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Buttons
{
    /// <summary>
    /// Factory interface for creating button builders based on component type.
    /// </summary>
    public interface IButtonBuilderFactory
    {
        /// <summary>
        /// Gets the appropriate button builder for the specified component type.
        /// </summary>
        /// <param name="componentType">The component type to get a builder for.</param>
        /// <returns>The button builder, or null if no builder is registered for the type.</returns>
        IButtonBuilder? GetBuilder(CommandComponentType componentType);

        /// <summary>
        /// Checks if a builder exists for the specified component type.
        /// </summary>
        /// <param name="componentType">The component type to check.</param>
        /// <returns>True if a builder is registered for the type.</returns>
        bool HasBuilder(CommandComponentType componentType);

        /// <summary>
        /// Builds a button for the component if a suitable builder is available.
        /// </summary>
        /// <param name="component">The component to build.</param>
        /// <param name="parentPanel">The parent panel.</param>
        /// <param name="tabName">The tab name.</param>
        /// <param name="assemblyInfo">The assembly info.</param>
        /// <returns>True if the component was handled by a builder.</returns>
        bool TryBuild(ParsedComponent component, RibbonPanel parentPanel, string tabName, ExtensionAssemblyInfo assemblyInfo);
    }
}
