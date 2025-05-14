using System;
using System.Collections.Generic;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class ExtensionManagerService
    {
        public IEnumerable<ParsedExtension> GetInstalledExtensions()
        {
            var installedExtensions = ExtensionParser.ParseInstalledExtensions();
            //Console.WriteLine(installedExtensions);
            return installedExtensions;
        }
    }
}
