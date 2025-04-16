using System;
using System.Diagnostics;
using System.Threading.Tasks;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.FolderParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class SessionManagerService
    {
        private readonly AssemblyBuilderService _assemblyBuilder;
        private readonly ExtensionManagerService _extensionManager;
        private readonly HookManager _hookManager;
        private readonly UIManagerService _uiManager;

        public SessionManagerService(
            AssemblyBuilderService assemblyBuilder,
            ExtensionManagerService extensionManager,
            HookManager hookManager,
            UIManagerService uiManager)
        {
            _assemblyBuilder = assemblyBuilder;
            _extensionManager = extensionManager;
            _hookManager = hookManager;
            _uiManager = uiManager;
        }

        public void LoadSession()
        {
            var extensions = _extensionManager.GetInstalledExtensions();
            foreach (var ext in extensions)
            {
                var assmInfo = _assemblyBuilder.BuildExtensionAssembly(ext);
                _uiManager.BuildUI(ext, assmInfo);
                _hookManager.RegisterHooks(ext);
            }
        }
    }
}