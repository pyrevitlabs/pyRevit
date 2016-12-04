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

namespace PyRevitBaseClasses
{
    class ExternalConfig
    {
        public static string ExtractDLLConfigParameter(string parameter)
        {
            ExeConfigurationFileMap map = new ExeConfigurationFileMap();
            map.ExeConfigFilename = Assembly.GetExecutingAssembly().Location + ".config";
            Configuration libConfig = ConfigurationManager.OpenMappedExeConfiguration(map, ConfigurationUserLevel.None);
            AppSettingsSection section = (libConfig.GetSection("appSettings") as AppSettingsSection);
            return section.Settings[parameter].Value;
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
    }
}
