using System;
using System.IO;
using System.Reflection;
using System.Diagnostics;
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
                catch (Exception ex)
                {
                    // Log assembly load failures - some assemblies may fail to load and that's acceptable
                    Trace.WriteLine($"Failed to load assembly '{engineDll}': {ex.Message}");
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
                var versionNumber = uiControlledApplication.ControlledApplication.VersionNumber;
                var fieldName = int.Parse(versionNumber) >= 2017 ? "m_uiapplication" : "m_application";
                var fi = uiControlledApplication.GetType().GetField(fieldName, BindingFlags.NonPublic | BindingFlags.Instance);
                var uiApplication = (UIApplication)fi.GetValue(uiControlledApplication);

                // Instantiate all services
                var typeGenerator = new CommandTypeGenerator();
                var assemblyBuilder = new AssemblyBuilderService(typeGenerator, versionNumber);
                var extensionManager = new ExtensionManagerService();
                var hookManager = new HookManager();
                var uiManager = new UIManagerService(uiApplication);

                var sessionManager = new SessionManagerService(
                    assemblyBuilder,
                    extensionManager,
                    hookManager,
                    uiManager
                );

                sessionManager.LoadSession();

                // execute light version of StartupScript python script  
                Result result = Result.Succeeded;
                var startupScript = GetStartupScriptPath(true);
                if (startupScript != null)
                {
                    var executor = new ScriptExecutor(uiApplication); // uiControlledApplication);
                    result = executor.ExecuteScript(startupScript);
                    if (result == Result.Failed)
                    {
                        TaskDialog.Show("Error Loading pyRevit", executor.Message);
                    }
                }



                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                TaskDialog.Show("Error Starting pyRevit Session", ex.ToString());
                return Result.Failed;
            }
        }

        public static Result LoadSession(object outputWindow = null, string buildStrategy = null)
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

                // Determine build strategy: use provided parameter, or read from config, or default to ILPack
                var assemblyBuildStrategyType = typeof(pyRevitAssemblyBuilder.AssemblyMaker.AssemblyBuildStrategy);
                object strategyValue;
                
                if (!string.IsNullOrEmpty(buildStrategy))
                {
                    // Use provided build strategy from Python
                    strategyValue = Enum.Parse(assemblyBuildStrategyType, buildStrategy);
                }
                else
                {
                    // Fallback: read from config
                    try
                    {
                        var config = PyRevitConfig.Load();
                        var strategyName = config.NewLoaderRoslyn ? "Roslyn" : "ILPack";
                        strategyValue = Enum.Parse(assemblyBuildStrategyType, strategyName);
                    }
                    catch
                    {
                        // Final fallback: default to ILPack
                        strategyValue = Enum.Parse(assemblyBuildStrategyType, "ILPack");
                    }
                }

                // Create services using factory
                var strategyEnum = (pyRevitAssemblyBuilder.AssemblyMaker.AssemblyBuildStrategy)strategyValue;
                var sessionManager = pyRevitAssemblyBuilder.SessionManager.ServiceFactory.CreateSessionManagerService(
                    revitVersion,
                    strategyEnum,
                    uiApplication,
                    outputWindow);

                // Load the session using the C# SessionManagerService
                sessionManager.LoadSession();

                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                // Log detailed error information before showing dialog
                Trace.WriteLine($"Error Loading C# Session: {ex}");
                Trace.WriteLine($"Stack Trace: {ex.StackTrace}");
                
                // Show user-friendly error dialog
                TaskDialog.Show("Error Loading C# Session", 
                    $"An error occurred while loading the C# session:\n\n{ex.Message}\n\nCheck the output window for details.");
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