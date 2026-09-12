#nullable enable

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Interface for managing pyRevit session loading, including assembly building and UI creation.
    /// </summary>
    public interface ISessionManagerService
    {
        /// <summary>
        /// Loads a new pyRevit session by building assemblies and creating UI for all installed extensions.
        /// </summary>
        /// <remarks>
        /// This method:
        /// 1. Initializes the script executor
        /// 2. Gets all library extensions
        /// 3. For each UI extension:
        ///    - Builds the extension assembly
        ///    - Loads the assembly
        ///    - Executes startup scripts if present
        ///    - Creates the UI
        /// </remarks>
        /// <param name="firstLoad">True on initial Revit startup, false on reload. Gates
        /// first-load-only work such as removing stale appdata files from closed sessions.</param>
        void LoadSession(bool firstLoad);
    }
}
