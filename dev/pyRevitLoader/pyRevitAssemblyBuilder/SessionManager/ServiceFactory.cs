#nullable enable
using System.Collections.Generic;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.UIManager;
using pyRevitAssemblyBuilder.UIManager.Builders;
using pyRevitAssemblyBuilder.UIManager.Buttons;
using pyRevitAssemblyBuilder.UIManager.Icons;
using pyRevitAssemblyBuilder.UIManager.Panels;
using pyRevitAssemblyBuilder.UIManager.Tooltips;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Factory for creating service instances used by the session manager.
    /// Implements dependency injection by returning interfaces instead of concrete types.
    /// </summary>
    public static class ServiceFactory
    {
        /// <summary>
        /// Creates a logger instance from a Python logger object.
        /// </summary>
        /// <param name="pythonLogger">The Python logger instance.</param>
        /// <returns>An ILogger instance.</returns>
        public static ILogger CreateLogger(object? pythonLogger)
        {
            return new LoggingHelper(pythonLogger);
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
        public static IExtensionManagerService CreateExtensionManagerService()
        {
            return new ExtensionManagerService();
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
        /// <returns>A new ITabBuilder instance.</returns>
        public static ITabBuilder CreateTabBuilder(UIApplication uiApplication, ILogger logger)
        {
            return new TabBuilder(uiApplication, logger);
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
        /// <param name="uiApplication">The Revit UIApplication instance.</param>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor instance.</param>
        /// <returns>A new IButtonBuilderFactory instance.</returns>
        public static IButtonBuilderFactory CreateButtonBuilderFactory(UIApplication uiApplication, ILogger logger, IButtonPostProcessor buttonPostProcessor)
        {
            // Create script initializers
            var smartButtonScriptInitializer = new SmartButtonScriptInitializer(uiApplication, logger);
            
            // Create individual button builders
            var linkButtonBuilder = new LinkButtonBuilder(logger, buttonPostProcessor);
            var pushButtonBuilder = new PushButtonBuilder(logger, buttonPostProcessor, smartButtonScriptInitializer);
            var panelButtonBuilder = new PanelButtonBuilder(logger, buttonPostProcessor);
            var pulldownButtonBuilder = new PulldownButtonBuilder(logger, buttonPostProcessor, linkButtonBuilder, smartButtonScriptInitializer);
            var splitButtonBuilder = new SplitButtonBuilder(logger, buttonPostProcessor, linkButtonBuilder);

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
        /// <param name="uiApplication">The Revit UIApplication instance.</param>
        /// <param name="logger">The logger instance.</param>
        /// <param name="buttonPostProcessor">The button post-processor instance.</param>
        /// <returns>A new IStackBuilder instance.</returns>
        public static IStackBuilder CreateStackBuilder(UIApplication uiApplication, ILogger logger, IButtonPostProcessor buttonPostProcessor)
        {
            var smartButtonScriptInitializer = new SmartButtonScriptInitializer(uiApplication, logger);
            var linkButtonBuilder = new LinkButtonBuilder(logger, buttonPostProcessor);
            var pulldownButtonBuilder = new PulldownButtonBuilder(logger, buttonPostProcessor, linkButtonBuilder, smartButtonScriptInitializer);
            
            return new StackBuilder(logger, buttonPostProcessor, linkButtonBuilder, pulldownButtonBuilder, smartButtonScriptInitializer);
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
        /// <returns>A new IUIManagerService instance.</returns>
        public static IUIManagerService CreateUIManagerService(
            UIApplication uiApplication,
            ILogger logger,
            IButtonPostProcessor buttonPostProcessor,
            ITabBuilder tabBuilder,
            IPanelBuilder panelBuilder,
            IButtonBuilderFactory buttonBuilderFactory,
            IStackBuilder stackBuilder,
            IComboBoxBuilder comboBoxBuilder)
        {
            return new UIManagerService(
                uiApplication,
                logger,
                buttonPostProcessor,
                tabBuilder,
                panelBuilder,
                buttonBuilderFactory,
                stackBuilder,
                comboBoxBuilder);
        }

        /// <summary>
        /// Creates a SessionManagerService instance with all required dependencies.
        /// This is the main entry point for creating a fully configured session manager.
        /// </summary>
        /// <param name="revitVersion">The Revit version number (e.g., "2024").</param>
        /// <param name="buildStrategy">The build strategy to use for assembly generation.</param>
        /// <param name="uiApplication">The Revit UIApplication instance.</param>
        /// <param name="pythonLogger">The Python logger instance for integration with pyRevit's logging system.</param>
        /// <returns>A new ISessionManagerService instance.</returns>
        public static ISessionManagerService CreateSessionManagerService(
            string revitVersion,
            AssemblyBuildStrategy buildStrategy,
            UIApplication uiApplication,
            object? pythonLogger)
        {
            // Create logger first - it's used by all other services
            var logger = CreateLogger(pythonLogger);
            
            // Create core services
            var assemblyBuilder = CreateAssemblyBuilderService(revitVersion, buildStrategy, logger);
            var extensionManager = CreateExtensionManagerService();
            var hookManager = CreateHookManager(logger);
            
            // Create icon and tooltip managers
            var iconManager = CreateIconManager(logger);
            var tooltipManager = CreateTooltipManager(logger);
            var buttonPostProcessor = CreateButtonPostProcessor(logger, iconManager, tooltipManager);
            
            // Create UI builders
            var panelStyleManager = CreatePanelStyleManager(logger);
            var tabBuilder = CreateTabBuilder(uiApplication, logger);
            var panelBuilder = CreatePanelBuilder(uiApplication, logger, panelStyleManager);
            var buttonBuilderFactory = CreateButtonBuilderFactory(uiApplication, logger, buttonPostProcessor);
            var stackBuilder = CreateStackBuilder(uiApplication, logger, buttonPostProcessor);
            var comboBoxBuilder = CreateComboBoxBuilder(uiApplication, logger, buttonPostProcessor);
            
            // Create UIManager with all dependencies
            var uiManager = CreateUIManagerService(
                uiApplication,
                logger,
                buttonPostProcessor,
                tabBuilder,
                panelBuilder,
                buttonBuilderFactory,
                stackBuilder,
                comboBoxBuilder);

            return new SessionManagerService(
                assemblyBuilder, 
                extensionManager,
                hookManager,
                uiManager,
                logger);
        }
        
        /// <summary>
        /// Creates a SessionManagerService instance with custom service implementations.
        /// Use this overload for testing or when custom implementations are needed.
        /// </summary>
        /// <param name="assemblyBuilder">Custom assembly builder service.</param>
        /// <param name="extensionManager">Custom extension manager service.</param>
        /// <param name="hookManager">Custom hook manager.</param>
        /// <param name="uiManager">Custom UI manager service.</param>
        /// <param name="logger">Custom logger.</param>
        /// <returns>A new ISessionManagerService instance.</returns>
        public static ISessionManagerService CreateSessionManagerService(
            IAssemblyBuilderService assemblyBuilder,
            IExtensionManagerService extensionManager,
            IHookManager hookManager,
            IUIManagerService uiManager,
            ILogger logger)
        {
            return new SessionManagerService(
                assemblyBuilder,
                extensionManager,
                hookManager,
                uiManager,
                logger);
        }
    }
}
