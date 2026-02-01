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

    /// <summary>
    /// Constants related to pyRevit extensions.
    /// </summary>
    internal static class ExtensionConstants
    {
        /// <summary>
        /// File suffix for UI extensions.
        /// </summary>
        public const string UI_EXTENSION_SUFFIX = ".extension";

        /// <summary>
        /// File suffix for library extensions.
        /// </summary>
        public const string LIBRARY_EXTENSION_SUFFIX = ".lib";

        /// <summary>
        /// Default context value for commands without explicit context.
        /// </summary>
        public const string DEFAULT_CONTEXT = "(zero-doc)";
    }

    /// <summary>
    /// Constants related to Revit API internals.
    /// </summary>
    public static class RevitApiConstants
    {
        /// <summary>
        /// Revit version where the UIApplication field name changed.
        /// </summary>
        public const int NEW_UIAPP_FIELD_VERSION = 2017;

        /// <summary>
        /// Field name for UIApplication in Revit 2017 and newer.
        /// </summary>
        public const string MODERN_UIAPP_FIELD = "m_uiapplication";

        /// <summary>
        /// Field name for UIApplication in Revit versions before 2017.
        /// </summary>
        public const string LEGACY_UIAPP_FIELD = "m_application";
    }
}
