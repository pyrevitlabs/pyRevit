using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Diagnostics;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.NLog;
using pyRevitLabs.TargetApps.Revit;

namespace pyRevitLabs.PyRevit {
    public class PyRevitRunnerCommand {
        public PyRevitRunnerCommand(string commandPath) => Path = commandPath;
        
        public override string ToString() {
            return $"{Name} | \"{Path}\"";
        }
        
        public string Name => System.IO.Path.GetFileName(Path).Replace(PyRevitConsts.ExtensionUICommandPostfix, "");
        public string Path { get; }
    }

    public class PyRevitRunnerExecEnv {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public PyRevitRunnerExecEnv(PyRevitAttachment attachment, string script, IEnumerable<string> modelPaths) {
            Attachment = attachment;
            Script = script;
            ModelPaths = modelPaths;

            // check if clone is compatible
            if (!CommonUtils.VerifyFile(PyRevitCloneRunner))
                throw new PyRevitException("Clone does not have Run feature. Update your clone to latest.");

            // generate unique id for this execution
            ExecutionId = Guid.NewGuid().ToString();
            // setup working dir
            WorkingDirectory = Path.Combine(Environment.GetEnvironmentVariable("TEMP"), ExecutionId);
            CommonUtils.EnsurePath(WorkingDirectory);

            // generate journal and manifest file
            GenerateJournal();
            GenerateManifest();
        }

        private const string JournalNameTemplate = "PyRevitRunner_{0}.txt";
        private const string LogNameTemplate = "PyRevitRunner_{0}.log";
        private const string ManifestNameTemplate = "PyRevitRunner.addin";

        private const string JournalTemplate = @"' pyrevitrunner generated journal
' 0:< 'C {0};
Dim Jrn
Set Jrn = CrsJournalScript
Jrn.Directive ""DebugMode"", ""PerformAutomaticActionInErrorDialog"", 1
Jrn.Directive ""DebugMode"", ""PermissiveJournal"", 1
Jrn.RibbonEvent ""TabActivated:Add-Ins""
Jrn.RibbonEvent ""Execute external command:CustomCtrl_%CustomCtrl_%Add-Ins%pyRevitRunner%PyRevitRunnerCommand:PyRevitRunner.PyRevitRunnerCommand""
Jrn.Data ""APIStringStringMapJournalData""  _
    , 4 _
    , ""ScriptSource"" , ""{1}"" _
    , ""SearchPaths"" , ""{2}"" _
    , ""Models"" , ""{3}"" _
    , ""LogFile"" , ""{4}""
Jrn.Command ""SystemMenu"" , ""Quit the application; prompts to save projects , ID_APP_EXIT""
Jrn.Data ""TaskDialogResult"" , ""Do you want to save changes to Untitled?"", ""No"", ""IDNO""
";

        public PyRevitAttachment Attachment { get; private set; }
        public string Script { get; private set; }
        public IEnumerable<string> ModelPaths { get; private set; }

        public RevitProduct Revit { get { return Attachment.Product; } }
        public PyRevitClone Clone { get { return Attachment.Clone; } }
        public PyRevitEngine Engine { get { return Attachment.Engine; } }

        public string ExecutionId { get; private set; }
        public string WorkingDirectory { get; private set; }

        public string JournalFile {
            get { return Path.Combine(WorkingDirectory, string.Format(JournalNameTemplate, ExecutionId)); }
        }

        public string LogFile {
            get { return Path.Combine(WorkingDirectory, string.Format(LogNameTemplate, ExecutionId)); }
        }

        public string PyRevitCloneRunner => Path.Combine(Engine.Path, "pyRevitRunner.dll");

        public string PyRevitRunnerManifestFile {
            get { return Path.Combine(WorkingDirectory, ManifestNameTemplate); }
        }

        public bool Purged { get; private set; } = false;

        public void Purge() {
            CommonUtils.DeleteDirectory(WorkingDirectory);
            Purged = true;
        }

