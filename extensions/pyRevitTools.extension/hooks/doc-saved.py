##### Autosave
import time
from pyrevit import script
from pyrevit.userconfig import user_config

doc = __eventargs__.Document
try:
    title = doc.Title
except:
    sys.exit()

# Does not save detached, family, or unsaved documents
# TBD adding regex for shared template/resource folders or drives
is_project = not doc.IsDetached and not doc.IsFamilyDocument and len(doc.PathName) > 0

# Hash pathname to avoid overlap between two documents with the same name in different folders
if user_config.autosave.get_option("enabled") and is_project:
    with open(script.get_document_data_file(str(hash(doc.PathName)),"txt"), "w") as f:
        f.write(str(title) + "|" + str(time.time()))
##### Autosave