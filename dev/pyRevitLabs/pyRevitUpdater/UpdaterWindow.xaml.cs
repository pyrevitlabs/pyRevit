using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;

using pyRevitLabs.TargetApps.Revit;

namespace pyRevitUpdater {
    public partial class UpdaterWindow : Window {
        public UpdaterWindow() {
            InitializeComponent();

            this.PreviewKeyDown += new KeyEventHandler(HandleEsc);
        }

        public string ClonePath { get; set; }
        public bool Updated { get; set; } = false;

        private void HandleEsc(object sender, KeyEventArgs e) {
            if (e.Key == Key.Escape)
                Close();
        }

        private async void UpdateButton_MouseUp(object sender, MouseButtonEventArgs e) {
            if (PyRevitUpdaterCLI.RevitsAreRunning()) {
                MessageBox.Show("Close all running instances of Revit please.", PyRevitConsts.AddinFileName);
                return;
            }

            if (!Updated) {
                UpdateButton.IsIndeterminate = true;
                UpdateButton.Tag = "updating...";
                await Task.Run(() => {
                    PyRevitUpdaterCLI.RunUpdate(ClonePath);
                });
                UpdateButton.IsIndeterminate = false;
                Updated = true;
                UpdateButton.Tag = "update completed";
                UpdateButton.ToolTip = "click to close";
            }
            else {
                Close();
            }
        }
    }
}
