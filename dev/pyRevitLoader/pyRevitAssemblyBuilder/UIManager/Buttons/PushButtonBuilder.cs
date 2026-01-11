#nullable enable
using System;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Buttons
{
    /// <summary>
    /// Builder for standard push buttons including PushButton, UrlButton, InvokeButton, and ContentButton.
    /// </summary>
    public class PushButtonBuilder : ButtonBuilderBase
    {
        private readonly SmartButtonScriptInitializer? _smartButtonScriptInitializer;

        /// <inheritdoc/>
        public override CommandComponentType[] SupportedTypes => new[]
        {
            CommandComponentType.PushButton,
            CommandComponentType.UrlButton,
            CommandComponentType.InvokeButton,
            CommandComponentType.ContentButton,
            CommandComponentType.SmartButton
        };

        /// <summary>
        /// Initializes a new instance of the <see cref="PushButtonBuilder"/> class.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor.</param>
        /// <param name="smartButtonScriptInitializer">Optional SmartButton script initializer.</param>
        public PushButtonBuilder(
            ILogger logger,
            IButtonPostProcessor buttonPostProcessor,
            SmartButtonScriptInitializer? smartButtonScriptInitializer = null)
            : base(logger, buttonPostProcessor)
        {
            _smartButtonScriptInitializer = smartButtonScriptInitializer;
        }

        /// <inheritdoc/>
        public override void Build(ParsedComponent component, RibbonPanel parentPanel, string tabName, ExtensionAssemblyInfo assemblyInfo)
        {
            if (parentPanel == null)
            {
                Logger.Warning($"Cannot create push button '{component.DisplayName}': parent panel is null.");
                return;
            }

            if (ItemExistsInPanel(parentPanel, component.DisplayName))
            {
                Logger.Debug($"Push button '{component.DisplayName}' already exists in panel.");
                return;
            }

            try
            {
                var pbData = CreatePushButtonData(component, assemblyInfo);
                var btn = parentPanel.AddItem(pbData) as PushButton;
                if (btn != null)
                {
                    ButtonPostProcessor.Process(btn, component);

                    // Handle SmartButton-specific initialization
                    if (component.Type == CommandComponentType.SmartButton && _smartButtonScriptInitializer != null)
                    {
                        var shouldActivate = _smartButtonScriptInitializer.ExecuteSelfInit(component, btn);
                        if (!shouldActivate)
                        {
                            btn.Enabled = false;
                            Logger.Debug($"SmartButton '{component.DisplayName}' deactivated by __selfinit__.");
                        }
                    }

                    Logger.Debug($"Created push button '{component.DisplayName}'.");
                }
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to create push button '{component.DisplayName}'. Exception: {ex.Message}");
            }
        }
    }
}
