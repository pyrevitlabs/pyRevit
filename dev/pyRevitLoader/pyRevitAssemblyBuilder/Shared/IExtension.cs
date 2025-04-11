using System.Collections.Generic;

namespace pyRevitAssemblyBuilder.Shared
{
    public interface IExtension
    {
        string Name { get; }
        string Directory { get; }
        object Children { get; }

        string GetHash();
        IEnumerable<ICommandComponent> GetAllCommands();
    }
}