using System.Collections.Generic;
using pyRevitAssemblyBuilder.Shared;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.SessionManager;

namespace pyRevitAssemblyBuilder.Startup
{
    public class DummyHookManager : IHookManager
    {
        public void RegisterHooks(IExtension extension) { /* no-op */ }
    }
}