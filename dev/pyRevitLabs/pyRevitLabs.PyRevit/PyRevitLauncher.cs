using System;
using System.Diagnostics;
using System.IO;
using System.Text.RegularExpressions;
using System.Threading;

using pyRevitLabs.Common;
using pyRevitLabs.NLog;
using pyRevitLabs.TargetApps.Revit;

namespace pyRevitLabs.PyRevit {
    /// <summary>
    /// A Revit session prepared by <see cref="PyRevitLauncher"/>: the per-launch directory holding
    /// the manifest and journal, and the clone and engine the session will load.
    /// </summary>
    public sealed class PyRevitLaunch {
        internal PyRevitLaunch(string directory, RevitProduct product, PyRevitClone clone, PyRevitEngine engine, string configRoot) {
            Directory = directory;
            Product = product;
            Clone = clone;
            Engine = engine;
            ConfigRoot = configRoot;
        }

        public string Directory { get; }
        public RevitProduct Product { get; }
        public PyRevitClone Clone { get; }
        public PyRevitEngine Engine { get; }

        /// <summary>The per-session pyRevit user data folder, or null when the session shares the user's.</summary>
        public string ConfigRoot { get; }

        public string ManifestFile => Path.Combine(Directory, PyRevitConsts.AddinFileName + ".addin");
        public string JournalFile => Path.Combine(Directory, "PyRevitLaunch.txt");
        public string ProcessIdFile => Path.Combine(Directory, "pid");
    }

    /// <summary>
    /// Starts Revit on a clone and engine of the caller's choice without touching the shared
    /// <c>pyRevit.addin</c> of the Revit year, so sessions on different clones can run side by side.
    /// </summary>
    /// <remarks>
    /// Revit reads add-in manifests from the folder of the journal it is started with, and a manifest
    /// there takes the place of a standard-folder manifest with the same add-in id; a manifest merely
    /// sitting in the working directory is ignored. The launcher therefore always starts Revit with a
    /// journal. The session finds its own clone through the environment variables set here, see
    /// <see cref="PyRevitAttachments"/>.
    /// </remarks>
    public static class PyRevitLauncher {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private const int DeleteAttempts = 15;
        private const int DeleteRetryDelayMs = 1000;
        private static readonly TimeSpan UnrecordedLaunchRetention = TimeSpan.FromDays(1);
        private static readonly Regex LanguageCodePattern = new Regex(@"\A[A-Za-z]{3}\z", RegexOptions.Compiled);

        private const string JournalTemplate = @"' pyrevit launch generated journal
' 0:< 'C {0};
Dim Jrn
Set Jrn = CrsJournalScript
";

        public static string LaunchRoot => Path.Combine(CommonUtils.GetUserTempDirectory(), "pyrevit", PyRevitConsts.LaunchDirName);

        /// <summary>
        /// Writes the manifest and journal of a new session into a fresh launch directory.
        /// </summary>
        /// <param name="isolated">Give the session its own pyRevit user data folder, seeded with a copy of the user's configuration file.</param>
        /// <exception cref="PyRevitException">The year is not installed or attachable, or the engine cannot be used as a runtime.</exception>
        public static PyRevitLaunch Prepare(PyRevitClone clone, PyRevitEngineVersion engineVersion, int revitYear, bool isolated) {
            if (!PyRevitAttachments.IsAttachableProductYear(revitYear))
                throw new PyRevitException($"Can not launch Revit {revitYear}: this pyRevit line supports Revit "
                                           + $"{RevitProductData.MinimumSupportedProductYear} or newer.");

            var product = PyRevitAttachments.SelectProductForAttach(revitYear, RevitProduct.ListInstalledProducts());
            if (product is null || !PyRevitAttachments.IsAttachable(product))
                throw new PyRevitException($"Can not launch Revit {revitYear}: it is not installed or its executable is missing.");

            var engine = clone.GetEngine(revitYear, engineVersion);
            if (!engine.Runtime)
                throw new PyRevitException($"Engine {engineVersion} can not be used as runtime.");

            PruneAbandoned();

            var directory = Path.Combine(LaunchRoot, Guid.NewGuid().ToString("N"));
            CommonUtils.EnsurePath(directory);

            string configRoot = null;
            if (isolated) {
                configRoot = Path.Combine(directory, PyRevitLabsConsts.AppdataDirName);
                CommonUtils.EnsurePath(configRoot);
                var sourceConfig = FindConfigToCopy(clone);
                if (sourceConfig != null)
                    File.Copy(sourceConfig, Path.Combine(configRoot, PyRevitLabsConsts.DefaultConfigsFileName));
            }

            var launch = new PyRevitLaunch(directory, product, clone, engine, configRoot);
            RevitAddons.CreateManifestFile(
                revitYear,
                Path.GetFileName(launch.ManifestFile),
                PyRevitConsts.AddinName,
                engine.AssemblyPath,
                PyRevitConsts.AddinId,
                PyRevitConsts.AddinClassName,
                PyRevitConsts.VendorId,
                addinPath: directory);
            File.WriteAllText(launch.JournalFile, string.Format(JournalTemplate, CommonUtils.GetISOTimeStampNow()));
            return launch;
        }

