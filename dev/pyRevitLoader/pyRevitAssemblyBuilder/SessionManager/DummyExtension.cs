using System.Collections.Generic;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.Shared;

namespace pyRevitAssemblyBuilder.SessionManager
{
    internal class DummyExtension : IExtension
    {
        public string Name => "DummyExt";

        public string GetHash() => "abc123";

        public IEnumerable<ICommandComponent> GetAllCommands()
        {
            return new[]
            {
                new DummyCommand("CommandOne"),
                new DummyCommand("CommandTwo")
            };
        }
    }

    internal class DummyCommand : ICommandComponent
    {
        public DummyCommand(string name)
        {
            Name = name;
        }

        public string Name { get; }
        public string ScriptPath => $"{Name}.py";
        public string Tooltip => $"Tooltip for {Name}";
        public string UniqueId => $"pyRevit.Generated.{Name}";
        public string ExtensionName => "DummyExt";
    }
}
