using System.Collections.Generic;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.Shared;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public interface IExtensionManager
    {
        IEnumerable<IExtension> GetInstalledExtensions();
    }
}