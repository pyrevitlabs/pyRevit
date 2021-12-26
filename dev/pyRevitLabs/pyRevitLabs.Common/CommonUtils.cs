using OpenMcdf;
using System;
using System.Text;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Text.RegularExpressions;

using LibGit2Sharp;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.NLog;
using System.Linq;
using System.Threading;

namespace pyRevitLabs.Common {
    public static class CommonUtils {
        // private static object ProgressLock = new object();
        // private static int lastReport;

        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        [DllImport("ole32.dll")]
        private static extern int StgIsStorageFile([MarshalAs(UnmanagedType.LPWStr)] string pwcsName);

        public static bool VerifyFile(string filePath) {
            if (filePath != null && filePath != string.Empty)
                return System.IO.File.Exists(filePath);
            return false;
        }

        // https://stackoverflow.com/a/937558/2350244
        public static bool IsFileLocked(FileInfo file) {
            try {
                using (FileStream stream = file.Open(FileMode.Open, FileAccess.Read, FileShare.None)) {
                    stream.Close();
                }
            }
            catch (IOException) {
                //the file is unavailable because it is:
                //still being written to
                //or being processed by another thread
                //or does not exist (has already been processed)
                return true;
            }

            //file is not locked
            return false;
        }

        public static void VerifyFileAccessible(string filePath) {
            // make sure file is accessible,
            // try multiple times and wait a little in between
            // fail after trying
            var finfo = new FileInfo(filePath);

            uint tries = 3;
            do {
                if (IsFileLocked(finfo)) {
                    Thread.Sleep(200);
                    tries--;
                }
                else
                    return;
            } while (tries > 0);

            throw new PyRevitException("File is not accessible");
        }

        public static bool VerifyPath(string path) {
            if (path != null && path != string.Empty)
                return Directory.Exists(path);
            return false;
        }

        public static bool VerifyPythonScript(string path) {
            return VerifyFile(path) && path.ToLower().EndsWith(".py");
        }

        // helper for deleting directories recursively
        // @handled @logs
        public static void DeleteDirectory(string targetDir, bool verbose = true) {
            if (CommonUtils.VerifyPath(targetDir)) {
                if (verbose)
                    logger.Debug("Recursive deleting directory \"{0}\"", targetDir);
                string[] files = Directory.GetFiles(targetDir);
                string[] dirs = Directory.GetDirectories(targetDir);

                try {
                    foreach (string file in files) {
                        System.IO.File.SetAttributes(file, FileAttributes.Normal);
                        System.IO.File.Delete(file);
                    }

                    foreach (string dir in dirs) {
                        DeleteDirectory(dir, verbose: false);
                    }

                    Directory.Delete(targetDir, false);
                }
                catch (Exception ex) {
                    throw new PyRevitException(string.Format("Error recursive deleting directory \"{0}\" | {1}",
                                                             targetDir, ex.Message));
                }
            }
        }

        // helper for copying a directory recursively
        // @handled @logs
        public static void CopyDirectory(string sourceDir, string destDir) {
            EnsurePath(destDir);
            logger.Debug("Copying \"{0}\" to \"{1}\"", sourceDir, destDir);
            try {
                // create all of the directories
                foreach (string dirPath in Directory.GetDirectories(sourceDir, "*",
                    SearchOption.AllDirectories))
                    Directory.CreateDirectory(dirPath.Replace(sourceDir, destDir));

                // copy all the files & Replaces any files with the same name
                foreach (string newPath in Directory.GetFiles(sourceDir, "*.*",
                    SearchOption.AllDirectories))
                    System.IO.File.Copy(newPath, newPath.Replace(sourceDir, destDir), true);
            }
            catch (Exception ex) {
                throw new PyRevitException(
                    string.Format("Error copying \"{0}\" to \"{1}\" | {2}", sourceDir, destDir, ex.Message)
                    );
            }
        }

        public static void EnsurePath(string path) {
            Directory.CreateDirectory(path);
        }

