using System;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.UIManager;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Factory for creating service instances used by the session manager.
    /// </summary>
    public static class ServiceFactory
    {
        /// <summary>
        /// Creates an AssemblyBuilderService instance.
        /// </summary>
        /// <param name="revitVersion">The Revit version number.</param>
        /// <param name="buildStrategy">The build strategy to use.</param>
        /// <returns>A new AssemblyBuilderService instance.</returns>
        public static AssemblyBuilderService CreateAssemblyBuilderService(string revitVersion, AssemblyBuildStrategy buildStrategy)
        {
            return new AssemblyBuilderService(revitVersion, buildStrategy);
        }

        /// <summary>
        /// Creates an ExtensionManagerService instance.
        /// </summary>
        /// <returns>A new ExtensionManagerService instance.</returns>
        public static ExtensionManagerService CreateExtensionManagerService()
        {
            return new ExtensionManagerService();
        }

        /// <summary>
        /// Creates a HookManager instance.
        /// </summary>
        /// <returns>A new HookManager instance.</returns>
        public static HookManager CreateHookManager()
        {
            return new HookManager();
        }

        /// <summary>
        /// Creates a UIManagerService instance.
        /// </summary>
        /// <param name="uiApplication">The Revit UIApplication instance.</param>
        /// <returns>A new UIManagerService instance.</returns>
        public static UIManagerService CreateUIManagerService(UIApplication uiApplication)
        {
            return new UIManagerService(uiApplication);
        }

        /// <summary>
        /// Creates a SessionManagerService instance with all required dependencies.
        /// </summary>
        /// <param name="revitVersion">The Revit version number (e.g., "2024").</param>
        /// <param name="buildStrategy">The build strategy to use for assembly generation.</param>
        /// <param name="uiApplication">The Revit UIApplication instance.</param>
        /// <param name="pythonLogger">Optional Python logger instance for integration with pyRevit's logging system.</param>
        /// <returns>A new SessionManagerService instance.</returns>
        public static SessionManagerService CreateSessionManagerService(
            string revitVersion,
            AssemblyBuildStrategy buildStrategy,
            UIApplication uiApplication,
            object pythonLogger = null)
        {
            var assemblyBuilder = CreateAssemblyBuilderService(revitVersion, buildStrategy);
            var extensionManager = CreateExtensionManagerService();
            var hookManager = CreateHookManager();
            var uiManager = CreateUIManagerService(uiApplication);

            return new SessionManagerService(
                assemblyBuilder, 
                extensionManager,
                hookManager,
                uiManager,
                pythonLogger);
        }
    }
}

