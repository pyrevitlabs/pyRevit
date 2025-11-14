using System.Linq;
using pyRevitAssemblyBuilder.AssemblyMaker;

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
            // Get all library extensions first - they need to be available to all UI extensions
            var libraryExtensions = _extensionManager.GetInstalledLibraryExtensions().ToList();
            
            // Get UI extensions
            var uiExtensions = _extensionManager.GetInstalledUIExtensions();

            foreach (var ext in uiExtensions)
            {
                var assmInfo = _assemblyBuilder.BuildExtensionAssembly(ext, libraryExtensions);
                _assemblyBuilder.LoadAssembly(assmInfo);
                _uiManager.BuildUI(ext, assmInfo);
                _hookManager.RegisterHooks(ext);
            }
        }
    }
}