"""Toggles visibility of section box in current 3D view"""

from rpw import DB, activeview, Action, Collector, SectionBox
from System.Collections.Generic import List


section_boxes = Collector(of_category=SectionBox,
                          is_type=False)

# worksets = DB.FilteredWorksetCollector(doc).OfKind(DB.WorksetKind.ViewWorkset)
sec_box = None
for sb in section_boxes:
    if sb.WorksetId == activeview.WorksetId:
        sec_box = sb

if sec_box:
    with Action('Toggle Section Box'):
        if sec_box.IsHidden(activeview):
            activeview.UnhideElements(List[DB.ElementId]([sec_box.unwrap().Id]))
        else:
            activeview.HideElements(List[DB.ElementId]([sec_box.unwrap().Id]))
