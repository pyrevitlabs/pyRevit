"""Regenerate the Revit API change catalog used by check_revit_api_compat.py.

This is an on-demand maintenance step, never part of a normal lint run: the
linter reads the committed ``revit_api_catalog/catalog.json`` and works
offline. Rerun this when a new Revit release (or a point release that
deprecates API) ships, then commit the regenerated catalog:

    pip install dnfile
    python dev/scripts/build_revit_api_catalog.py

Ground truth is the shipped API itself, not scraped documentation: for every
Revit year the earliest and the newest stable ``Nice3point.Revit.Api.RevitAPI``
and ``...RevitAPIUI`` NuGet packages are downloaded (they carry Autodesk's
``RevitAPI.dll`` / ``RevitAPIUI.dll``), the public API surface is read from
the assembly metadata with ``dnfile``, and the years are diffed. That yields,
per type and member, the exact years it exists, the first year it carries
``[Obsolete]`` (with Autodesk's message, which usually names the
replacement), and overloads whose Revit-typed parameters went away while the
member name survived (e.g. ``BindingMap.Insert(..., BuiltInParameterGroup)``).

The .NET 8 base-class and Windows Desktop (WPF/WinForms) reference packs are
read too: an instance member name that also exists on a .NET type (e.g.
``ShowDialog``, ``FileName``, ``GetData``) is marked ``bcl`` so the linter
does not mistake ``dialog.ShowDialog()`` for a Revit API call.

Human knowledge the assemblies cannot express - pyRevit helper functions,
fix wording, ambiguity tiers, .NET runtime and engine entries - lives in the
hand-edited ``revit_api_catalog/overrides.json``, which the linter merges at
run time, so editing it needs no regeneration.

Important:
    A year counts as available only when the first and the last update of
    that year both have the API, because users run any update. Years where
    only one of them has it are recorded under ``partial``; the linter treats
    them as missing, since a ``HOST_APP`` year check cannot tell updates apart.

    Presence includes inherited members: Autodesk moves members between a
    class and its base (``*EditScope.IsPermitted`` went to ``EditScope`` in
    2022), which is not a removal for callers.
"""

import argparse
import datetime
import io
import json
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parent / "revit_api_catalog" / "catalog.json"
SCHEMA_VERSION = 1
FIRST_YEAR = 2021
NUGET_INDEX = "https://api.nuget.org/v3-flatcontainer/{id}/index.json"
NUGET_PACKAGE = "https://api.nuget.org/v3-flatcontainer/{id}/{ver}/{id}.{ver}.nupkg"
PACKAGES = {
    "RevitAPI": "nice3point.revit.api.revitapi",
    "RevitAPIUI": "nice3point.revit.api.revitapiui",
}
BCL_PACKAGES = {
    "Microsoft.NETCore.App": "microsoft.netcore.app.ref",
    "Microsoft.WindowsDesktop.App": "microsoft.windowsdesktop.app.ref",
}
BCL_MAJOR = 8
SURFACE_CACHE_FORMAT = 3
REVIT_NAMESPACE_PREFIX = "Autodesk.Revit."

_ELEMENT_TYPE_NAMES = {
    0x01: "System.Void",
    0x02: "System.Boolean",
    0x03: "System.Char",
    0x04: "System.SByte",
    0x05: "System.Byte",
    0x06: "System.Int16",
    0x07: "System.UInt16",
    0x08: "System.Int32",
    0x09: "System.UInt32",
    0x0A: "System.Int64",
    0x0B: "System.UInt64",
    0x0C: "System.Single",
    0x0D: "System.Double",
    0x0E: "System.String",
    0x16: "System.TypedReference",
    0x18: "System.IntPtr",
    0x19: "System.UIntPtr",
    0x1C: "System.Object",
}


