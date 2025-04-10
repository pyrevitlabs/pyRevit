using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.Shared;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public interface IUIManager
    {
        void BuildUI(IExtension extension, ExtensionAssemblyInfo info);
    }
}