using pyRevitAssemblyBuilder.Shared;
using System.Reflection.Emit;

namespace pyRevitAssemblyBuilder.AssemblyMaker
{
    public interface ICommandTypeGenerator
    {
        void DefineCommandType(IExtension extension, ICommandComponent command, ModuleBuilder moduleBuilder);
    }
}