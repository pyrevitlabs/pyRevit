##### Autosave
import time, os
from pyrevit import forms
from pyrevit import script
from pyrevit.userconfig import user_config

doc = __eventargs__.Document
try:
    title = doc.Title
except:
    sys.exit()

savestatus_datafile = script.get_document_data_file(str(hash(doc.PathName)),"txt")

# Does not save detached, family, or unsaved documents
# TBD adding regex for shared template/resource folders or drives
is_project = not doc.IsDetached and not doc.IsFamilyDocument and len(doc.PathName) > 0

# Check if file exists before trying to read from
savefile_exists = os.path.exists(savestatus_datafile) and os.stat(savestatus_datafile).st_size > 0

def read():
    with open(savestatus_datafile, "r") as f:
        for line in f:
            x = line.split("|")
            return x

# Hash pathname to avoid overlap between two documents with the same name in different folders
if user_config.autosave.get_option("enabled") and is_project and savefile_exists:
    x = read()
    if str(title) == x[0] and time.time() - float(x[1]) >= user_config.autosave.get_option("interval"):
        try:
            with forms.ProgressBar(
                title="Autosaving...", indeterminate=True, cancellable=False
            ) as pb:
                pb.update_progress(1, 1)
                doc.Save()
        except:
            pass
##### Autosave