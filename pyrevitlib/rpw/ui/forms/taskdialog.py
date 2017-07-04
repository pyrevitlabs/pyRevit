""" Wrappers for Default Revit TaskDialogs """

import sys
from rpw import UI


class Alert():
    """ A Simple Revit TaskDialog for displaying quick messages """
    def __init__(self, message, title='Alert', heading='', exit=False):
        """
        Args:
            message (str): TaskDialog Message
            title (str, optional): TaskDialog Title
            heading (str, optional): TaskDialog Message Heading
            exit (bool, optional): Exit Script after Dialog. Useful for displayin Errors. Default is False

        Usage:
            >>> Alert('Your Message', title="Title", heading="Some Heading")
            >>> Alert('You need to select Something', exit=True)
        """
        dialog = UI.TaskDialog(title)
        dialog.MainInstruction = heading
        dialog.MainContent = message
        self.result = dialog.Show()

        if exit:
            sys.exit(1)

class TaskDialog():

    def __init__(self):
        # TODO: Implement TaskDialog With buttonss
        # https://knowledge.autodesk.com/search-result/caas/CloudHelp/cloudhelp/2016/ENU/Revit-API/files/GUID-68BD5F44-972C-47CE-9D49-543B37C90561-htm.html
        raise NotImplemented
    # TaskDialog mainDialog = new TaskDialog("Hello, Revit!");
    # mainDialog.MainInstruction = "Hello, Revit!";
    # mainDialog.MainContent =
    #         "This sample shows how to use a Revit task dialog to communicate with the user."
    #         + "The command links below open additional task dialogs with more information.";
    #
    # // Add commmandLink options to task dialog
    # mainDialog.AddCommandLink(TaskDialogCommandLinkId.CommandLink1,
    #          "View information about the Revit installation");
    # mainDialog.AddCommandLink(TaskDialogCommandLinkId.CommandLink2,
    #                 "View information about the active document");
    #
    # // Set common buttons and default button. If no CommonButton or CommandLink is added,
    # // task dialog will show a Close button by default
    # mainDialog.CommonButtons = TaskDialogCommonButtons.Close;
    # mainDialog.DefaultButton = TaskDialogResult.Close;
    #
    # // Set footer text. Footer text is usually used to link to the help document.
    # mainDialog.FooterText =
    #         ""                          + "Click here for the Revit API Developer Center";
    #
    # TaskDialogResult tResult = mainDialog.Show();
    #
    # // If the user clicks the first command link, a simple Task Dialog
    # // with only a Close button shows information about the Revit installation.
    # if (TaskDialogResult.CommandLink1 == tResult)
    # {
    #         TaskDialog dialog_CommandLink1 = new TaskDialog("Revit Build Information");
    #         dialog_CommandLink1.MainInstruction =
    #                 "Revit Version Name is: " + app.VersionName + "\n"
    #          + "Revit Version Number is: " + app.VersionNumber + "\n"
    #                 + "Revit Version Build is: " + app.VersionBuild;
    #
    #         dialog_CommandLink1.Show();
    #
    # }
    #
    # // If the user clicks the second command link, a simple Task Dialog
    # // created by static method shows information about the active document
    # else if (TaskDialogResult.CommandLink2 == tResult)
    # {
    #         TaskDialog.Show("Active Document Information",
    #                 "Active document: " + activeDoc.Title + "\n"
    #          + "Active view name: " + activeDoc.ActiveView.Name);
    # }
    #
    # return Autodesk.Revit.UI.Result.Succeeded;


if __name__ == '__main__':
    Alert('Test Aler!')
