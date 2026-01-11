using pyRevitExtensionParser;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class HookManager : IHookManager
    {
        private readonly ILogger _logger;

        public HookManager(ILogger logger)
        {
            _logger = logger ?? throw new ArgumentNullException(nameof(logger));
        }

        public void RegisterHooks(ParsedExtension extension)
        {
            if (extension == null)
                return;

            var hooks = GetScriptsFromDirectory(extension, "hooks");
            var checks = GetScriptsFromDirectory(extension, "checks");

            foreach (var hook in hooks)
            {
                _logger.Debug($"Found hook script: {hook}");
            }

            foreach (var check in checks)
            {
                _logger.Debug($"Found check script: {check}");
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
