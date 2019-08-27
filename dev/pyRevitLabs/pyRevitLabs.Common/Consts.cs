using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace pyRevitLabs.Common {
    public class PyRevitLabsConsts {
        // product
        public const string ProductName = "pyRevit";

        public const string DefaultGitDirName = ".git";
        public const string DefaultRemoteName = "origin";
        public const string OriginalRepoDefaultBranch = "master";

        public const string TragetBranch = OriginalRepoDefaultBranch;
        //public const string TragetBranch = @"develop";

        // consts for the official pyRevit repo
        public const string OriginalRepoName = ProductName;
        public static string OriginalRepoId = string.Format(@"eirannejad/{0}", ProductName);
        public static string OriginalRepoPath = string.Format(@"https://github.com/{0}{1}", OriginalRepoId, DefaultGitDirName);

        // consts for recording pyrevit.exe config in the pyRevit configuration file
        public const string AppdataDirName = ProductName;
        public const string AppdataCacheDirName = "Cache";
        public const string AppdataLogsDirName = "Logs";

        // pyRevit %appdata% path
        // @reviewed
        public static string PyRevitPath => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), AppdataDirName);

        // pyRevit %programdata% path
        // @reviewed
        public static string PyRevitProgramDataPath => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), AppdataDirName);

        // pyrevit general cache folder 
        public static string CacheDirectory => Path.Combine(PyRevitPath, AppdataCacheDirName);

        // pyrevit logs folder 
        public static string LogsDirectory => Path.Combine(PyRevitPath, AppdataLogsDirName);

    }
}
