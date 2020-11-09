using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Xml;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.NLog;

namespace pyRevitLabs.TargetApps.Revit {
    public enum RevitModelFileOpenWorksetConfig {
        All = 0,
        Unknown = 1,
        Editable = 2,
        LastViewed = 3,
        Specify = 4
    }

    public class RevitModelFile {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public RevitModelFile(string filePath) {
            FilePath = filePath.NormalizeAsPath();

            // extract basic info and prepare string
            // throws exception if stream doesn't exist
            var rawBasicInfoData = CommonUtils.GetStructuredStorageStream(FilePath, "BasicFileInfo");

            // dump stream data
            logger.Debug("Stream Dump in HEX: \"{0}\"", BitConverter.ToString(rawBasicInfoData));
            logger.Debug("Stream Dump in ASCII: \"{0}\"", Encoding.ASCII.GetString(rawBasicInfoData));

            if (rawBasicInfoData != null) {
                int index = 0;
                var boundIndices = new List<int>();
                // find the utf-16 string between two ascii \r\n
                while (index < rawBasicInfoData.Length - 1) {
                    if (rawBasicInfoData[index] == 0x0D && rawBasicInfoData[index + 1] == 0x0A)
                        boundIndices.Add(index);
                    index++;
                }
                //cleanup array
                int lastBoundIndex = boundIndices.Count - 1;
                var utf16Stream =
                    rawBasicInfoData.Skip(boundIndices[lastBoundIndex - 1] + 2)
                                    .Take(boundIndices[lastBoundIndex] - boundIndices[lastBoundIndex - 1] - 2)
                                    .ToArray();
                // fix ASCII value reprs
                // replace False with UTF-16 LE False
                utf16Stream = CommonUtils.ReplaceBytes(
                    utf16Stream,
                    //           F     a     l     s     e     null
                    new byte[] { 0x46, 0x61, 0x6C, 0x73, 0x65, 0x00 },
                    //           F           a           l           s           e
                    new byte[] { 0x46, 0x00, 0x61, 0x00, 0x6C, 0x00, 0x73, 0x00, 0x65, 0x00 }
                    );

                // replace True with UTF-16 LE True
                utf16Stream = CommonUtils.ReplaceBytes(
                    utf16Stream,
                    //           T     r     u     e     null
                    new byte[] { 0x54, 0x72, 0x75, 0x65, 0x00 },
                    //           T           r           u           e
                    new byte[] { 0x54, 0x00, 0x72, 0x00, 0x75, 0x00, 0x65, 0x00 }
                    );

                // take the string between the last two ascii \r\n
                var baseInfoString = Encoding.GetEncoding("UTF-16").GetString(utf16Stream);

                // dump the extracted string for debugging
                logger.Debug("Extracted BasicFileInfo Text: \"{0}\"", baseInfoString);

                ProcessBasicFileInfo(
                    baseInfoString.Split(new string[] { "\r\n" }, StringSplitOptions.RemoveEmptyEntries)
                    );
            }
            else
                throw new PyRevitException(string.Format("Target is not a valid Revit model \"{0}\"", filePath));

            // extract ProjectInformation (Revit Project Files)
            // ProjectInformation is a PK Zip stream
            var rawProjectInformationData = CommonUtils.GetStructuredStorageStream(FilePath, "ProjectInformation");
            if (rawProjectInformationData != null) {
                Stream zipData = new MemoryStream(rawProjectInformationData);
                var zipFile = new ZipArchive(zipData);
                foreach (var entry in zipFile.Entries) {
                    if (entry.FullName.ToLower().EndsWith(".project.xml")) {
                        logger.Debug("Reading Project Info from: \"{0}\"", entry.FullName);
                        using (Stream projectInfoXamlData = entry.Open()) {
                            var projectInfoXmlData = new StreamReader(projectInfoXamlData).ReadToEnd();
                            ProcessProjectInfo(projectInfoXmlData);
                        }
                    }
                }
            }
            else {
                ProjectInfoProperties = new Dictionary<string, string>();
            }

