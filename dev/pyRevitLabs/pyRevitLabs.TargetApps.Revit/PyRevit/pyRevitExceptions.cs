using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

using pyRevitLabs.Common;

namespace pyRevitLabs.TargetApps.Revit {
    public class pyRevitConfigValueNotSet : pyRevitException {
        public pyRevitConfigValueNotSet(string sectionName, string keyName) {
            ConfigSection = sectionName;
            ConfigKey = keyName;
        }

        public string ConfigSection { get; set; }
        public string ConfigKey { get; set; }

        public override string Message {
            get {
                return String.Format("Config value not set \"{0}:{1}\"", ConfigSection, ConfigKey);
            }
        }
    }

    public class pyRevitInvalidpyRevitCloneException : pyRevitInvalidGitCloneException {
        public pyRevitInvalidpyRevitCloneException() { }

        public pyRevitInvalidpyRevitCloneException(string invalidClonePath) : base(invalidClonePath) { }

        public override string Message {
            get {
                return string.Format("Path \"{0}\" is not a valid git pyRevit clone.", Path);
            }
        }
    }
}
