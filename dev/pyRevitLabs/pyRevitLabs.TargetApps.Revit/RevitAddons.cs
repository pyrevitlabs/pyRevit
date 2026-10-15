using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Xml;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.NLog;

namespace pyRevitLabs.TargetApps.Revit {
    public class RevitAddonManifest {
        public RevitAddonManifest(string manifestFile) {
            FilePath = manifestFile;

            var doc = new XmlDocument();
            doc.Load(manifestFile);
            Name = doc.DocumentElement.SelectSingleNode("/RevitAddIns/AddIn/Name").InnerText;
            Assembly = doc.DocumentElement.SelectSingleNode("/RevitAddIns/AddIn/Assembly").InnerText.NormalizeAsPath();
            FullClassName = doc.DocumentElement.SelectSingleNode("/RevitAddIns/AddIn/FullClassName").InnerText;
            VendorId = doc.DocumentElement.SelectSingleNode("/RevitAddIns/AddIn/VendorId").InnerText;

            var addInIdNode = doc.DocumentElement.SelectSingleNode("/RevitAddIns/AddIn/AddInId");
            if (addInIdNode != null) {
                AddInId = addInIdNode.InnerText;
            }
            else {
                AddInId = doc.DocumentElement.SelectSingleNode("/RevitAddIns/AddIn/ClientId").InnerText;
            }
        }

        public string FilePath { get; set; }

        public string Name { get; set; }
        public string Assembly { get; set; }
        public string AddInId { get; set; }
        public string FullClassName { get; set; }
        public string VendorId { get; set; }
    }

