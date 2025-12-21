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
        /// <param name="pythonLogger">The Python logger instance.</param>
        /// <returns>A new AssemblyBuilderService instance.</returns>
        public static AssemblyBuilderService CreateAssemblyBuilderService(string revitVersion, AssemblyBuildStrategy buildStrategy, object pythonLogger)
        {
            return new AssemblyBuilderService(revitVersion, buildStrategy, pythonLogger);
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
        /// <param name="pythonLogger">The Python logger instance.</param>
        /// <returns>A new HookManager instance.</returns>
        public static HookManager CreateHookManager(object pythonLogger)
        {
            return new HookManager(pythonLogger);
        }

        /// <summary>
        /// Creates a UIManagerService instance.
        /// </summary>
        /// <param name="uiApplication">The Revit UIApplication instance.</param>
        /// <param name="pythonLogger">The Python logger instance.</param>
        /// <returns>A new UIManagerService instance.</returns>
        public static UIManagerService CreateUIManagerService(UIApplication uiApplication, object pythonLogger)
        {
            return new UIManagerService(uiApplication, pythonLogger);
        }

        /// <summary>
        /// Creates a SessionManagerService instance with all required dependencies.
        /// </summary>
        /// <param name="revitVersion">The Revit version number (e.g., "2024").</param>
        /// <param name="buildStrategy">The build strategy to use for assembly generation.</param>
        /// <param name="uiApplication">The Revit UIApplication instance.</param>
        /// <param name="pythonLogger">The Python logger instance for integration with pyRevit's logging system.</param>
        /// <returns>A new SessionManagerService instance.</returns>
        public static SessionManagerService CreateSessionManagerService(
            string revitVersion,
            AssemblyBuildStrategy buildStrategy,
            UIApplication uiApplication,
            object pythonLogger)
        {
            var assemblyBuilder = CreateAssemblyBuilderService(revitVersion, buildStrategy, pythonLogger);
            var extensionManager = CreateExtensionManagerService();
            var hookManager = CreateHookManager(pythonLogger);
            var uiManager = CreateUIManagerService(uiApplication, pythonLogger);

            return new SessionManagerService(
                assemblyBuilder, 
                extensionManager,
                hookManager,
                uiManager,
                pythonLogger);
        }
    }
}

