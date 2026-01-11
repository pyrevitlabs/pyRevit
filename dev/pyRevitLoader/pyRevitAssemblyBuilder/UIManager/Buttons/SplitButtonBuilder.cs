#nullable enable
using System;
using System.Linq;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitAssemblyBuilder.UIManager.Icons;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager.Buttons
{
    /// <summary>
    /// Builder for split buttons.
    /// </summary>
    public class SplitButtonBuilder : ButtonBuilderBase
    {
        private readonly LinkButtonBuilder _linkButtonBuilder;

        /// <inheritdoc/>
        public override CommandComponentType[] SupportedTypes => new[]
        {
            CommandComponentType.SplitButton,
            CommandComponentType.SplitPushButton
        };

        /// <summary>
        /// Initializes a new instance of the <see cref="SplitButtonBuilder"/> class.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor.</param>
        /// <param name="linkButtonBuilder">The link button builder for child link buttons.</param>
        public SplitButtonBuilder(
            ILogger logger,
            IButtonPostProcessor buttonPostProcessor,
            LinkButtonBuilder linkButtonBuilder)
            : base(logger, buttonPostProcessor)
        {
            _linkButtonBuilder = linkButtonBuilder ?? throw new ArgumentNullException(nameof(linkButtonBuilder));
        }

        /// <inheritdoc/>
        public override void Build(ParsedComponent component, RibbonPanel parentPanel, string tabName, ExtensionAssemblyInfo assemblyInfo)
        {
            if (parentPanel == null)
            {
                Logger.Warning($"Cannot create split button '{component.DisplayName}': parent panel is null.");
                return;
            }

            if (ItemExistsInPanel(parentPanel, component.DisplayName))
            {
                Logger.Debug($"Split button '{component.DisplayName}' already exists in panel.");
                return;
            }

            try
            {
                // Use Title from bundle.yaml if available, with config script indicator if applicable
                var splitButtonText = ButtonPostProcessor.GetButtonText(component);
                var splitData = new SplitButtonData(component.DisplayName, splitButtonText);
                var splitBtn = parentPanel.AddItem(splitData) as SplitButton;

                if (splitBtn != null)
                {
                    // Apply post-processing to split button
                    ButtonPostProcessor.Process(splitBtn, component);

                    // Add children
                    AddChildrenToSplitButton(splitBtn, component, assemblyInfo);

                    Logger.Debug($"Created split button '{splitButtonText}' with {component.Children?.Count ?? 0} children.");
                }
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to create split button '{component.DisplayName}'. Exception: {ex.Message}");
            }
        }

        /// <summary>
        /// Adds child buttons to an existing split button.
        /// </summary>
        public void AddChildrenToSplitButton(SplitButton splitBtn, ParsedComponent component, ExtensionAssemblyInfo assemblyInfo)
        {
            foreach (var sub in component.Children ?? Enumerable.Empty<ParsedComponent>())
            {
                if (sub.Type == CommandComponentType.Separator)
                {
                    // Skip adding separators during reload - they persist in the UI
                    if (assemblyInfo?.IsReloading == true)
                    {
                        Logger.Debug($"Skipping separator during reload for split button '{component.DisplayName}'.");
                        continue;
                    }
                    try
                    {
                        splitBtn.AddSeparator();
                    }
                    catch (Exception ex)
                    {
                        Logger.Debug($"Failed to add separator to split button. Exception: {ex.Message}");
                    }
                }
                else if (sub.Type == CommandComponentType.PushButton ||
                         sub.Type == CommandComponentType.UrlButton ||
                         sub.Type == CommandComponentType.InvokeButton ||
                         sub.Type == CommandComponentType.ContentButton)
                {
                    var subBtn = splitBtn.AddPushButton(CreatePushButtonData(sub, assemblyInfo!));
                    if (subBtn != null)
                    {
                        ButtonPostProcessor.Process(subBtn, sub, component);
                    }
                }
                else if (sub.Type == CommandComponentType.LinkButton)
                {
                    var subLinkData = _linkButtonBuilder.CreateLinkButtonData(sub);
                    if (subLinkData != null)
                    {
                        var linkSubBtn = splitBtn.AddPushButton(subLinkData);
                        if (linkSubBtn != null)
                        {
                            ButtonPostProcessor.Process(linkSubBtn, sub, component);
                        }
                    }
                }
            }
        }
    }
}
