namespace pyRevitAssemblyBuilder.UIManager
{
    /// <summary>
    /// Constants used across the UIManager namespace.
    /// These values match the pythonic pyrevit.coreutils.ribbon module.
    /// </summary>
    public static class UIManagerConstants
    {
        #region Icon Sizes
        /// <summary>
        /// Small icon size (16x16 pixels).
        /// Matches pyrevit.coreutils.ribbon.ICON_SMALL.
        /// </summary>
        public const int ICON_SMALL = 16;

        /// <summary>
        /// Medium icon size (24x24 pixels).
        /// Matches pyrevit.coreutils.ribbon.ICON_MEDIUM.
        /// </summary>
        public const int ICON_MEDIUM = 24;

        /// <summary>
        /// Large icon size (32x32 pixels).
        /// Matches pyrevit.coreutils.ribbon.ICON_LARGE.
        /// </summary>
        public const int ICON_LARGE = 32;
        #endregion

        #region Tooltip Media
        /// <summary>
        /// Supported image format for tooltip images.
        /// Matches pyrevit.coreutils.ribbon.DEFAULT_TOOLTIP_IMAGE_FORMAT.
        /// </summary>
        public const string TOOLTIP_IMAGE_FORMAT = ".png";

        /// <summary>
        /// Default video format for older Revit versions (before 2019).
        /// Matches pyrevit.coreutils.ribbon.DEFAULT_TOOLTIP_VIDEO_FORMAT for older versions.
        /// </summary>
        public const string TOOLTIP_VIDEO_FORMAT_SWF = ".swf";

        /// <summary>
        /// Video format for Revit 2019 and newer.
        /// Matches pyrevit.coreutils.ribbon.DEFAULT_TOOLTIP_VIDEO_FORMAT for newer versions.
        /// </summary>
        public const string TOOLTIP_VIDEO_FORMAT_MP4 = ".mp4";
        #endregion

        #region UI Identifiers
        /// <summary>
        /// Unicode bullet character used to mark buttons that have a config script.
        /// Matches the pythonic loader's CONFIG_SCRIPT_TITLE_POSTFIX.
        /// </summary>
        public const string ConfigScriptTitlePostfix = "\u25CF";

        /// <summary>
        /// Identifier used to mark tabs as pyRevit tabs for runtime icon toggling.
        /// Must match PYREVIT_TAB_IDENTIFIER in pyrevit.coreutils.ribbon.
        /// </summary>
        public const string PyRevitTabIdentifier = "pyrevit_tab";
        #endregion

        #region DPI Settings
        /// <summary>
        /// Default DPI for bitmap rendering (standard Windows DPI).
        /// </summary>
        public const double DEFAULT_DPI = 96.0;
        #endregion
    }
}

