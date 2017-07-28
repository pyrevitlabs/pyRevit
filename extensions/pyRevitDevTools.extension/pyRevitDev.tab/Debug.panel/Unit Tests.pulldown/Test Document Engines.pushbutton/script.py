doc = __revit__.ActiveUIDocument.Document

this_doc = doc.GetHashCode()

from System import AppDomain as ad
ad.CurrentDomain.GetData('pyRevitIpyEngines')
d = ad.CurrentDomain.GetData('pyRevitIpyEngines')

for doc_code in d.Keys:
    if doc_code == this_doc:
        print('{} - This doc'.format(doc_code))
    else:
        print(doc_code)
