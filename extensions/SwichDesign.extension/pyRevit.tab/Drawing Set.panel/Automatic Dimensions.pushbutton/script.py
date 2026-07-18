# -*- coding: utf-8 -*-
"""Automatic dimension strings - exterior and interior.

FLOW: optionally select walls (plus fixtures/casework for interior mode),
click the button, choose Exterior or Interior in one dialog (with Dry-run
and R.O. toggles), done. Nothing selected = auto-detect all exterior
walls and dimension the whole building perimeter.

EXTERIOR (3 tiers per straight side, outside auto-detected from
Wall.Orientation):
  1 (closest):  wall jogs + openings (centerline, or R.O. sides)
  2:            wall jogs only
  3 (outermost): overall side

INTERIOR - three levels of measuring, every one of them bounded by the
room's own boundary polygon (Room.GetBoundarySegments), so a string can
only reference the walls that actually bound that room and can never
cross one:
  1: room lengths, east-west and north-south, each placed a quarter of
     the room's depth off a parallel wall (the least obstructed of the
     two quarter lines)
  2: openings - one string per room wall that hosts them, inside the
     room, measured to the wall's cut faces (jambs) so it can be laid
     out on site
  3: fixtures, casework and columns - to the object's CENTRE, to the
     nearest bounding wall (columns get both axes)

ANGLED BUILDINGS: nothing here works in world X/Y. Walls are clustered by
direction (modulo 90 deg, length-weighted) into FRAMES, and every point is
rotated into its frame at the I/O boundary - so an angled wing is simply a
second frame, and the tier/room/span math runs inside it unchanged. A
dimension always measures ALONG its line, so a rotated wall dimensioned
against a world axis returns the cosine-shortened projection - a wrong
NUMBER, not merely a badly placed one. An orthogonal building yields one
frame at 0 deg, which is the exact identity transform.

ENGINE: IronPython (pyRevit default - NO python3 shebang; CPython engine
is broken in this environment, PROJECT_BRIEF.md sections 13-16).
"""
import json
import os

from pyrevit import revit, forms, script
from Autodesk.Revit.DB import Wall, FamilyInstance

from autodimswichdesign import geometry, standards, revit_io
from autodimswichdesign.standards import format_ft_in

doc = revit.doc

MODE_EXT = "exterior"
MODE_INT = "interior"

AUTO_OFFSET_LABEL = "Auto (by view scale)"

XAML = os.path.join(os.path.dirname(__file__), "AutoDimWindow.xaml")

# ------------------------------------------------------ tool settings
#
# Our OWN settings file, deliberately NOT pyRevit's script.get_config()/
# save_config(). Those store into pyRevit_config.ini, whose location is
# decided by WHERE pyRevit is installed (a Program Files install forces
# the shared ProgramData file, no per-user fallback) - and when that ini
# is corrupt or read-only, pyRevit falls back to an in-memory config and
# every save is SILENTLY skipped (live-diagnosed on the user's Revit
# machine: null-byte ini -> "menu does not save previous selection";
# traced in pyRevit 6.5.3 userconfig.py, PROJECT_BRIEF session 42).
# One json file per user under %APPDATA% is immune to all of it.

SETTINGS_DIR = os.path.join(
    os.getenv("APPDATA") or os.path.expanduser("~"), "SwichDesign")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "autodim_settings.json")

SETTING_KEYS = ("mode", "measure_core", "openings_ro", "dry_run",
                "face_audit", "first_offset_text", "tier_spacing_text",
                "max_drag_text")


class ToolSettings(object):
    """Per-user settings in autodim_settings.json. Same get_option/
    set_option interface the dialog used with pyRevit's config.
    Self-healing: a missing or unparseable file simply means defaults -
    it can never disable saving the way a corrupt pyRevit ini does."""

    def __init__(self):
        self.values = {}
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self.values = data
        except Exception:
            self.values = {}
        if not self.values:
            self._migrate_from_pyrevit()

    def _migrate_from_pyrevit(self):
        """One-time pickup of settings saved by older versions through
        script.get_config(), so nobody loses their choices. Best-effort:
        a broken pyRevit config just yields defaults."""
        try:
            cfg = script.get_config()
            for key in SETTING_KEYS:
                val = cfg.get_option(key, None)
                if val is not None:
                    self.values[key] = val
        except Exception:
            pass

    def get_option(self, key, default=None):
        return self.values.get(key, default)

    def set_option(self, key, value):
        self.values[key] = value

    def save(self):
        """Write the file; returns an error string instead of raising
        (a failed settings save must never kill a dimension run). The
        write goes to a temp file first so an interrupted write cannot
        leave a half-written settings file - which is exactly how the
        user's pyRevit ini most likely got corrupted."""
        try:
            if not os.path.isdir(SETTINGS_DIR):
                os.makedirs(SETTINGS_DIR)
            tmp = SETTINGS_FILE + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self.values, f, indent=1, sort_keys=True)
            if os.path.exists(SETTINGS_FILE):
                os.remove(SETTINGS_FILE)
            os.rename(tmp, SETTINGS_FILE)
            return None
        except Exception as ex:
            return str(ex)


def pyrevit_config_broken():
    """True when pyRevit itself is running on an in-memory config (its
    ini is corrupt/unreadable) - OUR settings still save fine, but the
    user's pyRevit-wide settings will not, and they should know."""
    try:
        from pyrevit.userconfig import user_config
        return not user_config.config_file
    except Exception:
        return False


