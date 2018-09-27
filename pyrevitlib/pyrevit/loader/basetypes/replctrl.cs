using System.Windows.Controls;
using System.Windows.Media;

namespace PyRevitBaseClasses {
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
