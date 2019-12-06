# pylint: skip-file
import os
import os.path as op
from time import sleep
import clr

import System
from System import Windows
from System import EventHandler
from System import Threading

try:
    from pyrevit.framework import wpf
except Exception:
    clr.AddReference('IronPython.Wpf')
    import IronPython
    wpf = IronPython.Modules.Wpf


class OutputWindow(Windows.Window):
    def __init__(self, xaml_file_name):
        wpf.LoadComponent(self, op.join(op.dirname(__file__), xaml_file_name))
        self.closed = False
        self.update_threadid()

    def update_threadid(self):
        self.ThreadId_TextBlock.Text = 'Thread Id: {}:{}'.format(
            System.AppDomain.GetCurrentThreadId(),
            Threading.Thread.CurrentThread.ManagedThreadId
        )

    def update_progress(self, value):
        self.pbar2.Value = value

    def append(self, output):
        self.console.Text += output

    def window_closing(self, sender, args):
        self.closed = True


class RevitWindow(Windows.Window):
    def __init__(self, xaml_file_name):
        wpf.LoadComponent(self, op.join(op.dirname(__file__), xaml_file_name))
        self.progress_state = 0
        self.output = None
        self.update_threadid()

    def make_outputwindow(self):
        self.output = OutputWindow('OutputWindow.xaml')
        self.output.ShowDialog()

    def button_click(self, sender, args):
        new_ui_thread = Threading.Thread(
            Threading.ThreadStart(
                self.make_outputwindow
                ))
        new_ui_thread.SetApartmentState(Threading.ApartmentState.STA)
        new_ui_thread.Start()
        self.do_long_process()

    def update_progress(self):
        self.output.update_progress(self.progress_state)

    def append_message(self):
        self.output.append("Progress Update {}\n".format(self.progress_state))

    def do_long_process(self):
        for i in range(10):
            sleep(1)
            print(i)
            if self.output and not self.output.closed:
                self.progress_state = (i+1) * 10
                self.output.Dispatcher.Invoke(
                    System.Action(self.update_progress)
                    )
                self.output.Dispatcher.Invoke(
                    System.Action(self.append_message)
                    )

    def update_threadid(self):
        self.ThreadId_TextBlock.Text = 'Thread Id: {}:{}'.format(
            System.AppDomain.GetCurrentThreadId(),
            Threading.Thread.CurrentThread.ManagedThreadId
        )

    def window_closing(self, sender, args):
        print('Thread Id: {}:{}'.format(
            System.AppDomain.GetCurrentThreadId(),
            Threading.Thread.CurrentThread.ManagedThreadId
        ))


def start_revit():
    RevitWindow('RevitWindow.xaml').ShowDialog()

start_revit()