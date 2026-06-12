using System.Diagnostics;

namespace pyRevitLabs.TargetApps.Revit {
    public class RevitProcess {
        private Process _process;
        private RevitProduct _revitProduct = null;
        private bool _revitProductResolved = false;

        public RevitProcess(Process runningRevitProcess) {
            _process = runningRevitProcess;
        }

        public static bool IsRevitProcess(Process runningProcess) {
            if (runningProcess.ProcessName.ToLower() == "revit")
                return true;
            return false;
        }

        public int ProcessId {
            get {
                return _process.Id;
            }
        }

        public string Module {
            get {
                return _process.MainModule.FileName;
            }
        }

        public RevitProduct RevitProduct {
            get {
                if (!_revitProductResolved) {
                    _revitProductResolved = true;
                    try {
                        var modulePath = Module;
                        var fileInfo = FileVersionInfo.GetVersionInfo(modulePath);
                        _revitProduct = RevitProduct.ResolveProduct(fileInfo.ProductVersion, modulePath);
                    }
                    catch {
                        _revitProduct = null;
                    }
                }
                return _revitProduct;
            }
        }

        public override string ToString() {
            var product = RevitProduct;
            if (product != null)
                return string.Format("PID: {0} | {1}", _process.Id, product.ToString());

            try {
                var modulePath = Module;
                var fileInfo = FileVersionInfo.GetVersionInfo(modulePath);
                return string.Format("PID: {0} | Path: \"{1}\" | ProductVersion: {2} | Note: could not resolve product (not listed in pyrevit-hosts.json and/or failed to read binary version info)",
                                     _process.Id, modulePath, fileInfo.ProductVersion);
            }
            catch {
                return string.Format("PID: {0} | Note: could not read Revit product information", _process.Id);
            }
        }

        public void Kill() {
            _process.Kill();
        }
    }
}
