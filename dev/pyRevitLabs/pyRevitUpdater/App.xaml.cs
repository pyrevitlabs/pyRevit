using System;
using System.Collections.Generic;
using System.Configuration;
using System.Data;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;

using pyRevitLabs.CommonCLI;

namespace pyRevitUpdater {
    /// <summary>
    /// Interaction logic for App.xaml
    /// </summary>
    public partial class App : Application
    {
        private void ApplicationStartup(object sender, StartupEventArgs e) {
            PyRevitUpdaterCLI.ProcessArguments(e.Args);

            Environment.Exit(0);
        }
    }
}
