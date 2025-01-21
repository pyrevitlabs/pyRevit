"""Request Support tool config"""
#pylint: disable=E0401,C0103
from pyrevit import script, forms
import os, wpf, clr
clr.AddReference("System")
clr.AddReference("System.Management")
from System.Windows import Window
from System.Windows.Controls import TextBox, Button, Label, CheckBox, ListBox, ComboBox

# get the config xml file
output = script.get_output()
config = "config.xml"
defaults = "defaults.xml"

class SupportConfigUI(Window):
    def __init__(self):
        wpf.LoadComponent(self, os.path.join(os.path.dirname(__file__), "config.xaml"))
        self.UI_def_eml.Text = SupportConfig.get_default_email()
        [self.Tag1.Text,
         self.Tag2.Text,
         self.Tag3.Text,
         self.Tag4.Text,
         self.Tag5.Text,
         self.Tag6.Text,
         self.Tag7.Text,
         self.Tag8.Text] = SupportConfig.get_hashtags(
             SupportConfig.file_to_xml(config))
        if SupportConfig.get_default_email() == "No_Email":
            self.UI_email_ok.IsChecked = False
            self.UI_web.IsChecked = True
        self.ShowDialog()

    def UIe_Save_Config(self, sender, e):
        """Saves the email address to the config.xml file."""
        if self.UI_email_ok.IsChecked:
            if SupportConfig.check_email_format(self.UI_def_eml.Text):
                new_email = self.UI_def_eml.Text
            else:
                forms.alert("Please enter a valid email address.", exitscript=True)
        else:
            new_email = "No_Email"
        new_hashtags = [self.Tag1.Text,
                        self.Tag2.Text,
                        self.Tag3.Text,
                        self.Tag4.Text,
                        self.Tag5.Text,
                        self.Tag6.Text,
                        self.Tag7.Text,
                        self.Tag8.Text]
        SupportConfig.write_config_xml(SupportConfig.file_to_xml(config), new_email, new_hashtags)
        self.Close()
            
class SupportConfig:
    @staticmethod
    def file_to_xml(file_name):
        return os.path.join(os.path.dirname(__file__), file_name)

    @staticmethod
    def restore_defaults(sourcexml, targetxml):
        """Restores the default settings from the default_settings.xml file."""
        with open(sourcexml, "r") as file:
            data = file.read()
        with open(targetxml, "w") as file:
            file.write(data)

    @staticmethod
    def check_config_xml(file_name):
        """Checks if the config.xml file exists.
        Args:
        file_name (str): The path to the config.xml file.
        Returns:
        bool: True if the config.xml file exists."""
        if os.path.exists(file_name):
            return file_name
        else:
            SupportConfig.restore_defaults("defaults.xml", file_name)
            return file_name

    @staticmethod
    def get_config_xml_path(file_name):
        """Gets the path to the config.xml file.
        Returns:
        str: The path to the config.xml file."""
        config_xml_path = os.path.join(os.path.dirname(__file__), file_name)
        return config_xml_path
    
    @staticmethod
    def write_config_xml(file_name, new_email, new_hashtags):
        """Writes the default email address to the config.xml file."""
        config_xml_path = SupportConfig.get_config_xml_path(file_name)
        with open(config_xml_path, "w") as file:
            file.write(
                "<config>\n")
            file.write(
                "    <email>{}</email>\n".
                format(new_email))
            # write list of hashtags
            file.write("    <hashtags>\n")
            for hashtag in new_hashtags:
                file.write("        <hashtag>{}</hashtag>\n".format(hashtag))
    
    @staticmethod
    def get_default_email():
        """Reads the default email address from the config.xml file.
        Returns:
        str: The default email address."""
        config_xml_path = SupportConfig.get_config_xml_path(SupportConfig.file_to_xml(config))
        with open(config_xml_path, "r") as file:
            for line in file:
                if "<email>" in line:

                    return (
                        line.strip().replace("<email>", "").
                        replace("</email>", ""))
    
    @staticmethod
    def get_hashtags(file_name):
        """Reads the list of hashtags from the config.xml file.
        Returns:
        list: The list of hashtags."""
        config_xml_path = file_name
        with open(config_xml_path, "r") as file:
            hashtags = []
            for line in file:
                # read the hashtags
                if "<hashtag>" in line:
                    hashtag = line.strip().replace("<hashtag>", "").replace("</hashtag>", "")
                    hashtags.append(hashtag)
            return hashtags
   
    @staticmethod
    def check_email_format(email):
        """Checks if the email address is in the correct format.
        Args:
        email (str): The email address.
        Returns:
        bool: True if the email address is in the correct format."""
        if "@" in email and "." in email:
            return True
        return False

if __name__ == "__main__":
    # check if the config.xml file exists
    try:
        SupportConfig.check_config_xml(SupportConfig.file_to_xml(config))
    except:
        SupportConfig.restore_defaults(SupportConfig.file_to_xml(defaults), 
                                       SupportConfig.file_to_xml(config))
    SupportConfigUI()