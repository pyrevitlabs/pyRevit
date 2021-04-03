using System;
using System.IO;
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
            AddInId = doc.DocumentElement.SelectSingleNode("/RevitAddIns/AddIn/AddInId").InnerText;
            FullClassName = doc.DocumentElement.SelectSingleNode("/RevitAddIns/AddIn/FullClassName").InnerText;
            VendorId = doc.DocumentElement.SelectSingleNode("/RevitAddIns/AddIn/VendorId").InnerText;
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
            var rootFolder =
                allUsers ? System.Environment.SpecialFolder.CommonApplicationData : System.Environment.SpecialFolder.ApplicationData;
            return Path.Combine(System.Environment.GetFolderPath(rootFolder),
                                "Autodesk", "Revit", "Addins", revitYear.ToString());
        }

        public static string GetRevitAddonsFilePath(int revitYear, string addinFileName, bool allusers = false) {
            if (UserEnv.IsRunAsElevated())
                allusers = true;
            
            var rootFolder =
                allusers ? System.Environment.SpecialFolder.CommonApplicationData : System.Environment.SpecialFolder.ApplicationData;
            return Path.Combine(GetRevitAddonsFolder(revitYear, allUsers: allusers), addinFileName + ".addin");
        }

        public static void CreateManifestFile(int revitYear, string addinFileName,
                                              string addinName, string assemblyPath,
                                              string addinId, string addinClassName, string vendorId,
                                              bool allusers = false, string addinPath = null) {
            string manifest = string.Format(ManifestTemplate, addinName, assemblyPath, addinId, addinClassName, vendorId);
            logger.Debug("Creating addin manifest...\n{0}", manifest);
            string addinFile;
            if (addinPath is null)
                addinFile = GetRevitAddonsFilePath(revitYear, addinFileName, allusers: allusers);
            else
                addinFile = Path.Combine(addinPath, addinFileName);
            logger.Debug("Creating manifest file \"{0}\"", addinFile);
            CommonUtils.EnsureFile(addinFile);
            var f = File.CreateText(addinFile);
            f.Write(manifest);
            f.Close();
        }

        public static RevitAddonManifest GetAttachedManifest(string addinName, int revitYear, bool allUsers) {
            logger.Debug(
                "Querying clone attached to Revit {0} {1}",
                revitYear,
                allUsers ? "(All Users)" : "(Current User)"
                );

            return GetManifest(revitYear, addinName, allUsers: allUsers);
        }

        public static void RemoveManifestFile(int revitYear, string addinName, bool currentAndAllUsers = true) {
            RevitAddonManifest revitManifest = GetManifest(revitYear, addinName, allUsers: false);

            if (revitManifest != null) {
                logger.Debug("Removing manifest file \"{0}\"", revitManifest.FilePath);
                File.Delete(revitManifest.FilePath);
            }
            if (currentAndAllUsers) {
                revitManifest = GetManifest(revitYear, addinName, allUsers: true);
                if (revitManifest != null) {
                    logger.Debug("Removing all users manifest file \"{0}\"", revitManifest.FilePath);
                    File.Delete(revitManifest.FilePath);
                }
            }
        }

        public static RevitAddonManifest GetManifest(int revitYear, string addinName, bool allUsers) {
            string addinPath = GetRevitAddonsFolder(revitYear, allUsers: allUsers);
            if (CommonUtils.VerifyPath(addinPath)) {
                foreach (string file in Directory.GetFiles(addinPath)) {
                    if (file.ToLower().EndsWith(".addin")) {
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

                return null;
            }
            else {
                logger.Debug("Addons path \"{0}\" does not exist", addinPath);
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