        public static void EnsureFile(string filePath) {
            EnsurePath(Path.GetDirectoryName(filePath));
            if (!System.IO.File.Exists(filePath)) {
                var file = System.IO.File.CreateText(filePath);
                file.Close();
            }
        }

        public static string EnsureFileExtension(string filepath, string extension) => Path.ChangeExtension(filepath, extension);

        public static bool EnsureFileNameIsUnique(string targetDir, string fileName) {
            foreach (var subdir in Directory.GetDirectories(targetDir))
                if (Path.GetFileNameWithoutExtension(subdir).ToLower() == fileName.ToLower())
                    return false;

            foreach (var subFile in Directory.GetFiles(targetDir))
                if (Path.GetFileNameWithoutExtension(subFile).ToLower() == fileName.ToLower())
                    return false;

            return true;
        }

        public static string GetFileSignature(string filepath) {
            return Math.Abs(System.IO.File.GetLastWriteTimeUtc(filepath).GetHashCode()).ToString();
        }

        public static WebClient GetWebClient() {
            if (CheckInternetConnection()) {
                ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
                return new WebClient();
            }
            else
                throw new pyRevitNoInternetConnectionException();
        }

        public static HttpWebRequest GetHttpWebRequest(string url) {
            logger.Debug("Building HTTP request for: \"{0}\"", url);
            if (CheckInternetConnection()) {
                ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
                HttpWebRequest request = (HttpWebRequest)WebRequest.Create(url);
                request.UserAgent = "pyrevit-cli";
                return request;
            }
            else
                throw new pyRevitNoInternetConnectionException();
        }

        public static string DownloadFile(string url, string destPath, string progressToken = null) {
            try {
                using (var client = GetWebClient()) {
                    client.Headers.Add("User-Agent", "pyrevit-cli");
                    //if (GlobalConfigs.ReportProgress) {
                    //    logger.Debug("Downloading (async) \"{0}\"", url);

                    //    client.DownloadProgressChanged += Client_DownloadProgressChanged;

                    //    lastReport = 0;
                    //    client.DownloadFileAsync(new Uri(url), destPath, progressToken);

                    //    // wait until download is complete
                    //    while (client.IsBusy) ;
                    //}
                    //else {
                    logger.Debug("Downloading \"{0}\"", url);
                    client.DownloadFile(url, destPath);
                    //}
                }
            }
            catch (Exception dlEx) {
                logger.Debug("Error downloading file. | {0}", dlEx.Message);
                throw dlEx;
            }

            return destPath;
        }

        //private static void Client_DownloadProgressChanged(object sender, DownloadProgressChangedEventArgs e) {
        //    lock (ProgressLock) {
        //        if (e.ProgressPercentage > lastReport) {
        //            lastReport = e.ProgressPercentage;

        //            // build progress bar and print
        //            // =====>
        //            var pbar = string.Concat(Enumerable.Repeat("=", (int)((lastReport / 100.0) * 50.0))) + ">";
        //            // 4.57 KB/27.56 KB
        //            var sizePbar = string.Format("{0}/{1}", e.BytesReceived.CleanupSize(), e.TotalBytesToReceive.CleanupSize());

        //            // Downloading [==========================================>       ] 23.26 KB/27.56 KB
        //            string message = "";
        //            if (lastReport == 100) {
        //                if (e.UserState != null)
        //                    message = string.Format("\r{1}: Download complete ({0})", e.TotalBytesToReceive.CleanupSize(), (string)e.UserState);
        //                else
        //                    message = string.Format("\rDownload complete ({0})", e.TotalBytesToReceive.CleanupSize());
        //                Console.WriteLine("{0,-120}", message);
        //            }
        //            else {
        //                if (e.UserState != null)
        //                    message = string.Format("\r{2}: Downloading [{0,-50}] {1}", pbar, sizePbar, (string)e.UserState);
        //                else
        //                    message = string.Format("\rDownloading [{0,-50}] {1}", pbar, sizePbar);
        //                Console.Write("{0,-120}", message);
        //            }
        //        }
        //    }
        //}

