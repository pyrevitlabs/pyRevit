# -*- coding: utf-8 -*-
#pylint: disable=import-error,invalid-name,missing-module-docstring

__title__ = 'Help Request'
__doc__ = """This script sends a support request email to your BIM support.
You can quickly describe the issue and send the email directly from Revit.
The email will contain information about the active document, system, and GPU.
You can customize the email body by modifying the build_email_body function.

TIP: shift + click to edit the tool default email address.

Author: Tay Othman, AIA"""

import platform
import datetime
import subprocess
import multiprocessing
from pyrevit import HOST_APP, DB, revit, script, forms
from support_config import SupportConfig
import os, wpf, clr
clr.AddReference("System")
clr.AddReference("System.Management")
# clr.AddReference("IronPython.Modules")
import System
from System.Diagnostics import Process
from System.Management import ManagementObjectSearcher
from System.Windows import Window
from System.Windows.Controls import TextBox, Button, Label, CheckBox, ListBox, ComboBox


# Global Variables
doc = revit.doc
output = script.get_output()
divider = "-" * 50

class SupportForm(Window):
    def __init__(self):
        form_path = os.path.join(os.path.dirname(__file__), "form.xaml")
        wpf.LoadComponent(self, form_path)
        self.UI_txtEmail.Text = SupportConfig.get_default_email()
        self.UI_txtSubject.Text = "Support Request"
        self.populate_hashtags()
        self.ShowDialog()
    
    def populate_hashtags(self):
        """Populates the hashtags listbox."""
        [self.UI_Tag1.Content,
         self.UI_Tag2.Content,
         self.UI_Tag3.Content,
         self.UI_Tag4.Content,
         self.UI_Tag5.Content,
         self.UI_Tag6.Content,
         self.UI_Tag7.Content,
         self.UI_Tag8.Content] = (
             SupportConfig.get_hashtags(SupportConfig.
                                file_to_xml("config.xml")))
        
    def UIe_btn_run(self, sender, e):
        """Runs the script after the user clicks the button."""
        email_address = self.UI_txtEmail.Text
        subject_line = self.UI_txtSubject.Text
        email_body = build_email_body(self.UI_txtDescription.Text)
        if email_address == "No_Email":
            output.print_md("### Copy the report below and send it to your support team.")
            print(subject_line)
            print(email_body)
        else:
            send_email(email_address, subject_line, email_body)
        self.Close()

    def UIe_tag_selection(self, sender, e):
        selection = []
        selected_tags = self.UI_Tags.SelectedItems
        for tag in selected_tags:
            string_tag = tag.Content
            selection.append(string_tag)
        create_subject_line(selection, self.UI_txtSubject.Text)
        subject_line = self.UI_txtSubject.Text
        subject_segments = subject_line.split("|")
        last_segment = subject_segments[-1].strip()
        self.UI_txtSubject.Text = last_segment
        self.UI_txtSubject.Text = create_subject_line(
            selection,self.UI_txtSubject.Text)


def send_email(email_address, subject_line, email_body):
    """Sends an email using the default email client.
    Args:
    email_address (str): The email address.
    subject_line (str): The email subject.
    email_body (str): The email body."""
    email_body = System.Uri.EscapeDataString(email_body)
    mailto_link = create_mailto_link(email_address, subject_line, email_body)
    os.startfile(mailto_link)

def create_subject_line(tags, subject_line):
    """Creates the subject line for the email.
    Returns:
    str: The subject line."""
    # get the hashtag list and seperate them by | for the subject line
    combined_subject = "{} | {}".format(
        (" | ".join(tags)), subject_line)
    return combined_subject

def create_mailto_link(email, subject, body):
    """Creates a mailto link.
    Args:
    email (str): The email address.
    subject (str): The email subject.
    body (str): The email body.
    Returns:
    str: The mailto link."""
    mailto_link = "mailto:" + email + "?subject=" + subject + "&body=" + body
    return mailto_link

def get_issue_description(body):
    """Gets the issue description from the user.
    Returns:
    str: The issue description."""
    return body

def get_current_time():
    """Gets the current time.
    Returns:
    str: The current time."""
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return current_time

def get_system_info():
    """Gets the system information.
    Returns:
    str: The system information."""
    try:
        system = platform.system()
        version = platform.version()
        release = platform.release()
        if system == "Windows":
            os_info = "{} {} ({})".format(system, release, version)
        else:
            os_info = "{} {} ({})".format(system, release, version)
        return os_info
    except Exception as e:
        return "Error: {}".format(str(e))

