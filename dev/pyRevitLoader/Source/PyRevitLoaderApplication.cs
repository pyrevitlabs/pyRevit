/*
   ██▓███▓██   ██▓ ██▀███  ▓█████ ██▒   █▓ ██▓▄▄▄█████▓
  ▓██░  ██▒██  ██▒▓██ ▒ ██▒▓█   ▀▓██░   █▒▓██▒▓  ██▒ ▓▒
  ▓██░ ██▓▒▒██ ██░▓██ ░▄█ ▒▒███   ▓██  █▒░▒██▒▒ ▓██░ ▒░
  ▒██▄█▓▒ ▒░ ▐██▓░▒██▀▀█▄  ▒▓█  ▄  ▒██ █░░░██░░ ▓██▓ ░
  ▒██▒ ░  ░░ ██▒▓░░██▓ ▒██▒░▒████▒  ▒▀█░  ░██░  ▒██▒ ░
  ▒▓▒░ ░  ░ ██▒▒▒ ░ ▒▓ ░▒▓░░░ ▒░ ░  ░ ▐░  ░▓    ▒ ░░
  ░▒ ░    ▓██ ░▒░   ░▒ ░ ▒░ ░ ░  ░  ░ ░░   ▒ ░    ░
  ░░      ▒ ▒ ░░    ░░   ░    ░       ░░   ▒ ░  ░
          ░ ░        ░        ░  ░     ░   ░
          ░ ░                         ░

  This is the entry point for pyRevit. Revit loads the PyRevitLoader.dll addon
  at startup, and PyRevitLoaderApplication.OnStartup calls into the C# session
  manager to build the UI and the button commands.
 */

using Autodesk.Revit.Attributes;
using Autodesk.Revit.UI;
using pyRevitAssemblyBuilder.AssemblyMaker;
using pyRevitAssemblyBuilder.SessionManager;
using pyRevitExtensionParser;
using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;

/* Note:
 * It is necessary that this code object do not have any references to IronPython.
 * To ensure the correct version of IronPython dlls are loaded, the OnStartup()
 * methods manually loads the IronPython assemblies before calling into the 
 * ScriptExecutor that has IronPython references
 */
namespace PyRevitLoader
{
	[Regeneration(RegenerationOption.Manual)]
	[Transaction(TransactionMode.Manual)]
	class PyRevitLoaderApplication : IExternalApplication
	{
		public static string LoaderPath => Path.GetDirectoryName(typeof(PyRevitLoaderApplication).Assembly.Location);
		private static UIControlledApplication _uiControlledApplication;
		private static UIApplication GetUIApplication(UIControlledApplication application)
		{
			var versionNumber = application.ControlledApplication.VersionNumber;
			var fieldName = int.Parse(versionNumber) >= RevitApiConstants.NEW_UIAPP_FIELD_VERSION 
				? RevitApiConstants.MODERN_UIAPP_FIELD 
				: RevitApiConstants.LEGACY_UIAPP_FIELD;
			var fi = application.GetType().GetField(fieldName, BindingFlags.NonPublic | BindingFlags.Instance);

			if (fi == null)
			{
				throw new InvalidOperationException(
					$"Could not find field '{fieldName}' on type '{application.GetType().FullName}'. " +
					"The Revit API internal implementation may have changed in this version.");
			}

			return (UIApplication)fi.GetValue(application);
		}

		// Hook into Revit to allow starting a command.
		Result IExternalApplication.OnStartup(UIControlledApplication application)
		{
			_uiControlledApplication = application;
			LoadAssembliesInFolder(LoaderPath);
			// We also need to load dlls from two folders up
			var commonFolder = Path.GetDirectoryName(Path.GetDirectoryName(LoaderPath));
			LoadAssembliesInFolder(commonFolder);

			// Load the session directly through the C# session manager. The Python
			// pre/post-load services are driven from within LoadSession, so Revit
			// startup no longer bootstraps an IronPython engine to reach the loader.
			return LoadSession();
		}

		private static void LoadAssembliesInFolder(string folder)
		{
			// load all engine assemblies
			// this is to ensure pyRevit is loaded on its own assemblies
			foreach (var engineDll in Directory.GetFiles(folder, "*.dll"))
			{
				try
				{
					Assembly.LoadFrom(engineDll);
				}
				catch (Exception ex)
				{
					// Log assembly load failures - some assemblies may fail to load and that's acceptable
					Trace.WriteLine($"Failed to load assembly '{engineDll}': {ex.Message}");
				}
			}
		}

		// Shared entry for initial startup and reload. The C# SessionManagerService
		// drives the full load, including the residual Python pre/post-load services.
		public static Result LoadSession()
		{
			try
			{
				if (_uiControlledApplication == null)
				{
					throw new InvalidOperationException("UIControlledApplication not available." +
						" LoadSession can only be called after OnStartup.");
				}

				var uiApplication = GetUIApplication(_uiControlledApplication);
				var revitVersion = _uiControlledApplication.ControlledApplication.VersionNumber;

				var sessionManager = ServiceFactory.CreateSessionManagerService(
					revitVersion,
					AssemblyBuildStrategy.Roslyn,
					uiApplication);

				sessionManager.LoadSession();

				return Result.Succeeded;
			}
			catch (Exception ex)
			{
				TaskDialog.Show("Error Loading pyRevit Session",
					$"An error occurred while loading the pyRevit session:\n\n{ex.Message}\n\n" +
					$"Check the output window for details.");
				return Result.Failed;
			}
		}

		Result IExternalApplication.OnShutdown(UIControlledApplication application)
		{
			// FIXME: deallocate the python shell...
			return Result.Succeeded;
		}
	}
}
