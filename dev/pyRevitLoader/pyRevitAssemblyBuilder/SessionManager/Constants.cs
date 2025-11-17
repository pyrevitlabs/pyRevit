namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Constants used throughout the SessionManager namespace.
    /// </summary>
    internal static class Constants
    {
        /// <summary>
        /// Marker file name used to identify pyRevit root directory.
        /// </summary>
        public const string PYREVIT_MARKER_FILE = "pyRevitfile";

        /// <summary>
        /// Directory name for pyRevit library files.
        /// </summary>
        public const string PYREVIT_LIB_DIR = "pyrevitlib";

        /// <summary>
        /// Directory name for site-packages.
        /// </summary>
        public const string SITE_PACKAGES_DIR = "site-packages";

        /// <summary>
        /// Key for environment variables dictionary in AppDomain data.
        /// </summary>
        public const string ENV_DICT_KEY = "PYREVITEnvVarsDict";

        /// <summary>
        /// Key for referenced assemblies in environment dictionary.
        /// </summary>
        public const string REFED_ASSMS_KEY = "PYREVIT_REFEDASSMS";
    }
}

