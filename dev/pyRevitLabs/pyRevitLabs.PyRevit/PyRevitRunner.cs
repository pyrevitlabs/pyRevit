using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Diagnostics;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;
using pyRevitLabs.NLog;
using pyRevitLabs.TargetApps.Revit;

namespace pyRevitLabs.PyRevit {
    public class PyRevitRunnerCommand {
        public PyRevitRunnerCommand(string commandPath) => Path = commandPath;

        public override string ToString() {
            return $"{Name} | \"{Path}\"";
        }

        /// <summary>
        /// The command file name without its trailing <c>_command.py</c>, matched case-insensitively.
        /// </summary>
        public string Name {
            get {
                string fileName = System.IO.Path.GetFileName(Path);
                string postfix = PyRevitConsts.ExtensionUICommandPostfix;
                return fileName.EndsWith(postfix, StringComparison.OrdinalIgnoreCase)
                    ? fileName.Substring(0, fileName.Length - postfix.Length)
                    : fileName;
            }
        }
        public string Path { get; }
    }

    public class PyRevitRunnerExecEnv {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public PyRevitRunnerExecEnv(PyRevitAttachment attachment) {
            Attachment = attachment;

            // check if clone is compatible
            if (!CommonUtils.VerifyFile(PyRevitCloneRunner))
                throw new PyRevitException("Clone does not have Run feature. Update your clone to latest.");

            // generate unique id for this execution
            ExecutionId = Guid.NewGuid().ToString();
            // setup working dir
            WorkingDirectory = Path.Combine(CommonUtils.GetUserTempDirectory(), ExecutionId);
            CommonUtils.EnsurePath(WorkingDirectory);
        }

        private const string JournalNameTemplate = "PyRevitRunner_{0}.txt";
        private const string LogNameTemplate = "PyRevitRunner_{0}.log";
        private const string ManifestNameTemplate = "PyRevitRunner.addin";
        private const string DefaultEngineConfigs = "{\"full_frame\": true}";

        private const string JournalTemplate = @"' pyrevitrunner generated journal
' 0:< 'C {0};
Dim Jrn
Set Jrn = CrsJournalScript
Jrn.Directive ""DebugMode"", ""PerformAutomaticActionInErrorDialog"", {1}
Jrn.Directive ""DebugMode"", ""PermissiveJournal"", 1
Jrn.RibbonEvent ""TabActivated:Add-Ins""
Jrn.RibbonEvent ""Execute external command:CustomCtrl_%CustomCtrl_%Add-Ins%pyRevitRunner%PyRevitRunnerCommand:PyRevitRunner.PyRevitRunnerCommand""
Jrn.Data ""APIStringStringMapJournalData""  _
    , 6 _
    , ""ScriptSource"" , ""{2}"" _
    , ""SearchPaths"" , ""{3}"" _
    , ""Models"" , ""{4}"" _
    , ""EngineConfigs"" , ""{5}"" _
    , ""LogFile"" , ""{6}"" _
    , ""Inputs"" , ""{7}""
Jrn.Command ""SystemMenu"" , ""Quit the application; prompts to save projects , ID_APP_EXIT""
Jrn.Data ""TaskDialogResult"" , ""Do you want to save changes to Untitled?"", ""No"", ""IDNO""
";

        public void Begin(string script, IEnumerable<string> modelPaths, PyRevitRunnerOptions opts) {
            Script = script;
            ModelPaths = modelPaths;
            AllowDialogs = opts.AllowDialogs;
            InputsJson = opts.InputsJson;

            // generate journal and manifest file
            GenerateJournal();
            GenerateManifest();

            if (opts.ImportPath != null)
                CopyExistingAddons(opts.ImportPath);
        }

        public void End(PyRevitRunnerOptions opts) {
            // purge files if requested
            if (opts.PurgeTempFiles)
                Purge();
        }

        public PyRevitAttachment Attachment { get; private set; }
        public string Script { get; private set; }
        public IEnumerable<string> ModelPaths { get; private set; }
        public bool AllowDialogs { get; private set; }
        public string InputsJson { get; private set; }
        public bool PurgeAfterExec { get; private set; }

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

        // private

        // MDJ added code to copy all .addin files and subdirs into the batch running context.
        // This is to workaround built-in Revit addins like the NavisExporter not being available while using pyRevit batch.
        // Per MSDN, the below code is a relatively safe way to recurse through dirs and copy: http://msdn.microsoft.com/en-us/library/system.io.directoryinfo.aspx
        private void CopyExistingAddons(string sourceDirectory) {
            var targetDirectoryInfo = new DirectoryInfo(WorkingDirectory);
            CopyAll(new DirectoryInfo(sourceDirectory), targetDirectoryInfo);
        }

