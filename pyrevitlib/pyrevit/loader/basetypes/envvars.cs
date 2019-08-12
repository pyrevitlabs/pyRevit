using System;
using System.IO;
using System.Collections.Generic;
using IronPython.Runtime;


namespace PyRevitBaseClasses
{
    public static class EnvDictionaryKeys
    {
        public static string keyPrefix = "PYREVIT";

        public static string sessionUUID = string.Format("{0}_UUID", keyPrefix);
        public static string RevitVersion = string.Format("{0}_APPVERSION", keyPrefix);
        public static string pyRevitVersion = string.Format("{0}_VERSION", keyPrefix);
        public static string pyRevitClone = string.Format("{0}_CLONE", keyPrefix);
        public static string pyRevitIpyVersion = string.Format("{0}_IPYVERSION", keyPrefix);
        public static string pyRevitCpyVersion = string.Format("{0}_CPYVERSION", keyPrefix);

        public static string loggingLevel = string.Format("{0}_LOGGINGLEVEL", keyPrefix);
        public static string fileLogging = string.Format("{0}_FILELOGGING", keyPrefix);

        public static string loadedAssm = string.Format("{0}_LOADEDASSMS", keyPrefix);
        public static string refedAssms = string.Format("{0}_REFEDASSMS", keyPrefix);

        public static string telemetryState = string.Format("{0}_TELEMETRYSTATE", keyPrefix);
        public static string telemetryFileDir = string.Format("{0}_TELEMETRYDIR", keyPrefix);
        public static string telemetryFilePath = string.Format("{0}_TELEMETRYFILE", keyPrefix);
        public static string telemetryServerUrl = string.Format("{0}_TELEMETRYSERVER", keyPrefix);
        public static string appTelemetryState = string.Format("{0}_APPTELEMETRYSTATE", keyPrefix);
        public static string appTelemetryHandler = string.Format("{0}_APPTELEMETRYHANDLER", keyPrefix);
        public static string appTelemetryServerUrl = string.Format("{0}_APPTELEMETRYSERVER", keyPrefix);
        public static string appTelemetryEventFlags = string.Format("{0}_APPTELEMETRYEVENTFLAGS", keyPrefix);

        public static string hooks = string.Format("{0}_HOOKS", keyPrefix);
        public static string hooksHandler = string.Format("{0}_HOOKSHANDLER", keyPrefix);

        public static string autoupdating = string.Format("{0}_AUTOUPDATING", keyPrefix);
        public static string outputStyleSheet = string.Format("{0}_STYLESHEET", keyPrefix);

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
            _envData = (PythonDictionary)AppDomain.CurrentDomain.GetData(DomainStorageKeys.pyRevitEnvVarsDictKey);

            // base info
            if (_envData.Contains(EnvDictionaryKeys.sessionUUID))
                SessionUUID = (string)_envData[EnvDictionaryKeys.sessionUUID];

            if (_envData.Contains(EnvDictionaryKeys.RevitVersion))
                RevitVersion = (string)_envData[EnvDictionaryKeys.RevitVersion];

            if (_envData.Contains(EnvDictionaryKeys.pyRevitVersion))
                PyRevitVersion = (string)_envData[EnvDictionaryKeys.pyRevitVersion];

            if (_envData.Contains(EnvDictionaryKeys.pyRevitClone))
                PyRevitClone = (string)_envData[EnvDictionaryKeys.pyRevitClone];

            if (_envData.Contains(EnvDictionaryKeys.pyRevitIpyVersion))
                PyRevitIPYVersion = (int)_envData[EnvDictionaryKeys.pyRevitIpyVersion];

            if (_envData.Contains(EnvDictionaryKeys.pyRevitCpyVersion))
                PyRevitCPYVersion = (int)_envData[EnvDictionaryKeys.pyRevitCpyVersion];

            // logging
            if (_envData.Contains(EnvDictionaryKeys.loggingLevel))
                LoggingLevel = (int)_envData[EnvDictionaryKeys.loggingLevel];
            if (_envData.Contains(EnvDictionaryKeys.fileLogging))
                FileLogging = (bool)_envData[EnvDictionaryKeys.fileLogging];

            // assemblies
            if (_envData.Contains(EnvDictionaryKeys.loadedAssm))
                LoadedAssemblies = ((string)_envData[EnvDictionaryKeys.loadedAssm]).Split(Path.PathSeparator);
            if (_envData.Contains(EnvDictionaryKeys.refedAssms))
                ReferencedAssemblies = ((string)_envData[EnvDictionaryKeys.refedAssms]).Split(Path.PathSeparator);

            // script telemetry
            if (_envData.Contains(EnvDictionaryKeys.telemetryState))
                TelemetryState = (bool)_envData[EnvDictionaryKeys.telemetryState];

            if (_envData.Contains(EnvDictionaryKeys.telemetryFilePath))
                TelemetryFilePath = (string)_envData[EnvDictionaryKeys.telemetryFilePath];

            if (_envData.Contains(EnvDictionaryKeys.telemetryServerUrl))
                TelemetryServerUrl = (string)_envData[EnvDictionaryKeys.telemetryServerUrl];

            // app events telemetry
            if (_envData.Contains(EnvDictionaryKeys.appTelemetryState))
                AppTelemetryState = (bool)_envData[EnvDictionaryKeys.appTelemetryState];

            if (_envData.Contains(EnvDictionaryKeys.appTelemetryServerUrl))
                AppTelemetryServerUrl = (string)_envData[EnvDictionaryKeys.appTelemetryServerUrl];

            if (_envData.Contains(EnvDictionaryKeys.appTelemetryEventFlags))
                AppTelemetryEventFlags = (string)_envData[EnvDictionaryKeys.appTelemetryEventFlags];

            // hooks
            if (_envData.Contains(EnvDictionaryKeys.hooks))
                EventHooks = (Dictionary<string, Dictionary<string, string>>)_envData[EnvDictionaryKeys.hooks];
            else
                _envData[EnvDictionaryKeys.hooks] = EventHooks;

            // misc
            if (_envData.Contains(EnvDictionaryKeys.autoupdating))
                AutoUpdate = (bool)_envData[EnvDictionaryKeys.autoupdating];

            if (_envData.Contains(EnvDictionaryKeys.outputStyleSheet))
                ActiveStyleSheet = (string)_envData[EnvDictionaryKeys.outputStyleSheet];
        }

        public void ResetEventHooks() {
            ((Dictionary<string, Dictionary<string, string>>)_envData[EnvDictionaryKeys.hooks]).Clear();
        }
    }
}
