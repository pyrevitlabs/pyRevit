using System;
using System.Windows;
using System.Windows.Controls;

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
