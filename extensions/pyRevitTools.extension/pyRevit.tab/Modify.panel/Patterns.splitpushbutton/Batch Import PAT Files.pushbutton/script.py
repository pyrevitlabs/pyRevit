"""Batch import AutoCAD PAT files into Revit model."""

import math
from collections import namedtuple

from pyrevit import framework
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()
output = script.get_output()


DEFAULT_UNIT = 'MM'
DEFAULT_TYPE = 'DRAFTING'
MM_SCALE = 0.00328084
INCH_SCALE = 1/12.0


# namedtuple for patter contents
PatDef = namedtuple('PatDef', ['name', 'comments',
                               'version', 'units', 'type',
                               'grids'])


def extract_patdefs(patfile):
    patdefs = []

    # globals are for any settings that come before pattern name
    # they're typically set one time per file before pattern defs
    global_version = ''
    global_units = ''
    global_type = ''

    # these are for the pattern that's been detected and
    # being currently extracted
    active_name = ''
    active_comments= ''
    active_version = ''
    active_units = ''
    active_type = ''
    active_grids = []
    print('Extracting patterns from {}'.format(patfile))
    with open(patfile, 'r') as patf:
        for patline in patf.readlines():
            logger.debug('processing line: {}'.format(patline))
            # skip if patline is a comment line
            if patline.startswith(';'):
                cleanedpatline = patline.replace('\n', '')

                # if there is a pattern being processed,
                # assing to the patten, otherwise global
                if '%VERSION' in cleanedpatline:
                    detected_version = cleanedpatline.split('=')[1]
                    if active_name:
                        active_version = detected_version
                    else:
                        global_version = detected_version
                elif '%UNITS' in cleanedpatline:
                    detected_units = cleanedpatline.split('=')[1].upper()
                    if active_name:
                        active_units = detected_units
                    else:
                        global_units = detected_units
                elif '%TYPE' in cleanedpatline:
                    detected_type = cleanedpatline.split('=')[1].upper()
                    if active_name:
                        active_type = detected_type
                    else:
                        global_type = detected_type
                else:
                    continue

            # start a new patstring if starts with *
            elif patline.startswith('*'):
                # save the active pattern and start a new
                if active_grids:
                    patdefs.append(
                        PatDef(
                            name=active_name,
                            comments=active_comments,
                            version=active_version or global_version,
                            units=active_units or global_units or DEFAULT_UNIT,
                            type=active_type or global_type or DEFAULT_TYPE,
                            grids=active_grids
                            )
                    )
                # grab name and comments of new pattern
                # effectively starting a new capture
                name_and_comment = \
                    patline.replace('\n', '')[1:].split(',')
                if len(name_and_comment) == 2:
                    active_name, active_comments = name_and_comment
                else:
                    active_name = name_and_comment[0]
                    active_comments = ''
                active_version = ''
                active_units = ''
                active_type = ''
                active_grids = []
                
            # treat as pattern grid if split by , has 5 or more elements
            elif len(patline.split(',')) >= 5:
                active_grids.append(patline)

    # make sure last pattern is also added
    if active_grids:
        patdefs.append(
            PatDef(
                name=active_name,
                comments=active_comments,
                version=active_version or global_version,
                units=active_units or global_units or DEFAULT_UNIT,
                type=active_type or global_type or DEFAULT_TYPE,
                grids=active_grids
                )
        )

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


def make_pattern(patdef):
    logger.debug(patdef)

    # make the grids
    fill_grids = []
    for pgrid in patdef.grids:
        pscale = MM_SCALE if patdef.units=='MM' else INCH_SCALE
        logger.debug('scale is set to: {}'.format(pscale))
        fgrid = make_fillgrid(pgrid, scale=pscale)
        if fgrid:
            fill_grids.append(fgrid)
    # determine pattern type
    fp_target = \
        DB.FillPatternTarget.Model if patdef.type=='MODEL' \
        else DB.FillPatternTarget.Drafting
    logger.debug('type is set to: {}'.format(fp_target))

    # check if fillpattern element exists
    existing_fpelement = \
        revit.query.get_fillpattern_element(patdef.name, fp_target)

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