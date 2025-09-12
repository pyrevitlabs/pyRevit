# pylint: disable=E0401,W0613,C0103,C0111
# -*- coding: utf-8 -*-
import sys
from Autodesk.Revit.DB import Transaction, TransactionGroup
from pyrevit import revit, DB, script, forms
from pyrevit.framework import List

open_docs = forms.select_open_docs(title="Select Destination Documents")
if not open_docs:
    sys.exit(0)

legends = forms.select_views(
    title="Select Legend Views",
    filterfunc=lambda x: x.ViewType == DB.ViewType.Legend,
    use_selection=True,
)

if not legends:
    forms.alert("No Legend Views selected.")
    sys.exit(0)


class CopyUseDestination(DB.IDuplicateTypeNamesHandler):
    def OnDuplicateTypeNamesFound(self, args):
        return DB.DuplicateTypeAction.UseDestinationTypes


class LogMessage:
    def __init__(self):
        self.__messages = []

    def log_message_with_doc_and_legend(self, doc_title, legend_name, message):
        doc_title = "\n**** {} ****".format(
            doc_title,
        )
        legend_name = "\n** {} **".format(legend_name)
        if doc_title not in self.__messages:
            self.__messages.append(doc_title)
        # Add the legend name only if it is not already included in the current document's list
        if legend_name not in self.__messages[(self.__messages.index(doc_title)) :]:
            self.__messages.append(legend_name)
        self.__messages.append("- {}".format(message))

    def get_messages(self):
        return "\n" + "\n".join(self.__messages)

    def __len__(self):
        return len(self.__messages)


logger = script.get_logger()
logger_messages = LogMessage()

total_operations = len(legends) * len(open_docs)
current_operation = 0
skipped_docs = []

with forms.ProgressBar(cancellable=True) as pb:
    for dest_doc in open_docs:

        pb.title = "Processing Document: {}".format(dest_doc.Title)
        pb.update_progress(current_operation, total_operations)

        # get all legend names in destination
        all_graphviews = revit.query.get_all_views(doc=dest_doc)
        all_legend_names = [
            revit.query.get_name(x) for x in all_graphviews
            if x.ViewType == DB.ViewType.Legend
        ]

        # check for base legend to duplicate
        base_legend = revit.query.find_first_legend(doc=dest_doc)
        if not base_legend:
            forms.alert(
                "At least one Legend must exist in target document.\n"
                "Skipping document: {}".format(dest_doc.Title)
            )
            skipped_docs.append(dest_doc.Title)
            current_operation += len(legends)
            continue

        tg = TransactionGroup(dest_doc, "Copy Legends to document")
        tg.Start()

        for src_legend in legends:
            if pb.cancelled:
                tg.RollBack()
                forms.alert("Operation cancelled.")
                sys.exit(0)

            legend_name = revit.query.get_name(src_legend)
            pb.title = "Processing: {} > {}".format(dest_doc.Title, legend_name)

            view_elements = DB.FilteredElementCollector(
                revit.doc, src_legend.Id
            ).ToElements()
            elements_to_copy = []
            for el in view_elements:
                # ReferencePlanes  skipped because they are copied in the model space, not in the legend view
                is_element_reference_plane = isinstance(el, DB.ReferencePlane)
                if isinstance(el, DB.Element) and el.Category and not is_element_reference_plane:
                    elements_to_copy.append(el.Id)
                else:
                    logger_messages.log_message_with_doc_and_legend(
                        dest_doc.Title,
                        legend_name,
                        "Skipping element: {}".format(el.Id),
                    )

            if not elements_to_copy:
                logger_messages.log_message_with_doc_and_legend(
                    dest_doc.Title,
                    legend_name,
                    "Skipping empty view: {}".format(revit.query.get_name(src_legend)),
                )
                current_operation += 1
                pb.update_progress(current_operation, total_operations)
                continue

            t = Transaction(dest_doc, "Copy Legends to document")
            t.Start()
            dest_view = dest_doc.GetElement(
                base_legend.Duplicate(DB.ViewDuplicateOption.Duplicate)
            )

            options = DB.CopyPasteOptions()
            options.SetDuplicateTypeNamesHandler(CopyUseDestination())
            copied_elements = DB.ElementTransformUtils.CopyElements(
                src_legend,
                List[DB.ElementId](elements_to_copy),
                dest_view,
                None,
                options,
            )

            # copy element overrides
            for dest_id, src_id in zip(copied_elements, elements_to_copy):
                try:
                    dest_view.SetElementOverrides(
                        dest_id, src_legend.GetElementOverrides(src_id)
                    )
                except Exception as ex:
                    logger_messages.log_message_with_doc_and_legend(
                        dest_doc.Title,
                        legend_name,
                        "Error setting element overrides: {}\n{} in "
                        "{}".format(ex, src_id, dest_doc.Title),
                    )

            # set unique name
            src_name = revit.query.get_name(src_legend)
            new_name = src_name
            counter = 0

            while new_name in all_legend_names:
                counter += 1
                new_name = src_name + " (Duplicate %s)" % counter

            if counter > 0:
                logger_messages.log_message_with_doc_and_legend(
                    dest_doc.Title,
                    legend_name,
                    "Legend name already exists. Renaming to: {}".format(new_name),
                )

            revit.update.set_name(dest_view, new_name)
            dest_view.Scale = src_legend.Scale
            all_legend_names.append(new_name)

            t.Commit()

            current_operation += 1
            pb.update_progress(current_operation, total_operations)

        tg.Assimilate()


processed_docs = [doc for doc in open_docs if doc.Title not in skipped_docs]
if processed_docs:
    processed_docs_names = [doc.Title for doc in processed_docs]

    legend_count = len(legends)
    doc_count = len(processed_docs_names)
    legend_text = "legend" + ("s" if legend_count > 1 else "")

    main_instruction = "{} {} copied successfully to {} document{}".format(
        legend_count, legend_text, doc_count, "s" if doc_count > 1 else ""
    )

    details = []
    details.append("COPIED {}:".format(legend_text.upper()))
    for legend in legends:
        details.append("• {}".format(revit.query.get_name(legend)))

    details.append("\nTO DOCUMENT{}:".format("S" if doc_count > 1 else ""))
    for doc_name in processed_docs_names:
        details.append("• {}".format(doc_name))

    if skipped_docs:
        details.append("\nSKIPPED DOCUMENTS:")
        for doc_name in skipped_docs:
            details.append("• {} (no base legend found)".format(doc_name))

    content = "\n".join(details)
    forms.alert(msg=main_instruction, sub_msg=content)

    if len(logger_messages):
        logger.warning(logger_messages.get_messages())

else:
    forms.alert("Copy operation failed.")
