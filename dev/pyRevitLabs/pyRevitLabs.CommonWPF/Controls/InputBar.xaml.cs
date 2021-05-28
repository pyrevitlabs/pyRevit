using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading;
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
        // input control mechanism
        private object _inputLock = new object();
        private bool _waiting = false;

        // input history
        private int _historyPointer = -1;
        private List<string> _history = new List<string>();

        // input buffer
        private string _input = string.Empty;

        // debug commands config
        private string _dbgCont = string.Empty;
        private string _dbgStepOver = string.Empty;
        private string _dbgStepIn = string.Empty;
        private string _dbgStepOut = string.Empty;
        private string _dbgStop = string.Empty;

        public InputBar() {
            InitializeComponent();
        }

        public string ReadInput() {
            // clear inputs
            _input = string.Empty;
            inputTb.Text = string.Empty;
            inputTb.Focus();
            // see inputTb_KeyUp handler for history notes
            _historyPointer = _history.Count;
            
            // start waiting
            _waiting = true;
            
            // show input control
            do {
                // pass control to dispatcher to update ui
                inputTb.Dispatcher.Invoke(
                    () => { },
                    System.Windows.Threading.DispatcherPriority.Background
                    );

                // reduce cpu usage
                Thread.Sleep(50);

                lock (_inputLock) {
                    if (!_waiting)
                        break;
                }
            } while (true);

            // we are not waiting anymore (_waiting = false)

            // if no input is provided from the box or the buttons
            // it means the window has been cancelled
            // so if we are in debug mode (_dbgStop has value), let's stop
            if (_input == string.Empty && _dbgStop != string.Empty)
                _input = _dbgStop;

            // disable debug and file modes
            debugPanel.Visibility = Visibility.Collapsed;
            filePanel.Visibility = Visibility.Collapsed;

            return _input;
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

        public void EnableFilePicker() {
            filePanel.Visibility = Visibility.Visible;
            debugPanel.Visibility = Visibility.Collapsed;
        }

        public void EnableDebug(string dbgCont, string dbgStepOver, string dbgStepIn, string dbgStepOut, string dbgStop) {
            _dbgCont = dbgCont;
            _dbgStepOver = dbgStepOver;
            _dbgStepIn = dbgStepIn;
            _dbgStepOut = dbgStepOut;
            _dbgStop = dbgStop;

            debugPanel.Visibility = Visibility.Visible;
            filePanel.Visibility = Visibility.Collapsed;
        }

        // privates
        private void SendInput(string input) {
            lock (_inputLock) {
                _input = input;
                _waiting = false;
            }
        }

        private void inputTb_KeyUp(object sender, KeyEventArgs e) {
            switch (e.Key) {
                // submit input
                case Key.Enter:
                    if (inputTb.Text != string.Empty)
                        _history.Add(inputTb.Text);
                    SendInput(inputTb.Text);
                    break;

                /*
                 *  history array (count = n+1)
                 * | index = 0
                 * |                ▲ history up
                 * |                ▼ history down
                 * | index = n
                 * ------------------------------------------------
                 * input text box (index = n+1)
                 * ------------------------------------------------
                 * 
                 * if pointer is n+1 means the textbox should have focus
                 * as the new entry in the history
                 */
                case Key.Up:
                    _historyPointer--;
                    if (_historyPointer < _history.Count)
                        if (_historyPointer >= 0)
                            inputTb.Text = _history.ElementAt(_historyPointer);
                        else
                            _historyPointer = 0;
                    break;
                
                case Key.Down:
                    _historyPointer++;
                    if (_historyPointer >= 0)
                        if (_historyPointer < _history.Count)
                            inputTb.Text = _history.ElementAt(_historyPointer);
                        else {
                            _historyPointer = _history.Count;
                            inputTb.Text = string.Empty;
                        }
                            
                    break;

                default:
                    break;
            }
        }

        private void dbgCont_Click(object sender, RoutedEventArgs e) =>
            SendInput(_dbgCont);

        private void dbStepOver_Click(object sender, RoutedEventArgs e) =>
            SendInput(_dbgStepOver);

        private void dbgStepIn_Click(object sender, RoutedEventArgs e) =>
            SendInput(_dbgStepIn);

        private void dbgStepOut_Click(object sender, RoutedEventArgs e) =>
            SendInput(_dbgStepOut);

        private void dbgStop_Click(object sender, RoutedEventArgs e) =>
            SendInput(_dbgStop);

        private void pickFile_Click(object sender, RoutedEventArgs e) {
            var fileDlg = new System.Windows.Forms.OpenFileDialog() {
                Title = "Select File:",
                Filter = "Any|*.*"
            };
            fileDlg.ShowDialog();
            SendInput(fileDlg.FileName);
        }
    }
}
