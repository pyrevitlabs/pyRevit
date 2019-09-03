using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace pyRevitLabs.PyRevit {
    public enum PyRevitBundleTypes {
        Unknown,
        Tab,
        Panel,
        Stack,
        PullDown,
        SplitButton,
        SplitPushButton,
        PushButton,
        SmartButton,
        ToggleButton,
        PanelButton,
        NoButton,
        LinkButton,
        InvokeButton,
        ContentButton,
        URLButton
    }

    public class PyRevitBundle {
        public static string GetBundleDirExt(PyRevitBundleTypes bundleType) {
            switch (bundleType) {
                case PyRevitBundleTypes.Tab: return PyRevitConsts.BundleTabPostfix;
                case PyRevitBundleTypes.Panel: return PyRevitConsts.BundlePanelPostfix;
                case PyRevitBundleTypes.Stack: return PyRevitConsts.BundleStackPostfix;
                case PyRevitBundleTypes.PullDown: return PyRevitConsts.BundlePulldownButtonPostfix;
                case PyRevitBundleTypes.SplitButton: return PyRevitConsts.BundleSplitButtonPostfix;
                case PyRevitBundleTypes.SplitPushButton: return PyRevitConsts.BundleSplitPushButtonPostfix;
                case PyRevitBundleTypes.PushButton: return PyRevitConsts.BundlePushButtonPostfix;
                case PyRevitBundleTypes.SmartButton: return PyRevitConsts.BundleSmartButtonPostfix;
                case PyRevitBundleTypes.ToggleButton: return PyRevitConsts.BundleToggleButtonPostfix;
                case PyRevitBundleTypes.PanelButton: return PyRevitConsts.BundlePanelButtonPostfix;
                case PyRevitBundleTypes.NoButton: return PyRevitConsts.BundleNoButtonPostfix;
                case PyRevitBundleTypes.LinkButton: return PyRevitConsts.BundleLinkButtonPostfix;
                case PyRevitBundleTypes.InvokeButton: return PyRevitConsts.BundleInvokePostfix;
                case PyRevitBundleTypes.ContentButton: return PyRevitConsts.BundleContentPostfix;
                case PyRevitBundleTypes.URLButton: return PyRevitConsts.BundleURLPostfix;
                default: return null;
            }
        }

        public static bool IsType(string bundlePath, PyRevitBundleTypes bundleType) => bundlePath.ToLower().EndsWith(GetBundleDirExt(bundleType));
    }
}
