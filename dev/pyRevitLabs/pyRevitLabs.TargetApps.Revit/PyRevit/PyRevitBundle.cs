using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace pyRevitLabs.TargetApps.Revit {
    public enum PyRevitBundleTypes {
        Unknown,
        Tab,
        Panel,
        LinkButton,
        PushButton,
        ToggleButton,
        SmartButton,
        PullDown,
        Stack3,
        Stack2,
        SplitButton,
        SplitPushButton,
        PanelButton,
        NoButton,
    }

    public class PyRevitBundle {
        public static string GetBundleDirExt(PyRevitBundleTypes bundleType) {
            switch (bundleType) {
                case PyRevitBundleTypes.Tab: return PyRevit.BundleTabPostfix;
                case PyRevitBundleTypes.Panel: return PyRevit.BundlePanelPostfix;
                case PyRevitBundleTypes.LinkButton: return PyRevit.BundleLinkButtonPostfix;
                case PyRevitBundleTypes.PushButton: return PyRevit.BundlePushButtonPostfix;
                case PyRevitBundleTypes.ToggleButton: return PyRevit.BundleToggleButtonPostfix;
                case PyRevitBundleTypes.SmartButton: return PyRevit.BundleSmartButtonPostfix;
                case PyRevitBundleTypes.PullDown: return PyRevit.BundlePulldownButtonPostfix;
                case PyRevitBundleTypes.Stack3: return PyRevit.BundleStack3Postfix;
                case PyRevitBundleTypes.Stack2: return PyRevit.BundleStack2Postfix;
                case PyRevitBundleTypes.SplitButton: return PyRevit.BundleSplitButtonPostfix;
                case PyRevitBundleTypes.SplitPushButton: return PyRevit.BundleSplitPushButtonPostfix;
                case PyRevitBundleTypes.PanelButton: return PyRevit.BundlePanelButtonPostfix;
                case PyRevitBundleTypes.NoButton: return PyRevit.BundleNoButtonPostfix;
                default: return null;
            }
        }
    }
}
