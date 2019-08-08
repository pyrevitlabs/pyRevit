using System;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using System.Drawing;
using System.Diagnostics;

using pyRevitLabs.Common;
using pyRevitLabs.CommonCLI;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.TargetApps.Revit;
using pyRevitLabs.Language.Properties;

using pyRevitLabs.NLog;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Serialization;

using Console = Colorful.Console;

namespace pyRevitCLI {
    internal static class PyRevitCLIRevitCmds {
        static Logger logger = LogManager.GetCurrentClassLogger();

        internal static void
        PrintLocalRevits(bool running = false) {
            if (running) {
                PyRevitCLIAppCmds.PrintHeader("Running Revit Instances");
                foreach (var revit in RevitController.ListRunningRevits().OrderByDescending(x => x.RevitProduct.Version))
                    Console.WriteLine(revit);
            }
            else {
                PyRevitCLIAppCmds.PrintHeader("Installed Revits");
                foreach (var revit in RevitProduct.ListInstalledProducts().OrderByDescending(x => x.Version))
                    Console.WriteLine(revit);
            }
        }

        internal static void
        KillAllRevits(string revitYear) {
            int revitYearNumber = 0;
            if (int.TryParse(revitYear, out revitYearNumber))
                RevitController.KillRunningRevits(revitYearNumber);
            else
                RevitController.KillAllRunningRevits();
        }

        internal static void
        ProcessFileInfo(string targetPath, string outputCSV,
                        bool IncludeRVT=true, bool includeRTE=false, bool includeRFA=false, bool includeRFT=false) {
            // if targetpath is a single model print the model info
            if (File.Exists(targetPath))
                if (outputCSV != null)
                    ExportModelInfoToCSV(
                        new List<RevitModelFile>() { new RevitModelFile(targetPath) },
                        outputCSV
                        );
                else
                    PrintModelInfo(new RevitModelFile(targetPath));

            // collect all revit models
            else {
                var models = new List<RevitModelFile>();
                var errorList = new List<(string, string)>();
                var fileSearchPatterns = new List<string>();

                // determine search patterns
                // if no other file format is specified search for rvt only
                if ((!includeRTE && !includeRFA && !includeRFT) || IncludeRVT)
                    fileSearchPatterns.Add("*.rvt");

                if (includeRTE)
                    fileSearchPatterns.Add("*.rte");
                if (includeRFA)
                    fileSearchPatterns.Add("*.rfa");
                if (includeRFT)
                    fileSearchPatterns.Add("*.rft");

                logger.Info(string.Format("Searching for revit files under \"{0}\"", targetPath));
                FileAttributes attr = File.GetAttributes(targetPath);
                if ((attr & FileAttributes.Directory) == FileAttributes.Directory) {
                    foreach(string searchPattern in fileSearchPatterns) {
                        var files = Directory.EnumerateFiles(targetPath, searchPattern, SearchOption.AllDirectories);
                        logger.Info(string.Format(" {0} revit files found under \"{1}\"", files.Count(), targetPath));
                        foreach (var file in files) {
                            try {
                                logger.Info(string.Format("Revit file found \"{0}\"", file));
                                var model = new RevitModelFile(file);
                                models.Add(model);
                            }
                            catch (Exception ex) {
                                errorList.Add((file, ex.Message));
                            }
                        }
                    }
                }

                if (outputCSV != null)
                    ExportModelInfoToCSV(models, outputCSV, errorList);
                else {
                    // report info on all files
                    foreach (var model in models) {
                        Console.WriteLine(model.FilePath);
                        PrintModelInfo(new RevitModelFile(model.FilePath));
                        Console.WriteLine();
                    }

                    // write list of files with errors
                    if (errorList.Count > 0) {
                        Console.WriteLine("An error occured while processing these files:");
                        foreach (var errinfo in errorList)
                            Console.WriteLine(string.Format("\"{0}\": {1}\n", errinfo.Item1, errinfo.Item2));
                    }
                }
            }
        }

        internal static void
        ProcessBuildInfo(string outputCSV) {
            if (outputCSV != null)
                ExportBuildInfoToCSV(outputCSV);
            else
                PrintBuildInfo();
        }

        internal static void
        PrepareAddonsDir(string revitYear, bool allUses) {
            int revitYearNumber = 0;
            if (int.TryParse(revitYear, out revitYearNumber))
                RevitAddons.PrepareAddonPath(revitYearNumber, allUsers: allUses);
        }