def _stable_versions_per_year(package_id, years):
    """Return {year: [earliest, latest]} stable package versions (one if equal)."""
    with urllib.request.urlopen(NUGET_INDEX.format(id=package_id), timeout=60) as resp:
        versions = json.load(resp)["versions"]
    per_year = {}
    for version in versions:
        if "-" in version:
            continue
        parts = tuple(int(p) for p in version.split("."))
        year = parts[0]
        if year < FIRST_YEAR or (years and year not in years):
            continue
        per_year.setdefault(year, []).append((parts, version))
    result = {}
    for year, found in sorted(per_year.items()):
        found.sort()
        earliest, latest = found[0][1], found[-1][1]
        result[year] = [earliest] if earliest == latest else [earliest, latest]
    return result


def _download(package_id, version, cache_dir):
    target = cache_dir / "{}.{}.nupkg".format(package_id, version)
    if not target.exists():
        url = NUGET_PACKAGE.format(id=package_id, ver=version)
        print("  downloading {}".format(url), file=sys.stderr)
        with urllib.request.urlopen(url, timeout=300) as resp:
            data = resp.read()
        target.write_bytes(data)
    return target


def _assembly_bytes(nupkg_path, assembly_name):
    with zipfile.ZipFile(nupkg_path) as archive:
        for name in archive.namelist():
            if name.lower().endswith("/" + assembly_name.lower() + ".dll"):
                return archive.read(name)
    raise FileNotFoundError("{} not found in {}".format(assembly_name, nupkg_path))


class _SignatureReader:
    """Decodes ECMA-335 II.23.2 method signatures into parameter type names."""

    def __init__(self, blob, resolve_token):
        self._blob = blob
        self._pos = 0
        self._resolve_token = resolve_token

    def _byte(self):
        value = self._blob[self._pos]
        self._pos += 1
        return value

    def _compressed(self):
        first = self._byte()
        if first & 0x80 == 0:
            return first
        if first & 0xC0 == 0x80:
            return ((first & 0x3F) << 8) | self._byte()
        return (
            ((first & 0x1F) << 24)
            | (self._byte() << 16)
            | (self._byte() << 8)
            | self._byte()
        )

    def _type_token(self):
        coded = self._compressed()
        return self._resolve_token(coded & 0x03, coded >> 2)

    def _type(self):
        element = self._byte()
        if element in _ELEMENT_TYPE_NAMES:
            return _ELEMENT_TYPE_NAMES[element]
        if element in (0x1F, 0x20):
            self._type_token()
            return self._type()
        if element in (0x0F, 0x10, 0x45):
            return self._type()
        if element in (0x11, 0x12):
            return self._type_token()
        if element in (0x13, 0x1E):
            self._compressed()
            return "?"
        if element == 0x1D:
            return self._type() + "[]"
        if element == 0x14:
            inner = self._type()
            self._compressed()
            for _ in range(self._compressed()):
                self._compressed()
            for _ in range(self._compressed()):
                self._compressed()
            return inner + "[,]"
        if element == 0x15:
            self._byte()
            generic = self._type_token()
            args = [self._type() for _ in range(self._compressed())]
            return "{}<{}>".format(generic, ",".join(args))
        if element == 0x1B:
            self.method_params()
            return "fnptr"
        raise ValueError("unsupported element type 0x{:02x}".format(element))

    def method_params(self):
        """Return the parameter type names of a MethodDefSig/MethodRefSig."""
        callconv = self._byte()
        if callconv & 0x10:
            self._compressed()
        count = self._compressed()
        self._type()
        params = []
        for _ in range(count):
            if self._blob[self._pos] == 0x41:
                self._pos += 1
            params.append(self._type())
        return params


def _obsolete_message(blob):
    if len(blob) < 3 or blob[0:2] != b"\x01\x00":
        return ""
    if len(blob) == 4 and blob[2:4] == b"\x00\x00":
        return ""
    if blob[2] == 0xFF:
        return ""
    reader = _SignatureReader(blob, None)
    reader._pos = 2
    length = reader._compressed()
    start = reader._pos
    return blob[start : start + length].decode("utf-8", "replace").strip()