class AutoDimWindow(forms.WPFWindow):
    """The Automatic Dimensions dialog. Every choice is remembered
    between runs via the tool's OWN settings file (ToolSettings), so a
    broken/relocated pyRevit config cannot make the menu forget."""

    def __init__(self, wall_count, fixture_count):
        forms.WPFWindow.__init__(self, XAML)
        self.result = None
        self.wall_count = wall_count
        self.config = ToolSettings()

        mode = self.config.get_option("mode", MODE_INT)
        self.mode_ext_rb.IsChecked = (mode == MODE_EXT)
        self.mode_int_rb.IsChecked = (mode != MODE_EXT)

        core = bool(self.config.get_option("measure_core", False))
        self.face_core_rb.IsChecked = core
        self.face_finish_rb.IsChecked = not core

        ro = bool(self.config.get_option("openings_ro", False))
        self.open_ro_rb.IsChecked = ro
        self.open_cl_rb.IsChecked = not ro

        self.dry_cb.IsChecked = bool(self.config.get_option("dry_run", True))
        self.audit_cb.IsChecked = bool(
            self.config.get_option("face_audit", False))

        # exterior offsets: editable combos, raw text persisted so the
        # user sees exactly what they typed on the next run. Items are
        # set from code (plain strings) - ComboBoxItem elements in XAML
        # would turn .Text into "System.Windows.Controls.ComboBoxItem:...".
        self.first_offset_cb.ItemsSource = [
            AUTO_OFFSET_LABEL, '1/2"', '5/8"', '3/4"', '1"', '1 1/4"',
            '1 1/2"']
        self.first_offset_cb.Text = str(self.config.get_option(
            "first_offset_text", AUTO_OFFSET_LABEL))
        self.spacing_cb.ItemsSource = ['1/4"', '3/8"', '1/2"']
        self.spacing_cb.Text = str(self.config.get_option(
            "tier_spacing_text", '3/8"'))
        self.split_tb.Text = str(self.config.get_option(
            "max_drag_text", "0"))

        status = "{0} wall(s), {1} element(s) selected.".format(
            wall_count, fixture_count)
        if pyrevit_config_broken():
            status += ("  NOTE: pyRevit's own config file is unreadable "
                       "on this machine - this tool saves its settings "
                       "separately and is unaffected, but pyRevit-wide "
                       "settings will not persist until it is repaired.")
        self.status_tb.Text = status
        self._update_hint()

    def _update_hint(self):
        if self.mode_ext_rb.IsChecked:
            if self.wall_count:
                self.mode_hint_tb.Text = (
                    "Dimensions the {0} wall(s) you selected, one string set "
                    "per facing direction.".format(self.wall_count))
            else:
                self.mode_hint_tb.Text = (
                    "Select the perimeter walls first - exterior mode "
                    "dimensions your selection.")
        else:
            self.mode_hint_tb.Text = (
                "Whole view, driven by placed Rooms. Selection is ignored.")

    def mode_changed(self, sender, args):
        # fires during XAML load too, before the hint element exists
        if getattr(self, "mode_hint_tb", None) is not None:
            self._update_hint()

    def dimension_clicked(self, sender, args):
        # editable combos: read .Text (SelectedItem is null for typed
        # values). Unparseable first offset -> auto; unparseable spacing
        # -> default; both clamped to a 1/4" floor so a typo cannot put
        # a string inside the wall poche.
        first_text = self.first_offset_cb.Text
        spacing_text = self.spacing_cb.Text
        split_text = self.split_tb.Text

        first_in = standards.parse_paper_inches(first_text)
        if first_in is not None and first_in < 0.25:
            first_in = 0.25
        spacing_in = standards.parse_paper_inches(spacing_text)
        if spacing_in is None:
            spacing_in = standards.TIER_SPACING_DEFAULT_IN
        elif spacing_in < 0.25:
            spacing_in = 0.25
        try:
            max_drag_ft = float(str(split_text).strip())
        except ValueError:
            max_drag_ft = 0.0
        if max_drag_ft < 0.0:
            max_drag_ft = 0.0

        self.result = {
            "mode": MODE_EXT if self.mode_ext_rb.IsChecked else MODE_INT,
            "measure_core": bool(self.face_core_rb.IsChecked),
            "openings_ro": bool(self.open_ro_rb.IsChecked),
            "dry_run": bool(self.dry_cb.IsChecked),
            "face_audit": bool(self.audit_cb.IsChecked),
            "first_offset_in": first_in,   # None = auto per view scale
            "tier_spacing_in": spacing_in,
            "max_drag_ft": max_drag_ft,
        }
        for key in ("mode", "measure_core", "openings_ro", "dry_run",
                    "face_audit"):
            self.config.set_option(key, self.result[key])
        self.config.set_option("first_offset_text", first_text)
        self.config.set_option("tier_spacing_text", spacing_text)
        self.config.set_option("max_drag_text", split_text)
        save_err = self.config.save()
        if save_err:
            # settings failing to save must never block dimensioning -
            # main() surfaces this in the run notes
            self.result["settings_warning"] = (
                "Settings could not be saved ({0}) - this run works, "
                "but choices will not be remembered.".format(save_err))
        self.Close()

    def cancel_clicked(self, sender, args):
        self.result = None
        self.Close()


# ---------------------------------------------------------------- gather

def gather_selection(view):
    """Returns (walls, fixtures, skipped_walls). Fixtures are selected
    standalone FamilyInstances (not wall-hosted - hosted ones are
    openings and arrive via their host wall).

    Selected walls pass the SAME view-level filter as auto-collection:
    a crossing selection easily grabs below-level walls, and unfiltered
    they hijacked references (live: 'wall below was still selected and
    used' - the selection path bypassed the filter entirely).

    There is NO Function=Exterior auto-detection anymore (user rule:
    wall Function data cannot be trusted - same types get used both
    ways, or nobody sets it). Exterior mode = manual selection;
    interior mode = catch-all from the view's Rooms and walls."""
    belongs = revit_io.make_view_wall_filter(doc, view)
    walls = []
    skipped = 0
    fixtures = []
    for el in revit.get_selection().elements:
        if isinstance(el, Wall):
            if belongs(el):
                walls.append(el)
            else:
                skipped += 1
        elif isinstance(el, FamilyInstance):
            host = getattr(el, "Host", None)
            if host is None or not isinstance(host, Wall):
                if getattr(el.Location, "Point", None) is not None:
                    fixtures.append(el)
    return walls, fixtures, skipped


def build_runs(walls, notes, frame):
    """Walls -> list of run dicts, in FRAME-LOCAL coordinates.

    Every point that enters the geometry pipeline is rotated into the
    frame here, at the boundary. Inside the pipeline an angled wing looks
    exactly like an orthogonal building, so build_tiers/split_runs need no
    changes at all - and with Frame(0) an orthogonal model is untouched."""
    segments = []
    seg_walls = []
    openings_by_wall = {}
    for wall in walls:
        try:
            p0, p1 = revit_io.get_wall_endpoints(wall)
        except ValueError as ex:
            notes.append("Skipped: {0}".format(ex))
            continue
        segments.append((frame.to_local(p0), frame.to_local(p1)))
        seg_walls.append(wall)
        pairs = []
        for inst in revit_io.get_hosted_openings(wall, doc):
            try:
                pairs.append(
                    (frame.to_local(revit_io.get_opening_point(inst)), inst))
            except ValueError as ex:
                notes.append("Skipped opening: {0}".format(ex))
        openings_by_wall[wall.Id] = pairs

    runs = []
    for pts, idxs, closed in geometry.order_segments(segments):
        try:
            parts = geometry.split_runs(pts, idxs, closed)
        except geometry.GeometryError as ex:
            notes.append("Skipped a wall group: {0}".format(ex))
            continue
        for run_pts, run_idxs in parts:
            run_walls = []
            for i in run_idxs:
                if i is None:
                    continue  # gap-bridged connector, no source wall
                if seg_walls[i] not in run_walls:
                    run_walls.append(seg_walls[i])
            run_openings = []
            for w in run_walls:
                run_openings.extend(openings_by_wall.get(w.Id, []))
            try:
                tiers = geometry.build_tiers(
                    run_pts, [pt for pt, _ in run_openings])
            except geometry.GeometryError as ex:
                notes.append("Skipped one side: {0}".format(ex))
                continue
            runs.append({"pts": run_pts, "walls": run_walls,
                         "openings": run_openings, "tiers": tiers})
    return runs


# ------------------------------------------------- entries (value+kind)

def opening_entries(run, ro_mode, notes, frame):
    """[(value, kind, payload)] for the run's openings.
    kind 'open_c' payload=instance; 'open_side' payload=Reference;
    'jamb' payload=face record (host-wall cut face, no core swap).

    R.O. resolution order (USER RULING: the wall's cut opening IS the
    R.O. - jamb faces first; they are also the same reference species
    as the room-line faces that demonstrably survive placement, while
    family references are suspected of being silently deleted by
    Revit's commit-time failure resolution):
      1. the HOST WALL's jamb faces created by the opening cut,
      2. family Left/Right references,
      3. centerline, with a note."""
    axis = run["tiers"]["axis"]
    idx = 0 if axis == "x" else 1
    entries = []
    for pt, inst in run["openings"]:
        center = pt[idx]
        if ro_mode:
            width = revit_io.get_opening_width(inst)
            jambs = revit_io.get_jamb_faces(inst, axis, center, width, frame)
            if jambs is not None:
                entries.append(
                    (jambs[0]["origin"][idx], "jamb", jambs[0]))
                entries.append(
                    (jambs[1]["origin"][idx], "jamb", jambs[1]))
                continue
            sides = revit_io.get_opening_side_references(inst)
            if sides is not None:
                half = (width / 2.0) if width else 0.5
                entries.append((center - half, "open_side", sides[0]))
                entries.append((center + half, "open_side", sides[1]))
                continue
            notes.append(
                "Opening {0}: no jamb faces and no Left/Right "
                "references - using centerline".format(inst.Id))
        entries.append((center, "open_c", inst))
    return entries


