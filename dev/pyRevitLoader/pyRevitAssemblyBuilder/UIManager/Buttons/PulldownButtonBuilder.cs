#nullable enable
using System;
using System.Collections.Generic;
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
    /// Builder for pulldown buttons.
    /// </summary>
    public class PulldownButtonBuilder : ButtonBuilderBase
    {
        private readonly SmartButtonScriptInitializer? _smartButtonScriptInitializer;
        private readonly LinkButtonBuilder _linkButtonBuilder;

        /// <inheritdoc/>
        public override CommandComponentType[] SupportedTypes => new[]
        {
            CommandComponentType.PullDown
        };

        /// <summary>
        /// Initializes a new instance of the <see cref="PulldownButtonBuilder"/> class.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor.</param>
        /// <param name="linkButtonBuilder">The link button builder for child link buttons.</param>
        /// <param name="smartButtonScriptInitializer">Optional SmartButton script initializer.</param>
        public PulldownButtonBuilder(
            ILogger logger,
            IButtonPostProcessor buttonPostProcessor,
            LinkButtonBuilder linkButtonBuilder,
            SmartButtonScriptInitializer? smartButtonScriptInitializer = null)
            : base(logger, buttonPostProcessor)
        {
            _linkButtonBuilder = linkButtonBuilder ?? throw new ArgumentNullException(nameof(linkButtonBuilder));
            _smartButtonScriptInitializer = smartButtonScriptInitializer;
        }

        /// <inheritdoc/>
        public override void Build(ParsedComponent component, RibbonPanel parentPanel, string tabName, ExtensionAssemblyInfo assemblyInfo)
        {
            if (parentPanel == null)
            {
                Logger.Warning($"Cannot create pulldown button '{component.DisplayName}': parent panel is null.");
                return;
            }

            if (ItemExistsInPanel(parentPanel, component.DisplayName))
            {
                Logger.Debug($"Pulldown button '{component.DisplayName}' already exists in panel.");
                return;
            }

            CreatePulldown(component, parentPanel, tabName, assemblyInfo, addToPanel: true);
        }

        /// <summary>
        /// Creates a pulldown button and optionally adds it to a panel.
        /// </summary>
        /// <returns>The PulldownButtonData for use in stacks, or null if failed.</returns>
        public PulldownButtonData? CreatePulldown(
            ParsedComponent component,
            RibbonPanel parentPanel,
            string tabName,
            ExtensionAssemblyInfo assemblyInfo,
            bool addToPanel)
        {
            // Use localized title which handles fallback to DisplayName
            var pulldownText = ExtensionParser.GetComponentTitle(component);
            // Use DisplayName for the button's internal name to match control ID format
            var pdData = new PulldownButtonData(component.DisplayName, pulldownText);

            if (!addToPanel)
                return pdData;

            var pdBtn = parentPanel.AddItem(pdData) as PulldownButton;
            if (pdBtn == null)
            {
                Logger.Warning($"Failed to add pulldown button '{pulldownText}' to panel.");
                return null;
            }

            // Apply post-processing to the pulldown button itself
            ButtonPostProcessor.Process(pdBtn, component);

            // Add children
            AddChildrenToPulldown(pdBtn, component, assemblyInfo);

            Logger.Debug($"Created pulldown button '{pulldownText}' with {component.Children?.Count ?? 0} children.");
            return pdData;
        }

        /// <summary>
        /// Adds child buttons to an existing pulldown button.
        /// </summary>
        public void AddChildrenToPulldown(PulldownButton pdBtn, ParsedComponent component, ExtensionAssemblyInfo assemblyInfo)
        {
            foreach (var sub in component.Children ?? Enumerable.Empty<ParsedComponent>())
            {
                if (sub.Type == CommandComponentType.Separator)
                {
                    // Skip adding separators during reload - they persist in the UI
                    if (assemblyInfo?.IsReloading == true)
                    {
                        Logger.Debug($"Skipping separator during reload for pulldown button '{component.DisplayName}'.");
                        continue;
                    }
                    try
                    {
                        pdBtn.AddSeparator();
                    }
                    catch (Exception ex)
                    {
                        Logger.Debug($"Failed to add separator to pulldown button. Exception: {ex.Message}");
                    }
                }
                else if (sub.Type == CommandComponentType.PushButton ||
                         sub.Type == CommandComponentType.UrlButton ||
                         sub.Type == CommandComponentType.InvokeButton ||
                         sub.Type == CommandComponentType.ContentButton)
                {
                    var subBtn = pdBtn.AddPushButton(CreatePushButtonData(sub, assemblyInfo!));
                    if (subBtn != null)
                    {
                        ButtonPostProcessor.Process(subBtn, sub, component, IconMode.SmallToBoth);
                    }
                }
                else if (sub.Type == CommandComponentType.SmartButton)
                {
                    var smartSubBtn = pdBtn.AddPushButton(CreatePushButtonData(sub, assemblyInfo!));
                    if (smartSubBtn != null)
                    {
                        ButtonPostProcessor.Process(smartSubBtn, sub, component, IconMode.SmallToBoth);

                        // Execute __selfinit__ for SmartButton in pulldown
                        if (_smartButtonScriptInitializer != null)
                        {
                            var shouldActivate = _smartButtonScriptInitializer.ExecuteSelfInit(sub, smartSubBtn);
                            if (!shouldActivate)
                            {
                                smartSubBtn.Enabled = false;
                                Logger.Debug($"SmartButton '{sub.DisplayName}' in pulldown deactivated by __selfinit__.");
                            }
                        }
                    }
                }
                else if (sub.Type == CommandComponentType.LinkButton)
                {
                    var linkData = _linkButtonBuilder.CreateLinkButtonData(sub);
                    if (linkData != null)
                    {
                        var linkSubBtn = pdBtn.AddPushButton(linkData);
                        if (linkSubBtn != null)
                        {
                            ButtonPostProcessor.Process(linkSubBtn, sub, component, IconMode.SmallToBoth);
                        }
                    }
                }
            }
        }
    }
}
