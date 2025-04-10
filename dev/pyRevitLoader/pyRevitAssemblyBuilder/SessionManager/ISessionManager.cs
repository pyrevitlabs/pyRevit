using System.Threading.Tasks;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public interface ISessionManager
    {
        Task<string> LoadSessionAsync();
    }
}
