using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using System.IO;


namespace pyRevitLabs.TargetApps.Revit {
    public class RevitServerConfig {
        public string Version;
        public string Name;

        public RevitServerConfig(string version, string name) {
            Version = version;
            Name = name;
        }

        public override string ToString() {
            return String.Format("{0} / {1}", Version, Name);
        }
    }

    public static class RevitServerConfigurations {
        public static List<RevitServerConfig> GetAvailableServers() {
            // prepare output
            var rsConfigList = new List<RevitServerConfig>();

            // get %programdata%/Autodesk path
            string programData = Environment.GetEnvironmentVariable("PROGRAMDATA");
            string fullPath = Path.Combine(programData, "Autodesk");

            // find revit server config folders
            string serverConfigRegexPat = @"Revit Server \d\d\d\d";
            Regex rsConfigFinder = new Regex(serverConfigRegexPat, RegexOptions.IgnoreCase);

            if (fullPath != null) {
                var directories = Directory.GetDirectories(fullPath);
                foreach (string dir in directories) {
                    // read the config file and get a list of configured server
                    // e.g. RSN.ini contents is just a list of revit server names each on a line
                    //      SERVER01
                    //      SERVER02
                    if (rsConfigFinder.Match(dir).Success) {
                        // find revit server version from folder name
                        string rsVersionRegexPat = @"\d\d\d\d";
                        Regex rsVersionFinder = new Regex(rsVersionRegexPat, RegexOptions.IgnoreCase);
                        var rsVersion = rsVersionFinder.Match(dir).Groups[0].Value;

                        string rsConfigFile = Path.Combine(programData, dir, "Config", "RSN.ini");
                        var rsConfiguredList = File.ReadAllLines(rsConfigFile);
                        foreach (string rsConfigured in rsConfiguredList)
                            rsConfigList.Add(new RevitServerConfig(rsVersion, rsConfigured));
                    }
                }
            }

            return rsConfigList;
        }

        public static Dictionary<string, List<RevitServerConfig>> GetAvailableServersByVersion() {
            var serversDict = new Dictionary<string, List<RevitServerConfig>>();

            foreach (RevitServerConfig rsConfig in GetAvailableServers()) {
                if (serversDict.ContainsKey(rsConfig.Version)) {
                    serversDict[rsConfig.Version].Add(rsConfig);
                }
                else {
                    serversDict[rsConfig.Version] = new List<RevitServerConfig>();
                    serversDict[rsConfig.Version].Add(rsConfig);
                }
            }

            return serversDict;
        }

        public static Dictionary<string, List<RevitServerConfig>> GetAvailableServersByName() {
            var serversDict = new Dictionary<string, List<RevitServerConfig>>();

            foreach (RevitServerConfig rsConfig in GetAvailableServers()) {
                if (serversDict.ContainsKey(rsConfig.Name)) {
                    serversDict[rsConfig.Name].Add(rsConfig);
                }
                else {
                    serversDict[rsConfig.Name] = new List<RevitServerConfig>();
                    serversDict[rsConfig.Name].Add(rsConfig);
                }
            }

            return serversDict;
        }
    }
}