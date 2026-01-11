#nullable enable
using System;
using System.Linq;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitAssemblyBuilder.UIManager.Builders;
using pyRevitAssemblyBuilder.UIManager.Buttons;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitAssemblyBuilder.UIManager
{
    /// <summary>
    /// Service for building Revit UI elements from parsed extensions.
    /// Coordinates the creation of tabs, panels, and buttons using specialized builders.
    /// </summary>
    public class UIManagerService : IUIManagerService
    {
        private readonly ILogger _logger;
        private readonly IButtonPostProcessor _buttonPostProcessor;
        private readonly ITabBuilder _tabBuilder;
        private readonly IPanelBuilder _panelBuilder;
        private readonly IButtonBuilderFactory _buttonBuilderFactory;
        private readonly IStackBuilder _stackBuilder;
        private readonly IComboBoxBuilder _comboBoxBuilder;
        private readonly UIApplication _uiApp;
        private ParsedExtension? _currentExtension;

        /// <summary>
        /// Gets the UIApplication instance used by this service.
        /// </summary>
        public UIApplication UIApplication => _uiApp;

        /// <summary>
        /// Initializes a new instance of the <see cref="UIManagerService"/> class.
        /// </summary>
        /// <param name="uiApp">The Revit UIApplication instance.</param>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor instance.</param>
        /// <param name="tabBuilder">The tab builder instance.</param>
        /// <param name="panelBuilder">The panel builder instance.</param>
        /// <param name="buttonBuilderFactory">The button builder factory instance.</param>
        /// <param name="stackBuilder">The stack builder instance.</param>
        /// <param name="comboBoxBuilder">The combo box builder instance.</param>
        public UIManagerService(
            UIApplication uiApp,
            ILogger logger,
            IButtonPostProcessor buttonPostProcessor,
            ITabBuilder tabBuilder,
            IPanelBuilder panelBuilder,
            IButtonBuilderFactory buttonBuilderFactory,
            IStackBuilder stackBuilder,
            IComboBoxBuilder comboBoxBuilder)
        {
            _uiApp = uiApp ?? throw new ArgumentNullException(nameof(uiApp));
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _buttonPostProcessor = buttonPostProcessor ?? throw new ArgumentNullException(nameof(buttonPostProcessor));
            _tabBuilder = tabBuilder ?? throw new ArgumentNullException(nameof(tabBuilder));
            _panelBuilder = panelBuilder ?? throw new ArgumentNullException(nameof(panelBuilder));
            _buttonBuilderFactory = buttonBuilderFactory ?? throw new ArgumentNullException(nameof(buttonBuilderFactory));
            _stackBuilder = stackBuilder ?? throw new ArgumentNullException(nameof(stackBuilder));
            _comboBoxBuilder = comboBoxBuilder ?? throw new ArgumentNullException(nameof(comboBoxBuilder));
        }

        /// <summary>
        /// Builds the UI for the specified extension using the provided assembly information.
        /// </summary>
        /// <param name="extension">The parsed extension containing UI component definitions.</param>
        /// <param name="assemblyInfo">Information about the assembly containing command implementations.</param>
        public void BuildUI(ParsedExtension extension, ExtensionAssemblyInfo assemblyInfo)
        {
            if (extension == null)
            {
                _logger.Warning("Cannot build UI: extension is null.");
                return;
            }

            if (assemblyInfo == null)
            {
                _logger.Warning($"Cannot build UI for extension '{extension.Name}': assemblyInfo is null.");
                return;
            }

            if (extension.Children == null)
            {
                _logger.Debug($"Extension '{extension.Name}' has no children to build UI for.");
                return;
            }

            // Pre-load icon files in parallel to warm OS file cache
            _buttonPostProcessor.IconManager.PreloadExtensionIcons(extension);

            _currentExtension = extension;
            foreach (var component in extension.Children)
            {
                if (component != null)
                {
                    RecursivelyBuildUI(component, null, null, extension.Name, assemblyInfo);
                }
            }
            _currentExtension = null;
        }

        private void RecursivelyBuildUI(
            ParsedComponent component,
            ParsedComponent? parentComponent,
            RibbonPanel? parentPanel,
            string tabName,
            ExtensionAssemblyInfo assemblyInfo)
        {
            if (component == null)
            {
                _logger.Warning("Cannot build UI: component is null.");
                return;
            }

            if (assemblyInfo == null)
            {
                _logger.Warning("Cannot build UI: assemblyInfo is null.");
                return;
            }

            if (string.IsNullOrEmpty(tabName))
            {
                _logger.Warning($"Cannot build UI for component '{component.DisplayName}': tabName is null or empty.");
                return;
            }

            switch (component.Type)
            {
                case CommandComponentType.Tab:
                    HandleTab(component, assemblyInfo);
                    break;

                case CommandComponentType.Panel:
                    HandlePanel(component, tabName, assemblyInfo);
                    break;

                default:
                    if (component.HasSlideout)
                    {
                        // When a component is marked as a slideout, apply the slideout
                        EnsureSlideOutApplied(parentComponent, parentPanel);
                    }
                    else
                    {
                        // Only handle the component if it's not a slideout marker
                        HandleComponentBuilding(component, parentPanel, tabName, assemblyInfo);
                    }
                    break;
            }
        }

        private void HandleTab(ParsedComponent component, ExtensionAssemblyInfo assemblyInfo)
        {
            // Use TabBuilder to create the tab
            _tabBuilder.CreateTab(component);

            // Get tab name for children using localized title
            var tabText = ExtensionParser.GetComponentTitle(component);

            // Recursively build children
            foreach (var child in component.Children ?? Enumerable.Empty<ParsedComponent>())
                RecursivelyBuildUI(child, component, null, tabText, assemblyInfo);
        }

        private void HandlePanel(ParsedComponent component, string tabName, ExtensionAssemblyInfo assemblyInfo)
        {
            // Use PanelBuilder to create the panel
            var panel = _panelBuilder.CreatePanel(component, tabName);

            // Apply background colors if specified
            _panelBuilder.ApplyPanelBackgroundColors(panel, component, tabName);

            // Recursively build children
            foreach (var child in component.Children ?? Enumerable.Empty<ParsedComponent>())
                RecursivelyBuildUI(child, component, panel, tabName, assemblyInfo);
        }

        private void EnsureSlideOutApplied(ParsedComponent? parentComponent, RibbonPanel? parentPanel)
        {
            if (parentPanel != null && parentComponent?.Type == CommandComponentType.Panel)
            {
                try
                {
                    parentPanel.AddSlideOut();
                }
                catch (Exception ex)
                {
                    // Slideout may already exist or panel may not support it
                    _logger.Debug($"Failed to add slideout to panel '{parentPanel.Name}'. Exception: {ex.Message}");
                }
            }
        }

        private void HandleComponentBuilding(
            ParsedComponent component,
            RibbonPanel? parentPanel,
            string tabName,
            ExtensionAssemblyInfo assemblyInfo)
        {
            switch (component.Type)
            {
                case CommandComponentType.Separator:
                    HandleSeparator(parentPanel, assemblyInfo);
                    break;

                case CommandComponentType.Stack:
                    _stackBuilder.BuildStack(component, parentPanel!, assemblyInfo);
                    break;

                case CommandComponentType.ComboBox:
                    if (!ItemExistsInPanel(parentPanel, component.DisplayName))
                    {
                        _comboBoxBuilder.CreateComboBox(component, parentPanel!);
                    }
                    break;

                default:
                    // Try to build using the button builder factory
                    if (_buttonBuilderFactory.HasBuilder(component.Type))
                    {
                        if (!ItemExistsInPanel(parentPanel, component.DisplayName))
                        {
                            _buttonBuilderFactory.TryBuild(component, parentPanel!, tabName, assemblyInfo);
                        }
                    }
                    else
                    {
                        _logger.Debug($"No builder found for component type '{component.Type}' - '{component.DisplayName}'.");
                    }
                    break;
            }
        }

        private void HandleSeparator(RibbonPanel? parentPanel, ExtensionAssemblyInfo assemblyInfo)
        {
            // Skip adding separators during reload - they persist in the UI
            if (assemblyInfo?.IsReloading == true)
            {
                _logger.Debug($"Skipping separator during reload for panel '{parentPanel?.Name}'.");
                return;
            }

            if (parentPanel != null)
            {
                try
                {
                    parentPanel.AddSeparator();
                }
                catch (Exception ex)
                {
                    _logger.Debug($"Failed to add separator to panel '{parentPanel.Name}'. Exception: {ex.Message}");
                }
            }
        }

        /// <summary>
        /// Checks if a ribbon item with the specified name already exists in the panel.
        /// </summary>
        private bool ItemExistsInPanel(RibbonPanel? panel, string itemName)
        {
            if (panel == null || string.IsNullOrEmpty(itemName))
                return false;

            try
            {
                var existingItems = panel.GetItems();
                return existingItems.Any(item => item.Name == itemName);
            }
            catch (Exception ex)
            {
                _logger.Debug($"Error checking if item '{itemName}' exists in panel. Exception: {ex.Message}");
                return false;
            }
        }
    }
}
