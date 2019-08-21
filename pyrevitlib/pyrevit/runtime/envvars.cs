using System;
using System.IO;
using System.Collections.Generic;
using IronPython.Runtime;

using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime {
    public static class DomainStorageKeys {
        public static string keyPrefix = PyRevitConsts.ProductName.ToUpper();

        public static string EnvVarsDictKey = keyPrefix + "EnvVarsDict";
        public static string EnginesDictKey = keyPrefix + "CachedEngines";
        public static string IronPythonEngineDefaultStreamCfgKey = keyPrefix + "CachedEngineDefaultStreamCfg";
        public static string OutputWindowsDictKey = keyPrefix + "OutputWindowsDict";
    }

    public static class EnvDictionaryKeys
    {
        public static string keyPrefix = PyRevitConsts.ProductName.ToUpper();

        public static string SessionUUID = string.Format("{0}_UUID", keyPrefix);
        public static string RevitVersion = string.Format("{0}_APPVERSION", keyPrefix);
        public static string Version = string.Format("{0}_VERSION", keyPrefix);
        public static string Clone = string.Format("{0}_CLONE", keyPrefix);
        public static string IPYVersion = string.Format("{0}_IPYVERSION", keyPrefix);
        public static string CPYVersion = string.Format("{0}_CPYVERSION", keyPrefix);

        public static string LoggingLevel = string.Format("{0}_LOGGINGLEVEL", keyPrefix);
        public static string FileLogging = string.Format("{0}_FILELOGGING", keyPrefix);

        public static string LoadedAssms = string.Format("{0}_LOADEDASSMS", keyPrefix);
        public static string RefedAssms = string.Format("{0}_REFEDASSMS", keyPrefix);

        public static string TelemetryState = string.Format("{0}_TELEMETRYSTATE", keyPrefix);
        public static string TelemetryFileDir = string.Format("{0}_TELEMETRYDIR", keyPrefix);
        public static string TelemetryFilePath = string.Format("{0}_TELEMETRYFILE", keyPrefix);
        public static string TelemetryServerUrl = string.Format("{0}_TELEMETRYSERVER", keyPrefix);
        public static string AppTelemetryState = string.Format("{0}_APPTELEMETRYSTATE", keyPrefix);
        public static string AppTelemetryHandler = string.Format("{0}_APPTELEMETRYHANDLER", keyPrefix);
        public static string AppTelemetryServerUrl = string.Format("{0}_APPTELEMETRYSERVER", keyPrefix);
        public static string AppTelemetryEventFlags = string.Format("{0}_APPTELEMETRYEVENTFLAGS", keyPrefix);

        public static string Hooks = string.Format("{0}_HOOKS", keyPrefix);
        public static string HooksHandler = string.Format("{0}_HOOKSHANDLER", keyPrefix);

        public static string AutoUpdating = string.Format("{0}_AUTOUPDATE", keyPrefix);
        public static string OutputStyleSheet = string.Format("{0}_STYLESHEET", keyPrefix);
    }

    public class EnvDictionary
    {
        private PythonDictionary _envData = null;

        public string SessionUUID;
        public string RevitVersion;
        public string PyRevitVersion;
        public string PyRevitClone;
        public int PyRevitIPYVersion;
        public int PyRevitCPYVersion;

        public int LoggingLevel;
        public bool FileLogging;

        public string[] LoadedAssemblies;
        public string[] ReferencedAssemblies;

        public bool TelemetryState;
        public string TelemetryFilePath;
        public string TelemetryServerUrl;

        public bool AppTelemetryState;
        public string AppTelemetryServerUrl;
        public string AppTelemetryEventFlags;

        public Dictionary<string, Dictionary<string, string>> EventHooks = 
            new Dictionary<string, Dictionary<string, string>>();

        public string ActiveStyleSheet;
        public bool AutoUpdate;


        public EnvDictionary()
        {
            // get the dictionary from appdomain
            _envData = (PythonDictionary)AppDomain.CurrentDomain.GetData(DomainStorageKeys.EnvVarsDictKey);

            // base info
            if (_envData.Contains(EnvDictionaryKeys.SessionUUID))
                SessionUUID = (string)_envData[EnvDictionaryKeys.SessionUUID];

            if (_envData.Contains(EnvDictionaryKeys.RevitVersion))
                RevitVersion = (string)_envData[EnvDictionaryKeys.RevitVersion];

            if (_envData.Contains(EnvDictionaryKeys.Version))
                PyRevitVersion = (string)_envData[EnvDictionaryKeys.Version];

            if (_envData.Contains(EnvDictionaryKeys.Clone))
                PyRevitClone = (string)_envData[EnvDictionaryKeys.Clone];

            if (_envData.Contains(EnvDictionaryKeys.IPYVersion))
                PyRevitIPYVersion = (int)_envData[EnvDictionaryKeys.IPYVersion];

            if (_envData.Contains(EnvDictionaryKeys.CPYVersion))
                PyRevitCPYVersion = (int)_envData[EnvDictionaryKeys.CPYVersion];

            // logging
            if (_envData.Contains(EnvDictionaryKeys.LoggingLevel))
                LoggingLevel = (int)_envData[EnvDictionaryKeys.LoggingLevel];
            if (_envData.Contains(EnvDictionaryKeys.FileLogging))
                FileLogging = (bool)_envData[EnvDictionaryKeys.FileLogging];

            // assemblies
            if (_envData.Contains(EnvDictionaryKeys.LoadedAssms))
                LoadedAssemblies = ((string)_envData[EnvDictionaryKeys.LoadedAssms]).Split(Path.PathSeparator);
            if (_envData.Contains(EnvDictionaryKeys.RefedAssms))
                ReferencedAssemblies = ((string)_envData[EnvDictionaryKeys.RefedAssms]).Split(Path.PathSeparator);

            // script telemetry
            if (_envData.Contains(EnvDictionaryKeys.TelemetryState))
                TelemetryState = (bool)_envData[EnvDictionaryKeys.TelemetryState];

            if (_envData.Contains(EnvDictionaryKeys.TelemetryFilePath))
                TelemetryFilePath = (string)_envData[EnvDictionaryKeys.TelemetryFilePath];

            if (_envData.Contains(EnvDictionaryKeys.TelemetryServerUrl))
                TelemetryServerUrl = (string)_envData[EnvDictionaryKeys.TelemetryServerUrl];

            // app events telemetry
            if (_envData.Contains(EnvDictionaryKeys.AppTelemetryState))
                AppTelemetryState = (bool)_envData[EnvDictionaryKeys.AppTelemetryState];

            if (_envData.Contains(EnvDictionaryKeys.AppTelemetryServerUrl))
                AppTelemetryServerUrl = (string)_envData[EnvDictionaryKeys.AppTelemetryServerUrl];

            if (_envData.Contains(EnvDictionaryKeys.AppTelemetryEventFlags))
                AppTelemetryEventFlags = (string)_envData[EnvDictionaryKeys.AppTelemetryEventFlags];

            // hooks
            if (_envData.Contains(EnvDictionaryKeys.Hooks))
                EventHooks = (Dictionary<string, Dictionary<string, string>>)_envData[EnvDictionaryKeys.Hooks];
            else
                _envData[EnvDictionaryKeys.Hooks] = EventHooks;

            // misc 
            if (_envData.Contains(EnvDictionaryKeys.AutoUpdating))
                AutoUpdate = (bool)_envData[EnvDictionaryKeys.AutoUpdating];

            if (_envData.Contains(EnvDictionaryKeys.OutputStyleSheet))
                ActiveStyleSheet = (string)_envData[EnvDictionaryKeys.OutputStyleSheet];
        }

        public void ResetEventHooks() {
            ((Dictionary<string, Dictionary<string, string>>)_envData[EnvDictionaryKeys.Hooks]).Clear();
        }
    }
}
