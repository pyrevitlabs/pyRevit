#nullable enable
using System;
using System.Collections.Generic;
using System.Diagnostics;
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
        private readonly IUIRibbonScanner? _ribbonScanner;
        private readonly SmartButtonScriptInitializer? _smartButtonScriptInitializer;
        private readonly UIApplication _uiApp;
        private readonly BuildContext _buildContext;
        private ParsedExtension? _currentExtension;

        /// <summary>
        /// Cached Rocket Mode setting. Re-read at start of each BuildUI so reload picks up settings changes.
        /// When true, non-critical startup work (e.g. icon pre-loading) is skipped to reduce load time.
        /// </summary>
        private bool _rocketMode;

        /// <summary>
        /// Per-type aggregated time spent at the top level of the current extension
        /// (direct children of <c>extension.Children</c>). Populated during <see cref="BuildUI"/>
        /// and read back by <see cref="EmitBuildUIPerfLines"/>.
        /// </summary>
        private readonly Dictionary<CommandComponentType, long> _topLevelMs = new Dictionary<CommandComponentType, long>();
        private readonly Dictionary<CommandComponentType, int> _topLevelCount = new Dictionary<CommandComponentType, int>();

        /// <summary>
        /// Per-panel timing captured inside <see cref="HandleTab"/>. Recorded in build order
        /// so the emitted lines stay deterministic across runs even when sorted by elapsed.
        /// </summary>
        private readonly List<(string PanelName, long ElapsedMs)> _panelTimings = new List<(string, long)>();

        /// <summary>
        /// Snapshot of <see cref="IButtonPostProcessor.ResetAndGetStats"/> taken at the end of
        /// the most recent <see cref="BuildUI"/> call. Read by <see cref="EmitBuildUIPerfLines"/>.
        /// </summary>
        private (long ProcessMs, int Calls) _postProcessorStats;

        /// <summary>
        /// Snapshot of <see cref="IIconManager.ResetAndGetStats"/> taken at the end of the most
        /// recent <see cref="BuildUI"/> call.
        /// </summary>
        private (int CacheHits, int CacheMisses, long DecodeMs) _iconStats;

        /// <summary>
        /// Snapshot of <see cref="IButtonPostProcessor.ResetAndGetAddItemStats"/> taken at the
        /// end of the most recent <see cref="BuildUI"/> call.
        /// </summary>
        private (long AddItemMs, int Calls) _addItemStats;

        /// <summary>
        /// Snapshot of <see cref="SmartButtonScriptInitializer.ResetAndGetStats"/> taken at
        /// the end of the most recent <see cref="BuildUI"/> call. Holds the per-stage breakdown
        /// (engine init / compile / execute / invoke) plus per-button records for the [PERF] lines.
        /// </summary>
        private SmartButtonStats _smartButtonStats;


        /// <summary>
        /// Gets the UIApplication instance used by this service.
        /// </summary>
        public UIApplication UIApplication => _uiApp;

        /// <summary>
        /// Gets whether rocket mode is enabled.
        /// When true, non-critical startup work is skipped and engine caching is used for compatible extensions.
        /// </summary>
        public bool RocketMode => _rocketMode;

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
        /// <param name="buildContext">Shared build context that holds the current per-build settings; updated at the start of each <see cref="BuildUI"/> call so all builders observe the same snapshot.</param>
        /// <param name="ribbonScanner">Optional ribbon scanner for tracking UI elements.</param>
        /// <param name="smartButtonScriptInitializer">Optional SmartButton initializer; passed in only to read per-extension self-init timing.</param>
        public UIManagerService(
            UIApplication uiApp,
            ILogger logger,
            IButtonPostProcessor buttonPostProcessor,
            ITabBuilder tabBuilder,
            IPanelBuilder panelBuilder,
            IButtonBuilderFactory buttonBuilderFactory,
            IStackBuilder stackBuilder,
            IComboBoxBuilder comboBoxBuilder,
            BuildContext buildContext,
            IUIRibbonScanner? ribbonScanner = null,
            SmartButtonScriptInitializer? smartButtonScriptInitializer = null)
        {
            _uiApp = uiApp ?? throw new ArgumentNullException(nameof(uiApp));
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
            _buttonPostProcessor = buttonPostProcessor ?? throw new ArgumentNullException(nameof(buttonPostProcessor));
            _tabBuilder = tabBuilder ?? throw new ArgumentNullException(nameof(tabBuilder));
            _panelBuilder = panelBuilder ?? throw new ArgumentNullException(nameof(panelBuilder));
            _buttonBuilderFactory = buttonBuilderFactory ?? throw new ArgumentNullException(nameof(buttonBuilderFactory));
            _stackBuilder = stackBuilder ?? throw new ArgumentNullException(nameof(stackBuilder));
            _comboBoxBuilder = comboBoxBuilder ?? throw new ArgumentNullException(nameof(comboBoxBuilder));
            _buildContext = buildContext ?? throw new ArgumentNullException(nameof(buildContext));
            _ribbonScanner = ribbonScanner;
            _smartButtonScriptInitializer = smartButtonScriptInitializer;

            RefreshBuildSettings(initial: true);
        }

        /// <summary>
        /// Re-reads <see cref="PyRevitConfig"/> and pushes the new <see cref="BuildSettings"/> into the
        /// shared <see cref="BuildContext"/>. Called at construction and at the start of every
        /// <see cref="BuildUI"/> so toggling beta / rocket mode takes effect on the next reload (#3109)
        /// and all builders observe the same snapshot.
        /// </summary>
        private void RefreshBuildSettings(bool initial)
        {
            var settings = ComponentSupportUtils.ReadBuildSettings(_uiApp, _logger);
            _buildContext.Update(settings);

            try
            {
                _rocketMode = PyRevitConfig.Load().RocketMode;
            }
            catch (Exception ex)
            {
                _logger.Debug($"Failed to read RocketMode config: {ex.Message}");
                if (initial)
                    _rocketMode = false;
            }

            var prefix = initial ? string.Empty : "Re-read config - ";
            _logger.Debug($"{prefix}Beta tools loading: {settings.LoadBeta}, Rocket mode: {_rocketMode}");
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

            RefreshBuildSettings(initial: false);

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

            // Icon pre-loading removed for #3268: the legacy Python loader loads icons
            // on-demand during UI construction with no pre-loading step.
            // LoadBitmapSource() has its own BitmapCache, so each icon is decoded once.
            // The OS file cache is already warm from bundle.yaml parsing in PASS 1.

            _currentExtension = extension;
            _topLevelMs.Clear();
            _topLevelCount.Clear();
            _panelTimings.Clear();

            // Clear per-build accumulators on shared collaborators so what we capture below
            // attributes only to this extension's BuildUI window.
            _buttonPostProcessor.ResetAndGetStats();
            _buttonPostProcessor.ResetAndGetAddItemStats();
            _buttonPostProcessor.IconManager?.ResetAndGetStats();
            _smartButtonScriptInitializer?.ResetAndGetStats();

            var topLevelSw = new Stopwatch();
            foreach (var component in extension.Children)
            {
                if (component != null)
                {
                    topLevelSw.Restart();
                    RecursivelyBuildUI(component, null, null, extension.Name, assemblyInfo);
                    var elapsed = topLevelSw.ElapsedMilliseconds;

                    var key = component.Type;
                    _topLevelMs[key] = _topLevelMs.TryGetValue(key, out var prev) ? prev + elapsed : elapsed;
                    _topLevelCount[key] = _topLevelCount.TryGetValue(key, out var c) ? c + 1 : 1;
                }
            }

            _postProcessorStats = _buttonPostProcessor.ResetAndGetStats();
            _addItemStats = _buttonPostProcessor.ResetAndGetAddItemStats();
            _iconStats = _buttonPostProcessor.IconManager?.ResetAndGetStats() ?? (0, 0, 0L);
            _smartButtonStats = _smartButtonScriptInitializer?.ResetAndGetStats();
            _currentExtension = null;
        }

        /// <summary>
        /// Emits the per-extension [PERF] breakdown lines collected during the most recent
        /// <see cref="BuildUI"/> call. Called by the session manager immediately after the
        /// wrapping <c>[PERF] {ext.Name} - BuildUI: Xms</c> line so the sub-step detail sits
        /// underneath it in the log.
        /// </summary>
        public void EmitBuildUIPerfLines(string extensionName)
        {
            if (string.IsNullOrEmpty(extensionName))
                return;

            foreach (var kv in _topLevelMs.OrderByDescending(p => p.Value))
            {
                var count = _topLevelCount.TryGetValue(kv.Key, out var n) ? n : 0;
                _logger.Debug($"[PERF]   {extensionName}/{kv.Key} (x{count}): {kv.Value}ms");
            }

            foreach (var (panelName, elapsedMs) in _panelTimings.OrderByDescending(p => p.ElapsedMs))
            {
                _logger.Debug($"[PERF]   {extensionName}/Panel '{panelName}': {elapsedMs}ms");
            }

            var pp = _postProcessorStats;
            if (pp.Calls > 0)
            {
                _logger.Debug($"[PERF]   {extensionName}/Post: {pp.ProcessMs}ms (x{pp.Calls})");
            }

            var ic = _iconStats;
            if (ic.CacheHits > 0 || ic.CacheMisses > 0 || ic.DecodeMs > 0)
            {
                _logger.Debug(
                    $"[PERF]   {extensionName}/Icons: hits={ic.CacheHits}, " +
                    $"misses={ic.CacheMisses}, decode={ic.DecodeMs}ms");
            }

            var ai = _addItemStats;
            if (ai.Calls > 0)
            {
                _logger.Debug($"[PERF]   {extensionName}/AddItem: {ai.AddItemMs}ms (x{ai.Calls})");
            }

            var sb = _smartButtonStats;
            if (sb != null && sb.Calls > 0)
            {
                _logger.Debug($"[PERF]   {extensionName}/SmartButton: {sb.TotalMs}ms (x{sb.Calls})");
                if (sb.PerButton != null)
                {
                    foreach (var btn in sb.PerButton)
                    {
                        _logger.Debug($"[PERF]     '{btn.Name}': {btn.TotalMs}ms");
                    }
                }
            }
        }

        /// <summary>
        /// Checks if a component is supported based on Revit version constraints and beta status.
        /// </summary>
        /// <param name="component">The component to check.</param>
        /// <returns>True if the component should be loaded, false otherwise.</returns>
        private bool IsComponentSupported(ParsedComponent component)
        {
            var settings = _buildContext.CurrentSettings;
            return ComponentSupportUtils.IsSupported(
                component,
                settings.CurrentVersion,
                settings.LoadBeta,
                _logger);
        }

        private void RecursivelyBuildUI(
            ParsedComponent component,
            ParsedComponent? parentComponent,
            RibbonPanel? parentPanel,
            string tabName,
            ExtensionAssemblyInfo assemblyInfo,
            string? renamedTabTitle = null)
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

            // Check version compatibility and beta status before processing
            if (!IsComponentSupported(component))
            {
                _logger.Debug($"Skipping component '{component.DisplayName}' due to version incompatibility or beta status.");
                return;
            }

            switch (component.Type)
            {
                case CommandComponentType.Tab:
                    HandleTab(component, assemblyInfo);
                    break;

                case CommandComponentType.Panel:
                    HandlePanel(component, tabName, assemblyInfo, renamedTabTitle);
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
            // CreateTab handles find → tag → re-enable in a single ribbon scan.
            // Returns the tab's current Title if it was renamed (e.g. by a translation
            // script), or null if no rename detected.
            var renamedTabTitle = _tabBuilder.CreateTab(component);

            // Get tab name for children using localized title
            var tabText = ExtensionParser.GetComponentTitle(component);

            // Mark tab as touched in the registry (matching Python's set_dirty_flag behavior)
            _ribbonScanner?.MarkElementTouched("tab", tabText);

            // If CreateTab detected a rename, also mark the current (renamed) Title
            // so CleanupOrphanedElements() doesn't deactivate the tab (#3167).
            if (!string.IsNullOrEmpty(renamedTabTitle))
            {
                _ribbonScanner?.MarkElementTouched("tab", renamedTabTitle!);
                _logger.Debug($"Tab '{tabText}' has current Title '{renamedTabTitle}' — marked both as touched.");
            }

            // Recursively build children, passing the renamed title so panels can dual-mark too.
            // Time each child (typically a panel) individually so we can pinpoint a slow panel
            // within an otherwise fast tab.
            var childSw = new Stopwatch();
            foreach (var child in component.Children ?? Enumerable.Empty<ParsedComponent>())
            {
                if (child == null)
                    continue;

                childSw.Restart();
                RecursivelyBuildUI(child, component, null, tabText, assemblyInfo, renamedTabTitle);
                var elapsed = childSw.ElapsedMilliseconds;

                var label = string.IsNullOrEmpty(child.DisplayName) ? child.Type.ToString() : child.DisplayName;
                _panelTimings.Add((label, elapsed));
            }
        }

        private void HandlePanel(ParsedComponent component, string tabName,
            ExtensionAssemblyInfo assemblyInfo, string? renamedTabTitle = null)
        {
            // Use PanelBuilder to create the panel
            var panel = _panelBuilder.CreatePanel(component, tabName);

            // Get panel name for registry (using localized title)
            var panelText = ExtensionParser.GetComponentTitle(component);

            // Mark panel as touched in the registry (matching Python's set_dirty_flag behavior)
            _ribbonScanner?.MarkElementTouched("panel", panelText, tabName);

            // If the parent tab was renamed (e.g. by a translation script), the scanner
            // registered this panel under "panel:{renamedTab}:{panelText}". Mark that
            // key as touched too so cleanup doesn't hide the panel.
            if (!string.IsNullOrEmpty(renamedTabTitle))
            {
                _ribbonScanner?.MarkElementTouched("panel", panelText, renamedTabTitle);
            }

            // Apply background colors if specified
            _panelBuilder.ApplyPanelBackgroundColors(panel, component, tabName);

            // Recursively build children — propagate renamedTabTitle so any nested
            // components that depend on the tab name for registry keys stay consistent.
            foreach (var child in component.Children ?? Enumerable.Empty<ParsedComponent>())
                RecursivelyBuildUI(child, component, panel, tabName, assemblyInfo, renamedTabTitle);
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
            // Get panel name for button tracking
            var panelName = parentPanel?.Name ?? "";

            switch (component.Type)
            {
                case CommandComponentType.Separator:
                    HandleSeparator(parentPanel, assemblyInfo);
                    break;

                case CommandComponentType.Stack:
                    _stackBuilder.BuildStack(component, parentPanel!, assemblyInfo);
                    // Mark all children in the stack as touched
                    foreach (var child in component.Children ?? Enumerable.Empty<ParsedComponent>())
                    {
                        if (!IsStackChildVisible(child))
                            continue;

                        _ribbonScanner?.MarkElementTouched("button", child.DisplayName, panelName);
                    }
                    break;

                case CommandComponentType.ComboBox:
                    if (ItemExistsInPanel(parentPanel, component.DisplayName))
                    {
                        _comboBoxBuilder.UpdateComboBox(component, parentPanel!);
                    }
                    else
                    {
                        _comboBoxBuilder.CreateComboBox(component, parentPanel!);
                    }
                    _ribbonScanner?.MarkElementTouched("button", component.DisplayName, panelName);
                    break;

                default:
                    // Try to build using the button builder factory
                    if (_buttonBuilderFactory.HasBuilder(component.Type))
                    {
                        _buttonBuilderFactory.TryBuild(component, parentPanel!, tabName, assemblyInfo);
                        // Mark button as touched (whether created new or existing)
                        _ribbonScanner?.MarkElementTouched("button", component.DisplayName, panelName);
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

        private bool IsStackChildVisible(ParsedComponent child)
        {
            var settings = _buildContext.CurrentSettings;
            return ComponentSupportUtils.IsStackChildVisible(
                child,
                settings.CurrentVersion,
                settings.LoadBeta,
                _logger);
        }
    }
}
