using System.Linq;
using System.Collections.Generic;

using pyRevitLabs.Common.Extensions;

namespace pyRevitLabs.TargetApps.Revit {
    public class PyRevitEngine {
        public PyRevitEngine(int engineVer, string enginePath, string kernelName = "", string engineDescription = "", IEnumerable<string> compatibleProducts = null) {
            Version = engineVer;
            Path = enginePath;
            KernelName = kernelName;
            Description = engineDescription;
            CompatibleProducts = compatibleProducts != null ? compatibleProducts.ToList<string>() : new List<string>();
        }

        public override string ToString() {
            return string.Format(
                "KernelName:\"{0}\" | Version: \"{1}\" | Path: \"{2}\" | Desc: \"{3}\" | Compatible: \"{4}\"",
                KernelName, Version, Path, Description, CompatibleProducts.ConvertToCommaSeparatedString());
        }

        public int Version { get; private set; }
        public string Path { get; private set; }
        public string KernelName { get; private set; }

        public string LoaderPath {
            get {
                return System.IO.Path.Combine(Path, PyRevitConsts.DllName).NormalizeAsPath();
            }
        }

        public string Description { get; private set; }
        public List<string> CompatibleProducts { get; private set; }

        public bool IsCompatibleWith(string productName) {
            return CompatibleProducts.Contains(productName);
        }
    }
}
