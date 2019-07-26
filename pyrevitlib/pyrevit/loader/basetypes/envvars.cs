using System;
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

        public static string usageLogState = string.Format("{0}_USAGELOGSTATE", keyPrefix);
        public static string usageLogFilePath = string.Format("{0}_USAGELOGFILE", keyPrefix);
        public static string usageLogServerUrl = string.Format("{0}_USAGELOGSERVER", keyPrefix);

        public static string loadedAssm = string.Format("{0}_LOADEDASSMS", keyPrefix);
        public static string loadedAssmCount = string.Format("{0}_ASSMCOUNT", keyPrefix);

        public static string autoupdating = string.Format("{0}_AUTOUPDATING", keyPrefix);

        public static string refedAssms = string.Format("{0}_REFEDASSMS", keyPrefix);
    }

    public class EnvDictionary
    {
        public string sessionUUID;
        public string RevitVersion;
        public string pyRevitVersion;
        public string pyRevitClone;
        public int pyRevitIpyVersion;
        public int pyRevitCpyVersion;

        public string activeStyleSheet;

        public bool usageLogState;
        public string usageLogFilePath;
        public string usageLogServerUrl;

        public string[] referencedAssemblies;

        public EnvDictionary()
        {
            // get the dictionary from appdomain
            var _envData = (PythonDictionary)AppDomain.CurrentDomain.GetData(DomainStorageKeys.pyRevitEnvVarsDictKey);

            if (_envData.Contains(EnvDictionaryKeys.RevitVersion))
                RevitVersion = (string)_envData[EnvDictionaryKeys.RevitVersion];

            if (_envData.Contains(EnvDictionaryKeys.pyRevitVersion))
                pyRevitVersion = (string)_envData[EnvDictionaryKeys.pyRevitVersion];

            if (_envData.Contains(EnvDictionaryKeys.pyRevitClone))
                pyRevitClone = (string)_envData[EnvDictionaryKeys.pyRevitClone];

            if (_envData.Contains(EnvDictionaryKeys.pyRevitIpyVersion))
                pyRevitIpyVersion = (int)_envData[EnvDictionaryKeys.pyRevitIpyVersion];

            if (_envData.Contains(EnvDictionaryKeys.pyRevitCpyVersion))
                pyRevitCpyVersion = (int)_envData[EnvDictionaryKeys.pyRevitCpyVersion];

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

            if (_envData.Contains(EnvDictionaryKeys.refedAssms))
                referencedAssemblies  = (string[])_envData[EnvDictionaryKeys.refedAssms];
        }
    }
}
