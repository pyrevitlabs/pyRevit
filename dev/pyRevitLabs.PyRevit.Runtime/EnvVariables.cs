using System;
using System.IO;
using System.Collections.Generic;
using IronPython.Runtime;

using pyRevitLabs.Common;

namespace PyRevitLabs.PyRevit.Runtime
{
    public static class DomainStorageKeys
    {
        public static string keyPrefix = PyRevitLabsConsts.ProductName.ToUpperInvariant();

        public static string EnvVarsDictKey = keyPrefix + "EnvVarsDict";
        public static string EnginesDictKey = keyPrefix + "CachedEngines";
        public static string IronPythonEngineDefaultOutputStreamCfgKey = keyPrefix + "CachedEngineDefaultOutputStreamCfg";
        public static string IronPythonEngineDefaultErrorStreamCfgKey = keyPrefix + "CachedEngineDefaultErrorStreamCfg";
        public static string IronPythonEngineDefaultInputStreamCfgKey = keyPrefix + "CachedEngineDefaultInputStreamCfg";
        public static string OutputWindowsDictKey = keyPrefix + "OutputWindowsDict";
    }

    public static class EnvDictionaryKeys
    {
        public static string keyPrefix = PyRevitLabsConsts.ProductName.ToUpperInvariant();

        public static string SessionUUID = string.Format("{0}_UUID", keyPrefix);
        public static string RevitVersion = string.Format("{0}_APPVERSION", keyPrefix);
        public static string Version = string.Format("{0}_VERSION", keyPrefix);
        public static string Clone = string.Format("{0}_CLONE", keyPrefix);
        public static string IPYVersion = string.Format("{0}_IPYVERSION", keyPrefix);
        public static string CPYVersion = string.Format("{0}_CPYVERSION", keyPrefix);

        public static string LoadedAssms = string.Format("{0}_LOADEDASSMS", keyPrefix);
        public static string RefedAssms = string.Format("{0}_REFEDASSMS", keyPrefix);

        public static string TelemetryState = string.Format("{0}_TELEMETRYSTATE", keyPrefix);
        public static string TelemetryUTCTimeStamps = string.Format("{0}_TELEMETRYUTCTIMESTAMPS", keyPrefix);
        public static string TelemetryFileDir = string.Format("{0}_TELEMETRYDIR", keyPrefix);
        public static string TelemetryFilePath = string.Format("{0}_TELEMETRYFILE", keyPrefix);
        public static string TelemetryServerUrl = string.Format("{0}_TELEMETRYSERVER", keyPrefix);
        public static string TelemetryIncludeHooks = string.Format("{0}_TELEMETRYINCLUDEHOOKS", keyPrefix);

        public static string AppTelemetryState = string.Format("{0}_APPTELEMETRYSTATE", keyPrefix);
        public static string AppTelemetryHandler = string.Format("{0}_APPTELEMETRYHANDLER", keyPrefix);
        public static string AppTelemetryServerUrl = string.Format("{0}_APPTELEMETRYSERVER", keyPrefix);
        public static string AppTelemetryEventFlags = string.Format("{0}_APPTELEMETRYEVENTFLAGS", keyPrefix);

        public static string Hooks = string.Format("{0}_HOOKS", keyPrefix);
        public static string HooksHandler = string.Format("{0}_HOOKSHANDLER", keyPrefix);

        public static string AutoUpdating = string.Format("{0}_AUTOUPDATE", keyPrefix);
        public static string OutputStyleSheet = string.Format("{0}_STYLESHEET", keyPrefix);
        public static string RibbonUpdator = string.Format("{0}_RIBBONUPDATOR", keyPrefix);
        public static string TabColorizer = string.Format("{0}_TABCOLORIZER", keyPrefix);
    }

    public class EnvDictionary
    {
        private PythonDictionary _envData = null;

        public string SessionUUID;
        public string RevitVersion;
        public string PyRevitVersion;
        public string PyRevitClone;
        public string PyRevitIPYVersion;
        public string PyRevitCPYVersion;

        public string[] LoadedAssemblies;
        public string[] ReferencedAssemblies;

        public bool TelemetryState;
        public string TelemetryFilePath;
        public string TelemetryServerUrl;
        public bool TelemetryIncludeHooks;

        public bool AppTelemetryState;
        public string AppTelemetryServerUrl;
        public string AppTelemetryEventFlags;

        public Dictionary<string, Dictionary<string, string>> EventHooks =
            new Dictionary<string, Dictionary<string, string>>();

        public string ActiveStyleSheet;
        public bool AutoUpdate;
        public bool TelemetryUTCTimeStamps;