def _add_member(members, obsolete, name, kind, static, obsolete_key, overload=None):
    """Record one member (or one overload of a method) of a type.

    Invariant:
        A method counts as obsolete only when every overload is; the
        ``has_current_overload`` marker clears it after all are seen.
    """
    entry = members.setdefault(name, {"kind": kind, "static": static, "obsolete": None})
    if obsolete_key in obsolete and entry["obsolete"] is None:
        entry["obsolete"] = obsolete[obsolete_key]
    elif obsolete_key not in obsolete and kind == "method":
        entry["has_current_overload"] = True
    if overload is not None:
        entry.setdefault("overloads", []).append(overload)


def read_surface(dll_bytes):
    """Return the public API surface of one Revit assembly.

    Returns:
        (dict): ``{type_full_name: {"kind", "obsolete", "members"}}`` where
        members map name to ``{"kind", "static", "obsolete", "overloads"}``;
        ``obsolete`` is the attribute message (``""`` when it has none) or
        None, and ``overloads`` lists parameter-type-name lists.
    """
    import dnfile

    md = dnfile.dnPE(data=dll_bytes).net.mdtables

    def table_name(coded):
        return type(coded.table).__name__

    enclosing = {}
    if md.NestedClass:
        for row in md.NestedClass.rows:
            enclosing[row.NestedClass.row_index] = row.EnclosingClass.row_index

    typedefs = md.TypeDef.rows
    typeref_names = {}
    if md.TypeRef:
        for index, row in enumerate(md.TypeRef.rows, start=1):
            namespace = str(row.TypeNamespace or "")
            name = str(row.TypeName)
            typeref_names[index] = namespace + "." + name if namespace else name

    full_names = {}

    def full_name(index):
        if index in full_names:
            return full_names[index]
        row = typedefs[index - 1]
        name = str(row.TypeName).split("`")[0]
        if index in enclosing:
            result = full_name(enclosing[index]) + "." + name
        else:
            namespace = str(row.TypeNamespace or "")
            result = namespace + "." + name if namespace else name
        full_names[index] = result
        return result

    def is_visible(index):
        flags = typedefs[index - 1].Flags
        if index in enclosing:
            return bool(flags.tdNestedPublic) and is_visible(enclosing[index])
        return bool(flags.tdPublic)

    def resolve_token(tag, index):
        if tag == 0:
            return full_name(index)
        if tag == 1:
            return typeref_names.get(index, "?")
        return "?"

    obsolete = {}
    if md.CustomAttribute:
        for row in md.CustomAttribute.rows:
            ctor = row.Type
            if table_name(ctor) != "MemberRef":
                continue
            klass = ctor.row.Class
            if table_name(klass) != "TypeRef":
                continue
            if typeref_names.get(klass.row_index) != "System.ObsoleteAttribute":
                continue
            message = _obsolete_message(bytes(row.Value.value))
            obsolete[(table_name(row.Parent), row.Parent.row_index)] = message

    accessors = {}
    if md.MethodSemantics:
        for row in md.MethodSemantics.rows:
            key = (table_name(row.Association), row.Association.row_index)
            accessors.setdefault(key, []).append(row.Method.row)

    def accessor_flags(key):
        methods = accessors.get(key, [])
        public = any(m.Flags.mdPublic for m in methods)
        static = any(m.Flags.mdStatic for m in methods)
        return public, static

    surface = {}
    for index, row in enumerate(typedefs, start=1):
        if not is_visible(index):
            continue
        name = full_name(index)
        if not name.startswith(REVIT_NAMESPACE_PREFIX):
            continue
        base = ""
        if row.Extends and row.Extends.row_index:
            base = resolve_token(
                {"TypeDef": 0, "TypeRef": 1}.get(table_name(row.Extends), 2),
                row.Extends.row_index,
            )
        if row.Flags.tdInterface:
            kind = "interface"
        elif base == "System.Enum":
            kind = "enum"
        elif base == "System.MulticastDelegate":
            kind = "delegate"
        elif base == "System.ValueType":
            kind = "struct"
        else:
            kind = "class"
        members = {}

        for method_index in row.MethodList or []:
            method = method_index.row
            if not method.Flags.mdPublic:
                continue
            method_name = str(method.Name)
            if method.Flags.mdSpecialName and method_name not in (".ctor",):
                continue
            if method_name == ".cctor":
                continue
            try:
                params = _SignatureReader(
                    bytes(method.Signature.value), resolve_token
                ).method_params()
            except (ValueError, IndexError):
                params = []
            _add_member(
                members,
                obsolete,
                method_name,
                "method",
                bool(method.Flags.mdStatic),
                ("MethodDef", method_index.row_index),
                params,
            )
        for field_index in row.FieldList or []:
            field = field_index.row
            if not field.Flags.fdPublic or str(field.Name) == "value__":
                continue
            _add_member(
                members,
                obsolete,
                str(field.Name),
                "field",
                bool(field.Flags.fdStatic),
                ("Field", field_index.row_index),
            )
        surface[name] = {
            "kind": kind,
            "base": base,
            "obsolete": obsolete.get(("TypeDef", index)),
            "members": members,
        }
        surface[name]["_index"] = index

    by_index = {info.pop("_index"): info for info in surface.values()}
    if md.PropertyMap:
        for row in md.PropertyMap.rows:
            info = by_index.get(row.Parent.row_index)
            if info is None:
                continue
            for prop_index in row.PropertyList or []:
                public, static = accessor_flags(("Property", prop_index.row_index))
                if not public:
                    continue
                member = info["members"].setdefault(
                    str(prop_index.row.Name),
                    {"kind": "property", "static": static, "obsolete": None},
                )
                key = ("Property", prop_index.row_index)
                if key in obsolete and member["obsolete"] is None:
                    member["obsolete"] = obsolete[key]
    if md.EventMap:
        for row in md.EventMap.rows:
            info = by_index.get(row.Parent.row_index)
            if info is None:
                continue
            for event_index in row.EventList or []:
                public, static = accessor_flags(("Event", event_index.row_index))
                if not public:
                    continue
                member = info["members"].setdefault(
                    str(event_index.row.Name),
                    {"kind": "event", "static": static, "obsolete": None},
                )
                key = ("Event", event_index.row_index)
                if key in obsolete and member["obsolete"] is None:
                    member["obsolete"] = obsolete[key]

    for info in surface.values():
        for member in info["members"].values():
            if member["kind"] == "method" and member.get("has_current_overload"):
                member["obsolete"] = None
            member.pop("has_current_overload", None)
    return surface


