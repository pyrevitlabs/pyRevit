using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Navigation;
using System.Windows.Shapes;

using CefSharp.Wpf;

namespace PyRevitBaseClasses
{
    /// <summary>
    /// Interaction logic for outputwindow.xaml
    /// </summary>
    public partial class ScriptOutput : Window
    {
        public ScriptOutput()
        {
            InitializeComponent();

            renderer.Load("https://www.google.com");
        }
    }
}
