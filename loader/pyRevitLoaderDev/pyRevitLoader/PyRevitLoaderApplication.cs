using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Reflection.Emit;
using System.Xml.Linq;
using Autodesk.Revit;
using Autodesk.Revit.UI;
using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.Attributes;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Configuration;
using System.Collections.Specialized;

namespace PyRevitLoader
{
    [Regeneration(RegenerationOption.Manual)]
    [Transaction(TransactionMode.Manual)]
    class PyRevitLoaderApplication : IExternalApplication
    {
        private static string versionNumber;

        /// <summary>
        /// Hook into Revit to allow starting a command.
        /// </summary>
        Result IExternalApplication.OnStartup(UIControlledApplication application)
        {

            try
            {
                versionNumber = application.ControlledApplication.VersionNumber;
                if (application.ControlledApplication.VersionName.ToLower().Contains("vasari"))
                {
                    versionNumber = "_Vasari";
                }

                ExecuteStartupScript(application);

                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                TaskDialog.Show("Error setting up PyRevitLoader", ex.ToString());
                return Result.Failed;
            }
        }

        private static void ExecuteStartupScript(UIControlledApplication uiControlledApplication)
        {
            // we need a UIApplication object to assign as `__revit__` in python...
            var versionNumber = uiControlledApplication.ControlledApplication.VersionNumber;
            var fieldName = versionNumber == "2017" ? "m_uiapplication": "m_application";
            var fi = uiControlledApplication.GetType().GetField(fieldName, BindingFlags.NonPublic | BindingFlags.Instance);

            var uiApplication = (UIApplication)fi.GetValue(uiControlledApplication);
            // execute StartupScript
            var startupScript = GetStartupScriptSource();
            if (startupScript != null)
            {
                var executor = new ScriptExecutor(uiApplication, uiControlledApplication);
                var result = executor.ExecuteScript(startupScript, GetStartupScriptPath(), "", Path.GetFileName(GetStartupScriptPath()), "", false);
                if (result == (int)Result.Failed)
                {
                    TaskDialog.Show("PyRevitLoader", executor.Message);
                }
            }
        }

        private static string GetStartupScriptPath()
        {
            return ProcessRelativeOrAbsolutePath(ExtractDLLConfigParameter("startupscript"));
        }

        public static string GetImportLibraryPath()
        {
            return ProcessRelativeOrAbsolutePath(ExtractDLLConfigParameter("lib"));
        }

        public static string ExtractDLLConfigParameter(string parameter)
        {
            ExeConfigurationFileMap map = new ExeConfigurationFileMap();
            map.ExeConfigFilename = Assembly.GetExecutingAssembly().Location + ".config";
            Configuration libConfig = ConfigurationManager.OpenMappedExeConfiguration(map, ConfigurationUserLevel.None);
            AppSettingsSection section = (libConfig.GetSection("appSettings") as AppSettingsSection);
            return section.Settings[parameter].Value;
        }

        public static string GetStartupScriptSource()
        {
            var startupScriptFullPath = GetStartupScriptPath();
            if (File.Exists(startupScriptFullPath))
            {
                using (var reader = File.OpenText(startupScriptFullPath))
                {
                    var source = reader.ReadToEnd();
                    return source;
                }
            }
            // no startup script found
            return null;
        }

        private static string ProcessRelativeOrAbsolutePath(string path)
        {
            if (Path.IsPathRooted(path))
            {
                return path;
            }
            else
            {
                var dllfolder = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
                return Path.Combine(dllfolder, path);
            }
        }

        Result IExternalApplication.OnShutdown(UIControlledApplication application)
        {
            // FIXME: deallocate the python shell...
            return Result.Succeeded;
        }
    }
}
