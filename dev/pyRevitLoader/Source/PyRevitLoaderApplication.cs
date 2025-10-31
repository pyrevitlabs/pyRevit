using System;
using System.IO;
using System.Reflection;
using Autodesk.Revit.UI;
using Autodesk.Revit.Attributes;

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
        private static string SelectedEngineDir = null;

        // Hook into Revit to allow starting a command.
        Result IExternalApplication.OnStartup(UIControlledApplication application)
        {
            // Decide engine folder by Revit version and load assemblies from there
            var revVersion = uiControlledApplication.ControlledApplication.VersionNumber;
            var targetEngineDir = ResolveEngineFolder(revVersion);

            // Always load selected engine dir first so its assemblies win binding
            LoadAssembliesInFolder(targetEngineDir);
            SelectedEngineDir = targetEngineDir;

            // Also load common folder (bin/<tfm>) for any shared dlls
            var commonFolder = Path.GetDirectoryName(targetEngineDir);
            LoadAssembliesInFolder(commonFolder);

            try
            {
                return ExecuteStartupScript(application);
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

        private static string ResolveEngineFolder(string revitVersion)
        {
            // LoaderPath currently points to bin/<tfm>/engines/<ipyFolder>
            var currentEngineDir = LoaderPath;
            var enginesDir = Path.GetDirectoryName(currentEngineDir); // .../engines
            var binTfmDir = Path.GetDirectoryName(enginesDir); // .../bin/<tfm>
            var binRoot = Path.GetDirectoryName(binTfmDir); // .../bin
            var ipyFolderName = new DirectoryInfo(currentEngineDir).Name;

            int ver;
            if (!int.TryParse(revitVersion, out ver))
                return currentEngineDir;

            var tfm = ver >= 2027 ? "net10" : (ver >= 2025 ? "netcore" : "netfx");
            var candidate = Path.Combine(binRoot, tfm, "engines", ipyFolderName);
            return Directory.Exists(candidate) ? candidate : currentEngineDir;
        }

        private static Result ExecuteStartupScript(UIControlledApplication uiControlledApplication)
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

        private static string GetStartupScriptPath()
        {
            // Use the selected engine dir (bin/<tfm>/engines/<ipy>),
            // and then one level up for the dll directory hosting the startup script.
            var loaderDir = SelectedEngineDir ?? Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
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