        // MDJ added code to copy all .addin files and subdirs into the batch running context.
        // This is to workaround built-in Revit addins like the NavisExporter not being available while using pyRevit batch. 
        // Per MSDN, the below code is a relatively safe way to recurse through dirs and copy: http://msdn.microsoft.com/en-us/library/system.io.directoryinfo.aspx 

        public void CopyExistingAddons(string sourceDirectory) {
            var targetDirectoryInfo = new DirectoryInfo(WorkingDirectory);
            CopyAll(new DirectoryInfo(sourceDirectory), targetDirectoryInfo);
        }

        // private
        private void GenerateJournal() {
            File.WriteAllText(
                JournalFile,
                string.Format(
                    JournalTemplate,                                    // template string
                    CommonUtils.GetISOTimeStampNow(),                   // timestamp with format: 27-Oct-2016 19:33:31.459
                    Script,                                             // script path
                    "",                                                 // sys paths
                    string.Join(";", ModelPaths),                       // model paths
                    LogFile                                             // log file
                ));
        }

        private void GenerateManifest() {
            RevitAddons.CreateManifestFile(Revit.ProductYear,
                                      Path.GetFileName(PyRevitRunnerManifestFile),
                                      "pyRevitRunner",
                                      PyRevitCloneRunner,
                                      "D49D3677-61C4-47A8-BFFF-49E6616D54C1",
                                      "PyRevitRunner.PyRevitRunnerApplication",
                                      PyRevitConsts.VendorId,
                                      addinPath: WorkingDirectory);
        }

        private static void CopyAll(DirectoryInfo source, DirectoryInfo target)
        {
            if (source.FullName.NormalizeAsPath() == target.FullName.NormalizeAsPath())
                return;

            // Check if the target directory exists, if not, create it.
            CommonUtils.EnsurePath(target.FullName);

            // Copy each file into it's new directory.
            foreach (FileInfo fi in source.GetFiles())
            {
                logger.Debug(@"Copying {0}\{1}", target.FullName, fi.Name);
                fi.CopyTo(Path.Combine(target.ToString(), fi.Name), true);
            }

            // Copy each subdirectory using recursion.
            foreach (DirectoryInfo diSourceSubDir in source.GetDirectories())
            {
                DirectoryInfo nextTargetSubDir =
                    target.CreateSubdirectory(diSourceSubDir.Name);
                CopyAll(diSourceSubDir, nextTargetSubDir);
            }
        }
    }

    public class PyRevitRunnerOptions {
        public PyRevitRunnerOptions() { }

        public bool PurgeTempFiles = false;
        public string ImportPath;
    }

    public static class PyRevitRunner {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public static PyRevitRunnerExecEnv Run(PyRevitAttachment attachment,
                                               string scriptPath,
                                               IEnumerable<string> modelPaths,
                                               PyRevitRunnerOptions opts = null) {
            var product = attachment.Product;
            var clone = attachment.Clone;
            var engineVer = attachment.Engine != null ? attachment.Engine.Version : 0;
            logger.Debug("Running script: \"{0}\"", scriptPath);
            logger.Debug("With: {0}", product);
            logger.Debug("Using: {0}", clone);
            logger.Debug("On Engine: {0}", engineVer);

            // setup the execution environment
            if (opts is null)
                opts = new PyRevitRunnerOptions();

            var execEnv = new PyRevitRunnerExecEnv(attachment, scriptPath, modelPaths);

            // purge files if requested
            if (opts.ImportPath != null)
                execEnv.CopyExistingAddons(opts.ImportPath);

            // run the process
            ProcessStartInfo revitProcessInfo = new ProcessStartInfo(product.ExecutiveLocation) {
                Arguments = execEnv.JournalFile,
                WorkingDirectory = execEnv.WorkingDirectory,
                UseShellExecute = false,
                CreateNoWindow = true
            };
            logger.Debug("Running Revit in playback mode with journal: \"{0}\"", execEnv.JournalFile);
            var revitProcess = Process.Start(revitProcessInfo);
            revitProcess.WaitForExit();

            // purge files if requested
            if (opts.PurgeTempFiles)
                execEnv.Purge();

            return execEnv;
        }
    }
}
