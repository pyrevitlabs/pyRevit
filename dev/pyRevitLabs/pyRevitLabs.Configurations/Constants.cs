namespace pyRevitLabs.Configurations;

internal static class Constants
{
    // core 
    public const string CoreSection = "core";
    public const string BinaryCacheKey = "bincache";
    public const string CheckUpdatesKey = "checkupdates";
    public const string AutoUpdateKey = "autoupdate";
    public const string RocketModeKey = "rocketmode";
    public const string VerboseKey = "verbose";
    public const string DebugKey = "debug";
    public const string FileLoggingKey = "filelogging";
    public const string StartupLogTimeoutKey = "startuplogtimeout";
    public const string RequiredHostBuildKey = "requiredhostbuild";
    public const string MinDriveSpaceKey = "minhostdrivefreespace";
    public const string LoadBetaKey = "loadbeta";
    public const string CPythonEngineKey = "cpyengine";
    public const string LocaleKey = "user_locale";
    public const string OutputStyleSheet = "outputstylesheet";
    public const string UserExtensionsKey = "userextensions";
    public const string UserCanUpdateKey = "usercanupdate";
    public const string UserCanExtendKey = "usercanextend";
    public const string UserCanConfigKey = "usercanconfig";
    public const string ColorizeDocsKey = "colorize_docs";
    public const string AppendTooltipExKey = "tooltip_debug_info";

    // routes
    public const string RoutesSection = "routes";
    public const string RoutesServerKey = "enabled";
    public const string RoutesHostKey = "host";
    public const string RoutesPortKey = "port";
    public const string LoadCoreAPIKey = "core_api";

    // telemetry
    public const string TelemetrySection = "telemetry";
    public const string TelemetryUTCTimestampsKey = "utc_timestamps";
    public const string TelemetryStatusKey = "active";
    public const string TelemetryFileDirKey = "telemetry_file_dir";
    public const string TelemetryServerUrlKey = "telemetry_server_url";
    public const string TelemetryIncludeHooksKey = "include_hooks";
    public const string AppTelemetryStatusKey = "active_app";
    public const string AppTelemetryServerUrlKey = "apptelemetry_server_url";
    public const string AppTelemetryEventFlagsKey = "apptelemetry_event_flags";

    // pyrevit.exe specific 
    public const string EnvSectionName = "environment";
    public const string EnvInstalledClonesKey = "clones";
    public const string EnvExtensionLookupSourcesKey = "sources";
    public const string EnvTemplateSourcesKey = "templates";
    public const string EnvExtensionDBFileName = "PyRevitExtensionsDB.json";
}