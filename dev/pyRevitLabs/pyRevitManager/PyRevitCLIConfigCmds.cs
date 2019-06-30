using System;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using System.Drawing;
using System.Diagnostics;

using pyRevitLabs.Common;
using pyRevitLabs.CommonCLI;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.TargetApps.Revit;
using pyRevitLabs.Language.Properties;

using pyRevitLabs.NLog;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Serialization;

using Console = Colorful.Console;

namespace pyRevitManager {
    internal static class PyRevitCLIConfigCmds {
        static Logger logger = LogManager.GetCurrentClassLogger();

        internal static void
        SeedConfigs(string templateConfigFilePath) {
            PyRevit.SeedConfig(setupFromTemplate: templateConfigFilePath);
        }
    }
}