def get_computer_name():
    """Gets the computer name.
    Returns:
    str: The computer name."""
    try:
        computer_name = platform.node()
        return computer_name
    except Exception as e:
        return "Error: {}".format(str(e))

def get_username():
    """Gets the username.
    Returns:
    str: The username."""
    try:
        username = os.environ.get('USERNAME')
        return username
    except Exception as e:
        return "Error: {}".format(str(e))

def get_cpu_cores():
    """Gets the number of CPU threads.
    Returns:
    str: The number of CPU threads."""
    try:
        cpu_info = "{} cores".format(multiprocessing.cpu_count())
        return cpu_info
    except Exception as e:
        return "Error: {}".format(str(e))

def get_cpu_brand():
    """Gets the CPU's commercial name.
    Returns:
    str: The CPU brand."""
    try:
        cpu_info = System.Environment.GetEnvironmentVariable("PROCESSOR_IDENTIFIER")
        searcher = ManagementObjectSearcher("SELECT * FROM Win32_Processor")
        for item in searcher.Get():
            cpu_info = item["Name"]
        return cpu_info
    except Exception as e:
        return "Error: {}".format(str(e))

def get_project_info_number():
    """Gets the project number from the active document.
    Returns:
    str: The project number."""
    try:
        project_number = doc.ProjectInformation.Number
        return project_number
    except Exception as e:
        return "Error: {}".format(str(e))