def wallpoint_entries(run, values):
    """[(value, 'wallpt', pt)] mapping tier values back to run points."""
    axis = run["tiers"]["axis"]
    idx = 0 if axis == "x" else 1
    entries = []
    for v in values:
        for p in run["pts"]:
            if abs(p[idx] - v) <= geometry.TIER_MERGE_TOL_FT:
                entries.append((v, "wallpt", p))
                break
    return entries


def dedupe_entries(entries):
    """Drop entries within tolerance of an earlier one (list order =
    anchor priority, so put preferred kinds first), then sort the
    survivors by value."""
    kept = []
    for e in entries:
        if all(abs(e[0] - o[0]) > geometry.TIER_MERGE_TOL_FT for o in kept):
            kept.append(e)
    return sorted(kept, key=lambda x: x[0])


def resolve_entries(entries, axis, axis_faces, run, notes,
                    measure_core=False, view=None, core_cache=None,
                    prefer_exterior=True, face_audit=False, frame=None):
    """Entries -> (references, kept_values). measure_core swaps wall
    finish-face references for the CORE boundary on the same side
    ("face of stud"), using per-wall MEASURED calibration - the fixed
    index table proved wrong on live walls (witness lines landed on
    random layers)."""
    refs = []
    kept = []
    for value, kind, payload in entries:
        ref = None
        if kind in ("jamb", "vwall"):
            # view-aware host-wall face (opening jamb or wall end):
            # already a visible reference, never core-swapped
            ref = payload["ref"]
        elif kind == "face":
            # scan-line entries carry their face record directly
            ref = payload["ref"]
            if measure_core and view is not None:
                core_ref = revit_io.core_face_reference(
                    payload, view, doc,
                    core_cache if core_cache is not None else {}, notes, frame)
                if core_ref is not None:
                    ref = core_ref
        elif kind == "open_side":
            ref = payload
        elif kind == "open_c":
            try:
                ref = revit_io.get_opening_centerline_reference(payload)
            except ValueError as ex:
                notes.append(str(ex))
        elif kind == "cross":
            ref = revit_io.get_wall_centerline_reference(payload)
            if ref is None:
                notes.append(
                    "Partition {0}: no centerline reference - skipped"
                    .format(payload.Id))
        elif kind == "fixture":
            ref = revit_io.get_instance_center_reference(payload, axis, frame)
            if ref is None:
                notes.append(
                    "Fixture {0}: no center reference - skipped"
                    .format(payload.Id))
        elif kind == "wallpt":
            face_info = revit_io.find_face_reference(
                axis_faces, payload, prefer_exterior)
            if face_info is not None:
                # snap out to the wall's true finish face: the solid can
                # show two faces on one side a fraction of an inch apart,
                # and scoring by distance-to-target lands on the inner one
                # (live audit: 0.3" inside the finish). Same wall, same
                # side - this only ever moves the anchor outward.
                face_info = revit_io.outermost_same_face(
                    axis_faces, face_info, axis)
            if face_audit:
                idx = 0 if axis == "x" else 1
                lines = []
                for c in revit_io.face_candidates(axis_faces, payload):
                    chosen = (face_info is not None
                              and c["origin"] == face_info["origin"]
                              and c["wall_id"] == face_info["wall"].Id)
                    lines.append(
                        "{0} wall {1} @ {2} | {3} side | {4:.3f} ft from "
                        "target".format(
                            "-->" if chosen else "   ",
                            c["wall_id"], format_ft_in(c["origin"][idx]),
                            "outer" if c["exterior"] else "inner",
                            c["plane_d"]))
                notes.append(
                    "FACE AUDIT at ({0:.2f}, {1:.2f}) [{2}]:\n  {3}".format(
                        payload[0], payload[1], axis.upper(),
                        "\n  ".join(lines) or "no candidate faces"))
            if face_info is not None:
                ref = face_info["ref"]
                if measure_core and view is not None:
                    core_ref = revit_io.core_face_reference(
                        face_info, view, doc,
                        core_cache if core_cache is not None else {},
                        notes, frame)
                    if core_ref is not None:
                        ref = core_ref
            if ref is None and run is not None:
                for w in run["walls"]:
                    ref = revit_io.get_centerline_end_reference(w, payload)
                    if ref is not None:
                        notes.append(
                            "No face at ({0:.1f}, {1:.1f}) - used wall "
                            "end point".format(payload[0], payload[1]))
                        break
            if ref is None:
                notes.append(
                    "No reference at ({0:.1f}, {1:.1f}) - skipped"
                    .format(payload[0], payload[1]))
        if ref is not None:
            refs.append(ref)
            kept.append(value)
    return refs, kept


# ------------------------------------- direction grouping (exterior)

def orientation_side(run, frame):
    """+1/-1: which perpendicular side the run's exterior faces, from
    the average Wall.Orientation of its walls, measured in the frame."""
    axis = run["tiers"]["axis"]
    total = 0.0
    for w in run["walls"]:
        orientation = getattr(w, "Orientation", None)
        if orientation is not None:
            local = frame.to_local((orientation.X, orientation.Y))
            total += local[1] if axis == "x" else local[0]
    return 1.0 if total >= 0 else -1.0


def group_label(axis, side):
    """Compass name, assuming project +Y is north (report label only)."""
    if axis == "x":
        return "North" if side > 0 else "South"
    return "East" if side > 0 else "West"


def _merge_vals(values):
    out = []
    for v in sorted(values):
        if not out or abs(v - out[-1]) > geometry.TIER_MERGE_TOL_FT:
            out.append(v)
    return out


def _merge_group(group, axis, side, label):
    """Union tier1/tier2 across the group's runs; tier3 (overall) spans
    the FULL extent of the direction - min to max across every run -
    per explicit user rule: the outermost string measures the TOTAL
    building length including jog extensions (and _drop_duplicate_tiers
    removes it when there is no jog, so it only appears when it adds
    information)."""
    pts = []
    walls = []
    openings = []
    t1 = []
    t2 = []
    t3_vals = []
    for r in group:
        pts.extend(r["pts"])
        for w in r["walls"]:
            if w not in walls:
                walls.append(w)
        openings.extend(r["openings"])
        t1.extend(r["tiers"]["tier1"])
        t2.extend(r["tiers"]["tier2"])
        t3_vals.extend(r["tiers"]["tier3"])
    t3 = [min(t3_vals), max(t3_vals)]
    return {
        "pts": pts,
        "walls": walls,
        "openings": openings,
        "tiers": {"axis": axis,
                  "tier1": _merge_vals(t1),
                  "tier2": _merge_vals(t2),
                  "tier3": t3},
        "side": side,
        "label": label,
    }


