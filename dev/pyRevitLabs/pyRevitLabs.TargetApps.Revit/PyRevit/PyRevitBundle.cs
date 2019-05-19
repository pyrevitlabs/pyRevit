using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace pyRevitLabs.TargetApps.Revit {
    public class PyRevitBundle {
        public static string GetBundleDirExt(PyRevitBundleTypes bundleType) {
            switch (bundleType) {
                case PyRevitBundleTypes.Tab: return PyRevitConsts.BundleTabPostfix;
                case PyRevitBundleTypes.Panel: return PyRevitConsts.BundlePanelPostfix;
                case PyRevitBundleTypes.LinkButton: return PyRevitConsts.BundleLinkButtonPostfix;
                case PyRevitBundleTypes.PushButton: return PyRevitConsts.BundlePushButtonPostfix;
                case PyRevitBundleTypes.ToggleButton: return PyRevitConsts.BundleToggleButtonPostfix;
                case PyRevitBundleTypes.SmartButton: return PyRevitConsts.BundleSmartButtonPostfix;
                case PyRevitBundleTypes.PullDown: return PyRevitConsts.BundlePulldownButtonPostfix;
                case PyRevitBundleTypes.Stack3: return PyRevitConsts.BundleStack3Postfix;
                case PyRevitBundleTypes.Stack2: return PyRevitConsts.BundleStack2Postfix;
                case PyRevitBundleTypes.SplitButton: return PyRevitConsts.BundleSplitButtonPostfix;
                case PyRevitBundleTypes.SplitPushButton: return PyRevitConsts.BundleSplitPushButtonPostfix;
                case PyRevitBundleTypes.PanelButton: return PyRevitConsts.BundlePanelButtonPostfix;
                case PyRevitBundleTypes.NoButton: return PyRevitConsts.BundleNoButtonPostfix;
                default: return null;
            }
        }
    }
}