        public static bool CheckInternetConnection() {
            try {
                using (var client = new WebClient())
                using (client.OpenRead("http://clients3.google.com/generate_204")) {
                    return true;
                }
            }
            catch {
                return false;
            }
        }

        public static byte[] GetStructuredStorageStream(string filePath, string streamName) {
            logger.Debug(string.Format("Attempting to read \"{0}\" stream from structured storage file at \"{1}\"",
                                       streamName, filePath));
            int res = StgIsStorageFile(filePath);

            if (res == 0) {
                CompoundFile cf = new CompoundFile(filePath);
                logger.Debug($"Found CF Root: {cf.RootStorage}");
                if (cf.RootStorage.TryGetStream(streamName, out var foundStream)) {
                    byte[] streamData = foundStream.GetData();
                    cf.Close();
                    return streamData;
                }
                return null;
            }
            else {
                throw new NotSupportedException("File is not a structured storage file");
            }
        }

        public static void OpenUrl(string url, string logErrMsg = null) {
            if (CheckInternetConnection()) {
                if (!Regex.IsMatch(url, @"'^https*://'"))
                    url = "http://" + url;
                logger.Debug("Opening {0}", url);
                Process.Start(url);
            }
            else {
                if (logErrMsg is null)
                    logErrMsg = string.Format("Error opening url \"{0}\"", url);

                logger.Error(string.Format("{0}. No internet connection detected.", logErrMsg));
            }
        }

        public static bool VerifyUrl(string url) {
            if (CheckInternetConnection()) {
                HttpWebRequest request = GetHttpWebRequest(url);
                try {
                    var response = request.GetResponse();
                }
                catch (Exception ex) {
                    logger.Debug(ex);
                    return false;
                }
            }

            return true;
        }

        public static void SetFileSecurity(string filePath, string userNameWithDoman) {
            //get file info
            FileInfo fi = new FileInfo(filePath);

            //get security access
            FileSecurity fs = fi.GetAccessControl();

            //remove any inherited access
            fs.SetAccessRuleProtection(true, false);

            //get any special user access
            AuthorizationRuleCollection rules =
                fs.GetAccessRules(true, true, typeof(System.Security.Principal.NTAccount));

            //remove any special access
            foreach (FileSystemAccessRule rule in rules)
                fs.RemoveAccessRule(rule);

            //add current user with full control.
            fs.AddAccessRule(
                new FileSystemAccessRule(userNameWithDoman, FileSystemRights.FullControl, AccessControlType.Allow)
                );

            //add all other users delete only permissions.
            //fs.AddAccessRule(
            //    new FileSystemAccessRule("Authenticated Users", FileSystemRights.Delete, AccessControlType.Allow)
            //    );

            //flush security access.
            System.IO.File.SetAccessControl(filePath, fs);
        }

        public static void OpenInExplorer(string resourcePath) {
            Process.Start("explorer.exe", resourcePath);
        }

        // public static void AddShortcut(string shortCutName,
        //                                string appName,
        //                                string pathToExe,
        //                                string args,
        //                                string workingDir,
        //                                string iconPath,
        //                                string description,
        //                                bool allUsers = false) {
        //     string commonStartMenuPath = Environment.GetFolderPath(
        //         allUsers ? Environment.SpecialFolder.CommonStartMenu : Environment.SpecialFolder.StartMenu
        //         );
        //     string appStartMenuPath = Path.Combine(commonStartMenuPath, "Programs", appName);

        //     EnsurePath(appStartMenuPath);

        //     string shortcutLocation = Path.Combine(appStartMenuPath, shortCutName + ".lnk");
        //     WshShell shell = new WshShell();
        //     IWshShortcut shortcut = (IWshShortcut)shell.CreateShortcut(shortcutLocation);

        //     shortcut.Description = "Test App Description";
        //     //shortcut.IconLocation = @"C:\Program Files (x86)\TestApp\TestApp.ico"; //uncomment to set the icon of the shortcut
        //     shortcut.TargetPath = pathToExe;
        //     shortcut.Arguments = args;
        //     shortcut.Description = description;
        //     shortcut.IconLocation = iconPath;
        //     shortcut.WorkingDirectory = workingDir;
        //     shortcut.Save();
        // }

