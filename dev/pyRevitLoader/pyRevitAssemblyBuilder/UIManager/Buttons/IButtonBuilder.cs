#nullable enable
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Buttons
{
    /// <summary>
    /// Interface for building specific types of ribbon buttons.
    /// </summary>
    public interface IButtonBuilder
    {
        /// <summary>
        /// Gets the component types this builder can handle.
        /// </summary>
        CommandComponentType[] SupportedTypes { get; }

        /// <summary>
        /// Checks if this builder can handle the specified component type.
        /// </summary>
        /// <param name="componentType">The component type to check.</param>
        /// <returns>True if this builder can handle the component type.</returns>
        bool CanHandle(CommandComponentType componentType);

        /// <summary>
        /// Builds a button for the specified component and adds it to the panel.
        /// </summary>
        /// <param name="component">The component to build a button for.</param>
        /// <param name="parentPanel">The panel to add the button to.</param>
        /// <param name="tabName">The name of the tab containing the panel.</param>
        /// <param name="assemblyInfo">Information about the assembly containing command implementations.</param>
        void Build(ParsedComponent component, RibbonPanel parentPanel, string tabName, ExtensionAssemblyInfo assemblyInfo);
    }
}
