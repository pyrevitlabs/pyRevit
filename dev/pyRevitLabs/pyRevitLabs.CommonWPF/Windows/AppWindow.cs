using System;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.ComponentModel;

// packages
using MahApps.Metro;
using MahApps.Metro.Controls;

namespace pyRevitLabs.CommonWPF.Windows {
    /// <summary>
    /// Interaction logic for AppWindow.xaml
    /// </summary>
    public class AppWindow : MetroWindow, INotifyPropertyChanged {
        public AppWindow() {
            InitializeComponent();
        }

        private void InitializeComponent() {
            // setting up user name and app version buttons
            var windowButtons = new WindowCommands();

            var userButton = new Button() { Content = CurrentUser, ToolTip = "Active User. Click to copy to clipboard.", Focusable = false };
            userButton.Click += Copy_Button_Title;
            windowButtons.Items.Add(userButton);

            if (AppVersion != null && AppVersion != string.Empty) {
                var versionButton = new Button() { Content = AppVersion, ToolTip = "Version. Click to copy to clipboard.", Focusable = false };
                versionButton.Click += Copy_Button_Title;
                windowButtons.Items.Add(versionButton);
            }

            RightWindowCommands = windowButtons;

            TitleCharacterCasing = CharacterCasing.Normal;
            SaveWindowPosition = true;
        }

        // property updates
        public event PropertyChangedEventHandler PropertyChanged;

        protected void RaisePropertyChanged(string propertyName) {
            if (null != this.PropertyChanged) {
                PropertyChanged(this, new PropertyChangedEventArgs(propertyName));
            }
        }

        // app version
        public virtual string AppVersion { get { return Assembly.GetExecutingAssembly().GetName().Version.ToString(); } }

        // current user id
        public string CurrentUser { get { return System.Security.Principal.WindowsIdentity.GetCurrent().Name; } }

        // helper for loading icons into window
        public ImageSource LoadIcon(Uri path) {
            BitmapImage bitmap = new BitmapImage();
            bitmap.BeginInit();
            bitmap.UriSource = path;
            bitmap.CacheOption = BitmapCacheOption.OnLoad;
            bitmap.CreateOptions = BitmapCreateOptions.IgnoreImageCache;
            bitmap.EndInit();
            bitmap.Freeze();
            return bitmap;
        }

        // window button standard hander: copies to clipboard
        private void Copy_Button_Title(object sender, RoutedEventArgs e) {
            var button = e.Source as Button;
            Clipboard.SetText(button.Content.ToString());
            var notif = new ToolTip() { Content = "Copied to Clipboard" };
            notif.StaysOpen = false;
            notif.IsOpen = true;
        }

    }
}
