using System.Diagnostics;

namespace pyRevitLabs.TargetApps.Revit {
    public class RevitProcess {
        private Process _process;

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
                var fileInfo = FileVersionInfo.GetVersionInfo(Module);
                return RevitProduct.LookupRevitProduct(fileInfo.ProductVersion);
            }
        }

        public override string ToString() {
            return string.Format("PID: {0} | {1}", _process.Id, RevitProduct.ToString());
        }

        public void Kill() {
            _process.Kill();
        }
    }
}