def read_member_names(dll_bytes):
    """Return every public member name declared by public types of an assembly."""
    import dnfile

    md = dnfile.dnPE(data=dll_bytes).net.mdtables
    if not md.TypeDef:
        return set()
    names = set()
    for row in md.TypeDef.rows:
        flags = row.Flags
        if not (flags.tdPublic or flags.tdNestedPublic):
            continue
        for method_index in row.MethodList or []:
            method = method_index.row
            if method.Flags.mdPublic or method.Flags.mdFamily:
                name = str(method.Name)
                for prefix in ("get_", "set_", "add_", "remove_"):
                    if method.Flags.mdSpecialName and name.startswith(prefix):
                        name = name[len(prefix) :]
                        break
                names.add(name)
        for field_index in row.FieldList or []:
            if field_index.row.Flags.fdPublic:
                names.add(str(field_index.row.Name))
    return names


def _load_bcl_names(cache_dir):
    """Public member names across the .NET {major} BCL and Windows Desktop packs."""
    names = set()
    sources = {}
    for label, package_id in BCL_PACKAGES.items():
        with urllib.request.urlopen(
            NUGET_INDEX.format(id=package_id), timeout=60
        ) as resp:
            versions = json.load(resp)["versions"]
        stable = [
            v for v in versions if "-" not in v and v.split(".")[0] == str(BCL_MAJOR)
        ]
        version = max(stable, key=lambda v: tuple(int(p) for p in v.split(".")))
        sources[label] = version
        cached = cache_dir / "{}.{}.names.json".format(package_id, version)
        if cached.exists():
            names.update(json.loads(cached.read_text(encoding="utf-8")))
            continue
        nupkg = _download(package_id, version, cache_dir)
        package_names = set()
        with zipfile.ZipFile(nupkg) as archive:
            for entry in archive.namelist():
                if entry.startswith("ref/") and entry.endswith(".dll"):
                    try:
                        package_names |= read_member_names(archive.read(entry))
                    except Exception as err:  # noqa: BLE001
                        print("  skipped {}: {}".format(entry, err), file=sys.stderr)
        print(
            "  {} {}: {} member names".format(label, version, len(package_names)),
            file=sys.stderr,
        )
        cached.write_text(json.dumps(sorted(package_names)), encoding="utf-8")
        names |= package_names
    return names, sources


