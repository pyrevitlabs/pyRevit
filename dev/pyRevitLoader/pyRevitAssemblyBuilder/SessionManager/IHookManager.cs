using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.Shared;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public interface IHookManager
    {
        void RegisterHooks(IExtension extension);
    }
}