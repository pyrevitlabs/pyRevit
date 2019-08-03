using System;
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

        public static string outputStyleSheet = string.Format("{0}_STYLESHEET", keyPrefix);

        public static string telemetryState = string.Format("{0}_TELEMETRYSTATE", keyPrefix);
        public static string telemetryFileDir = string.Format("{0}_TELEMETRYDIR", keyPrefix);
        public static string telemetryFilePath = string.Format("{0}_TELEMETRYFILE", keyPrefix);
        public static string telemetryServerUrl = string.Format("{0}_TELEMETRYSERVER", keyPrefix);
        public static string appTelemetryFilePath = string.Format("{0}_APPTELEMETRYFILE", keyPrefix);
        public static string appTelemetryServerUrl = string.Format("{0}_APPTELEMETRYSERVER", keyPrefix);
        public static string appTelemetryEventFlags = string.Format("{0}_APPTELEMETRYEVENTFLAGS", keyPrefix);

        public static string loadedAssm = string.Format("{0}_LOADEDASSMS", keyPrefix);
        public static string loadedAssmCount = string.Format("{0}_ASSMCOUNT", keyPrefix);

        public static string autoupdating = string.Format("{0}_AUTOUPDATING", keyPrefix);

        public static string refedAssms = string.Format("{0}_REFEDASSMS", keyPrefix);

        public static string hooks = string.Format("{0}_HOOKS", keyPrefix);
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

        public string ActiveStyleSheet;

        public bool TelemetryState;
        public string TelemetryFilePath;
        public string TelemetryServerUrl;

        public string[] ReferencedAssemblies;

        public List<Dictionary<string, object>> EventHooks = new List<Dictionary<string, object>>();

        public EnvDictionary()
        {
            // get the dictionary from appdomain
            _envData = (PythonDictionary)AppDomain.CurrentDomain.GetData(DomainStorageKeys.pyRevitEnvVarsDictKey);

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

            if (_envData.Contains(EnvDictionaryKeys.sessionUUID))
                SessionUUID = (string)_envData[EnvDictionaryKeys.sessionUUID];


            if (_envData.Contains(EnvDictionaryKeys.outputStyleSheet))
                ActiveStyleSheet = (string)_envData[EnvDictionaryKeys.outputStyleSheet];


            if (_envData.Contains(EnvDictionaryKeys.telemetryState))
                TelemetryState = (bool)_envData[EnvDictionaryKeys.telemetryState];

            if (_envData.Contains(EnvDictionaryKeys.telemetryFilePath))
                TelemetryFilePath = (string)_envData[EnvDictionaryKeys.telemetryFilePath];

            if (_envData.Contains(EnvDictionaryKeys.telemetryServerUrl))
                TelemetryServerUrl = (string)_envData[EnvDictionaryKeys.telemetryServerUrl];

            if (_envData.Contains(EnvDictionaryKeys.refedAssms)) {
                var assms = (string)_envData[EnvDictionaryKeys.refedAssms];
                ReferencedAssemblies = assms.Split(ExternalConfig.defaultsep);
            }

            if (_envData.Contains(EnvDictionaryKeys.hooks))
                EventHooks = (List<Dictionary<string, object>>)_envData[EnvDictionaryKeys.hooks];
            else
                _envData[EnvDictionaryKeys.hooks] = EventHooks;
        }

        public void ResetEventHooks() {
            EventHooks = new List<Dictionary<string, object>>();
            _envData[EnvDictionaryKeys.hooks] = EventHooks;
        }
    }
}
