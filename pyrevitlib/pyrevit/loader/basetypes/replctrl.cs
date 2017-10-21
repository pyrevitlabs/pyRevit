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

namespace PyRevitBaseClasses
{
    public partial class REPLControl : TextBlock
    {
        public REPLControl()
        {
            InitializeComponent();
        }

        private void InitializeComponent()
        {
            this.FontFamily = new FontFamily("Verdana");
            this.Text = "IronPython 2.7.X on .NET 4.X (64-bit)" +
                        "\nType \"help\", \"copyright\", \"credits\" or \"license\" for more information." +
                        "\n >>> REPL Prompt Coming Soon...";
        }
    }
}