def group_exterior_runs(runs, frame, segments_local, max_drag_ft=0.0):
    """Merge the runs facing one direction (axis + outside side) into
    string sets - ONE per CLUSTER of runs whose witness lines can reach
    a shared line without crossing a selected wall.

    Single mass: one cluster per direction = the v3.4 image-confirmed
    convention (the west string carries main-wall corners AND
    bump-attachment jogs; a bump's width reads in the north/south
    string with long witness lines). Large plan with several masses:
    a far run whose witness lines would have to pass THROUGH another
    selected wall gets its own cluster, placed at its own extreme on
    its own correct side (live report: one global string per direction
    dragged witness lines across the plan into "a mess of crossed
    lines"). segments_local are this frame's SELECTED wall segments in
    frame coordinates - only selected walls can block a merge.
    max_drag_ft > 0 adds the optional distance rule: a run farther than
    this behind a cluster's base splits off even without a crossing."""
    buckets = {}
    for r in runs:
        key = (r["tiers"]["axis"], orientation_side(r, frame))
        buckets.setdefault(key, []).append(r)

    merged = []
    for key in sorted(buckets.keys()):
        axis, side = key
        group = buckets[key]
        pidx = 1 if axis == "x" else 0
        records = []
        for r in group:
            perp_vals = [p[pidx] for p in r["pts"]]
            extreme = max(perp_vals) if side > 0 else min(perp_vals)
            records.append((extreme, r["tiers"]["tier1"]))
        clusters = geometry.cluster_exterior_runs(
            records, segments_local, axis, side, max_drag_ft)
        for c_no in range(len(clusters)):
            c_runs = [group[i] for i in clusters[c_no]]
            name = group_label(axis, side)
            if c_no:
                name = "{0} {1}".format(name, c_no + 1)
            label = "{0} ({1} run(s))".format(name, len(c_runs))
            merged.append(_merge_group(c_runs, axis, side, label))
    return merged


# ------------------------------------------------------------ placement

def run_side_and_base(run, fixtures_assigned, frame):
    """(side, base) for exterior placement: direction groups carry
    their side; Wall.Orientation is the fallback. (Interior placement
    is scan-line based and never calls this.)"""
    axis = run["tiers"]["axis"]
    pidx = 1 if axis == "x" else 0
    perp_vals = [p[pidx] for p in run["pts"]]

    if run.get("side") is not None:
        side = run["side"]
    else:
        side = orientation_side(run, frame)

    base = max(perp_vals) if side > 0 else min(perp_vals)
    return side, base


def _drop_duplicate_tiers(plan):
    """Remove tiers whose values duplicate an earlier tier - a jog-free
    run otherwise stacks identical strings (live-observed: doubled
    overall dimension)."""
    kept = []
    seen = []
    for label, entries in plan:
        sig = tuple(int(round(e[0] * 20)) for e in entries)  # ~0.05 ft
        if sig in seen:
            continue
        seen.append(sig)
        kept.append((label, entries))
    return kept


def build_tier_plan(run, ro_mode, notes, frame):
    """Exterior 3-tier plan: list of (label, entries), innermost first.
    (Interior no longer uses per-run plans - see run_interior.)"""
    tiers = run["tiers"]
    t1 = dedupe_entries(
        opening_entries(run, ro_mode, notes, frame)
        + wallpoint_entries(run, tiers["tier1"]))
    t2 = dedupe_entries(wallpoint_entries(run, tiers["tier2"]))
    t3 = dedupe_entries(wallpoint_entries(run, tiers["tier3"]))
    return _drop_duplicate_tiers(
        [("jogs+openings", t1), ("jogs", t2), ("overall", t3)])


def place_run(view, run, plan, all_walls, face_cache, fixtures, notes,
              measure_core=False, core_cache=None, face_audit=False,
              frame=None, first_offset_in=None, spacing_in=None):
    if frame is None:
        frame = geometry.Frame(0.0)
    axis = run["tiers"]["axis"]
    if axis not in face_cache:
        face_cache[axis] = revit_io.collect_axis_faces(
            all_walls, axis, None, frame)
    axis_faces = face_cache[axis]

    side, base = run_side_and_base(run, fixtures, frame)

    # base is a location-line extreme; the visible finish face can sit
    # up to a full wall thickness beyond it (depends on each wall's
    # Location Line setting), which ate most of the small first-tier
    # offset. Snap outward to the measured face - never inward.
    raw_base = base
    base = geometry.snap_base_outward(
        base, side,
        revit_io.exterior_face_perps(run["walls"], axis, frame))
    if abs(base - raw_base) > 0.01:
        notes.append(
            "{0}: base snapped {1:.2f} ft outward, location line -> "
            "outermost finish face.".format(
                run.get("label") or "Run", (base - raw_base) * side))

    # paper inches -> model feet. None = the per-scale Auto preset, so
    # one saved setting works across sheets at different scales.
    if first_offset_in is None:
        first_offset_in = standards.first_offset_for_scale(view.Scale)
    if spacing_in is None:
        spacing_in = standards.TIER_SPACING_DEFAULT_IN
    first = first_offset_in * standards.INCH * view.Scale
    step = spacing_in * standards.INCH * view.Scale
    positions = geometry.tier_positions(base, side, first, step, len(plan))

    origin = getattr(view, "Origin", None)
    base_z = origin.Z if origin is not None else 0.0

    placed = 0
    tier_no = 0
    for label, entries in plan:
        # increments even when a tier is skipped - tier identity (and
        # therefore each string's line position) stays deterministic
        tier_no += 1
        refs, kept = resolve_entries(entries, axis, axis_faces, run, notes,
                                     measure_core, view, core_cache,
                                     True, face_audit, frame)
        if len(refs) < 2:
            notes.append("Tier '{0}': fewer than 2 references - skipped"
                         .format(label))
            continue
        revit_io.create_dimension_tier(
            doc, view, refs, axis, (kept[0], kept[-1]),
            positions[tier_no - 1], base_z, frame)
        placed += 1
    return placed


# ---------------------------------------- interior: per-room strings

# Every interior string is bounded by the room's own boundary polygon
# (revit_io.get_room_polygon -> geometry.polygon_span_at). A string can
# only ever reference the two walls the room's boundary actually crosses
# at that line, so "never go through a wall" is structural, not a
# heuristic. The previous build let strings continue past walls and pick
# up whatever wall face was nearest - that is what produced measurements
# to random walls across the plan.

MIN_ROOM_FT = 2.5        # a room thinner than this gets no string
OBSTRUCTION_CLEAR_FT = 1.5   # object counts as "on" a line within this
LINE_CLEAR_FT = 1.0      # two strings closer than this overlap


def room_inward(poly, edge_mid, axis_perp_idx, edge_perp):
    """+1/-1: which side of a boundary edge the room interior is on.
    Decided by testing a point a few inches off the edge against the
    polygon itself - exact for any room shape, unlike a centroid guess
    (an L-shaped room's centroid can fall outside the room)."""
    for sign in (1.0, -1.0):
        probe = list(edge_mid)
        probe[axis_perp_idx] = edge_perp + sign * 0.25
        if geometry.point_in_polygon((probe[0], probe[1]), poly):
            return sign
    return 1.0


def edge_face_entry(room, edge, axis, value, inward, view_faces, notes):
    """(value, 'face', face_record) for one end of a room span.

    Fast path: the wall named by the boundary segment. Fallback: any
    view-visible wall face on the same plane facing into the room -
    BoundarySegment.ElementId comes back null for walls that protrude
    into a room (Building Coder #1046), and room-separation lines have no
    wall at all. Entry kind is 'face', so the core/finish switch applies."""
    wall_id = room["wall_ids"][edge] if edge < len(room["wall_ids"]) else None
    faces = view_faces[axis]
    rec = None
    if wall_id is not None:
        rec = revit_io.face_at(faces, axis, value, inward, wall_id)
    if rec is None:
        rec = revit_io.face_at(faces, axis, value, inward)
        if rec is not None and wall_id is not None:
            notes.append(
                "{0}: boundary wall {1} exposed no face at {2} - used the "
                "coincident face instead".format(
                    room["name"], wall_id, format_ft_in(value)))
    if rec is None:
        notes.append(
            "{0}: no view-visible wall face at {1} ({2} axis) - that end "
            "of the string is missing (room-separation line?)".format(
                room["name"], format_ft_in(value), axis.upper()))
        return None
    return (rec["origin"][0 if axis == "x" else 1], "face", rec)


