using System.Collections.Generic;

namespace pyRevitAssemblyBuilder.Shared
{
    public interface ICommandComponent
    {
        string Name { get; }
        string ScriptPath { get; }
        string Tooltip { get; }
        string UniqueId { get; }
        string ExtensionName { get; }
        string Type { get; }
        IEnumerable<object> Children { get; }
    }
}
