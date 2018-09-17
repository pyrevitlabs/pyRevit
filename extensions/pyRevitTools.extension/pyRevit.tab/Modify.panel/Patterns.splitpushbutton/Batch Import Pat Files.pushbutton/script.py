"""Batch import AutoCAD PAT files into Revit model."""

import math

from pyrevit.framework import List
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script

__author__ = "Ehsan Iran-Nejad"

logger = script.get_logger()
output = script.get_output()


def extract_patstrings(patfile):
    patstrings = []
    active_patstring = ''
    print('Extracting patterns from {}'.format(patfile))
    with open(patfile, 'r') as patf:
        for patline in patf.readlines():
            # skip if patline is a comment line
            if patline.startswith(';'):
                continue

            # start a new patstring if starts with *
            elif patline.startswith('*'):
                if active_patstring:
                    patstrings.append(active_patstring)
                active_patstring = patline
            
            # treat as pattern definition if 
            elif ',' in patline:
                active_patstring += patline

    # make sure last pattern is also added
    if active_patstring:
        patstrings.append(active_patstring)

    return patstrings


def make_fillgrid(gridstring, scale=0.00328084):
    rvt_fill_grid = DB.FillGrid()
    griddata = [float(x.strip()) for x in gridstring.split(',') if x]
    if griddata:
        rvt_fill_grid.Angle = math.radians(griddata[0])
        rvt_fill_grid.Origin = \
            DB.UV(griddata[1] * scale, griddata[2] * scale)
        rvt_fill_grid.Shift = griddata[3] * scale
        rvt_fill_grid.Offset = griddata[4] * scale
        if len(griddata) > 5:
            scaled_segments = [abs(x) * scale for x in griddata[5:]]
            rvt_fill_grid.SetSegments(scaled_segments)
        
        return rvt_fill_grid


def make_pattern(patstring):
    # grab the name
    datastrings = patstring.split('\n')
    patname = datastrings[0][1:].split(',')[0]
    fill_grids = []
    for dstring in  datastrings[1:]:
        fgrid = make_fillgrid(dstring)
        if fgrid:
            fill_grids.append(fgrid)
    fp_target = DB.FillPatternTarget.Drafting # .Model
    rvt_fill_pat = DB.FillPattern(patname,
                                  fp_target,
                                  DB.FillPatternHostOrientation.ToHost)

    rvt_fill_pat.SetFillGrids(List[DB.FillGrid](fill_grids))
    fill_pat_element = DB.FillPatternElement.Create(revit.doc, rvt_fill_pat)

    logger.debug('Fill Pattern:{}'.format(fill_pat_element.Name))
    fp = fill_pat_element.GetFillPattern()
    logger.debug('Fill Grids Count: {}'.format(len(fp.GetFillGrids())))
    for idx, fg in enumerate(fp.GetFillGrids()):
        logger.debug('FillGrid #{} '
                        'Origin:{} Angle:{} Shift:{} Offset:{} Segments:{}'
                        .format(idx, fg.Origin,
                                fg.Angle, fg.Shift,
                                fg.Offset, fg.GetSegments()))


def get_files():
    return forms.pick_file(file_ext='pat', multi_file=True)


patfiles = get_files()
if patfiles:
    with revit.Transaction("Batch import PAT files"):
        for patfile in patfiles:
            patstrings = extract_patstrings(patfile)
            for patstring in patstrings:
                make_pattern(patstring)