def span_entries(room, span, axis, view_faces, notes):
    """Both ends of a room span as 'face' entries. The low end's wall
    faces +axis into the room, the high end's faces -axis."""
    entries = []
    for (value, edge), inward in ((span[0], 1.0), (span[1], -1.0)):
        entry = edge_face_entry(room, edge, axis, value, inward,
                                view_faces, notes)
        if entry is not None:
            entries.append(entry)
    return entries


def obstruction_cost(axis, perp, objects, occupied):
    """How cluttered a candidate dimension line is: objects sitting on it
    plus strings already placed there. Picks the least-obstructed quarter
    line (user rule: room length sits a quarter off a parallel wall)."""
    pidx = 1 if axis == "x" else 0
    cost = 0
    for obj in objects:
        if abs(obj["pt"][pidx] - perp) <= OBSTRUCTION_CLEAR_FT:
            cost += 1
    for pos in occupied[axis]:
        if abs(pos - perp) <= LINE_CLEAR_FT:
            cost += 1
    return cost


def nudge(axis, pos, occupied, step, away, bounds=None):
    """Move a string off any line already occupied, stepping in the `away`
    direction (which must point INTO the room), then claim its position.

    bounds (lo, hi) is the room's extent along the direction being nudged;
    a nudge is never allowed to push the dimension line out of the room,
    so a crowded small room ends up with two lines close together rather
    than one line outside the wall."""
    limit_lo = bounds[0] + 0.25 if bounds else None
    limit_hi = bounds[1] - 0.25 if bounds else None
    tries = 0
    while (any(abs(p - pos) < LINE_CLEAR_FT for p in occupied[axis])
           and tries < 4):
        moved = pos + away * max(step, 0.5)
        if limit_lo is not None and not (limit_lo <= moved <= limit_hi):
            break
        pos = moved
        tries += 1
    occupied[axis].append(pos)
    return pos


def drop_redundant(items, room_name, notes):
    """Within one room, keep ONE dimension per distinct measurement.

    Two strings on the same axis whose reference values are the same, to
    ~1/8", ARE the same dimension - drawing both is pure cleanup work.
    Live example: six stacked casework shelves in the W.I.C. each produced
    the identical 8'-0.3" -> 9'-10.3" dimension, because they share an X
    position; one line locates all six.

    Deliberate consequence, worth knowing: two separate fixtures that
    happen to sit the same distance from the same wall collapse to one
    dimension. That is the same number in the same place on the sheet, so
    it reads correctly - but it means the second fixture is located by the
    first one's line rather than its own."""
    kept = []
    seen = set()
    dropped = 0
    for item in items:
        signature = (item["axis"],
                     tuple(int(round(value * 100.0))
                           for value, _, _ in item["entries"]))
        if signature in seen:
            dropped += 1
            continue
        seen.add(signature)
        kept.append(item)
    if dropped:
        notes.append(
            "{0}: {1} redundant dimension(s) dropped (same measurement "
            "already drawn).".format(room_name, dropped))
    return kept


# ---- level 1: room lengths (east-west and north-south) ----

def room_length_items(room, view_faces, objects, occupied, notes):
    """One string per axis measuring the room clear across, placed at a
    quarter of the room's depth off a parallel wall - whichever of the two
    quarter lines is least obstructed. Both axes landing on the room CENTRE
    (and therefore crossing each other) was the reported bug."""
    poly = room["poly"]
    items = []
    for axis in ("x", "y"):
        best = None
        for perp in geometry.quarter_lines(poly, axis):
            span = geometry.polygon_span_at(poly, axis, perp)
            if span is None:
                continue  # quarter line misses the room (L-shaped leg)
            if (span[1][0] - span[0][0]) < MIN_ROOM_FT:
                continue
            cost = obstruction_cost(axis, perp, objects, occupied)
            if best is None or cost < best[0]:
                best = (cost, perp, span)
        if best is None:
            notes.append("{0} [{1}]: no usable quarter line - skipped"
                         .format(room["name"], axis.upper()))
            continue
        _, perp, span = best
        entries = dedupe_entries(span_entries(room, span, axis,
                                              view_faces, notes))
        if len(entries) < 2:
            continue
        occupied[axis].append(perp)
        items.append({"axis": axis, "pos": perp, "entries": entries,
                      "run": None, "kind": "length",
                      "label": "{0} [{1}] length".format(
                          room["name"], axis.upper())})
    return items


# ---- level 2: openings, measured inside the room ----

def room_opening_items(room, view, view_faces, occupied, ro_mode, notes,
                       frame):
    """One string per room wall that hosts openings, running just inside
    the room parallel to that wall, spanning room corner to room corner so
    it never leaves the room.

    ro_mode picks what the opening itself is measured to, and it now drives
    INTERIOR as well as exterior (it used to be ignored here, which is why
    interior strings never showed opening centres):
      R.O.  -> the host wall's own view-visible cut faces, i.e. the jambs
      false -> the opening's centreline reference"""
    poly = room["poly"]
    step = standards.TIER_SPACING_FT * view.Scale
    items = []
    n = len(poly)

    # ONE string per WALL, not per boundary edge. A single wall routinely
    # generates several boundary segments of a room (Revit splits them at
    # every junction), and emitting a string per edge produced stacks of
    # byte-identical strings nudged apart - live: wall 5307847 gave three
    # identical [Y] strings in one room. Grouping by wall also means an
    # opening sitting on a different segment OF THE SAME WALL is still
    # picked up, which is where some of the missed openings came from.
    by_wall = {}
    for edge in range(n):
        wall_id = room["wall_ids"][edge]
        if wall_id is None:
            continue
        wall = doc.GetElement(wall_id)
        if not isinstance(wall, Wall):
            continue
        a = poly[edge]
        b = poly[(edge + 1) % n]
        axis = "x" if abs(b[0] - a[0]) >= abs(b[1] - a[1]) else "y"
        idx = 0 if axis == "x" else 1
        length = abs(b[idx] - a[idx])
        key = (str(wall_id), axis)
        rec = by_wall.get(key)
        if rec is None or length > rec["length"]:
            # the wall's LONGEST edge in this room decides where the string
            # sits - a short stub segment would put it in the wrong place
            by_wall[key] = {"wall": wall, "axis": axis, "edge": edge,
                            "length": length}

    for key in sorted(by_wall.keys()):
        rec = by_wall[key]
        wall = rec["wall"]
        axis = rec["axis"]
        edge = rec["edge"]
        opens = revit_io.get_hosted_openings(wall, doc)
        if not opens:
            continue

        a = poly[edge]
        b = poly[(edge + 1) % n]
        idx = 0 if axis == "x" else 1
        pidx = 1 - idx
        edge_perp = (a[pidx] + b[pidx]) / 2.0
        edge_mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        inward = room_inward(poly, edge_mid, pidx, edge_perp)

        # scan just inside the wall to find the room's two PERPENDICULAR
        # boundary walls - those are the string's end anchors, and they
        # are what keeps it inside this room
        span = geometry.polygon_span_at(
            poly, axis, edge_perp + inward * 0.5)
        if span is None:
            continue
        entries = span_entries(room, span, axis, view_faces, notes)
        lo_val, hi_val = span[0][0], span[1][0]

        host_faces = revit_io.collect_axis_faces(
            [wall], axis, view, frame)
        if not host_faces:
            notes.append("{0}: wall {1} has no view-visible axis faces - "
                         "its openings are not dimensioned".format(
                             room["name"], wall.Id))
            continue

        found = 0
        outside = []
        for inst in opens:
            try:
                center = frame.to_local(
                    revit_io.get_opening_point(inst))[idx]
            except ValueError as ex:
                notes.append("Skipped opening: {0}".format(ex))
                continue
            if not (lo_val - 0.5 <= center <= hi_val + 0.5):
                # in this wall, but beyond this room's extent along it -
                # it belongs to the room next door. Recorded, not silent:
                # a genuinely missed opening shows up here.
                outside.append(str(inst.Id))
                continue
            found += 1
            jambs = None
            if ro_mode:
                width = revit_io.get_opening_width(inst)
                jambs = revit_io.jamb_faces_from(
                    host_faces, center, idx, width)
                if jambs is None:
                    notes.append(
                        "Opening {0}: no view-visible jamb faces - "
                        "centreline used".format(inst.Id))
            if jambs is not None:
                entries.append((jambs[0]["origin"][idx], "jamb", jambs[0]))
                entries.append((jambs[1]["origin"][idx], "jamb", jambs[1]))
            else:
                entries.append((center, "open_c", inst))
        if outside:
            notes.append(
                "{0}: opening(s) {1} are in boundary wall {2} but outside "
                "this room's extent along it - not dimensioned here".format(
                    room["name"], ", ".join(outside[:5]), wall.Id))
        if not found:
            continue

        entries = dedupe_entries(entries)
        if len(entries) < 2:
            continue

        # hug the wall (half its thickness clears the poche), on the ROOM
        # side, and never nudge back out through it
        half_thk = getattr(wall, "Width", 0.5) / 2.0
        perp_span = geometry.polygon_span_at(
            poly, "y" if axis == "x" else "x", (lo_val + hi_val) / 2.0)
        bounds = ((perp_span[0][0], perp_span[1][0])
                  if perp_span is not None else None)
        pos = nudge(axis, edge_perp + inward * (half_thk + 0.75 * step),
                    occupied, step, inward, bounds)
        items.append({"axis": axis, "pos": pos, "entries": entries,
                      "run": None, "kind": "openings",
                      "label": "{0} openings, wall {1} [{2}]".format(
                          room["name"], wall.Id, axis.upper())})
    return items