    public static class RevitAddons {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        // TODO: generate this using xml module so other metadata could be added inside <AddIn> (tested)
        // <pyRevitClonePath>{5}</pyRevitClonePath>
        // <pyRevitEngineVersion>{6}</pyRevitEngineVersion>
        private const string ManifestTemplate = @"<?xml version=""1.0"" encoding=""utf-8"" standalone=""no""?>
<RevitAddIns>
    <AddIn Type = ""Application"">
        <Name>{0}</Name>
        <Assembly>{1}</Assembly>
        <AddInId>{2}</AddInId>
        <FullClassName>{3}</FullClassName>
        <VendorId>{4}</VendorId>
    </AddIn>
</RevitAddIns>
";
        public static string GetRevitAddonsFolder(int revitYear, bool allUsers = false) {
            if (allUsers) {
                if (revitYear >= 2027) {
                    // Revit 2027+ moved the all-users add-in manifest location.
                    // The legacy ProgramData path is ignored entirely.
                    // The version-specific install dir (e.g. "Revit 2027\AddIns\")
                    // is reserved for signed internal add-ins only.
                    // Third-party unsigned add-ins must use:
                    //   C:\Program Files\Autodesk\Revit\Addins\<year>
                    return Path.Combine(
                        Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
                        "Autodesk", "Revit", "Addins", revitYear.ToString()
                    );
                }
                else {
                    // Revit ≤2026: all-users manifests go in ProgramData
                    return Path.Combine(
                        Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData),
                        "Autodesk", "Revit", "Addins", revitYear.ToString()
                    );
                }
            }
            else {
                // Per-user path is unchanged for all Revit versions
                return Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                    "Autodesk", "Revit", "Addins", revitYear.ToString()
                );
            }
        }

        public static string GetRevitAddonsFilePath(int revitYear, string addinFileName, bool allusers = false) {
            return Path.Combine(GetRevitAddonsFolder(revitYear, allUsers: allusers), addinFileName + ".addin");
        }

        /// <summary>
        ///     Creates a manifest after staging its contents in the destination directory.
        /// </summary>
        /// <param name="addinFileName">The manifest filename, without the extension unless <paramref name="addinPath"/> is specified.</param>
        /// <param name="addinPath">The explicit destination directory, or <see langword="null"/> for the standard directory.</param>
        /// <param name="beforeReplace">An optional action removing existing attachments after staging and before installation.</param>
        /// <remarks>
        ///     Staging failures leave existing attachments unchanged; removal precedes installation even for attachments referencing expired clones.
        /// </remarks>
        public static void CreateManifestFile(int revitYear, string addinFileName,
                                              string addinName, string assemblyPath,
                                              string addinId, string addinClassName, string vendorId,
                                              bool allusers = false, string addinPath = null,
                                              Action beforeReplace = null) {
            string manifest = string.Format(ManifestTemplate, addinName, assemblyPath, addinId, addinClassName, vendorId);
            logger.Debug("Creating addin manifest...\n{0}", manifest);
            string addinFile;
            if (addinPath is null)
                addinFile = GetRevitAddonsFilePath(revitYear, addinFileName, allusers: allusers);
            else
                addinFile = Path.Combine(addinPath, addinFileName);
            logger.Debug("Creating manifest file \"{0}\"", addinFile);
            Directory.CreateDirectory(Path.GetDirectoryName(addinFile));
            var temporaryFile = Path.Combine(Path.GetDirectoryName(addinFile), "pyRevit-manifest-" + Guid.NewGuid() + ".tmp");
            try {
                File.WriteAllText(temporaryFile, manifest);
                beforeReplace?.Invoke();
                if (File.Exists(addinFile))
                    File.Replace(temporaryFile, addinFile, null);
                else
                    File.Move(temporaryFile, addinFile);
            }
            finally {
                try {
                    if (File.Exists(temporaryFile))
                        File.Delete(temporaryFile);
                }
                catch (Exception exception) {
                    logger.Error("Error cleaning up staged manifest \"{0}\" | {1}", temporaryFile, exception.Message);
                }
            }
        }

        public static RevitAddonManifest GetAttachedManifest(string addinName, int revitYear, bool allUsers) {
            logger.Debug(
                "Querying clone attached to Revit {0} {1}",
                revitYear,
                allUsers ? "(All Users)" : "(Current User)"
                );

            return GetManifest(revitYear, addinName, allUsers: allUsers);
        }

        /// <summary>
        ///     Removes matching manifests from each requested scope, attempting every scope even when a deletion fails.
        /// </summary>
        /// <exception cref="PyRevitException">One or more manifests could not be removed; the message identifies each failed path.</exception>
        public static void RemoveManifestFile(int revitYear, string addinName, bool currentAndAllUsers = true) {
            var failures = new List<string>();
            foreach (var allUsers in currentAndAllUsers ? new[] { false, true } : new[] { false }) {
                var manifestPath = GetRevitAddonsFolder(revitYear, allUsers);
                try {
                    var revitManifest = GetManifest(revitYear, addinName, allUsers);
                    if (revitManifest is null)
                        continue;
                    manifestPath = revitManifest.FilePath;
                    logger.Debug("Removing manifest file \"{0}\"", manifestPath);
                    File.Delete(manifestPath);
                }
                catch (Exception exception) {
                    failures.Add(string.Format("\"{0}\": {1}", manifestPath, exception.Message));
                }
            }
            if (failures.Count > 0)
                throw new PyRevitException("Could not remove all manifests:" +
                                          Environment.NewLine + string.Join(Environment.NewLine, failures));
        }

        public static RevitAddonManifest GetManifest(int revitYear, string addinName, bool allUsers) {
            // Helper method to search for manifest in a given path
            RevitAddonManifest SearchManifestInPath(string searchPath) {
                if (CommonUtils.VerifyPath(searchPath)) {
                    foreach (string file in Directory.GetFiles(searchPath)
                                                     .Where(f => f.EndsWith(".addin", StringComparison.OrdinalIgnoreCase))) {
                        try {
                            logger.Debug(string.Format("Reading Revit \"{0}\" manifest file \"{1}\"",
                                                       revitYear, file));
                            var revitManifest = new RevitAddonManifest(file);
                            if (revitManifest.Name.ToLower() == addinName.ToLower())
                                return revitManifest;
                        }
                        catch (Exception ex) {
                            logger.Debug(string.Format("Not pyRevit \"{0}\" manifest file \"{1}\" | {2}",
                                    revitYear,
                                    file,
                                    ex.Message)
                                );
                        }
                    }
                }
                else {
                    logger.Debug("Addons path \"{0}\" does not exist", searchPath);
                }
                return null;
            }

            // First, search in the new location (if applicable)
            string addinPath = GetRevitAddonsFolder(revitYear, allUsers: allUsers);
            var manifest = SearchManifestInPath(addinPath);
            if (manifest != null)
                return manifest;

            // For Revit 2027+ all-users installations, also check the old location for migration scenarios
            if (allUsers && revitYear >= 2027) {
                var oldPath = Path.Combine(
                    System.Environment.GetFolderPath(System.Environment.SpecialFolder.CommonApplicationData),
                    "Autodesk", "Revit", "Addins", revitYear.ToString());
                logger.Debug("Also checking old all-users location for Revit {0}: {1}", revitYear, oldPath);
                manifest = SearchManifestInPath(oldPath);
                if (manifest != null)
                    return manifest;
            }

            return null;
        }

        public static string PrepareAddonPath(int revitYear, bool allUsers) {
            var addonPath = GetRevitAddonsFolder(revitYear, allUsers: allUsers);
            CommonUtils.EnsurePath(addonPath);
            logger.Debug("Prepared: {0}", addonPath);
            return addonPath;
        }
    }
}
