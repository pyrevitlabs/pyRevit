"""Batch import AutoCAD PAT files into Revit model."""

import math
from collections import namedtuple

from pyrevit import framework
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script

__author__ = "Ehsan Iran-Nejad"

logger = script.get_logger()
output = script.get_output()


MM_SCALE = 0.00328084
INCH_SCALE = 1/12.0

# namedtuple for patter contents
PatDef = namedtuple('PatDef', ['name', 'comments',
                               'version', 'units', 'type',
                               'grids'])


def extract_patdefs(patfile):
    patdefs = []
    active_name = ''
    active_comments= ''
    active_version = ''
    active_units = 'MM'
    active_type = 'DRAFTING'
    active_grids = []
    print('Extracting patterns from {}'.format(patfile))
    with open(patfile, 'r') as patf:
        for patline in patf.readlines():
            # skip if patline is a comment line
            if patline.startswith(';'):
                cleanedpatline = patline.replace('\n', '')
                if '%VERSION' in cleanedpatline:
                    active_version = cleanedpatline.split('=')[1]
                elif '%UNITS' in cleanedpatline:
                    active_units = cleanedpatline.split('=')[1].upper()
                elif '%TYPE' in cleanedpatline:
                    active_type = cleanedpatline.split('=')[1].upper()
                else:
                    continue

            # start a new patstring if starts with *
            elif patline.startswith('*'):
                if active_grids:
                    patdefs.append(
                        PatDef(name=active_name,
                               comments=active_comments,
                               version=active_version,
                               units=active_units,
                               type=active_type,
                               grids=active_grids)
                    )
                # grab name and comments of new pattern
                # effectively starting a new capture
                active_name, active_comments = \
                    patline.replace('\n', '')[1:].split(',')
                active_version = ''
                active_units = 'MM'
                active_type = 'DRAFTING'
                active_grids = []
                
            # treat as pattern grid if split by , has 5 or more elements
            elif len(patline.split(',')) >= 5:
                active_grids.append(patline)

    # make sure last pattern is also added
    if active_grids:
        patdefs.append(PatDef(name=active_name,
                              comments=active_comments,
                              version=active_version,
                              units=active_units,
                              type=active_type,
                              grids=active_grids))

    return patdefs


def make_fillgrid(gridstring, scale=0.00328084):
    logger.debug(gridstring, scale)
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


def get_existing_fillpatternelement(fpname, fptarget):
    existing_fillpatternelements = \
        DB.FilteredElementCollector(revit.doc)\
        .OfClass(framework.get_type(DB.FillPatternElement))

    for exfpe in existing_fillpatternelements:
        exfp = exfpe.GetFillPattern()
        if fpname == exfp.Name \
                and fptarget == exfp.Target:
            return exfpe


def make_pattern(patdef):
    logger.debug(patdef)

    # make the grids
    fill_grids = []
    for pgrid in patdef.grids:
        fgrid = make_fillgrid(pgrid,
                              scale=MM_SCALE if patdef.units=='MM'
                                    else INCH_SCALE)
        if fgrid:
            fill_grids.append(fgrid)
    # determine pattern type
    fp_target = \
        DB.FillPatternTarget.Model if patdef.type=='MODEL' \
        else DB.FillPatternTarget.Drafting

    # check if fillpattern element exists
    existing_fpelement = get_existing_fillpatternelement(patdef.name, fp_target)

    # make fillpattern
    rvt_fill_pat = DB.FillPattern(patdef.name,
                                fp_target,
                                DB.FillPatternHostOrientation.ToHost)
    rvt_fill_pat.SetFillGrids(framework.List[DB.FillGrid](fill_grids))

    if existing_fpelement:
        existing_fpelement.SetFillPattern(rvt_fill_pat)
        logger.debug('Updated FillPatternElement with id:{}'
                     .format(existing_fpelement.Id))
    else:
        # make pattern element
        logger.debug('Creating new fillpattern element...')
        fill_pat_element = DB.FillPatternElement.Create(revit.doc, rvt_fill_pat)

        # log results
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
            patdefs = extract_patdefs(patfile)
            for patdef in patdefs:
                print('Processing "{}" @ "{}" ({}, {})'
                      .format(patdef.name, patfile, patdef.units, patdef.type))
                make_pattern(patdef)
    print('Done...')