def _load_surface(package_versions, cache_dir):
    """Merged RevitAPI + RevitAPIUI surface for one set of package versions."""
    merged = {}
    for assembly, package_id in PACKAGES.items():
        version = package_versions[assembly]
        cached = cache_dir / "{}.{}.surface.json".format(package_id, version)
        if cached.exists():
            payload = json.loads(cached.read_text(encoding="utf-8"))
            if payload.get("format") == SURFACE_CACHE_FORMAT:
                merged.update(payload["surface"])
                continue
        nupkg = _download(package_id, version, cache_dir)
        started = time.time()
        surface = read_surface(_assembly_bytes(nupkg, assembly))
        print(
            "  {} {}: {} public types ({:.0f}s)".format(
                assembly, version, len(surface), time.time() - started
            ),
            file=sys.stderr,
        )
        cached.write_text(
            json.dumps({"format": SURFACE_CACHE_FORMAT, "surface": surface}),
            encoding="utf-8",
        )
        merged.update(surface)
    return merged


def _ranges(years):
    """Compress sorted years to inclusive ``[first, last]`` runs."""
    runs = []
    for year in sorted(years):
        if runs and year == runs[-1][1] + 1:
            runs[-1][1] = year
        else:
            runs.append([year, year])
    return runs


def _first_obsolete(per_year, years):
    """Return (first year, latest message) of an [Obsolete] that sticks."""
    since = None
    message = None
    for year in years:
        info = per_year.get(year)
        if info is None:
            continue
        if info["obsolete"] is not None:
            if since is None:
                since = year
            message = info["obsolete"] or message
        else:
            since = None
            message = None
    return since, message


def _find_member(surface, type_name, member_name):
    """Return a member's info on a type or its nearest declaring base, or None."""
    seen = set()
    while type_name in surface and type_name not in seen:
        seen.add(type_name)
        info = surface[type_name]
        if member_name in info["members"]:
            return info["members"][member_name]
        type_name = info.get("base") or ""
    return None


def _state(found):
    """Classify per-sample presence: 'full', 'partial' or None."""
    if all(found):
        return "full"
    return "partial" if any(found) else None


class _YearView:
    """Presence of types and members across the update samples of one year."""

    def __init__(self, samples):
        self.samples = samples
        self.latest = samples[-1]

    def type_state(self, type_name):
        return _state([type_name in s for s in self.samples])

    def type_info(self, type_name):
        for sample in reversed(self.samples):
            if type_name in sample:
                return sample[type_name]
        return None

    def member_state(self, type_name, member_name):
        return _state([_find_member(s, type_name, member_name) for s in self.samples])

    def member_info(self, type_name, member_name):
        for sample in reversed(self.samples):
            info = _find_member(sample, type_name, member_name)
            if info is not None:
                return info
        return None

    def declared(self, type_name):
        names = set()
        for sample in self.samples:
            if type_name in sample:
                names.update(sample[type_name]["members"])
        return names


