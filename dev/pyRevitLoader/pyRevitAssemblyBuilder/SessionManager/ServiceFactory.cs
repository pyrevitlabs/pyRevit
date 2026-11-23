#nullable enable
using System;
using System.Collections.Generic;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.UIManager;
using pyRevitAssemblyBuilder.UIManager.Builders;
using pyRevitAssemblyBuilder.UIManager.Buttons;
using pyRevitAssemblyBuilder.UIManager.Icons;
using pyRevitAssemblyBuilder.UIManager.Panels;
using pyRevitAssemblyBuilder.UIManager.Tooltips;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Factory for creating service instances used by the session manager.
    /// Implements dependency injection by returning interfaces instead of concrete types.
    /// </summary>
    public static class ServiceFactory
    {
        /// <summary>
        /// Creates a logger instance for the C# session manager.
        /// </summary>
        /// <returns>An ILogger instance.</returns>
        public static ILogger CreateLogger()
        {
            return new LoggingHelper();
        }

        /// <summary>
        /// Creates an AssemblyBuilderService instance.
        /// </summary>
        /// <param name="revitVersion">The Revit version number.</param>
        /// <param name="buildStrategy">The build strategy to use.</param>
        /// <param name="logger">The logger instance.</param>
        /// <returns>A new IAssemblyBuilderService instance.</returns>
        public static IAssemblyBuilderService CreateAssemblyBuilderService(string revitVersion, AssemblyBuildStrategy buildStrategy, ILogger logger)
        {
            return new AssemblyBuilderService(revitVersion, buildStrategy, logger);
        }

        /// <summary>
        /// Creates an ExtensionManagerService instance.
        /// </summary>
        /// <returns>A new IExtensionManagerService instance.</returns>
        public static IExtensionManagerService CreateExtensionManagerService(int revitYear = 0, UIApplication? uiApplication = null, ILogger? logger = null)
        {
            Func<string?>? revitUsernameProvider = uiApplication == null
                ? null
                : () => uiApplication.Application?.Username;
            return new ExtensionManagerService(revitYear, revitUsernameProvider, logger);
        }

        /// <summary>
        /// Creates a HookManager instance.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <returns>A new IHookManager instance.</returns>
        public static IHookManager CreateHookManager(ILogger logger)
        {
            return new HookManager(logger);
        }

        /// <summary>
        /// Creates an IconManager instance.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <returns>A new IIconManager instance.</returns>
        public static IIconManager CreateIconManager(ILogger logger)
        {
            return new IconManager(logger);
        }

        /// <summary>
        /// Creates a TooltipManager instance.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <returns>A new ITooltipManager instance.</returns>
        public static ITooltipManager CreateTooltipManager(ILogger logger)
        {
            return new TooltipManager(logger);
        }

        /// <summary>
        /// Creates a ButtonPostProcessor instance.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <param name="iconManager">The icon manager instance.</param>
        /// <param name="tooltipManager">The tooltip manager instance.</param>
        /// <returns>A new IButtonPostProcessor instance.</returns>
        public static IButtonPostProcessor CreateButtonPostProcessor(ILogger logger, IIconManager iconManager, ITooltipManager tooltipManager)
        {
            return new ButtonPostProcessor(logger, iconManager, tooltipManager);
        }

        /// <summary>
        /// Creates a PanelStyleManager instance.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <returns>A new IPanelStyleManager instance.</returns>
        public static IPanelStyleManager CreatePanelStyleManager(ILogger logger)
        {
            return new PanelStyleManager(logger);
        }

        /// <summary>
        /// Creates a TabBuilder instance.
        /// </summary>
        /// <param name="uiApplication">The Revit UIApplication instance.</param>
        /// <param name="logger">The logger instance.</param>
        /// <param name="tabIconDecorator">Must be the instance passed to <see cref="SessionManagerService"/>, which resets and refreshes it around each UI build.</param>
        /// <param name="showTabIcons">Whether tab bundle icons are drawn on the ribbon tabs.</param>
        /// <returns>A new ITabBuilder instance.</returns>
        public static ITabBuilder CreateTabBuilder(UIApplication uiApplication, ILogger logger, ITabIconDecorator tabIconDecorator, bool showTabIcons = true)
        {
            return new TabBuilder(uiApplication, logger, tabIconDecorator, showTabIcons);
        }

        /// <summary>
        /// Creates a PanelBuilder instance.
        /// </summary>
        /// <param name="uiApplication">The Revit UIApplication instance.</param>
        /// <param name="logger">The logger instance.</param>
        /// <param name="styleManager">The panel style manager instance.</param>
        /// <returns>A new IPanelBuilder instance.</returns>
        public static IPanelBuilder CreatePanelBuilder(UIApplication uiApplication, ILogger logger, IPanelStyleManager styleManager)
        {
            return new PanelBuilder(uiApplication, logger, styleManager);
        }

        /// <summary>
        /// Creates a ButtonBuilderFactory with all registered button builders.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor instance.</param>
        /// <param name="buildContext">Shared build context that carries the current per-build settings.</param>
        /// <param name="smartButtonScriptInitializer">The shared SmartButton script initializer.</param>
        /// <returns>A new IButtonBuilderFactory instance.</returns>
        public static IButtonBuilderFactory CreateButtonBuilderFactory(ILogger logger, IButtonPostProcessor buttonPostProcessor, BuildContext buildContext, SmartButtonScriptInitializer smartButtonScriptInitializer)
        {
            // Create individual button builders
            var linkButtonBuilder = new LinkButtonBuilder(buildContext, logger, buttonPostProcessor);
            var pushButtonBuilder = new PushButtonBuilder(logger, buttonPostProcessor, smartButtonScriptInitializer);
            var panelButtonBuilder = new PanelButtonBuilder(logger, buttonPostProcessor);
            var pulldownButtonBuilder = new PulldownButtonBuilder(buildContext, logger, buttonPostProcessor, linkButtonBuilder, smartButtonScriptInitializer);
            var splitButtonBuilder = new SplitButtonBuilder(buildContext, logger, buttonPostProcessor, linkButtonBuilder, smartButtonScriptInitializer);

            // Create factory with all builders
            var builders = new List<IButtonBuilder>
            {
                pushButtonBuilder,
                panelButtonBuilder,
                linkButtonBuilder,
                pulldownButtonBuilder,
                splitButtonBuilder
            };

            return new ButtonBuilderFactory(logger, builders);
        }

        /// <summary>
        /// Creates a StackBuilder instance.
        /// </summary>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor instance.</param>
        /// <param name="buildContext">Shared build context that carries the current per-build settings.</param>
        /// <param name="smartButtonScriptInitializer">The shared SmartButton script initializer.</param>
        /// <returns>A new IStackBuilder instance.</returns>
        public static IStackBuilder CreateStackBuilder(ILogger logger, IButtonPostProcessor buttonPostProcessor, BuildContext buildContext, SmartButtonScriptInitializer smartButtonScriptInitializer)
        {
            var linkButtonBuilder = new LinkButtonBuilder(buildContext, logger, buttonPostProcessor);
            var pulldownButtonBuilder = new PulldownButtonBuilder(buildContext, logger, buttonPostProcessor, linkButtonBuilder, smartButtonScriptInitializer);
            var splitButtonBuilder = new SplitButtonBuilder(buildContext, logger, buttonPostProcessor, linkButtonBuilder, smartButtonScriptInitializer);

            return new StackBuilder(buildContext, logger, buttonPostProcessor, linkButtonBuilder, pulldownButtonBuilder, splitButtonBuilder, smartButtonScriptInitializer);
        }

        /// <summary>
        /// Creates a ComboBoxBuilder instance.
        /// </summary>
        /// <param name="uiApplication">The Revit UIApplication instance.</param>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor instance.</param>
        /// <returns>A new IComboBoxBuilder instance.</returns>
        public static IComboBoxBuilder CreateComboBoxBuilder(UIApplication uiApplication, ILogger logger, IButtonPostProcessor buttonPostProcessor)
        {
            var comboBoxScriptInitializer = new ComboBoxScriptInitializer(uiApplication, logger);
            return new ComboBoxBuilder(logger, buttonPostProcessor, comboBoxScriptInitializer);
        }

        /// <summary>
        /// Creates the checkbox builder and the script initializer that wires checkbox handlers.
        /// </summary>
        /// <param name="panelStyleManager">Resolves the AdWindows panel that hosts each checkbox.</param>
        /// <param name="libraryPathsProvider">Supplies the installed library extensions' search paths, so checkbox scripts can import from them like commands.</param>
        /// <remarks>
        /// Important: creating the initializer releases the checkbox handlers and engine of the
        /// previous session load, so call this once per load.
        /// </remarks>
        public static ICheckBoxBuilder CreateCheckBoxBuilder(
            UIApplication uiApplication,
            ILogger logger,
            IPanelStyleManager panelStyleManager,
            Func<IEnumerable<string>>? libraryPathsProvider = null)
        {
            var checkBoxScriptInitializer = new CheckBoxScriptInitializer(uiApplication, logger, libraryPathsProvider);
            return new CheckBoxBuilder(logger, panelStyleManager, checkBoxScriptInitializer);
        }

        /// <summary>
        /// Creates a UIManagerService instance.
        /// </summary>
        /// <param name="uiApplication">The Revit UIApplication instance.</param>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor instance.</param>
        /// <param name="tabBuilder">The tab builder instance.</param>
        /// <param name="panelBuilder">The panel builder instance.</param>
        /// <param name="buttonBuilderFactory">The button builder factory instance.</param>
        /// <param name="stackBuilder">The stack builder instance.</param>
        /// <param name="comboBoxBuilder">The combo box builder instance.</param>
        /// <returns>A new IUIRibbonScanner instance.</returns>
        public static IUIRibbonScanner CreateUIRibbonScanner(ILogger logger)
        {
            return new RibbonScanner(logger);
        }

        /// <summary>
        /// Creates a UIManagerService instance.
        /// </summary>
        public static IUIManagerService CreateUIManagerService(
            UIApplication uiApplication,
            ILogger logger,
            IButtonPostProcessor buttonPostProcessor,
            ITabBuilder tabBuilder,
            IPanelBuilder panelBuilder,
            IButtonBuilderFactory buttonBuilderFactory,
            IStackBuilder stackBuilder,
            IComboBoxBuilder comboBoxBuilder,
            ICheckBoxBuilder checkBoxBuilder,
            BuildContext buildContext,
            IUIRibbonScanner? ribbonScanner = null)
        {
            return new UIManagerService(
                uiApplication,
                logger,
                buttonPostProcessor,
                tabBuilder,
                panelBuilder,
                buttonBuilderFactory,
                stackBuilder,
                comboBoxBuilder,
                checkBoxBuilder,
                buildContext,
                ribbonScanner);
        }

        /// <summary>
        /// Creates a SessionManagerService instance with all required dependencies.
        /// This is the main entry point for creating a fully configured session manager.
        /// </summary>
        /// <param name="revitVersion">The Revit version number (e.g., "2024").</param>
        /// <param name="buildStrategy">The build strategy to use for assembly generation.</param>
        /// <param name="uiApplication">The Revit UIApplication instance.</param>
        /// <returns>A new ISessionManagerService instance.</returns>
        /// <remarks>
        ///     Important: configuration invalidation must remain before <see cref="CreateLogger"/> and <see cref="UIManagerService"/> construction; moving it later reinstates stale session settings from issue #3776.
        /// </remarks>
        public static ISessionManagerService CreateSessionManagerService(
            string revitVersion,
            AssemblyBuildStrategy buildStrategy,
            UIApplication uiApplication)
        {
            PyRevitConfig.ClearCache();

            // Create logger first - it's used by all other services.
            var logger = CreateLogger();
            ExtensionParser.SetLogger(new ExtensionParserLoggerAdapter(logger));

            // Create core services
            var assemblyBuilder = CreateAssemblyBuilderService(revitVersion, buildStrategy, logger);
            int.TryParse(revitVersion, out int revitYear);
            var extensionManager = CreateExtensionManagerService(revitYear, uiApplication, logger);
            var hookManager = CreateHookManager(logger);

            // Create icon and tooltip managers
            var iconManager = CreateIconManager(logger);
            var tooltipManager = CreateTooltipManager(logger);
            var buttonPostProcessor = CreateButtonPostProcessor(logger, iconManager, tooltipManager);

            // Create UI builders. The BuildContext is shared by reference between the UIManager
            // (writer) and every builder that needs to know the current beta / version snapshot,
            // so all readers observe the same value within a single BuildUI call.
            var buildContext = new BuildContext();
            var panelStyleManager = CreatePanelStyleManager(logger);
            var themeDetector = new RevitThemeDetector(logger);
            var tabIconDecorator = new TabIconDecorator(path => iconManager.LoadBitmapSource(path), themeDetector.IsDarkTheme);
            var tabBuilder = CreateTabBuilder(uiApplication, logger, tabIconDecorator, ReadShowTabIcons(logger));
            var panelBuilder = CreatePanelBuilder(uiApplication, logger, panelStyleManager);
            var smartButtonScriptInitializer = new SmartButtonScriptInitializer(uiApplication, logger, buildContext);
            var buttonBuilderFactory = CreateButtonBuilderFactory(logger, buttonPostProcessor, buildContext, smartButtonScriptInitializer);
            var stackBuilder = CreateStackBuilder(logger, buttonPostProcessor, buildContext, smartButtonScriptInitializer);
            var comboBoxBuilder = CreateComboBoxBuilder(uiApplication, logger, buttonPostProcessor);
            var checkBoxBuilder = CreateCheckBoxBuilder(
                uiApplication,
                logger,
                panelStyleManager,
                () => LibraryExtensionSearchPaths.Collect(extensionManager.GetInstalledLibraryExtensions()));

            // Create ribbon scanner for UI cleanup
            var ribbonScanner = CreateUIRibbonScanner(logger);

            // Create UIManager with all dependencies including ribbon scanner
            var uiManager = CreateUIManagerService(
                uiApplication,
                logger,
                buttonPostProcessor,
                tabBuilder,
                panelBuilder,
                buttonBuilderFactory,
                stackBuilder,
                comboBoxBuilder,
                checkBoxBuilder,
                buildContext,
                ribbonScanner);

            return new SessionManagerService(
                assemblyBuilder,
                extensionManager,
                hookManager,
                uiManager,
                ribbonScanner,
                logger,
                tabIconDecorator);
        }

        /// <summary>
        /// Creates a SessionManagerService instance with custom service implementations.
        /// Use this overload for testing or when custom implementations are needed.
        /// </summary>
        /// <param name="assemblyBuilder">Custom assembly builder service.</param>
        /// <param name="extensionManager">Custom extension manager service.</param>
        /// <param name="hookManager">Custom hook manager.</param>
        /// <param name="uiManager">Custom UI manager service.</param>
        /// <param name="ribbonScanner">Custom ribbon scanner service.</param>
        /// <param name="logger">Custom logger.</param>
        /// <returns>A new ISessionManagerService instance.</returns>
        /// <remarks>Callers injecting custom services own configuration freshness; this overload does not invalidate the shared configuration.</remarks>
        public static ISessionManagerService CreateSessionManagerService(
            IAssemblyBuilderService assemblyBuilder,
            IExtensionManagerService extensionManager,
            IHookManager hookManager,
            IUIManagerService uiManager,
            IUIRibbonScanner ribbonScanner,
            ILogger logger)
        {
            ExtensionParser.SetLogger(new ExtensionParserLoggerAdapter(logger));
            return new SessionManagerService(
                assemblyBuilder,
                extensionManager,
                hookManager,
                uiManager,
                ribbonScanner,
                logger);
        }

        private static bool ReadShowTabIcons(ILogger logger)
        {
            try
            {
                return PyRevitConfig.Load().ShowTabIcons;
            }
            catch (Exception ex)
            {
                logger.Debug($"Failed to read show_tab_icons config; showing tab icons. Exception: {ex.Message}");
                return true;
            }
        }
    }
}
