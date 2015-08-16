cl = FilteredElementCollector(doc)
list = cl.OfClass(FamilySymbol)

for f in list:
    print Element.Name.GetValue(f)