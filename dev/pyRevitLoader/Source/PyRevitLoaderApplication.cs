using System;
using System.IO;
using System.Reflection;
using Autodesk.Revit.UI;
using Autodesk.Revit.Attributes;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitExtensionParser;

/* Note:
 * It is necessary that this code object do not have any references to IronPython.
 * To ensure the correct version of IronPython dlls are loaded, the OnStartup()
 * methods manually loads the IronPython assemblies before calling into the 
 * ScriptExecutor that has IronPython references
 */
namespace PyRevitLoader
{
    [Regeneration(RegenerationOption.Manual)]
    [Transaction(TransactionMode.Manual)]
    class PyRevitLoaderApplication : IExternalApplication
    {
        public static string LoaderPath => Path.GetDirectoryName(typeof(PyRevitLoaderApplication).Assembly.Location);
        
        // Store the UIControlledApplication for later use
        private static UIControlledApplication _uiControlledApplication;

        // Hook into Revit to allow starting a command.
        Result IExternalApplication.OnStartup(UIControlledApplication application)
        {
            // Store the UIControlledApplication for later use
            _uiControlledApplication = application;
            
            LoadAssembliesInFolder(LoaderPath);
            // We need to also looad dlls from two folders up
            var commonFolder = Path.GetDirectoryName(Path.GetDirectoryName(LoaderPath));
            LoadAssembliesInFolder(commonFolder);

            try
            {
                // we need a UIApplication object to assign as `__revit__` in python...
                var versionNumber = application.ControlledApplication.VersionNumber;
                var fieldName = int.Parse(versionNumber) >= 2017 ? "m_uiapplication" : "m_application";
                var fi = application.GetType().GetField(fieldName, BindingFlags.NonPublic | BindingFlags.Instance);

                var uiApplication = (UIApplication)fi.GetValue(application);

                var executor = new ScriptExecutor(uiApplication);
                var result = ExecuteStartupScript(application);
                if (result == Result.Failed)
                {
                    TaskDialog.Show("Error Loading pyRevit", executor.Message);
                }

                return result;
            }
            catch (Exception ex)
            {
                TaskDialog.Show("Error Loading Startup Script", ex.ToString());
                return Result.Failed;
            }
        }

        private static void LoadAssembliesInFolder(string folder)
        {
            // load all engine assemblies
            // this is to ensure pyRevit is loaded on its own assemblies
            foreach (var engineDll in Directory.GetFiles(folder, "*.dll"))
            {
                try
                {
                    Assembly.LoadFrom(engineDll);
                }
                catch
                {

                }
            }
        }

        private static Result ExecuteStartupScript(UIControlledApplication uiControlledApplication)
        {
            // Always execute Python startup script
            // The Python script will determine whether to use C# or Python session management
            // based on the configuration
            return ExecuteStartUpPython(uiControlledApplication);
        }

        public static Result ExecuteStartUpPython(UIControlledApplication uiControlledApplication)
        {
            // we need a UIApplication object to assign as `__revit__` in python...
            var versionNumber = uiControlledApplication.ControlledApplication.VersionNumber;
            var fieldName = int.Parse(versionNumber) >= 2017 ? "m_uiapplication" : "m_application";
            var fi = uiControlledApplication.GetType().GetField(fieldName, BindingFlags.NonPublic | BindingFlags.Instance);

            var uiApplication = (UIApplication)fi.GetValue(uiControlledApplication);
            // execute StartupScript
            Result result = Result.Succeeded;
            var startupScript = GetStartupScriptPath();
            if (startupScript != null)
            {
                var executor = new ScriptExecutor(uiApplication); // uiControlledApplication);
                result = executor.ExecuteScript(startupScript);
                if (result == Result.Failed)
                {
                    TaskDialog.Show("Error Loading pyRevit", executor.Message);
                }
            }

            return result;
        }

        public static Result LoadSession(object outputWindow = null)
        {
            try
            {
                // Use the stored UIControlledApplication
                if (_uiControlledApplication == null)
                {
                    throw new InvalidOperationException("UIControlledApplication not available. LoadSession can only be called after OnStartup.");
                }
                
                var uiControlledApplication = _uiControlledApplication;
                // we need a UIApplication object to assign as `__revit__` in python...
                var versionNumber = uiControlledApplication.ControlledApplication.VersionNumber;
                var fieldName = int.Parse(versionNumber) >= 2017 ? "m_uiapplication" : "m_application";
                var fi = uiControlledApplication.GetType().GetField(fieldName, BindingFlags.NonPublic | BindingFlags.Instance);

                var uiApplication = (UIApplication)fi.GetValue(uiControlledApplication);

                // Get the current Revit version
                var revitVersion = uiControlledApplication.ControlledApplication.VersionNumber;

                // Create the build strategy enum value - default to ILPack
                var assemblyBuildStrategyType = typeof(pyRevitAssemblyBuilder.AssemblyMaker.AssemblyBuildStrategy);
                var strategyValue = Enum.Parse(assemblyBuildStrategyType, "ILPack");

                // Instantiate the services (following the same pattern as Python code)
                var assemblyBuilderServiceType = typeof(pyRevitAssemblyBuilder.AssemblyMaker.AssemblyBuilderService);
                var assemblyBuilder = Activator.CreateInstance(
                    assemblyBuilderServiceType,
                    revitVersion,
                    strategyValue
                );

                var extensionManagerServiceType = typeof(pyRevitAssemblyBuilder.SessionManager.ExtensionManagerService);
                var extensionManager = Activator.CreateInstance(extensionManagerServiceType);

                var hookManagerType = typeof(pyRevitAssemblyBuilder.SessionManager.HookManager);
                var hookManager = Activator.CreateInstance(hookManagerType);

                var uiManagerServiceType = typeof(pyRevitAssemblyBuilder.SessionManager.UIManagerService);
                var uiManager = Activator.CreateInstance(
                    uiManagerServiceType,
                    uiApplication
                );

                var sessionManagerServiceType = typeof(pyRevitAssemblyBuilder.SessionManager.SessionManagerService);
                var sessionManager = Activator.CreateInstance(
                    sessionManagerServiceType,
                    assemblyBuilder,
                    extensionManager,
                    hookManager,
                    uiManager,
                    outputWindow
                );

                // Load the session using the C# SessionManagerService
                var loadSessionMethod = sessionManagerServiceType.GetMethod("LoadSession");
                loadSessionMethod.Invoke(sessionManager, null);

                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                TaskDialog.Show("Error Loading C# Session", ex.ToString());
                return Result.Failed;
            }
        }
        private static string GetStartupScriptPath()
        {
            var loaderDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            var dllDir = Path.GetDirectoryName(loaderDir);
            return Path.Combine(dllDir, string.Format("{0}.py", Assembly.GetExecutingAssembly().GetName().Name));
        }
        Result IExternalApplication.OnShutdown(UIControlledApplication application)
        {
            // FIXME: deallocate the python shell...
            return Result.Succeeded;
        }
    }
}