# ---- level 3: fixtures, casework, columns - centre to nearest wall ----

def object_items(room, obj, view_faces, occupied, step, notes, frame):
    """Dimension an object's CENTRE to the nearest bounding wall (user
    rule 3). Columns get both axes; plumbing fixtures and casework get one
    dimension, on the axis whose wall is closest."""
    poly = room["poly"]
    inst = obj["inst"]

    # the room's extent through the object, per axis, and which end is
    # nearer - all from the room polygon, so the wall picked is always one
    # that really bounds this room
    reach = {}
    for axis in ("x", "y"):
        idx = 0 if axis == "x" else 1
        span = geometry.polygon_span_at(poly, axis, obj["pt"][1 - idx])
        if span is None:
            continue
        value = obj["pt"][idx]
        d_lo = value - span[0][0]
        d_hi = span[1][0] - value
        if d_lo <= d_hi:
            reach[axis] = (d_lo, span[0], 1.0)
        else:
            reach[axis] = (d_hi, span[1], -1.0)
    if not reach:
        return []

    if obj["is_column"]:
        axes = sorted(reach.keys())
    else:
        axes = [min(reach, key=lambda a: reach[a][0])]

    items = []
    for axis in axes:
        idx = 0 if axis == "x" else 1
        _, (value, edge), inward = reach[axis]
        wall_entry = edge_face_entry(room, edge, axis, value, inward,
                                     view_faces, notes)
        if wall_entry is None:
            continue
        center_ref = revit_io.get_instance_center_reference(
            inst, axis, frame)
        if center_ref is None:
            notes.append(
                "{0}: {1} {2} exposes no centre reference - not "
                "dimensioned (its family has no Center (Left/Right) or "
                "Center (Front/Back) reference plane)".format(
                    room["name"], inst.Category.Name if inst.Category
                    else "Object", inst.Id))
            continue
        entries = dedupe_entries(
            [wall_entry, (obj["pt"][idx], "fixture", inst)])
        if len(entries) < 2:
            continue

        # the line runs through the object's own centre, offset only if
        # something is already there. It is nudged along the PERPENDICULAR
        # axis (not `inward`, which points along the measured axis), toward
        # the middle of the room, and never past the room's walls.
        perp_axis = "y" if axis == "x" else "x"
        perp_span = geometry.polygon_span_at(poly, perp_axis, obj["pt"][idx])
        obj_perp = obj["pt"][1 - idx]
        if perp_span is None:
            away, bounds = 1.0, None
        else:
            lo, hi = perp_span[0][0], perp_span[1][0]
            away = 1.0 if (lo + hi) / 2.0 >= obj_perp else -1.0
            bounds = (lo, hi)
        pos = nudge(axis, obj_perp, occupied, step, away, bounds)

        items.append({"axis": axis, "pos": pos, "entries": entries,
                      "run": None, "kind": "object",
                      "label": "{0} object {1} [{2}]".format(
                          room["name"], inst.Id, axis.upper())})
    return items


def show_interior_dry_run(items, notes):
    output = script.get_output()
    output.print_md("# Dimension strings — dry run (interior)")
    output.print_md("{0} string(s) | no model changes".format(len(items)))
    for n in range(len(items)):
        item = items[n]
        frame = item.get("frame")
        turned = ""
        if frame is not None and abs(frame.degrees()) > 0.05:
            # values below are in the room's OWN frame, not world X/Y
            turned = " — frame {0:.1f}°".format(frame.degrees())
        output.print_md(
            "### {0} — measures {1}, placed at {2}={3}{4}".format(
                item["label"], item["axis"].upper(),
                "Y" if item["axis"] == "x" else "X",
                format_ft_in(item["pos"]), turned))
        parts = ["{0} ({1})".format(format_ft_in(v), KIND_LABEL[k])
                 for v, k, _ in item["entries"]]
        output.print_md("- " + " | ".join(parts))
    if notes:
        output.print_md("### Notes")
        for note in notes:
            output.print_md("- {0}".format(note))