def _availability(states, all_years):
    """Turn {year: state} into catalog fields (``avail``/``partial`` runs)."""
    full = {y for y, state in states.items() if state == "full"}
    partial = {y for y, state in states.items() if state == "partial"}
    fields = {}
    if full != set(all_years):
        fields["avail"] = _ranges(full)
    if partial:
        fields["partial"] = _ranges(partial)
    return fields


def _overload_param_types(per_year, member_years):
    """Map Revit parameter types to the years an overload accepting them exists.

    Only types whose availability is narrower than the member's own years are
    kept: those mark overloads removed (or added) while the name survived.
    Overloads are read from each year's latest update.
    """
    availability = {}
    for year, info in per_year.items():
        for params in info.get("overloads") or []:
            for param in params:
                base = param.rstrip("[],")
                if base.startswith(REVIT_NAMESPACE_PREFIX):
                    availability.setdefault(base, set()).add(year)
    return {
        param: _ranges(years)
        for param, years in sorted(availability.items())
        if years != member_years
    }


def build_catalog(samples, package_versions, bcl_names=frozenset(), bcl_sources=None):
    """Diff per-year update samples into the catalog document.

    Args:
        samples (dict[int, list[dict]]): per Revit year, surfaces of its
            update releases in release order (earliest first, latest last).
        package_versions (dict): per year, the package versions sampled;
            recorded so a reviewer can see what the catalog was built from.
        bcl_names (set[str]): .NET member names; matching instance names
            are marked ``bcl``.
        bcl_sources (dict): .NET reference pack versions, for the record.

    Invariant:
        A type appears under ``types`` when it, or one of its declared
        members, is not fully present (or not un-deprecated) in every
        cataloged year; unchanged types without changed members are omitted
        to keep the catalog reviewable. A member's availability counts
        inherited declarations, so moving a member to a base class is not a
        removal.
    """
    years = sorted(samples)
    views = {y: _YearView(samples[y]) for y in years}
    type_names = sorted({n for y in years for s in samples[y] for n in s})
    types = {}
    instance_members = {}
    for type_name in type_names:
        type_states = {y: views[y].type_state(type_name) for y in years}
        present = [y for y in years if type_states[y]]
        latest = views[max(present)].type_info(type_name)
        type_entry = {"kind": latest["kind"]}
        if latest.get("base", "").startswith(REVIT_NAMESPACE_PREFIX):
            type_entry["base"] = latest["base"]
        type_entry.update(_availability(type_states, years))
        obsolete_since, obsolete_msg = _first_obsolete(
            {y: views[y].type_info(type_name) for y in present}, years
        )
        if obsolete_since:
            type_entry["obsolete"] = {"since": obsolete_since, "message": obsolete_msg}

        member_names = sorted(
            set().union(*(views[y].declared(type_name) for y in present))
        )
        members = {}
        for member_name in member_names:
            states = {}
            per_year = {}
            for y in present:
                state = views[y].member_state(type_name, member_name)
                if state:
                    states[y] = state
                    per_year[y] = views[y].member_info(type_name, member_name)
            member_years = {y for y, state in states.items() if state == "full"}
            sample = per_year[max(per_year)]
            entry = {}
            if member_years != {y for y in present if type_states[y] == "full"}:
                entry.update(_availability(states, years))
                entry.setdefault("avail", _ranges(member_years))
            since, message = _first_obsolete(per_year, years)
            if since:
                entry["obsolete"] = {"since": since, "message": message}
            if sample["kind"] == "method":
                overloads = _overload_param_types(per_year, set(per_year))
                if overloads:
                    entry["overload_params"] = overloads
            if not sample["static"] and member_name != ".ctor":
                index = instance_members.setdefault(member_name, {})
                index.setdefault("years", set()).update(member_years)
                index.setdefault("partial", set()).update(
                    y for y, state in states.items() if state == "partial"
                )
                index.setdefault("current_years", set()).update(
                    y for y, info in per_year.items() if info["obsolete"] is None
                )
                for year, info in per_year.items():
                    for params in info.get("overloads") or []:
                        for param in params:
                            base = param.rstrip("[],")
                            if base.startswith(REVIT_NAMESPACE_PREFIX):
                                index.setdefault("params", {}).setdefault(
                                    base, set()
                                ).add(year)
            if entry:
                entry["kind"] = sample["kind"]
                if sample["static"]:
                    entry["static"] = True
                members[member_name] = entry
        if members:
            type_entry["members"] = members
        if members or set(type_entry) - {"kind", "base"}:
            types[type_name] = type_entry

    all_years = set(years)
    names = {}
    for member_name, index in sorted(instance_members.items()):
        entry = {}
        full = index["years"]
        if full != all_years:
            entry["avail"] = _ranges(full)
        partial = index["partial"] - full
        if partial:
            entry["partial"] = _ranges(partial)
        deprecated_years = full - index["current_years"]
        if deprecated_years:
            entry["obsolete_years"] = _ranges(deprecated_years)
        params = {
            param: _ranges(param_years)
            for param, param_years in sorted(index.get("params", {}).items())
            if param_years != full | partial
        }
        if params:
            entry["overload_params"] = params
        if entry:
            if member_name in bcl_names:
                entry["bcl"] = True
            names[member_name] = entry

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_on": datetime.date.today().isoformat(),
        "generator": "dev/scripts/build_revit_api_catalog.py",
        "years": years,
        "packages": {
            str(year): versions for year, versions in sorted(package_versions.items())
        },
        "bcl_packages": bcl_sources or {},
        "types": types,
        "instance_members": names,
    }