        /// <summary>
        /// Starts Revit on the prepared session and records its process id in the launch directory.
        /// </summary>
        /// <param name="language">A Revit <c>/language</c> code such as ENU, or null for Revit's own choice.</param>
        /// <exception cref="PyRevitException">The language is not a three-letter code.</exception>
        public static Process Start(PyRevitLaunch launch, string language = null) {
            var arguments = $"\"{launch.JournalFile}\"";
            if (!string.IsNullOrWhiteSpace(language)) {
                var languageCode = language.Trim();
                if (!LanguageCodePattern.IsMatch(languageCode))
                    throw new PyRevitException($"Revit language must be a three-letter code such as ENU, not \"{languageCode}\".");
                arguments += " /language " + languageCode;
            }

            var startInfo = new ProcessStartInfo(launch.Product.ExecutiveLocation) {
                Arguments = arguments,
                WorkingDirectory = launch.Directory,
                UseShellExecute = false,
            };
            startInfo.EnvironmentVariables[PyRevitConsts.LaunchManifestEnvVar] = launch.ManifestFile;
            startInfo.EnvironmentVariables[PyRevitConsts.LaunchRevitYearEnvVar] = launch.Product.ProductYear.ToString();
            if (launch.ConfigRoot != null) {
                startInfo.EnvironmentVariables[PyRevitLabsConsts.PyRevitAgentDirOverrideEnvVar] = PyRevitLabsConsts.AgentPath;
                startInfo.EnvironmentVariables[PyRevitLabsConsts.PyRevitPathOverrideEnvVar] = launch.ConfigRoot;
                startInfo.EnvironmentVariables[PyRevitLabsConsts.PyRevitIgnoreLocalConfigEnvVar] = "1";
            }

            logger.Debug("Starting Revit {0} with \"{1}\"", launch.Product.ProductYear, arguments);
            var process = Process.Start(startInfo);
            try {
                File.WriteAllText(launch.ProcessIdFile, process.Id.ToString());
            }
            catch (Exception exception) {
                logger.Warn("Can not record the process id in \"{0}\" | {1}", launch.ProcessIdFile, exception.Message);
            }
            return process;
        }

        /// <summary>
        /// The config a session of <paramref name="clone"/> would load when started normally: the
        /// clone's own config when it has one, otherwise the user's active config.
        /// </summary>
        private static string FindConfigToCopy(PyRevitClone clone) {
            var cloneConfig = File.Exists(Path.Combine(clone.ClonePath, "pyRevitfile"))
                ? PyRevitInstallScope.FindConfigIniInDirectory(clone.ClonePath)
                : null;
            if (cloneConfig != null)
                return cloneConfig;

            var userConfig = PyRevitInstallScope.GetActiveConfig(createIfMissing: false).ConfigPath;
            return File.Exists(userConfig) ? userConfig : null;
        }

        /// <summary>
        /// Removes the launch directory. Revit's worker processes can outlive Revit by a few seconds
        /// and keep their journal files open, so removal is retried before giving up; a directory
        /// that still can't be removed is left for <see cref="PruneAbandoned"/>.
        /// </summary>
        public static void Cleanup(PyRevitLaunch launch) {
            try {
                DeleteDirectory(launch.Directory, DeleteAttempts);
            }
            catch (Exception exception) {
                logger.Warn("Can not remove launch directory \"{0}\" | {1}", launch.Directory, exception.Message);
            }
        }

        private static void DeleteDirectory(string directory, int attempts) {
            for (var attempt = 1; ; attempt++) {
                try {
                    Directory.Delete(directory, recursive: true);
                    return;
                }
                catch (Exception exception) when ((exception is IOException || exception is UnauthorizedAccessException) && attempt < attempts) {
                    Thread.Sleep(DeleteRetryDelayMs);
                }
            }
        }

        /// <summary>
        /// Removes launch directories whose Revit is no longer running, left behind when the
        /// launcher itself was killed before it could clean up.
        /// </summary>
        /// <remarks>
        /// A directory without a recorded process id may still belong to a running Revit whose id
        /// could not be written, so it is only removed after <see cref="UnrecordedLaunchRetention"/>.
        /// </remarks>
        public static void PruneAbandoned() {
            if (!Directory.Exists(LaunchRoot))
                return;

            foreach (var directory in Directory.GetDirectories(LaunchRoot)) {
                try {
                    var processIdFile = Path.Combine(directory, "pid");
                    var abandoned = File.Exists(processIdFile)
                        ? !IsRevitRunning(processIdFile)
                        : DateTime.UtcNow - Directory.GetCreationTimeUtc(directory) > UnrecordedLaunchRetention;
                    if (abandoned)
                        DeleteDirectory(directory, attempts: 1);
                }
                catch (Exception exception) {
                    logger.Debug("Can not prune launch directory \"{0}\" | {1}", directory, exception.Message);
                }
            }
        }

        private static bool IsRevitRunning(string processIdFile) {
            if (!int.TryParse(File.ReadAllText(processIdFile).Trim(), out var processId))
                return false;
            try {
                using (var process = Process.GetProcessById(processId))
                    return !process.HasExited && process.ProcessName.Equals("Revit", StringComparison.OrdinalIgnoreCase);
            }
            catch (ArgumentException) {
                return false;
            }
        }
    }
}