def run_interior(view, fixtures, ro_mode, dry, measure_core, notes):
    rooms = revit_io.get_rooms(doc, view)
    if not rooms:
        forms.alert(
            "Interior mode is driven by Rooms, and this view has no "
            "placed rooms.\n\nPlace Room elements (with area) and run "
            "again.",
            title="Dimension Strings — interior")
        return

    all_walls = revit_io.get_basic_walls(doc, view)

    # Each ROOM is dimensioned in the frame of its OWN walls, so an angled
    # wing needs no special case: its rooms simply carry a different frame.
    # A room's frame comes from its boundary edges, length-weighted, so the
    # long walls decide and a short jog cannot tilt the room.
    for room in rooms:
        edges = [(room["poly"][k], room["poly"][(k + 1) % len(room["poly"])])
                 for k in range(len(room["poly"]))]
        room["frame"] = geometry.direction_frames(edges)[0]
        room["poly"] = [room["frame"].to_local(p) for p in room["poly"]]

    angles = sorted(set(round(r["frame"].degrees(), 1) for r in rooms))
    notes.append("Room direction(s): {0}".format(
        ", ".join("{0} deg".format(a) for a in angles)))

    # VIEW-AWARE faces per (axis, frame): Options.View makes these
    # references visible in the plan by construction. Model-geometry
    # references produced dimensions that existed but rendered in no view
    # at all (sessions 9e-9f) - every interior reference goes through these.
    # Cached per frame because a face's local origin/normal differ per frame.
    face_cache = {}

    def faces_for(frame):
        key = round(frame.angle, 6)
        if key not in face_cache:
            face_cache[key] = {}
            for axis in ("x", "y"):
                face_cache[key][axis] = revit_io.collect_axis_faces(
                    all_walls, axis, view, frame)
        return face_cache[key]

    objects = revit_io.get_room_objects(doc, view)
    step = standards.TIER_SPACING_FT * view.Scale

    items = []
    counts = {"length": 0, "openings": 0, "objects": 0}
    placed_objects = 0
    for room in rooms:
        frame = room["frame"]
        view_faces = faces_for(frame)

        # one occupancy list per room: strings nudge off each other here,
        # not across the whole floor
        occupied = {"x": [], "y": []}
        mine = []
        for obj in objects:
            local = dict(obj)
            local["pt"] = frame.to_local(obj["pt"])
            if geometry.point_in_polygon(local["pt"], room["poly"]):
                mine.append(local)

        # Openings first: they have a hard constraint (hug their own wall).
        # The room-length line then picks whichever quarter line is least
        # obstructed by them and by the fixtures; object dims come last and
        # avoid both.
        opening_items = room_opening_items(
            room, view, view_faces, occupied, ro_mode, notes, frame)
        length_items = room_length_items(
            room, view_faces, mine, occupied, notes)

        object_dims = []
        for obj in mine:
            got = object_items(room, obj, view_faces, occupied, step, notes,
                               frame)
            if got:
                placed_objects += 1
            object_dims.extend(got)

        # one dimension per distinct measurement, across all three levels
        room_items = drop_redundant(
            length_items + opening_items + object_dims, room["name"], notes)
        for item in room_items:
            item["frame"] = frame

        counts["length"] += len([i for i in room_items
                                 if i["kind"] == "length"])
        counts["openings"] += len([i for i in room_items
                                   if i["kind"] == "openings"])
        counts["objects"] += len([i for i in room_items
                                  if i["kind"] == "object"])
        items.extend(room_items)

    in_rooms = 0
    for obj in objects:
        for r in rooms:
            if geometry.point_in_polygon(
                    r["frame"].to_local(obj["pt"]), r["poly"]):
                in_rooms += 1
                break
    notes.append(
        "{0} room(s) -> {1} room-length string(s), {2} opening string(s), "
        "{3} object dimension(s). {4} fixture/casework/column instance(s) "
        "sit in rooms; {5} of them produced a dimension before redundant "
        "ones were dropped (objects sharing a position share a "
        "dimension).".format(
            len(rooms), counts["length"], counts["openings"],
            counts["objects"], in_rooms, placed_objects))
    notes.append(
        "Openings measured to: {0}.".format(
            "the wall's cut faces (jambs)" if ro_mode else "centreline"))
    if fixtures:
        notes.append(
            "{0} selected element(s) ignored: interior mode dimensions "
            "every fixture/casework/column inside a Room automatically, "
            "so selection is not used.".format(len(fixtures)))

    if dry:
        if measure_core:
            notes.append("Core mode: faces calibrated by measurement "
                         "at placement time.")
        show_interior_dry_run(items, notes)
        return

    origin = getattr(view, "Origin", None)
    base_z = origin.Z if origin is not None else 0.0
    core_cache = {}
    placed = 0
    failed = 0
    created = []  # (label, dimension id) - verified after commit
    with revit.Transaction("Automatic Dimensions: Interior"):
        for item in items:
            try:
                refs, kept = resolve_entries(
                    item["entries"], item["axis"],
                    [], item["run"], notes,
                    measure_core, view, core_cache,
                    prefer_exterior=False, frame=item["frame"])
                if len(refs) < 2:
                    notes.append("{0}: fewer than 2 references - "
                                 "skipped".format(item["label"]))
                    continue
                dim = revit_io.create_dimension_tier(
                    doc, view, refs, item["axis"], (kept[0], kept[-1]),
                    item["pos"], base_z, item["frame"])
                created.append((item["label"], dim.Id))
                placed += 1
            except Exception as ex:
                failed += 1
                notes.append("{0} failed: {1}".format(item["label"], ex))

    # Revit's commit-time failure resolution can DELETE dimensions it
    # considers invalid WITHOUT any exception (live-observed: 16 created,
    # 0 failures, opening strings absent). Verify survival explicitly.
    vanished = [label for label, dim_id in created
                if doc.GetElement(dim_id) is None]
    if vanished:
        failed += len(vanished)
        placed -= len(vanished)
        notes.insert(0, (
            "REVIT SILENTLY DELETED {0} string(s) at commit (invalid "
            "references): {1}".format(len(vanished),
                                      ", ".join(vanished[:9]))))

    # A dimension can survive commit and still render in NO view, if its
    # references are not visible geometry (live-diagnosed, sessions 9e-9f:
    # the dim exists, owner view is right, and Revit draws nothing). Every
    # reference here is view-aware, but the fixture CENTRE references are
    # the one unproven species - so check every dim and name the invisible
    # ones instead of letting them fail silently.
    invisible = []
    for label, dim_id in created:
        dim = doc.GetElement(dim_id)
        if dim is None:
            continue
        try:
            shown = (dim.get_BoundingBox(
                doc.GetElement(dim.OwnerViewId)) is not None)
        except Exception:
            shown = True  # cannot tell - do not cry wolf
        if not shown:
            invisible.append("{0} (id {1})".format(label, dim_id))
    if invisible:
        notes.insert(0, (
            "{0} dimension(s) were created but render in NO view - their "
            "references are not visible geometry in this plan: {1}".format(
                len(invisible), ", ".join(invisible[:9]))))

    if measure_core and core_cache:
        fell_back = [k for k in core_cache if not core_cache[k]]
        notes.append("Core calibration: {0} wall(s) OK, {1} fell back "
                     "to finish faces (ids: {2})".format(
                         len(core_cache) - len(fell_back),
                         len(fell_back),
                         ", ".join(fell_back[:8]) or "none"))

    summary = "Placed {0} of {1} interior dimension string(s).".format(
        placed, len(items))
    if failed:
        # failures FIRST and verbatim - these lines are exactly what is
        # needed to diagnose a skipped string, don't bury them
        failure_notes = [x for x in notes
                         if "failed" in x or "skipped" in x.lower()]
        summary += ("\n{0} string(s) failed/skipped:\n".format(failed)
                    + "\n".join(failure_notes[:9]))
    if notes:
        output = script.get_output()
        output.print_md("### Interior placement notes")
        for note in notes:
            output.print_md("- {0}".format(note))
    forms.alert(summary, title="Dimension Strings — interior")


# -------------------------------------------------------------- reports

KIND_LABEL = {"wallpt": "wall", "open_c": "opening CL",
              "open_side": "opening side", "cross": "partition CL",
              "fixture": "fixture", "face": "wall face",
              "jamb": "R.O. jamb", "vwall": "wall end"}


def show_dry_run(runs, plans, mode, notes):
    output = script.get_output()
    output.print_md("# Dimension strings — dry run ({0})".format(
        "exterior" if mode == MODE_EXT else "interior"))
    output.print_md("{0} run(s) | no model changes".format(len(runs)))
    for n in range(len(runs)):
        tiers = runs[n]["tiers"]
        title = runs[n].get("label") or "Run {0}".format(n + 1)
        output.print_md("### {0} — axis {1}, {2} wall(s), "
                        "{3} opening(s)".format(
                            title, tiers["axis"].upper(),
                            len(runs[n]["walls"]),
                            len(runs[n]["openings"])))
        for label, entries in plans[n]:
            parts = ["{0} ({1})".format(format_ft_in(v), KIND_LABEL[k])
                     for v, k, _ in entries]
            output.print_md("- {0}: {1}".format(label, " | ".join(parts)))
    if notes:
        output.print_md("### Notes")
        for note in notes:
            output.print_md("- {0}".format(note))


# ----------------------------------------------------------------- main