        private void GenerateJournal() {
            var engineConfigs = EscapeJournalString(DefaultEngineConfigs);
            File.WriteAllText(
                JournalFile,
                string.Format(
                    JournalTemplate,                                    // template string
                    CommonUtils.GetISOTimeStampNow(),                   // timestamp with format: 27-Oct-2016 19:33:31.459
                    AllowDialogs ? 0 : 1,                               // whether journal playback should allow dialogs
                    Script,                                             // script path
                    "",                                                 // sys paths
                    string.Join(";", ModelPaths),                       // model paths
                    engineConfigs,                                      // engine configs
                    LogFile,                                            // log file
                    EscapeJournalString(InputsJson ?? "")               // script inputs
                ));
        }

        private static string EscapeJournalString(string value) => value.Replace("\"", "\"\"");

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

        private static void CopyAll(DirectoryInfo source, DirectoryInfo target) {
            if (source.FullName.NormalizeAsPath() == target.FullName.NormalizeAsPath())
                return;

            // Check if the target directory exists, if not, create it.
            CommonUtils.EnsurePath(target.FullName);

            // Copy each file into it's new directory.
            foreach (FileInfo fi in source.GetFiles()) {
                logger.Debug(@"Copying {0}\{1}", target.FullName, fi.Name);
                fi.CopyTo(Path.Combine(target.ToString(), fi.Name), true);
            }

            // Copy each subdirectory using recursion.
            foreach (DirectoryInfo diSourceSubDir in source.GetDirectories()) {
                DirectoryInfo nextTargetSubDir =
                    target.CreateSubdirectory(diSourceSubDir.Name);
                CopyAll(diSourceSubDir, nextTargetSubDir);
            }
        }

        private void Purge() {
            CommonUtils.DeleteDirectory(WorkingDirectory);
            Purged = true;
        }
    }

    public class PyRevitRunnerOptions {
        public bool PurgeTempFiles { get; set; } = false;
        public bool AllowDialogs { get; set; } = false;
        public string ImportPath { get; set; }

        /// <summary>
        /// The JSON object the script receives as <c>__inputs__</c>, as produced by
        /// <see cref="PyRevitRunner.NormalizeInputs"/>. Null or empty gives the script an empty object.
        /// </summary>
        public string InputsJson { get; set; }
    }

    public static class PyRevitRunner {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        /// <summary>
        /// Validates caller-supplied script inputs and rewrites them as the single-line ASCII JSON the
        /// runner journal can carry.
        /// </summary>
        /// <param name="inputsJson">JSON text; null or whitespace means no inputs.</param>
        /// <returns>Compact JSON with non-ASCII characters escaped, or null when no inputs were given.</returns>
        /// <exception cref="PyRevitException">The text is not valid JSON, or is not a JSON object.</exception>
        public static string NormalizeInputs(string inputsJson) {
            if (string.IsNullOrWhiteSpace(inputsJson))
                return null;

            JToken parsed;
            try {
                using (var reader = new JsonTextReader(new StringReader(inputsJson)) { DateParseHandling = DateParseHandling.None }) {
                    parsed = JToken.ReadFrom(reader);
                }
            }
            catch (JsonException ex) {
                throw new PyRevitException($"Inputs are not valid JSON: {ex.Message}");
            }

            if (parsed.Type != JTokenType.Object)
                throw new PyRevitException("Inputs must be a JSON object.");

            using (var stringWriter = new StringWriter())
            using (var jsonWriter = new JsonTextWriter(stringWriter) {
                Formatting = Formatting.None,
                StringEscapeHandling = StringEscapeHandling.EscapeNonAscii
            }) {
                parsed.WriteTo(jsonWriter);
                jsonWriter.Flush();
                return stringWriter.ToString();
            }
        }

        /// <summary>
        /// Resolves the <c>--inputs</c> / <c>--inputs-file</c> options of <c>pyrevit run</c> to the
        /// validated, single-line JSON the runner journal carries.
        /// </summary>
        /// <param name="inputsJson">JSON text from <c>--inputs</c>, or null.</param>
        /// <param name="inputsFile">Path of a JSON file from <c>--inputs-file</c>, read instead of <paramref name="inputsJson"/> when given.</param>
        /// <returns>The result of <see cref="NormalizeInputs"/>.</returns>
        /// <exception cref="PyRevitException">The file is missing, or the text is not a JSON object.</exception>
        public static string ReadInputs(string inputsJson, string inputsFile) {
            if (inputsFile != null) {
                if (!File.Exists(inputsFile))
                    throw new PyRevitException($"Inputs file not found: \"{inputsFile}\"");
                inputsJson = File.ReadAllText(inputsFile);
            }
            return NormalizeInputs(inputsJson);
        }

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

            var execEnv = new PyRevitRunnerExecEnv(attachment);
            execEnv.Begin(scriptPath, modelPaths, opts);
            {
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
            }
            execEnv.End(opts);

            return execEnv;
        }
    }
}
