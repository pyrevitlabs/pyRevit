using System.Windows;
using System.Windows.Controls;

namespace pyRevitLabs.TargetApps.Revit.Controls {
    public class PyRevitWindow : Window {
        static PyRevitWindow(){
            DefaultStyleKeyProperty.OverrideMetadata(typeof(PyRevitWindow), new FrameworkPropertyMetadata(typeof(PyRevitWindow)));
        }

        public PyRevitWindow() {
        }

        public override void OnApplyTemplate() {
            base.OnApplyTemplate();
        }
    }
}