            // extract partatom (Revit Family Files) and prepare string
            // PartAtom is a Xml stream
            // https://ein.sh/pyRevit/pyrevit/updates/2019/01/19/basicfileinfo.html
            var rawPartAtomData = CommonUtils.GetStructuredStorageStream(FilePath, "PartAtom");
            if (rawPartAtomData != null) {
                IsFamily = true;
                ProcessPartAtom(Encoding.ASCII.GetString(rawPartAtomData));
            }
            else {
                CategoryName = "";
                HostCategoryName = "";
            }
        }

        public static bool IsRevitFile(string filePath) {
            try {
                var model = new RevitModelFile(filePath);
                return true;
            }
            catch { return false; }
        }

        private Regex buildFieldRegex(string fieldName, string captureId) {
            return new Regex(string.Format(@"{0}(?<{1}>.*$)", fieldName, captureId));
        }

        private void ProcessBasicFileInfo(IEnumerable<string> basicInfoDataLines) {
            foreach (string line in basicInfoDataLines) {
                logger.Debug("Parsing info from BasicFileInfo: \"{0}\"", line);
                // Worksharing: Not enabled
                var match = buildFieldRegex("Worksharing: ", "workshared").Match(line);
                if (match.Success) {
                    var workshared = match.Groups["workshared"].Value;
                    logger.Debug("IsWorkshared: {0}", workshared);
                    if (!workshared.Contains("Not"))
                        IsWorkshared = true;
                }

                // Username: 

                // Central Model Path: 
                match = buildFieldRegex("Central Model Path: ", "centralpath").Match(line);
                if (match.Success) {
                    var path = match.Groups["centralpath"].Value;
                    logger.Debug("Central Model Path: {0}", path);
                    CentralModelPath = path;
                }

                // Format: 2019

                // Build: 20180806_1515(x64)
                match = buildFieldRegex("Build: ", "build").Match(line);
                if (match.Success) {
                    var revitProduct = RevitProduct.LookupRevitProduct(line);
                    if (revitProduct != null)
                        RevitProduct = revitProduct;
                }

                // Last Save Path: C:\Users\eirannejad\Desktop\Project1.rvt
                match = buildFieldRegex("Last Save Path: ", "lastpath").Match(line);
                if (match.Success) {
                    var path = match.Groups["lastpath"].Value;
                    logger.Debug("Last Saved Path: {0}", path);
                    LastSavedPath = path;
                }

                // Open Workset Default: 3
                match = buildFieldRegex("Open Workset Default: ", "openws").Match(line);
                if (match.Success) {
                    var owconfig = match.Groups["openws"].Value;
                    logger.Debug("Open Workset Default: {0}", owconfig);
                    OpenWorksetConfig = (RevitModelFileOpenWorksetConfig)Enum.ToObject(
                        typeof(RevitModelFileOpenWorksetConfig), int.Parse(owconfig)
                        );
                }

                // Project Spark File: 0

                // Central Model Identity: 00000000-0000-0000-0000-000000000000

                // Locale when saved: ENU

                // All Local Changes Saved To Central: 0

                // Central model's version number corresponding to the last reload latest: 4

                // Central model's episode GUID corresponding to the last reload latest: 2ecc6fa1-2960-4473-9fd9-0abce22022fc
                if (line.Contains("Central model's episode GUID corresponding to the last reload latest: ")) {
                    var guid = line.ExtractGuid();
                    logger.Debug("Extracted Last Reload Latest GUID: {0}", guid);
                    LastReloadLatestUniqueId = guid;
                }

                // Unique Document GUID: 2ecc6fa1-2960-4473-9fd9-0abce22022fc
                if (line.Contains("Unique Document GUID: ")) {
                    var guid = line.ExtractGuid();
                    logger.Debug("Extracted GUID: {0}", guid);
                    UniqueId = guid;
                }

                // Unique Document Increments: 4
                match = buildFieldRegex("Unique Document Increments: ", "increment").Match(line);
                if (match.Success) {
                    var docincrement = match.Groups["increment"].Value;
                    logger.Debug("Unique Document Increments: {0}", docincrement);
                    DocumentIncrement = int.Parse(docincrement);
                }

                // Model Identity: 00000000-0000-0000-0000-000000000000

                // IsSingleUserCloudModel: 慆獬e

                // Author: Autodesk Revit
            }
        }

