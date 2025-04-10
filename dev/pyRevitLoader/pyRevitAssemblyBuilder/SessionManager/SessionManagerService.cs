using System;
using System.Diagnostics;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using pyRevitAssemblyBuilder.AssemblyMaker;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class SessionManagerService : ISessionManager
    {
        private readonly ILogger<SessionManagerService> _logger;
        private readonly AssemblyBuilderService _assemblyBuilder;
        private readonly IExtensionManager _extensionManager;
        private readonly IHookManager _hookManager;
        private readonly IUIManager _uiManager;

        public SessionManagerService(
            ILogger<SessionManagerService> logger,
            AssemblyBuilderService assemblyBuilder,
            IExtensionManager extensionManager,
            IHookManager hookManager,
            IUIManager uiManager)
        {
            _logger = logger;
            _assemblyBuilder = assemblyBuilder;
            _extensionManager = extensionManager;
            _hookManager = hookManager;
            _uiManager = uiManager;
        }

        public async Task<string> LoadSessionAsync()
        {
            var stopwatch = Stopwatch.StartNew();

            _logger.LogInformation("[pyRevit] Loading new session...");

            var extensions = _extensionManager.GetInstalledExtensions();
            foreach (var ext in extensions)
            {
                var assmInfo = _assemblyBuilder.BuildExtensionAssembly(ext);
                //_uiManager.BuildUI(ext, assmInfo);
                _hookManager.RegisterHooks(ext);
            }

            stopwatch.Stop();
            _logger.LogInformation("Session loaded in {Time:F2} sec", stopwatch.Elapsed.TotalSeconds);

            return Guid.NewGuid().ToString(); // simulate session UUID
        }
    }
}