        /// <summary>
        /// A config option that is not set reaches this dictionary as a null, so
        /// every field read below goes through a type-matched <c>GetXxx</c> helper
        /// rather than an unboxing cast, which would throw and take down session
        /// load over a single absent option.
        /// </summary>
        public EnvDictionary()
        {
            _envData = AppDomain.CurrentDomain.GetData(DomainStorageKeys.EnvVarsDictKey) as PythonDictionary;
            if (_envData is null)
            {
                _envData = new PythonDictionary();
                AppDomain.CurrentDomain.SetData(DomainStorageKeys.EnvVarsDictKey, _envData);
            }

            // base info
            SessionUUID = GetString(EnvDictionaryKeys.SessionUUID, SessionUUID);
            RevitVersion = GetString(EnvDictionaryKeys.RevitVersion, RevitVersion);
            PyRevitVersion = GetString(EnvDictionaryKeys.Version, PyRevitVersion);
            PyRevitClone = GetString(EnvDictionaryKeys.Clone, PyRevitClone);
            PyRevitIPYVersion = GetString(EnvDictionaryKeys.IPYVersion, PyRevitIPYVersion);
            PyRevitCPYVersion = GetString(EnvDictionaryKeys.CPYVersion, PyRevitCPYVersion);

            // assemblies
            LoadedAssemblies = GetPathList(EnvDictionaryKeys.LoadedAssms, LoadedAssemblies);
            ReferencedAssemblies = GetPathList(EnvDictionaryKeys.RefedAssms, ReferencedAssemblies);

            // telemetry
            TelemetryUTCTimeStamps = GetBool(EnvDictionaryKeys.TelemetryUTCTimeStamps, TelemetryUTCTimeStamps);

            // script telemetry
            TelemetryState = GetBool(EnvDictionaryKeys.TelemetryState, TelemetryState);
            TelemetryFilePath = GetString(EnvDictionaryKeys.TelemetryFilePath, TelemetryFilePath);
            TelemetryServerUrl = GetString(EnvDictionaryKeys.TelemetryServerUrl, TelemetryServerUrl);
            TelemetryIncludeHooks = GetBool(EnvDictionaryKeys.TelemetryIncludeHooks, TelemetryIncludeHooks);

            // app events telemetry
            AppTelemetryState = GetBool(EnvDictionaryKeys.AppTelemetryState, AppTelemetryState);
            AppTelemetryServerUrl = GetString(EnvDictionaryKeys.AppTelemetryServerUrl, AppTelemetryServerUrl);
            AppTelemetryEventFlags = GetString(EnvDictionaryKeys.AppTelemetryEventFlags, AppTelemetryEventFlags);

            // hooks
            if (_envData.Contains(EnvDictionaryKeys.Hooks)
                    && _envData[EnvDictionaryKeys.Hooks] is Dictionary<string, Dictionary<string, string>> hooks)
                EventHooks = hooks;
            else
                _envData[EnvDictionaryKeys.Hooks] = EventHooks;

            // misc
            AutoUpdate = GetBool(EnvDictionaryKeys.AutoUpdating, AutoUpdate);
            ActiveStyleSheet = GetString(EnvDictionaryKeys.OutputStyleSheet, ActiveStyleSheet);
        }

        private string GetString(string key, string fallback)
        {
            return _envData.Contains(key) && _envData[key] is string value ? value : fallback;
        }

        private bool GetBool(string key, bool fallback)
        {
            return _envData.Contains(key) && _envData[key] is bool value ? value : fallback;
        }

        private string[] GetPathList(string key, string[] fallback)
        {
            return _envData.Contains(key) && _envData[key] is string value
                ? value.Split(Path.PathSeparator)
                : fallback;
        }

        public void ResetEventHooks()
        {
            if (_envData.Contains(EnvDictionaryKeys.Hooks)
                    && _envData[EnvDictionaryKeys.Hooks] is Dictionary<string, Dictionary<string, string>> hooks)
                hooks.Clear();
            else
                _envData[EnvDictionaryKeys.Hooks] = new Dictionary<string, Dictionary<string, string>>();
        }

        /// <summary>
        /// Seeds the AppDomain environment dictionary with session values supplied by the C# loader.
        /// Called via reflection by EnvDictionarySeeder in pyRevitAssemblyBuilder (which has no
        /// compile-time reference to IronPython), so the PythonDictionary is created here where
        /// IronPython is already available.
        /// </summary>
        /// <param name="values">
        /// Key/value pairs to store. Keys must match the string values of <see cref="EnvDictionaryKeys"/>.
        /// Values must be plain CLR primitives (string, bool, int) — IronPython coerces them correctly.
        /// </param>
        public static void Seed(Dictionary<string, object> values)
        {
            var envData = AppDomain.CurrentDomain.GetData(DomainStorageKeys.EnvVarsDictKey) as PythonDictionary
                          ?? new PythonDictionary();

            foreach (var kv in values)
                envData[kv.Key] = kv.Value;

            if (!envData.Contains(EnvDictionaryKeys.Hooks))
                envData[EnvDictionaryKeys.Hooks] = new Dictionary<string, Dictionary<string, string>>();

            AppDomain.CurrentDomain.SetData(DomainStorageKeys.EnvVarsDictKey, envData);
        }
    }
}