        internal static void
        RunPythonCommand(string inputCommand, string targetFile, string revitYear, PyRevitRunnerOptions runOptions) {
            // determine if script or command

            var modelFiles = new List<string>();
            // make sure file exists
            if (targetFile != null)
                CommonUtils.VerifyFile(targetFile);

            if (inputCommand != null) {
                // determine target revit year
                int revitYearNumber = 0;
                // if revit year is not specified try to get from model file
                if (revitYear == null) {
                    if (targetFile != null) {
                        try {
                            revitYearNumber = new RevitModelFile(targetFile).RevitProduct.ProductYear;
                            // collect model names also
                            modelFiles.Add(targetFile);
                        }
                        catch (Exception ex) {
                            logger.Error(
                                "Revit version must be explicitly specifies if using a model list file. | {0}",
                                ex.Message
                                );
                        }
                    }
                    // if no revit year and no model, run with latest revit
                    else
                        revitYearNumber = RevitProduct.ListInstalledProducts().Max(r => r.ProductYear);
                }
                // otherwise, grab the year from argument
                else {
                    revitYearNumber = int.Parse(revitYear);
                    // prepare model list of provided
                    if (targetFile != null) {
                        try {
                            var modelVer = new RevitModelFile(targetFile).RevitProduct.ProductYear;
                            if (revitYearNumber < modelVer)
                                logger.Warn("Model is newer than the target Revit version.");
                            else
                                modelFiles.Add(targetFile);
                        }
                        catch {
                            // attempt at reading the list file and grab the model files only
                            foreach (var modelPath in File.ReadAllLines(targetFile)) {
                                if (CommonUtils.VerifyFile(modelPath)) {
                                    try {
                                        var modelVer = new RevitModelFile(modelPath).RevitProduct.ProductYear;
                                        if (revitYearNumber < modelVer)
                                            logger.Warn("Model is newer than the target Revit version.");
                                        else
                                            modelFiles.Add(modelPath);
                                    }
                                    catch {
                                        logger.Error("File is not a valid Revit file: \"{0}\"", modelPath);
                                    }
                                }
                                else
                                    logger.Error("File does not exist: \"{0}\"", modelPath);
                            }
                        }
                    }
                }

                // now run
                if (revitYearNumber != 0) {
                    // determine attached clone
                    var attachment = PyRevitAttachments.GetAttached(revitYearNumber);
                    if (attachment == null)
                        logger.Error("pyRevit is not attached to Revit \"{0}\". " +
                                     "Runner needs to use the attached clone and engine to execute the script.",
                                     revitYear);
                    else {
                        // determine script to run
                        string commandScriptPath = null;

                        if (!CommonUtils.VerifyPythonScript(inputCommand)) {
                            logger.Debug("Input is not a script file \"{0}\"", inputCommand);
                            logger.Debug("Attempting to find run command matching \"{0}\"", inputCommand);

                            // try to find run command in attached clone being used for execution
                            // if not found, try to get run command from all other installed extensions
                            var targetExtensions = new List<PyRevitExtension>();
                            if (attachment.Clone != null) {
                                targetExtensions.AddRange(attachment.Clone.GetExtensions());
                            }
                            targetExtensions.AddRange(PyRevitExtensions.GetInstalledExtensions());

                            foreach (PyRevitExtension ext in targetExtensions) {
                                logger.Debug("Searching for run command in: \"{0}\"", ext.ToString());
                                if (ext.Type == PyRevitExtensionTypes.RunnerExtension) {
                                    try {
                                        var cmdScript = ext.GetRunCommand(inputCommand);
                                        if (cmdScript != null) {
                                            logger.Debug("Run command matching \"{0}\" found: \"{1}\"",
                                                         inputCommand, cmdScript);
                                            commandScriptPath = cmdScript;
                                            break;
                                        }
                                    }
                                    catch {
                                        // does not include command
                                        continue;
                                    }
                                }
                            }
                        }
                        else
                            commandScriptPath = inputCommand;

                        // if command is not found, stop
                        if (commandScriptPath == null)
                            throw new PyRevitException(
                                string.Format("Run command not found: \"{0}\"", inputCommand)
                                );

                        // RUN!
                        var execEnv = PyRevitRunner.Run(
                            attachment,
                            commandScriptPath,
                            modelFiles,
                            runOptions
                        );

                        // print results (exec env)
                        PyRevitCLIAppCmds.PrintHeader("Execution Environment");
                        Console.WriteLine(string.Format("Execution Id: \"{0}\"", execEnv.ExecutionId));
                        Console.WriteLine(string.Format("Product: {0}", execEnv.Revit));
                        Console.WriteLine(string.Format("Clone: {0}", execEnv.Clone));
                        Console.WriteLine(string.Format("Engine: {0}", execEnv.Engine));
                        Console.WriteLine(string.Format("Script: \"{0}\"", execEnv.Script));
                        Console.WriteLine(string.Format("Working Directory: \"{0}\"", execEnv.WorkingDirectory));
                        Console.WriteLine(string.Format("Journal File: \"{0}\"", execEnv.JournalFile));
                        Console.WriteLine(string.Format("Manifest File: \"{0}\"", execEnv.PyRevitRunnerManifestFile));
                        Console.WriteLine(string.Format("Log File: \"{0}\"", execEnv.LogFile));
                        // report whether the env was purge or not
                        if (execEnv.Purged)
                            Console.WriteLine("Execution env is successfully purged.");

                        // print target models
                        if (execEnv.ModelPaths.Count() > 0) {
                            PyRevitCLIAppCmds.PrintHeader("Target Models");
                            foreach (var modelPath in execEnv.ModelPaths)
                                Console.WriteLine(modelPath);
                        }

                        // print log file contents if exists
                        if (File.Exists(execEnv.LogFile)) {
                            PyRevitCLIAppCmds.PrintHeader("Execution Log");
                            Console.WriteLine(File.ReadAllText(execEnv.LogFile));
                        }
                    }
                }
            }
        }

