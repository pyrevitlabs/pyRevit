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

namespace pyRevitLabs.CommonWPF.Controls {
    /// <summary>
    /// Interaction logic for InputDebugBar.xaml
    /// </summary>
    public partial class InputBar : UserControl {
        private object _inputLock = new object();
        private bool _waiting = false;

        public InputBar() {
            InitializeComponent();
        }

        public string ReadInput() {
            Show();

            _waiting = true;
            inputTb.Text = "";
            inputTb.Focus();
            do {
                // pass control to dispatcher to update ui
                inputTb.Dispatcher.Invoke(
                    () => { },
                    System.Windows.Threading.DispatcherPriority.Background
                    );

                lock (_inputLock) {
                    if (!_waiting)
                        break;
                }
            } while (true);

            Hide();
            return inputTb.Text;
        }

        public void CancelRead() {
            lock (_inputLock) {
                _waiting = false;
            }
        }

        public void Show() {
            Visibility = Visibility.Visible;
        }

        public void Hide() {
            Visibility = Visibility.Collapsed;
        }

        private void inputTb_KeyUp(object sender, KeyEventArgs e) {
            if (e.Key == Key.Enter) {
                CancelRead();
            }
        }
    }
}