        public static string NewShortUUID() {
            return Convert.ToBase64String(Guid.NewGuid().ToByteArray());
        }

        // https://en.wikipedia.org/wiki/ISO_8601
        // https://stackoverflow.com/a/27321188/2350244
        public static string GetISOTimeStamp(DateTime dtimeValue) => dtimeValue.ToString("yyyy-MM-ddTHH:mm:ssK");

        public static string GetISOTimeStampNow() => GetISOTimeStamp(DateTime.Now.ToUniversalTime());

        public static string GetISOTimeStampLocalNow() => GetISOTimeStamp(DateTime.Now);

        public static Encoding GetUTF8NoBOMEncoding() {
            // https://coderwall.com/p/o59zug/encoding-multiply-files-to-utf8-without-bom-with-c
            return new System.Text.UTF8Encoding(false);
        }

        public static int FindBytes(byte[] src, byte[] find) {
            int index = -1;
            int matchIndex = 0;
            // handle the complete source array
            for (int i = 0; i < src.Length; i++) {
                if (src[i] == find[matchIndex]) {
                    if (matchIndex == (find.Length - 1)) {
                        index = i - matchIndex;
                        break;
                    }
                    matchIndex++;
                }
                else if (src[i] == find[0]) {
                    matchIndex = 1;
                }
                else {
                    matchIndex = 0;
                }

            }
            return index;
        }

        public static byte[] ReplaceBytes(byte[] src, byte[] search, byte[] repl) {
            byte[] dst = null;
            int index = FindBytes(src, search);
            if (index >= 0) {
                dst = new byte[src.Length - search.Length + repl.Length];
                // before found array
                Buffer.BlockCopy(src, 0, dst, 0, index);
                // repl copy
                Buffer.BlockCopy(repl, 0, dst, index, repl.Length);
                // rest of src array
                Buffer.BlockCopy(
                    src,
                    index + search.Length,
                    dst,
                    index + repl.Length,
                    src.Length - (index + search.Length));
                return dst;
            }
            return src;
        }

        // https://stackoverflow.com/a/49922533/2350244
        public static string GenerateRandomName(int len = 16) {
            Random r = new Random();
            string[] consonants = { "b", "c", "d", "f", "g", "h", "j", "k", "l", "m", "l", "n", "p", "q", "r", "s", "sh", "zh", "t", "v", "w", "x" };
            string[] vowels = { "a", "e", "i", "o", "u", "ae", "y" };
            string Name = "";
            Name += consonants[r.Next(consonants.Length)].ToUpperInvariant();
            Name += vowels[r.Next(vowels.Length)];
            int b = 2; //b tells how many times a new letter has been added. It's 2 right now because the first two letters are already in the name.
            while (b < len) {
                Name += consonants[r.Next(consonants.Length)];
                b++;
                Name += vowels[r.Next(vowels.Length)];
                b++;
            }
            return Name;
        }

        public static string GetProcessFileName() => Process.GetCurrentProcess().MainModule.FileName;
        public static string GetProcessPath() => Path.GetDirectoryName(GetProcessFileName());
        public static string GetAssemblyPath<T>() => Path.GetDirectoryName(typeof(T).Assembly.Location);

        public static string GenerateSHA1Hash(string filePath) {
            // Use input string to calculate SHA1 hash
            using (FileStream fs = new FileStream(filePath, FileMode.Open)) {
                using (BufferedStream bs = new BufferedStream(fs)) {
                    using (var sha1 = new System.Security.Cryptography.SHA1Managed()) {
                        StringBuilder sb = new StringBuilder();
                        foreach (byte b in sha1.ComputeHash(bs)) {
                            sb.Append(b.ToString("X2"));
                        }
                        return sb.ToString();
                    }
                }
            }
        }
    }
}

