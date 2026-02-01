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

			try
			{
				var uiApplication = GetUIApplication(application);
				var result = ExecuteStartupScript(application);
				return result;
			}
			catch (Exception ex)
			{
				TaskDialog.Show("Error Loading Startup Script", ex.ToString());
				return Result.Failed;
			}
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

	private static Result ExecuteStartupScript(UIControlledApplication uiControlledApplication)
		{
			var uiApplication = GetUIApplication(uiControlledApplication);
			// execute StartupScript
			Result result = Result.Succeeded;
			var startupScript = GetStartupScriptPath();
			if (startupScript != null)
			{
				var executor = new ScriptExecutor(uiApplication);
				result = executor.ExecuteScript(startupScript);
				if (result == Result.Failed)
				{
					TaskDialog.Show("Error Loading pyRevit", executor.Message);
				}
			}

			return result;
		}

		public static Result LoadSession(object pythonLogger = null, string buildStrategy = null)
		{
			try
			{
				// Use the stored UIControlledApplication
				if (_uiControlledApplication == null)
				{
					throw new InvalidOperationException("UIControlledApplication not available." +
						" LoadSession can only be called after OnStartup.");
				}

				var uiControlledApplication = _uiControlledApplication;
				var uiApplication = GetUIApplication(uiControlledApplication);

				// Get the current Revit version
				var revitVersion = uiControlledApplication.ControlledApplication.VersionNumber;

			// Always use Roslyn build strategy
			AssemblyBuildStrategy strategyEnum = AssemblyBuildStrategy.Roslyn;

				var sessionManager = ServiceFactory.CreateSessionManagerService(
					revitVersion,
					strategyEnum,
					uiApplication,
					pythonLogger);

				// Load the session using the C# SessionManagerService
				sessionManager.LoadSession();

				return Result.Succeeded;
			}
			catch (Exception ex)
			{
				TaskDialog.Show("Error Loading C# Session",
					$"An error occurred while loading the C# session:\n\n{ex.Message}\n\n" +
					$"Check the output window for details.");
				return Result.Failed;
			}
		}
		private static string GetStartupScriptPath()
		{
			var assemblyLocation = Assembly.GetExecutingAssembly().Location;
			var loaderDir = Path.GetDirectoryName(assemblyLocation);
			if (string.IsNullOrEmpty(loaderDir))
			{
				throw new InvalidOperationException($"Could not determine directory for assembly location: {assemblyLocation}");
			}

			var dllDir = Path.GetDirectoryName(loaderDir);
			if (string.IsNullOrEmpty(dllDir))
			{
				throw new InvalidOperationException($"Could not determine parent directory for loader directory: {loaderDir}");
			}

			var assemblyName = Assembly.GetExecutingAssembly().GetName().Name;
			return Path.Combine(dllDir, $"{assemblyName}.py");
		}
		Result IExternalApplication.OnShutdown(UIControlledApplication application)
		{
			// FIXME: deallocate the python shell...
			return Result.Succeeded;
		}
	}
}