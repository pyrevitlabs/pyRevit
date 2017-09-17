using System;
using IronPython.Runtime;


namespace PyRevitBaseClasses
{
	public static class EnvDictionaryKeys
	{
		public static string docEngineDict = "pyRevitIpyEngines";

        public static string baseName = "PYREVIT";

        // root env var dictionary key.
        // must be the same in this file and pyrevit/coreutils/envvars.py
		public static string root = String.Format("{0}_ENVVARDICT", EnvDictionaryKeys.baseName);

		public static string sessionUUID = String.Format("{0}_UUID", EnvDictionaryKeys.baseName);
		public static string addonVersion = String.Format("{0}_VERSION", EnvDictionaryKeys.baseName);

        // must be the same in this file and pyrevit/coreutils/logger.py
        public static string loggingLevel = String.Format("{0}_LOGGINGLEVEL", EnvDictionaryKeys.baseName);

		public static string usageLogState = String.Format("{0}_USAGELOGSTATE", EnvDictionaryKeys.baseName);
		public static string usageLogFilePath = String.Format("{0}_USAGELOGFILE", EnvDictionaryKeys.baseName);
		public static string usageLogServerUrl = String.Format("{0}_USAGELOGSERVER", EnvDictionaryKeys.baseName);

        public static string outputWindows = String.Format("{0}_OUTPUTSWINDOWS", EnvDictionaryKeys.baseName);

        public static string loadedAssm = String.Format("{0}_LOADEDASSMS", EnvDictionaryKeys.baseName);
        public static string loadedAssmCount = String.Format("{0}_ASSMCOUNT", EnvDictionaryKeys.baseName);

    }

    public class EnvDictionary
	{
		private readonly PythonDictionary _envData;
		public string sessionUUID;
		public string addonVersion;
		public bool usageLogState;
		public string usageLogFilePath;
		public string usageLogServerUrl;

		public EnvDictionary() {
			// get the dictionary from appdomain
			_envData = (PythonDictionary)AppDomain.CurrentDomain.GetData(EnvDictionaryKeys.root);

			if (_envData.Contains(EnvDictionaryKeys.addonVersion))
    			addonVersion = (string)_envData[EnvDictionaryKeys.addonVersion];
			if (_envData.Contains(EnvDictionaryKeys.sessionUUID))
    			sessionUUID = (string)_envData[EnvDictionaryKeys.sessionUUID];
			if (_envData.Contains(EnvDictionaryKeys.usageLogState))
    			usageLogState = (bool)_envData[EnvDictionaryKeys.usageLogState];
			if (_envData.Contains(EnvDictionaryKeys.usageLogFilePath))
    			usageLogFilePath = (string)_envData[EnvDictionaryKeys.usageLogFilePath];
			if (_envData.Contains(EnvDictionaryKeys.usageLogServerUrl))
    			usageLogServerUrl = (string)_envData[EnvDictionaryKeys.usageLogServerUrl];
		}
	}
}