        // privates:
        // print info on a revit model
        private static void PrintModelInfo(RevitModelFile model) {
            Console.WriteLine(string.Format("Created in: {0} ({1}({2}))",
                                model.RevitProduct.ProductName,
                                model.RevitProduct.BuildNumber,
                                model.RevitProduct.BuildTarget));
            Console.WriteLine(string.Format("Workshared: {0}", model.IsWorkshared ? "Yes" : "No"));
            if (model.IsWorkshared)
                Console.WriteLine(string.Format("Central Model Path: {0}", model.CentralModelPath));
            Console.WriteLine(string.Format("Last Saved Path: {0}", model.LastSavedPath));
            Console.WriteLine(string.Format("Document Id: {0}", model.UniqueId));
            Console.WriteLine(string.Format("Open Workset Settings: {0}", model.OpenWorksetConfig));
            Console.WriteLine(string.Format("Document Increment: {0}", model.DocumentIncrement));

            // print project information properties
            Console.WriteLine("Project Information (Properties):");
            foreach(var item in model.ProjectInfoProperties.OrderBy(x => x.Key)) {
                Console.WriteLine("\t{0} = {1}", item.Key, item.Value.ToEscaped());
            }

            if (model.IsFamily) {
                Console.WriteLine("Model is a Revit Family!");
                Console.WriteLine(string.Format("Category Name: {0}", model.CategoryName));
                Console.WriteLine(string.Format("Host Category Name: {0}", model.HostCategoryName));
            }
        }

        private static void PrintBuildInfo() {
            PyRevitCLIAppCmds.PrintHeader("Supported Revits");
            foreach (var revit in RevitProduct.ListSupportedProducts().OrderByDescending(x => x.Version))
                Console.WriteLine(string.Format("{0} | Version: {1} | Build: {2}({3})", revit.ProductName, revit.Version, revit.BuildNumber, revit.BuildTarget));

        }

        // export model info to csv
        private static void ExportModelInfoToCSV(IEnumerable<RevitModelFile> models,
                                                 string outputCSV,
                                                 List<(string, string)> errorList = null) {
            logger.Info(string.Format("Building CSV data to \"{0}\"", outputCSV));
            var csv = new StringBuilder();
            csv.Append(
                "filepath,productname,buildnumber,isworkshared,centralmodelpath,lastsavedpath,uniqueid,projectinfo,error\n"
                );
            foreach (var model in models) {
                // build project info string
                var jsonData = new Dictionary<string, object>();
                foreach (var item in model.ProjectInfoProperties.OrderBy(x => x.Key)) {
                    jsonData[item.Key] = item.Value;
                }

                // create csv entry
                var data = new List<string>() {
                    string.Format("\"{0}\"", model.FilePath),
                    string.Format("\"{0}\"", model.RevitProduct != null ? model.RevitProduct.ProductName : ""),
                    string.Format("\"{0}\"", model.RevitProduct != null ? model.RevitProduct.BuildNumber : ""),
                    string.Format("\"{0}\"", model.IsWorkshared ? "True" : "False"),
                    string.Format("\"{0}\"", model.CentralModelPath),
                    string.Format("\"{0}\"", model.LastSavedPath),
                    string.Format("\"{0}\"", model.UniqueId.ToString()),
                    JsonConvert.SerializeObject(jsonData).PrepareJSONForCSV(),
                    ""
                };

                csv.Append(string.Join(",", data) + "\n");
            }

            // write list of files with errors
            if (errorList != null) {
                logger.Debug("Adding errors to \"{0}\"", outputCSV);
                foreach (var errinfo in errorList)
                    csv.Append(string.Format("\"{0}\",,,,,,,,\"{1}\"\n", errinfo.Item1, errinfo.Item2));
            }

            logger.Info(string.Format("Writing results to \"{0}\"", outputCSV));
            File.WriteAllText(outputCSV, csv.ToString());
        }

        // export build info to csv
        private static void ExportBuildInfoToCSV(string outputCSV) {
            logger.Info(string.Format("Building CSV data to \"{0}\"", outputCSV));
            var csv = new StringBuilder();
            csv.Append(
                "\"buildnum\",\"buildversion\",\"productname\"\n"
                );
            foreach (var revit in RevitProduct.ListSupportedProducts().OrderByDescending(x => x.Version)) {
                // create csv entry
                var data = new List<string>() {
                    string.Format("\"{0}\"", revit.BuildNumber),
                    string.Format("\"{0}\"", revit.Version),
                    string.Format("\"{0}\"", revit.ProductName),
                };

                csv.Append(string.Join(",", data) + "\n");
            }

            logger.Info(string.Format("Writing results to \"{0}\"", outputCSV));
            File.WriteAllText(outputCSV, csv.ToString());
        }
    }
}
