using System;
using System.Collections.Generic;
using IronPython.Runtime;


namespace PyRevitBaseClasses
{
	public static class EnvDictionaryKeys
	{
		// keep updated from pyrevit root module
		public static string addonName = "pyRevit";
		// keep updated from pyrevit.coreutils.envvars
		public static string root = String.Format("{0}_envvardict", EnvDictionaryKeys.addonName);
		// keep updated from pyrevit.versionmgr
		public static string addonVersion = String.Format("{0}_versionISC", EnvDictionaryKeys.addonName);
		// keep updated from pyrevit.coreutils.usagelog
		public static string usageLogState = String.Format("{0}_usagelogstateISC", EnvDictionaryKeys.addonName);
		public static string usageLogFilePath = String.Format("{0}_usagelogfileISC", EnvDictionaryKeys.addonName);
		public static string usageLogServerUrl = String.Format("{0}_usagelogserverISC", EnvDictionaryKeys.addonName);
	}

	public class EnvDictionary
	{
		private readonly PythonDictionary _envData;

		public EnvDictionary() {
			// get the dictionary from appdomain
			_envData = (PythonDictionary)AppDomain.CurrentDomain.GetData(EnvDictionaryKeys.root);
		}

		public string GetPyRevitVersion() {
			return (string)_envData[EnvDictionaryKeys.addonVersion];
		}

		public bool GetUsageLogState() {
			return (bool)_envData[EnvDictionaryKeys.usageLogState];
		}

		public string GetUsageLogFilePath() {
			return (string)_envData[EnvDictionaryKeys.usageLogFilePath];
		}

		public string GetUsageLogServerUrl() {
			return (string)_envData[EnvDictionaryKeys.usageLogServerUrl];
		}
	}
}