def main():
    """Download, diff and write the catalog; returns a process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--years",
        type=int,
        nargs="*",
        help="Revit years to include (default: every year >= {} on NuGet)".format(
            FIRST_YEAR
        ),
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(tempfile.gettempdir()) / "pyrevit-revit-api-catalog",
        help="where downloaded packages and extracted surfaces are cached",
    )
    parser.add_argument("--output", type=Path, default=CATALOG_PATH)
    args = parser.parse_args()

    try:
        import dnfile  # noqa: F401
    except ImportError:
        print(
            "error: regeneration needs the 'dnfile' package: pip install dnfile",
            file=sys.stderr,
        )
        return 2

    args.cache_dir.mkdir(parents=True, exist_ok=True)
    wanted = set(args.years or [])
    per_package = {
        assembly: _stable_versions_per_year(package_id, wanted)
        for assembly, package_id in PACKAGES.items()
    }
    years = sorted(set.intersection(*(set(v) for v in per_package.values())))
    if not years:
        print("error: no Revit API packages found", file=sys.stderr)
        return 2

    samples = {}
    package_versions = {}
    for year in years:
        print("Revit {}:".format(year), file=sys.stderr)
        labels = ("earliest", "latest")
        package_versions[year] = {}
        samples[year] = []
        for position, label in ((0, labels[0]), (-1, labels[1])):
            versions = {a: per_package[a][year][position] for a in PACKAGES}
            if (
                package_versions[year]
                and versions == package_versions[year]["earliest"]
            ):
                continue
            package_versions[year][label] = versions
            samples[year].append(_load_surface(versions, args.cache_dir))

    print(".NET {} reference packs:".format(BCL_MAJOR), file=sys.stderr)
    bcl_names, bcl_sources = _load_bcl_names(args.cache_dir)
    catalog = build_catalog(samples, package_versions, bcl_names, bcl_sources)
    buffer = io.StringIO()
    json.dump(catalog, buffer, indent=1, sort_keys=True, ensure_ascii=False)
    buffer.write("\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(buffer.getvalue(), encoding="utf-8")
    print(
        "wrote {} ({} types, {} instance member names)".format(
            args.output, len(catalog["types"]), len(catalog["instance_members"])
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
