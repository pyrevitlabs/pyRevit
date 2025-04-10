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

    public class DummyUIManager : IUIManager
    {
        public void BuildUI(IExtension extension, ExtensionAssemblyInfo info) { /* no-op */ }
    }

    internal class DummyExtension : IExtension
    {
        public string Name => "LoaderExt";
        public string GetHash() => "xyz789";

        public IEnumerable<ICommandComponent> GetAllCommands()
        {
            return new[]
            {
                new DummyCommand("CommandA"),
                new DummyCommand("CommandB")
            };
        }
    }

    internal class DummyCommand : ICommandComponent
    {
        public DummyCommand(string name) => Name = name;

        public string Name { get; }
        public string ScriptPath => $"{Name}.py";
        public string Tooltip => $"Tooltip for {Name}";
        public string UniqueId => $"pyRevit.Loader.{Name}";
        public string ExtensionName => "LoaderExt";
    }
}