from pyrevit import revit, HOST_APP

for model in __models__:
    doc = HOST_APP.app.OpenDocumentFile(model)
    with revit.Transaction("Create ThreeDView", doc=doc):
        revit.create.create_3d_view("ThreeDView", doc=doc)
    doc.Save()
