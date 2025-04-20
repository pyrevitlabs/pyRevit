using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class HookManager
    {
        public void RegisterHooks(WrappedExtension extension)
        {
            if (extension == null)
                return;

            var hooks = GetHookScripts(extension);
            var checks = GetCheckScripts(extension);

            foreach (var hook in hooks)
            {
                Console.WriteLine($"[pyRevit] Found hook script: {hook}");
            }

            foreach (var check in checks)
            {
                Console.WriteLine($"[pyRevit] Found check script: {check}");
            }

            // Future: implement actual execution logic for scripts if needed
        }

        private IEnumerable<string> GetHookScripts(WrappedExtension extension)
        {
            var hooksPath = Path.Combine(extension.Directory, "hooks");
            return Directory.Exists(hooksPath)
                ? Directory.GetFiles(hooksPath)
                : Enumerable.Empty<string>();
        }

        private IEnumerable<string> GetCheckScripts(WrappedExtension extension)
        {
            var checksPath = Path.Combine(extension.Directory, "checks");
            return Directory.Exists(checksPath)
                ? Directory.GetFiles(checksPath)
                : Enumerable.Empty<string>();
        }
    }
}
