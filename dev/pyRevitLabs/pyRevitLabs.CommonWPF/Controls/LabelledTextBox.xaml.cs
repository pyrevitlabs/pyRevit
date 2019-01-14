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

namespace pyRevitLabs.CommonWPF.Controls
{
    /// <summary>
    /// Interaction logic for LabelledTextBox.xaml
    /// </summary>
    public partial class LabelledTextBox : UserControl
    {
        public static readonly DependencyProperty LabelProperty =
            DependencyProperty.Register("Label", typeof(String), typeof(LabelledTextBox),
                                        new FrameworkPropertyMetadata(String.Empty));

        public static readonly DependencyProperty TextProperty =
            DependencyProperty.Register("Text", typeof(String), typeof(LabelledTextBox),
                                        new FrameworkPropertyMetadata(String.Empty));


        public LabelledTextBox()
        {
            InitializeComponent();
        }

        public LabelledTextBox(string label)
        {
            InitializeComponent();
            Label = label;
        }

        public string Label
        {
            get { return GetValue(LabelProperty) as String; }
            set { SetValue(LabelProperty, value); }
        }

        public string Text
        {
            get { return GetValue(TextProperty) as String; }
            set { SetValue(TextProperty, value); }
        }
    }
}