def main():
    view = doc.ActiveView
    notes = []

    walls, fixtures, skipped_sel = gather_selection(view)
    if skipped_sel:
        notes.append(
            "{0} selected wall(s) IGNORED - based below this view's "
            "level or not cut by its cut plane (the below-level walls "
            "that previously hijacked witness lines).".format(skipped_sel))

    window = AutoDimWindow(len(walls), len(fixtures))
    window.show_dialog()
    if not window.result:
        return
    mode = window.result["mode"]
    dry = window.result["dry_run"]
    ro_mode = window.result["openings_ro"]
    measure_core = window.result["measure_core"]
    face_audit = window.result["face_audit"]
    first_offset_in = window.result["first_offset_in"]  # None = auto
    spacing_in = window.result["tier_spacing_in"]
    max_drag_ft = window.result["max_drag_ft"]
    if window.result.get("settings_warning"):
        notes.append(window.result["settings_warning"])

    if mode == MODE_INT:
        # interior is Room-driven scan lines + per-wall opening strings
        # - selection only supplies fixtures/casework
        stats = revit_io.get_wall_stats(doc, view)
        notes.append(
            "Collection: {0} wall(s) visible, {1} basic, {2} on this "
            "level (below-level/underlay walls excluded).".format(
                stats["visible"], stats["basic"], stats["this_level"]))
        run_interior(view, fixtures, ro_mode, dry, measure_core, notes)
        return

    # EXTERIOR: manual selection only - wall Function data is not
    # trusted (user rule: same types get used inside and out)
    if not walls:
        forms.alert(
            "Exterior mode dimensions the walls YOU select.\n\n"
            "Select the perimeter walls of one level and run again "
            "(the wall type's Interior/Exterior Function setting is "
            "deliberately ignored - it is unreliable in real models).",
            title="Dimension Strings — exterior")
        return

    # THE BUILDING'S DIRECTIONS. A dimension always measures ALONG its
    # line, so a rotated wall dimensioned against a world axis returns the
    # cosine-shortened projection - a wrong NUMBER, not just bad placement.
    # Walls are clustered by direction (mod 90 deg, length-weighted) and
    # each cluster is dimensioned inside its own frame. An orthogonal
    # building yields exactly one frame at 0 deg = the exact identity, so
    # it behaves as before.
    segments = []
    seg_walls = []
    for wall in walls:
        try:
            segments.append(revit_io.get_wall_endpoints(wall))
            seg_walls.append(wall)
        except ValueError:
            continue
    frames = geometry.direction_frames(segments)
    notes.append("Building direction(s): {0}".format(
        ", ".join("{0:.1f} deg".format(f.degrees()) for f in frames)))

    by_frame = {}
    frame_segments = {}
    skewed = 0
    for i in range(len(seg_walls)):
        idx = geometry.frame_of(segments[i], frames)
        if idx is None:
            skewed += 1
            continue
        by_frame.setdefault(idx, []).append(seg_walls[i])
        frame_segments.setdefault(idx, []).append(segments[i])
    if skewed:
        notes.append(
            "{0} wall(s) lie on none of the building's directions and were "
            "NOT dimensioned - a dimension can only measure along a line, "
            "and forcing them onto an axis they do not lie on would report "
            "a shortened length.".format(skewed))

    # Reference faces come from ALL walls in the view regardless of the
    # selection - with a partial selection, corner planes belong to
    # UNSELECTED neighbor walls, and missing them made each run end
    # land on a different random layer (live-observed: 109" vs 116").
    all_walls = revit_io.get_basic_walls(doc, view)

    # a work item per frame: (frame, runs, plans)
    work = []
    for idx in sorted(by_frame.keys()):
        frame = frames[idx]
        f_segs = [(frame.to_local(a), frame.to_local(b))
                  for a, b in frame_segments[idx]]
        f_runs = build_runs(by_frame[idx], notes, frame)
        if not f_runs:
            continue
        f_runs = group_exterior_runs(f_runs, frame, f_segs, max_drag_ft)
        f_plans = [build_tier_plan(r, ro_mode, notes, frame) for r in f_runs]
        keep = [n for n in range(len(f_runs))
                if any(len(e) >= 2 for _, e in f_plans[n])]
        f_runs = [f_runs[n] for n in keep]
        f_plans = [f_plans[n] for n in keep]
        for n in range(len(f_runs)):
            if len(frames) > 1:
                f_runs[n]["label"] = "{0} @ {1:.1f} deg".format(
                    f_runs[n].get("label") or "Run", frame.degrees())
            work.append((frame, f_runs[n], f_plans[n]))

    if not work:
        forms.alert("Could not build any dimensionable wall run.\n\n"
                    + "\n".join(notes), title="Dimension Strings")
        return

    runs = [w[1] for w in work]
    plans = [w[2] for w in work]

    # say what the offset settings resolve to for THIS view, so the
    # dry run is checkable before anything is placed
    resolved_first = (first_offset_in if first_offset_in is not None
                      else standards.first_offset_for_scale(view.Scale))
    notes.append(
        'Exterior offsets at 1:{0}: first string {1}" paper = {2:.2f} ft '
        '({3}), tier spacing {4}" paper = {5:.2f} ft.'.format(
            view.Scale, resolved_first,
            resolved_first * standards.INCH * view.Scale,
            "auto preset" if first_offset_in is None else "manual",
            spacing_in, spacing_in * standards.INCH * view.Scale))
    if max_drag_ft > 0.0:
        notes.append(
            "Side splitting: crossing rule plus manual distance cap of "
            "{0:.1f} ft.".format(max_drag_ft))

    if dry:
        if measure_core:
            notes.append(
                "Core mode: core faces are calibrated by measurement "
                "at placement time (temporary dimensions, auto-deleted) "
                "- dry-run values are location-line based.")
        if face_audit:
            # resolve references WITHOUT placing anything, purely to record
            # which face won each contest. measure_core is forced off here:
            # core calibration writes temporary dimensions and needs an open
            # transaction, which a dry run must not have.
            audit_faces = {}
            for frame, run, plan in work:
                axis = run["tiers"]["axis"]
                key = (axis, round(frame.angle, 6))
                if key not in audit_faces:
                    audit_faces[key] = revit_io.collect_axis_faces(
                        all_walls, axis, None, frame)
                for _, entries in plan:
                    resolve_entries(entries, axis, audit_faces[key],
                                    run, notes, False, view, None,
                                    True, True, frame)
        show_dry_run(runs, plans, mode, notes)
        return

    face_caches = {}
    core_cache = {}
    placed = 0
    failed = 0
    with revit.Transaction("Automatic Dimensions: Exterior"):
        for n in range(len(work)):
            frame, run, plan = work[n]
            key = round(frame.angle, 6)
            face_cache = face_caches.setdefault(key, {})
            try:
                placed += place_run(
                    view, run, plan, all_walls, face_cache,
                    [], notes, measure_core, core_cache, face_audit, frame,
                    first_offset_in, spacing_in)
            except Exception as ex:
                failed += 1
                notes.append("Run {0} failed: {1}".format(n + 1, ex))

    if measure_core and core_cache:
        fell_back = [k for k in core_cache if not core_cache[k]]
        notes.append("Core calibration: {0} wall(s) OK, {1} fell back "
                     "to finish faces (wall ids: {2})".format(
                         len(core_cache) - len(fell_back),
                         len(fell_back),
                         ", ".join(fell_back[:8]) or "none"))

    summary = "Placed {0} dimension string(s) across {1} run(s).".format(
        placed, len(runs))
    if failed:
        summary += "\n{0} run(s) failed.".format(failed)
    if notes:
        summary += "\n\nNotes (first 10):\n" + "\n".join(notes[:10])
        output = script.get_output()
        output.print_md("### Placement notes")
        for note in notes:
            output.print_md("- {0}".format(note))
    forms.alert(summary, title="Dimension Strings")


main()
