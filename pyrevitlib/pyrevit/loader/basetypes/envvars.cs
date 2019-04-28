using System;
using IronPython.Runtime;


namespace PyRevitBaseClasses
{
    public static class EnvDictionaryKeys
    {
        public static string keyPrefix = "PYREVIT";

        public static string sessionUUID = string.Format("{0}_UUID", keyPrefix);
        public static string pyRevitVersion = string.Format("{0}_VERSION", keyPrefix);

        public static string loggingLevel = string.Format("{0}_LOGGINGLEVEL", keyPrefix);
        public static string fileLogging = string.Format("{0}_FILELOGGING", keyPrefix);

        public static string outputStyleSheet = string.Format("{0}_STYLESHEET", keyPrefix);

        public static string usageLogState = string.Format("{0}_USAGELOGSTATE", keyPrefix);
        public static string usageLogFilePath = string.Format("{0}_USAGELOGFILE", keyPrefix);
        public static string usageLogServerUrl = string.Format("{0}_USAGELOGSERVER", keyPrefix);

        public static string loadedAssm = string.Format("{0}_LOADEDASSMS", keyPrefix);
        public static string loadedAssmCount = string.Format("{0}_ASSMCOUNT", keyPrefix);

        public static string autoupdating = string.Format("{0}_AUTOUPDATING", keyPrefix);
    }

    public class EnvDictionary
    {
        public string sessionUUID;
        public string pyRevitVersion;

        public string activeStyleSheet;

        public bool usageLogState;
        public string usageLogFilePath;
        public string usageLogServerUrl;

        public EnvDictionary()
        {
            // get the dictionary from appdomain
            var _envData = (PythonDictionary)AppDomain.CurrentDomain.GetData(DomainStorageKeys.pyRevitEnvVarsDictKey);

            if (_envData.Contains(EnvDictionaryKeys.pyRevitVersion))
                pyRevitVersion = (string)_envData[EnvDictionaryKeys.pyRevitVersion];

            if (_envData.Contains(EnvDictionaryKeys.sessionUUID))
                sessionUUID = (string)_envData[EnvDictionaryKeys.sessionUUID];


            if (_envData.Contains(EnvDictionaryKeys.outputStyleSheet))
                activeStyleSheet = (string)_envData[EnvDictionaryKeys.outputStyleSheet];


            if (_envData.Contains(EnvDictionaryKeys.usageLogState))
                usageLogState = (bool)_envData[EnvDictionaryKeys.usageLogState];

            if (_envData.Contains(EnvDictionaryKeys.usageLogFilePath))
                usageLogFilePath = (string)_envData[EnvDictionaryKeys.usageLogFilePath];

            if (_envData.Contains(EnvDictionaryKeys.usageLogServerUrl))
                usageLogServerUrl = (string)_envData[EnvDictionaryKeys.usageLogServerUrl];
        }
    }
}