        private void ProcessPartAtom(string rawPartAtom) {
            logger.Debug("Parsing PartAtom Data: \"{0}\"", rawPartAtom);
            var doc = new XmlDocument();
            try {
                doc.LoadXml(rawPartAtom);
                XmlNamespaceManager nsmgr = new XmlNamespaceManager(doc.NameTable);
                nsmgr.AddNamespace("rfa", @"http://www.w3.org/2005/Atom");
                nsmgr.AddNamespace("A", @"urn:schemas-autodesk-com:partatom");

                // extract family category
                var catElements = doc.SelectNodes("//rfa:entry/rfa:category/rfa:term", nsmgr);
                CategoryName = catElements.Count > 0 ? catElements[catElements.Count - 1].InnerText : "";

                // extract host
                var hostElement = doc.SelectSingleNode("//rfa:entry/A:features/A:feature/A:group/rfa:Host", nsmgr);
                HostCategoryName = hostElement != null ? hostElement.InnerText : "";
            }
            catch (Exception ex) {
                logger.Debug("Error parsing PartAtom XML. | {0}", ex.Message);
            }
        }

        private void ProcessProjectInfo(string rawProjectInfoData) {
            logger.Debug("Parsing ProjctInformation Data: \"{0}\"", rawProjectInfoData);
            var doc = new XmlDocument();
            try {
                doc.LoadXml(rawProjectInfoData);
                XmlNamespaceManager nsmgr = new XmlNamespaceManager(doc.NameTable);
                nsmgr.AddNamespace("rfa", @"http://www.w3.org/2005/Atom");
                nsmgr.AddNamespace("A", @"urn:schemas-autodesk-com:partatom");

                // extract project parameters
                var projectInfoDict = new Dictionary<string, string>();
                XmlNodeList propertyGroups = doc.SelectNodes("//rfa:entry/A:features/A:feature/A:group", nsmgr);
                foreach (XmlElement properyGroup in propertyGroups) {
                    foreach (XmlElement child in properyGroup.ChildNodes) {
                        if (child.HasAttribute("displayName")) {
                            string propertyName = child.GetAttribute("displayName");
                            string propertyValue = child.InnerText;
                            logger.Debug("\"{0}\" = \"{1}\"", propertyName, propertyValue);
                            projectInfoDict.Add(propertyName, propertyValue);
                        }
                    }
                }

                // set the created info dict
                ProjectInfoProperties = projectInfoDict;
            }
            catch (Exception ex) {
                logger.Debug("Error parsing PartAtom XML. | {0}", ex.Message);
            }
        }

        public string FilePath { get; private set; }

        public bool IsFamily { get; private set; }

        public bool IsWorkshared { get; private set; } = false;

        public string LastSavedPath { get; private set; } = null;

        public string CentralModelPath { get; private set; } = null;

        public RevitModelFileOpenWorksetConfig OpenWorksetConfig { get; private set; } = 0;

        public int DocumentIncrement { get; private set; } = 0;

        public Guid UniqueId { get; private set; } = new Guid();

        public Guid LastReloadLatestUniqueId { get; private set; } = new Guid();

        public RevitProduct RevitProduct { get; private set; } = null;

        public Dictionary<string, string> ProjectInfoProperties { get; private set; }

        public string CategoryName { get; private set; }

        public string HostCategoryName { get; private set; }
    }
}