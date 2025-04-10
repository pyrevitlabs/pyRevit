using System.Collections.Generic;

namespace pyRevitAssemblyBuilder.Shared
{
    public interface IExtension
    {
        string Name { get; }
        string GetHash();
        IEnumerable<ICommandComponent> GetAllCommands();
    }
}