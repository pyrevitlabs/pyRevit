#nullable enable
using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Buttons
{
    /// <summary>
    /// Factory for creating and managing button builders.
    /// </summary>
    public class ButtonBuilderFactory : IButtonBuilderFactory
    {
        private readonly ILogger _logger;
        private readonly Dictionary<CommandComponentType, IButtonBuilder> _builders;

        /// <summary>
        /// Initializes a new instance of the <see cref="ButtonBuilderFactory"/> class.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <param name="builders">The collection of button builders to register.</param>
        public ButtonBuilderFactory(ILogger logger, IEnumerable<IButtonBuilder> builders)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _builders = new Dictionary<CommandComponentType, IButtonBuilder>();

            // Register all builders
            foreach (var builder in builders)
            {
                RegisterBuilder(builder);
            }
        }

        /// <summary>
        /// Registers a button builder for its supported component types.
        /// </summary>
        /// <param name="builder">The builder to register.</param>
        public void RegisterBuilder(IButtonBuilder builder)
        {
            if (builder == null)
                return;

            foreach (var componentType in builder.SupportedTypes)
            {
                if (_builders.ContainsKey(componentType))
                {
                    _logger.Debug($"Overriding builder for component type '{componentType}'.");
                }
                _builders[componentType] = builder;
            }
        }

        /// <inheritdoc/>
        public IButtonBuilder? GetBuilder(CommandComponentType componentType)
        {
            return _builders.TryGetValue(componentType, out var builder) ? builder : null;
        }

        /// <inheritdoc/>
        public bool HasBuilder(CommandComponentType componentType)
        {
            return _builders.ContainsKey(componentType);
        }

        /// <inheritdoc/>
        public bool TryBuild(ParsedComponent component, RibbonPanel parentPanel, string tabName, ExtensionAssemblyInfo assemblyInfo)
        {
            var builder = GetBuilder(component.Type);
            if (builder == null)
            {
                return false;
            }

            builder.Build(component, parentPanel, tabName, assemblyInfo);
            return true;
        }
    }
}
