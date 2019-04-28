using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace pyRevitLabs.TargetApps.Revit {
    // pyrevit log levels
    public enum PyRevitLogLevels {
        None,
        Verbose,
        Debug
    }

    // pyrevit extension types
    public enum PyRevitExtensionTypes {
        Unknown,
        UIExtension,
        LibraryExtension,
    }

    // pyrevit bundle types
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

    // pyrevit attachment types
    public enum PyRevitAttachmentType {
        AllUsers,
        CurrentUser
    }

}
