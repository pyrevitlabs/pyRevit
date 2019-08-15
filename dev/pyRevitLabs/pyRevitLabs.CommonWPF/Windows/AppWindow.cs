using System;
using System.Reflection;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.ComponentModel;
using System.Windows.Data;

// packages
using pyRevitLabs.MahAppsMetro;
using pyRevitLabs.MahAppsMetro.Controls;

namespace pyRevitLabs.CommonWPF.Windows {
    /// <summary>
    /// Interaction logic for AppWindow.xaml
    /// </summary>
    public class AppWindow : MetroWindow, INotifyPropertyChanged {
        private string _appVerOverride = string.Empty;

        public AppWindow() {
            InitializeComponent();
        }

        private void InitializeComponent() {
            // setting up user name and app version buttons
            var windowButtons = new WindowCommands();

            var userButton = new Button() {
                Content = CurrentUser,
                ToolTip = "Active User. Click to copy to clipboard.",
                Focusable = false
            };

            userButton.Click += Copy_Button_Title;
            windowButtons.Items.Add(userButton);

            if (AppVersion != null && AppVersion != string.Empty) {
                // create a toolbar button and bind to appversion
                Binding myBinding = new Binding();
                myBinding.Source = this;
                myBinding.Path = new PropertyPath("AppVersion");
                myBinding.UpdateSourceTrigger = UpdateSourceTrigger.PropertyChanged;

                var versionButton = new Button() {
                    ToolTip = "Version. Click to copy to clipboard.",
                    Focusable = false,
                };

                BindingOperations.SetBinding(versionButton, Button.ContentProperty, myBinding);

                versionButton.Click += Copy_Button_Title;
                windowButtons.Items.Add(versionButton);
            }

            RightWindowCommands = windowButtons;
            LeftWindowCommands = new WindowCommands();

            TitleCharacterCasing = CharacterCasing.Normal;
            SaveWindowPosition = true;
        }

        // property updates
        public event PropertyChangedEventHandler PropertyChanged;

        protected virtual void RaisePropertyChanged(string propertyName) {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }

        // app version
        public virtual string AppVersion {
            get {
                if (_appVerOverride != string.Empty)
                    return _appVerOverride;
                else
                    return Assembly.GetExecutingAssembly().GetName().Version.ToString();
            }
            set {
                _appVerOverride = value;
                RaisePropertyChanged("AppVersion");
            }
        }

        // current user id
        public string CurrentUser { get { return System.Security.Principal.WindowsIdentity.GetCurrent().Name; } }

        // helper for loading and setting icons into window
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

        public void SetIcon(string iconPath) {
            Icon = LoadIcon(new Uri(iconPath));
            IconBitmapScalingMode = BitmapScalingMode.HighQuality;
            IconEdgeMode = EdgeMode.Aliased;
            IconScalingMode = MultiFrameImageMode.ScaleDownLargerFrame;
            ShowIconOnTitleBar = true;
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
