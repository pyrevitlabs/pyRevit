using pyRevitExtensionParser;
using pyRevitLabs.NLog;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class HookManager
    {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public void RegisterHooks(ParsedExtension extension)
        {
            if (extension == null)
                return;

            var hooks = GetScriptsFromDirectory(extension, "hooks");
            var checks = GetScriptsFromDirectory(extension, "checks");

            foreach (var hook in hooks)
            {
                logger.Debug("Found hook script: {0}", hook);
            }

            foreach (var check in checks)
            {
                logger.Debug("Found check script: {0}", check);
            }

            // Future: implement actual execution logic for scripts if needed
        }

        private IEnumerable<string> GetScriptsFromDirectory(ParsedExtension extension, string subdirectory)
        {
            var scriptsPath = Path.Combine(extension.Directory, subdirectory);
            return Directory.Exists(scriptsPath)
                ? Directory.GetFiles(scriptsPath)
                : Enumerable.Empty<string>();
        }
    }
}
