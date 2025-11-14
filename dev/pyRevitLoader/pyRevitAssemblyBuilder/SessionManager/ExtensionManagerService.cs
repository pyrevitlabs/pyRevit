using System.Collections.Generic;
using System.Linq;
using pyRevitExtensionParser;
using static pyRevitExtensionParser.ExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class ExtensionManagerService
    {
        public IEnumerable<ParsedExtension> GetInstalledExtensions()
        {
            var installedExtensions = ExtensionParser.ParseInstalledExtensions();
            return installedExtensions;
        }

        public IEnumerable<ParsedExtension> GetInstalledUIExtensions()
        {
            return ExtensionParser.ParseInstalledExtensions()
                .Where(ext => ext.Directory.EndsWith(".extension", System.StringComparison.OrdinalIgnoreCase));
        }

        public IEnumerable<ParsedExtension> GetInstalledLibraryExtensions()
        {
            return ExtensionParser.ParseInstalledExtensions()
                .Where(ext => ext.Directory.EndsWith(".lib", System.StringComparison.OrdinalIgnoreCase));
        }
    }
}
