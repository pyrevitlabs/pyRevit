using System;
using IronPython.Runtime;


namespace PyRevitBaseClasses
{
	public static class EnvDictionaryKeys
	{
		public static string docEngineDict = "pyRevitIpyEngines";
		public static string addonName = "pyRevit";
		public static string root = String.Format("{0}_envvardict", EnvDictionaryKeys.addonName);
		public static string sessionUUID = String.Format("{0}_uuidISC", EnvDictionaryKeys.addonName);
		public static string addonVersion = String.Format("{0}_versionISC", EnvDictionaryKeys.addonName);
		public static string usageLogState = String.Format("{0}_usagelogstateISC", EnvDictionaryKeys.addonName);
		public static string usageLogFilePath = String.Format("{0}_usagelogfileISC", EnvDictionaryKeys.addonName);
		public static string usageLogServerUrl = String.Format("{0}_usagelogserverISC", EnvDictionaryKeys.addonName);
        public static string pyrevitOutputWindows = String.Format("{0}_outputsISC", EnvDictionaryKeys.addonName);
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
