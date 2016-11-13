# void WriteJournalData(ExternalCommandData commandData)
# {
#     // Get the StringStringMap class which can write data into.
#     IDictionary<String, String> dataMap = commandData.JournalData;
#     dataMap.Clear();
#
#     // Begin to add the support data
#     dataMap.Add("Name", "Autodesk.Revit");
#     dataMap.Add("Information", "This is an example.");
#     dataMap.Add("Greeting", "Hello Everyone.");
# }
#
# /// <summary>
# /// This sample shows how to get data from journal file.
# /// </summary>
# void ReadJournalData(ExternalCommandData commandData)
# {
#     // Get the StringStringMap class which can write data into.
#     IDictionary<String, String> dataMap = commandData.JournalData;
#
#     // Begin to get the support data.
#     String prompt = "Name: " + dataMap["Name"];
#     prompt += "\nInformation: " + dataMap["Information"];
#     prompt += "\nGreeting: " + dataMap["Greeting"];
#
#     TaskDialog.Show("Revit",prompt);
# }