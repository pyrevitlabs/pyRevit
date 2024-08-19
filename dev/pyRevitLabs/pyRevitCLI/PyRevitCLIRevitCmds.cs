﻿using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.Json;
using pyRevitLabs.NLog;
using pyRevitLabs.PyRevit;
using pyRevitLabs.TargetApps.Revit;
using Console = Colorful.Console;

namespace pyRevitCLI
{
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
        ListAvailableCommands() {
            foreach (PyRevitClone clone in PyRevitClones.GetRegisteredClones()) {
                PyRevitCLIAppCmds.PrintHeader($"Commands in Clone \"{clone.Name}\"");
                foreach ( PyRevitExtension ext in clone.GetExtensions()) {
                    if (ext.Type == PyRevitExtensionTypes.UIExtension) {
                        foreach (PyRevitRunnerCommand cmd in ext.GetCommands())
                            Console.WriteLine(cmd);
                    }
                }
            }

            foreach (PyRevitExtension ext in PyRevitExtensions.GetInstalledExtensions()) {
                if (ext.Type == PyRevitExtensionTypes.UIExtension) {
                    PyRevitCLIAppCmds.PrintHeader($"Commands in Extension \"{ext.Name}\"");
                    foreach (PyRevitRunnerCommand cmd in ext.GetCommands())
                        Console.WriteLine(cmd);
                }
            }
        }

        internal static void
        RunExtensionCommand(string commandName, string targetFile, string revitYear, PyRevitRunnerOptions runOptions, bool targetIsFileList = false) {
            // verify command
            if (commandName is null || commandName == string.Empty)
                throw new Exception("Command name must be provided.");

            // try target revit year
            int revitYearNumber = 0;
            int.TryParse(revitYear, out revitYearNumber);


            // setup a list of models
            var modelFiles = new List<string>();
            // if target file is a list of model paths
            if (targetIsFileList) {
                // attempt at reading the list file and grab the model files only
                foreach (var modelPath in File.ReadAllLines(targetFile))
                    modelFiles.Add(modelPath);
            }
            // otherwise just work on this model
            else
                modelFiles.Add(targetFile);


            // verify all models are accessible
            foreach (string modelFile in modelFiles)
                if (!CommonUtils.VerifyFile(modelFile))
                    throw new Exception($"Model does not exist at \"{modelFile}\"");


            // determine which Revit version to launch
            if (revitYearNumber != 0) {
                foreach (string modelFile in modelFiles) {
                    var modelInfo = new RevitModelFile(modelFile);

                    // if specific revit version is provided, make sure model is not newer
                    if (modelInfo.RevitProduct != null) {
                        if (modelInfo.RevitProduct.ProductYear > revitYearNumber)
                            throw new Exception($"Model at \"{modelFile}\" is newer than the specified version: {revitYearNumber}");
                    }
                    else
                        throw new Exception($"Can not detect the Revit version of model at \"{modelFile}\". Model might be newer than specified version {revitYearNumber}.");
                }
            }
            else {
                // determine revit model version from given files
                foreach (string modelFile in modelFiles) {
                    var modelInfo = new RevitModelFile(modelFile);
                    if (modelInfo.RevitProduct != null) {
                        if (revitYearNumber == 0)
                            revitYearNumber = modelInfo.RevitProduct.ProductYear;
                        else if (modelInfo.RevitProduct.ProductYear > revitYearNumber)
                            revitYearNumber = modelInfo.RevitProduct.ProductYear;
                    }
                }

                // if could not determine revit version from given files,
                // use latest version
                if (revitYearNumber == 0)
                    revitYearNumber = RevitProduct.ListInstalledProducts().Max(r => r.ProductYear);
            }

            // now run
            if (revitYearNumber != 0) {
                // determine attached clone
                var attachment = PyRevitAttachments.GetAttached(revitYearNumber);
                if (attachment is null)
                    logger.Error($"pyRevit is not attached to Revit \"{revitYearNumber}\". " +
                                  "Runner needs to use the attached clone and engine to execute the script.");
                else {
                    // determine script to run
                    string commandScriptPath = null;

                    if (!CommonUtils.VerifyPythonScript(commandName)) {
                        logger.Debug("Input is not a script file \"{0}\"", commandName);
                        logger.Debug("Attempting to find run command matching \"{0}\"", commandName);

                        // try to find run command in attached clone being used for execution
                        // if not found, try to get run command from all other installed extensions
                        var targetExtensions = new List<PyRevitExtension>();
                        if (attachment.Clone != null) {
                            targetExtensions.AddRange(attachment.Clone.GetExtensions());
                        }
                        targetExtensions.AddRange(PyRevitExtensions.GetInstalledExtensions());

                        foreach (PyRevitExtension ext in targetExtensions) {
                            logger.Debug("Searching for run command in: \"{0}\"", ext.ToString());
                            if (ext.Type == PyRevitExtensionTypes.UIExtension) {
                                try {
                                    var cmdScript = ext.GetCommand(commandName);
                                    if (cmdScript != null) {
                                        logger.Debug("Run command matching \"{0}\" found: \"{1}\"",
                                                        commandName, cmdScript);
                                        commandScriptPath = cmdScript.Path;
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
                        commandScriptPath = commandName;

                    // if command is not found, stop
                    if (commandScriptPath is null)
                        throw new PyRevitException(
                            string.Format("Run command not found: \"{0}\"", commandName)
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

        // privates:
        // print info on a revit model
        private static void PrintModelInfo(RevitModelFile model) {
            if (model.RevitProduct != null)
                Console.WriteLine(
                    $"Created in: {model.RevitProduct.Name} {model.RevitProduct.BuildNumber}({model.RevitProduct.BuildTarget})");
            else
                Console.WriteLine(model.BuildInfoLine);

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
                Console.WriteLine(string.Format("{0} | Version: {1} | Build: {2}({3})", revit.Name, revit.Version, revit.BuildNumber, revit.BuildTarget));

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
                    string.Format("\"{0}\"", model.RevitProduct != null ? model.RevitProduct.Name : ""),
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
                    string.Format("\"{0}\"", revit.Name),
                };

                csv.Append(string.Join(",", data) + "\n");
            }

            logger.Info(string.Format("Writing results to \"{0}\"", outputCSV));
            File.WriteAllText(outputCSV, csv.ToString());
        }
    }
}
