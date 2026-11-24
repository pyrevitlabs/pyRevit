# Print Sheets

pyRevit includes a fairly advanced print tool that allows you to print the sheets in a model or a linked model in order, format the output file names and apply custom print settings on a per sheet basis

With the model open, launch **Print Sheets** from the ***Drawing Set*** panel.

![Print Sheets window](../assets/tools/print-sheets/print-sheets-window.png)

!!! note "Screenshots"

    The screenshots of [Per-Page Print Settings](#per-page-print-settings-variable-paper-size), [Combining Sheets Into One File](#combining-sheets-into-one-file) and [Starting Print](#starting-print) come from an older version of the tool. The options they show still exist.

## Selecting Model and Drawing Index

Select the host model first in **Model**. If the host model has other Revit models linked into it, the list shows the linked models as well, as `Linked: <model name>`. **&lt;All Models&gt;** lists the sheets of the host and of every linked model together. Printing options for linked models are fairly limited compared to printing from main model due to the challenges in opening the linked model, apply printing changes, and reloading the model back into the host model.

After selecting the model, **Sheet Index** lists all the drawing indices in the selected model. The drawing index is used to read the order of the sheets. The intention is that you would have one drawing index in your model that is placed on the index sheet and the same drawing index is being used to print the sheets in order. **&lt;All Sheets&gt;** lists every sheet of the model.

The sheet list then shows each sheet with its index number, and the final name of the PDF file for each sheet.

## Indexing Configuration

The print tools provides a few options to adjust the indexing

![Sheet Ordering options](../assets/tools/print-sheets/print-sheets-indexing.png)

- **Reverse Print Order** reverses the order of the sheets
- **Show Non-Printable Sheets** lists the non-printable(placeholder) sheets on the list as well and allows you to reserve index numbers for these sheets. The print tool would not attempt to print these sheets and this is an option to help with indexing only.
- **Index Digits** is the number of digits used as index
- Set the starting integer for indexing on **Index Start** field. **Reset** to 0 if necessary.
- **Sheet Lookup** filters the sheet list.

## Print Configurations

The print tools provides a few options to adjust the printing output

![Sheet Printing options](../assets/tools/print-sheets/print-sheets-printing-options.png)

- **Printer**: in Revit 2022 and later the list starts with **Revit Internal Printer**, which exports the PDF files with Revit itself instead of a PDF printer driver.
- **Export DWG** also exports each sheet to DWG. It is not available when combining into one PDF, for linked models, or for **&lt;All Models&gt;**.
- **Output Folder** is where the PDF and DWG files are saved. Leave it empty to use `Desktop\pyRevit Print Folder`. An external PDF printer may use its own save location.
- **Subfolder** saves the files in a subfolder of the output folder. Use `\` for nested folders.
- Both folder fields accept the `{date}`, `{time}`, `{model}` and `{sheet_index}` tags.

### Naming Formats

You can define highly customized naming formats for your prints. The Edit Naming Formats window, provides a list of smart tags that would be replaced with the target value at print time, to form the final name of the PDF file. For example:

`{index}_{number}_{name}.pdf`

would be translated to Sheet index, Sheet number, and Sheet name for each sheet.

![Naming Formats window](../assets/tools/print-sheets/naming-formats.png)

There are a couple of advanced tags (shown in black) that allow you to read values for custom parameters at print time. For example `{tblock_param:PARAM_NAME}` allows you to apply the value of a custom project parameter for titleblocks, or a native titleblock parameter to the final file name.

### Per-Page Print Settings / Variable Paper Size

The print tool, under **Page Settings**, allows you to define a custom print setting for each sheet by choosing `<Variable Paper Size>`. Once this option is selected, the print tool reviews the sheets and tries to determine the best print option for that sheet based on its titleblock size.

![](../assets/tools/print-sheets/2019-11-07-08-59-23-print-sheets.png)

You can select any ranges of sheets and manually **Set Print Settings** on those sheets as well.

![](../assets/tools/print-sheets/2019-11-07-08-59-46-print-sheets.png)

The **Set Print Settings** window shows two groups of print settings that are available in the model

- **Matching Print Settings** are the onces with the matching sheet size and orientation to the sheet
- **All Print Settings** are all the available print settings in the model

![](../assets/tools/print-sheets/2019-11-07-08-59-55-print-sheets.png)

Select the appropriate print setting and the sheet list reflects the newly applied settings

![](../assets/tools/print-sheets/2019-11-07-09-00-08-print-sheets.png)

### Combining Sheets Into One File

The print tool allows you to combine multiple sheets into one file (`Ordered Sheet Set.pdf`). Under this option, many of the indexing and print settings are not available to the underlying printing mechanism in Autodesk Revit. For full flexibility, it is better to print the sheets individually and combine them later.

![](../assets/tools/print-sheets/2019-11-07-09-01-57-print-sheets.png)

## Starting Print

Once you are happy with the indices, printing configurations, and the output file names, click on the big Print button to start the print process.

![](../assets/tools/print-sheets/2019-11-07-09-07-33-print-sheets.png)

 The tool will ask you

- Whether you want to print the selected sheets (if any) or all the sheets listed in the tool

![](../assets/tools/print-sheets/2019-11-07-09-01-30-print-sheets.png)

- If you are sure about starting the print process if there are more than 5 sheets in the print queue

![](../assets/tools/print-sheets/2019-11-07-09-01-39-print-sheets.png)

- Whether to replace the files the print creates when they already exist in the output folder

## Other options

- A *Print Setting* type parameter (of type Text) on a titleblock family can hold the name of the print setting to use. With `<Variable Paper Size>`, the tool assigns that print setting to the sheets using this titleblock.
- Right-click a file name in the sheet list to copy the file names.
- When sheets of different models would get the same file name, add `{index}` to the naming format, or `{proj_number}` when the models have different project numbers.
- A combined PDF cannot be made when the paper size varies by sheet.