def get_total_memory():
    """Gets the total memory of the system.
    Returns:
    str: The total memory of the system."""
    try:
        searcher = ManagementObjectSearcher("SELECT * FROM Win32_OperatingSystem")
        for os in searcher.Get():
            total_memory = int(os["TotalVisibleMemorySize"]) * 1024
        pass  # Removed undefined variable reference
        total_gigabytes = -(-total_memory // (1024 ** 3))
        return total_gigabytes
    except Exception as e:
        return "Error: {}".format(str(e))

def get_memory_usage():
    """Gets the memory usage of the system.
    Returns:
    str: The memory usage of the system."""
    try:
        searcher = ManagementObjectSearcher("SELECT * FROM Win32_OperatingSystem")
        for os in searcher.Get():
            total_memory = int(os["TotalVisibleMemorySize"]) * 1024
            free_memory = int(os["FreePhysicalMemory"]) * 1024
        used_memory = total_memory - free_memory
        used_gigabytes = -(-used_memory // (1024 ** 3))
        return used_gigabytes
    except Exception as e:
        return "Error: {}".format(str(e))

def build_gpu_searcher():
    """
    Retrieves the GPU information using WMI.
    Returns:
    ManagementObjectSearcher: An object that can be used to query GPU info.
    """
    searcher = ManagementObjectSearcher('SELECT * FROM Win32_VideoController')
    return searcher

def get_gpu_name(searcher_gpu):
    """
    Retrieves the GPU name.
    Returns:
    str: The GPU name.
    """
    return searcher_gpu['Name']

def get_gpu_vram(searcher_gpu):
    """Gets the total VRAM of the GPU.
    Args:
        searcher_gpu (ManagementBaseObject): The GPU object.
    Returns:
        str: The total VRAM of the GPU."""
    gpu_vram= searcher_gpu['AdapterRAM']
    if gpu_vram is not None:
        try:
            if gpu_vram == 4293918720:
                return ("Total VRAM: {0} MB or More".
                        format(gpu_vram // (1024 ** 2)))
            else:
                return ("Total VRAM: {0} MB".
            format(gpu_vram // (1024 ** 2)))
        except Exception as e:
            return("Error processing GPU {0}: {1}".
                    format(searcher_gpu['Name'], str(e)))
    else:
        return "GPU does not have a dedicated VRAM."

def get_gpu_driver_version(searcher_gpu):
    """
    Retrieves the GPU driver version.
    Returns:
    str: The GPU driver version.
    """
    return searcher_gpu['DriverVersion']

def convert_driver_date(date):
    """Converts the driver date to a readable format.
    Args:
        date (str): The driver date in the decimal format.
    Returns:
        str: The driver date in the format YYYY-MM-DD."""
    return date[:4] + "-" + date[4:6] + "-" + date[6:8]

def get_gpu_driver_date(searcher_gpu):
    """
    Retrieves the GPU driver date.
    Returns:
    str: The GPU driver date.
    """
    return convert_driver_date(searcher_gpu['DriverDate'])

def collect_gpu_info():
    """
    Collects the GPU information.
    Returns:
    list: A list of dictionaries containing the GPU information.
    """
    searcher_gpu = build_gpu_searcher()
    gpu_info_list = []
    for gpu in searcher_gpu.Get():
        gpu_info = {
            "GPU Name": get_gpu_name(gpu),
            "GPU Driver Version": get_gpu_driver_version(gpu),
            "GPU Driver Date": get_gpu_driver_date(gpu),
            "GPU VRAM": "{}".format(get_gpu_vram(gpu))
        }
        gpu_info_list.append(gpu_info)
    return gpu_info_list

def tabulate_gpu_info(gpu_info_list):
    """
    Tabulates the GPU information.
    Args:
    gpu_info_list (list): A list of dictionaries containing the GPU information.
    Returns:
    str: The tabulated GPU information.
    """
    tabulated_gpu_info = ""
    for gpu_info in gpu_info_list:
        tabulated_gpu_info += "GPU Name: {}\n".format(gpu_info["GPU Name"])
        tabulated_gpu_info += "GPU Driver Version: {}\n".format(gpu_info["GPU Driver Version"])
        tabulated_gpu_info += "GPU Driver Date: {}\n".format(gpu_info["GPU Driver Date"])
        tabulated_gpu_info += "GPU VRAM: {}\n".format(gpu_info["GPU VRAM"])
        tabulated_gpu_info += divider + "\n"
    return tabulated_gpu_info

def get_revit_version():
    """Gets the Revit version and build number.
    Returns:
    str: The Revit version and build number.
    """
    try:
        revit_version = HOST_APP.app.VersionNumber
        revit_build = HOST_APP.app.VersionBuild
        return "{} (Build {})".format(revit_version, revit_build)
    except Exception as e:
        return "Error: {}".format(str(e))

def collect_system_info():
    """Collects the system information.
    Returns:
    dict: A dictionary containing the system information."""
    system_info = {
        "Revit Version": get_revit_version(),
        "Operating System": get_system_info(),
        "Computer Name": get_computer_name(),
        "Username": get_username(),
        "CPU Brand": get_cpu_brand(),
        "CPU Cores": get_cpu_cores(),
        "Total Memory": "{} GB".format(get_total_memory()),
        "Memory Usage": "{} GB".format(get_memory_usage()),
    }
    return system_info

def get_active_document_name():
    """Gets the name of the active document.
    Returns:
    str: The name of the active document."""
    return doc.Title

def get_active_view():
    """Gets the name of the active view.
    Returns:
    str: The name of the active view."""
    return doc.ActiveView.Name

def get_document_path():
    """Gets the path of the active document.
    Returns:
    str: The path of the active document."""
    return doc.PathName

def collect_document_info():
    """Collects the document information.
    Returns:
    dict: A dictionary containing the document information."""
    document_info = {
        "Document Name": get_active_document_name(),
        "Document Path": get_document_path(),
        "Active View": get_active_view()
    }
    return document_info

def build_email_body(body):
    """Builds the email body.
    Returns:
    str: The email body."""
    document_info = collect_document_info()
    system_info = collect_system_info()
    email_body = """
    
Support Request
===============================================================================    
Issue:

{}

===============================================================================

Revit Document Information
Project Number: {}
Document Name: {}
Document Path: {}
Active View: {}

===============================================================================
System Information

Revit Version: {}
Operating System: {}
Computer Name: {}
Username: {}
CPU Brand: {}
CPU Threads: {}
Total Memory: {}
Memory Usage: {}
===============================================================================
GPU Information
{}
""".format(
        get_issue_description(body),
        get_project_info_number(),
        document_info['Document Name'],
        document_info['Document Path'],
        document_info['Active View'],
        system_info['Revit Version'],
        system_info['Operating System'],
        system_info['Computer Name'],
        system_info['Username'],
        system_info['CPU Brand'],
        system_info['CPU Cores'],
        system_info['Total Memory'],
        system_info['Memory Usage'],
        tabulate_gpu_info(collect_gpu_info())
    )
    return email_body

if __name__ == "__main__":
    UI = SupportForm()





