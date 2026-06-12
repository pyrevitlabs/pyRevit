"""Migrate bundle metadata from scripts into bundle.yaml files.

Scans bundles in a selected .extension folder, merges discovered metadata into
each bundle.yaml using a selected merge policy, and can optionally clean up
metadata lines in scripts after migration.
"""
# pylint: disable=import-error,invalid-name,broad-except,wrong-import-position
from __future__ import absolute_import, print_function

import ast
import codecs
import os
import os.path as op
from collections import OrderedDict

import clr
clr.AddReference('pyRevitExtensionParser')
from pyRevitExtensionParser import ExtensionParser  # noqa: E402

from pyrevit import forms, script
from pyrevit.coreutils import yaml as pyryaml


SCRIPT_BUNDLE_EXTS = (
    '.pushbutton', '.smartbutton', '.panelbutton', '.invokebutton',
    '.nobutton', '.linkbutton', '.combobox',
)

DUNDER_NAMES = frozenset((
    '__title__', '__authors__', '__author__', '__doc__', '__helpurl__',
    '__context__', '__highlight__', '__min_revit_ver__', '__max_revit_ver__',
    '__beta__', '__cleanengine__', '__fullframeengine__', '__persistentengine__',
))

output = script.get_output()


def clr_to_python(value):
    """Recursively convert .NET Dictionary / List values into native Python."""
    if value is None:
        return None
    if isinstance(value, (str, bool, int, float)):
        return value
    if hasattr(value, 'Keys') and hasattr(value, 'TryGetValue'):
        return OrderedDict((str(k), clr_to_python(value[k])) for k in value.Keys)
    if hasattr(value, 'Count') and not isinstance(value, str):
        return [clr_to_python(v) for v in value]
    return value


def find_script_in_bundle(bundle_dir):
    """Return the dunder-bearing .py script inside a bundle dir, or None."""
    try:
        files = os.listdir(bundle_dir)
    except OSError:
        return None
    for f in files:
        if f.lower() == 'script.py':
            return op.join(bundle_dir, f)
    for f in files:
        lower = f.lower()
        if lower.endswith('.py') and (
                lower.endswith('_script.py')
                or lower.endswith('-script.py')
                or lower.endswith('.script.py')):
            return op.join(bundle_dir, f)
    return None


def iter_bundles(extension_root):
    """Yield (bundle_dir, script_path) for every script-carrying bundle."""
    for dirpath, dirnames, _ in os.walk(extension_root):
        for name in dirnames:
            if any(name.lower().endswith(ext) for ext in SCRIPT_BUNDLE_EXTS):
                bundle = op.join(dirpath, name)
                script_path = find_script_in_bundle(bundle)
                if script_path:
                    yield bundle, script_path


def read_script_metadata(script_path):
    """Pull dunders from script_path via the C# parser, as a native dict."""
    raw = ExtensionParser.ReadScriptMetadata(script_path)
    out = OrderedDict()
    for k in raw.Keys:
        out[str(k)] = clr_to_python(raw[k])
    return out


def merge_yaml(existing, incoming, policy, rel_label, dry_run=False):
    """Return (merged, changed, skipped)."""
    existing = existing or OrderedDict()
    merged = OrderedDict(existing)
    changed = False
    effective_policy = policy
    if dry_run and policy == 'ask':
        effective_policy = 'script_wins'

    for key, new_value in incoming.items():
        if key not in merged:
            merged[key] = new_value
            changed = True
            continue
        if merged[key] == new_value:
            continue
        if effective_policy == 'yaml_wins':
            continue
        if effective_policy == 'script_wins':
            merged[key] = new_value
            changed = True
            continue
        choice = forms.CommandSwitchWindow.show(
            ['Keep YAML: {!r}'.format(merged[key]),
             'Use SCRIPT: {!r}'.format(new_value)],
            message='[{}] Conflict on `{}`'.format(rel_label, key),
        )
        if not choice:
            return existing, False, True
        if choice.startswith('Use SCRIPT'):
            merged[key] = new_value
            changed = True

    return merged, changed, False


def _read_script_source(script_path):
    """Read script text as UTF-8 (with optional BOM)."""
    try:
        with codecs.open(script_path, 'r', 'utf-8-sig') as f:
            return f.read()
    except (OSError, IOError):
        return None


def _strip_strings_and_comments(line):
    """Roughly mask strings/comments so bracket counts ignore string contents."""
    out = []
    i = 0
    n = len(line)
    in_single = False
    in_double = False
    in_triple = None
    while i < n:
        if in_triple:
            if line.startswith(in_triple, i):
                out.extend([' '] * len(in_triple))
                i += len(in_triple)
                in_triple = None
                continue
            out.append(' ')
            i += 1
            continue
        if not in_single and not in_double:
            if line.startswith('"""', i) or line.startswith("'''", i):
                in_triple = line[i:i + 3]
                out.extend([' '] * 3)
                i += 3
                continue
            if line[i] == '#':
                out.extend([' '] * (n - i))
                break
            if line[i] == "'":
                in_single = True
                out.append(' ')
                i += 1
                continue
            if line[i] == '"':
                in_double = True
                out.append(' ')
                i += 1
                continue
        if in_single:
            if line[i] == "'":
                in_single = False
            out.append(' ')
            i += 1
            continue
        if in_double:
            if line[i] == '"':
                in_double = False
            out.append(' ')
            i += 1
            continue
        out.append(line[i])
        i += 1
    return ''.join(out)


def _assignment_complete_on_line(masked_line):
    """True if bracket/quote structure on this line is closed after the line."""
    stack = []
    pairs = {')': '(', ']': '[', '}': '{'}
    in_single = in_double = False
    in_triple = None
    i = 0
    n = len(masked_line)
    while i < n:
        ch = masked_line[i]
        if in_triple:
            if masked_line.startswith(in_triple, i):
                i += len(in_triple)
                in_triple = None
            else:
                i += 1
            continue
        if not in_single and not in_double:
            if masked_line.startswith('"""', i) or masked_line.startswith("'''", i):
                in_triple = masked_line[i:i + 3]
                i += 3
                continue
            if ch == "'":
                in_single = True
                i += 1
                continue
            if ch == '"':
                in_double = True
                i += 1
                continue
            if ch in '([{':
                stack.append(ch)
            elif ch in ')]}':
                if stack and stack[-1] == pairs[ch]:
                    stack.pop()
            i += 1
            continue
        if in_single:
            if ch == "'":
                in_single = False
            i += 1
            continue
        if in_double:
            if ch == '"':
                in_double = False
            i += 1
            continue
    return not stack and not in_single and not in_double and not in_triple


def _line_range_for_assignment_block(source_lines, start_idx):
    """Return 0-based indices for a module-level assignment starting at start_idx."""
    if start_idx < 0 or start_idx >= len(source_lines):
        return []

    indices = []
    combined = ''
    for idx in range(start_idx, len(source_lines)):
        indices.append(idx)
        combined += source_lines[idx]
        if source_lines[idx].rstrip().endswith('\\'):
            continue
        if _assignment_complete_on_line(_strip_strings_and_comments(combined)):
            return indices
    return indices


def _dunder_used_as_load(tree, dunder_name):
    """True if dunder_name is read anywhere in the module."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == dunder_name:
            if isinstance(node.ctx, ast.Load):
                return True
    return False


def _assign_target_names(target):
    """Yield Name ids from an assignment target (Name or Tuple/List)."""
    if isinstance(target, ast.Name):
        yield target.id
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            for name in _assign_target_names(elt):
                yield name


def find_cleanup_line_indices(script_path):
    """Return (sorted 0-based line indices, warning_message).

    Skips the script with a clear warning when ast.parse fails so a broken
    source is fixed before this tool touches it.
    """
    source = _read_script_source(script_path)
    if source is None:
        return None, 'could not read script'

    source_lines = source.splitlines(True)
    try:
        tree = ast.parse(source)
    except SyntaxError as ex:
        return None, 'syntax error at line {}: {}'.format(
            ex.lineno or '?', ex.msg or ex
        )

    indices = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        assign_names = []
        for target in node.targets:
            for name in _assign_target_names(target):
                if name in DUNDER_NAMES:
                    assign_names.append(name)
        if not assign_names:
            continue
        if any(_dunder_used_as_load(tree, name) for name in assign_names):
            continue
        start = node.lineno - 1
        end_lineno = getattr(node, 'end_lineno', None)
        if end_lineno is not None:
            for idx in range(start, end_lineno):
                indices.add(idx)
        else:
            for idx in _line_range_for_assignment_block(source_lines, start):
                indices.add(idx)
    return sorted(indices), None


def apply_script_cleanup(script_path, cleanup_mode):
    """Comment out or remove module-level dunder lines.

    cleanup_mode: 'comment' or 'remove'
    Returns (changed, warning_message).
    """
    indices, warn = find_cleanup_line_indices(script_path)
    if warn and not indices:
        return False, warn
    if not indices:
        return False, warn

    source_lines = _read_script_source(script_path)
    if source_lines is None:
        return False, 'could not read script'
    lines = source_lines.splitlines(True)

    index_set = set(indices)
    new_lines = []
    for idx, line in enumerate(lines):
        if idx not in index_set:
            new_lines.append(line)
            continue
        if cleanup_mode == 'remove':
            continue
        if line.lstrip().startswith('#'):
            new_lines.append(line)
        else:
            new_lines.append('# ' + line)

    with codecs.open(script_path, 'w', 'utf-8') as f:
        f.writelines(new_lines)
    return True, warn


# === Main ===
target = forms.pick_folder(title='Pick .extension folder to migrate')
if not target:
    script.exit()
if not target.lower().endswith('.extension'):
    forms.alert('Target folder must end with .extension.', exitscript=True)

run_choice = forms.CommandSwitchWindow.show(
    ['Preview only (no files written)',
     'Apply changes'],
    message='Run mode',
)
if not run_choice:
    script.exit()
dry_run = run_choice.startswith('Preview')

if dry_run:
    backup_msg = (
        'Preview mode scans the extension and reports what would change.\n\n'
        'No files will be written. Commit or back up your extension before '
        'running Apply changes.'
    )
else:
    backup_msg = (
        'Apply mode will write bundle.yaml files under the selected extension '
        'and may edit script.py files if you choose cleanup.\n\n'
        'Commit your changes or make a backup before continuing.'
    )

if not forms.alert(backup_msg, ok=True, cancel=True):
    script.exit()

cleanup_mode = None
cleanup_choice = 'Leave script.py alone'
merge_choice = None

if dry_run:
    # Preview only reports yaml merges; cleanup never runs and per-key
    # conflict prompts are disabled (see merge_yaml dry_run handling).
    policy = 'script_wins'
    merge_choice = 'Script wins (preview default)'
else:
    cleanup_choice = forms.CommandSwitchWindow.show(
        ['Leave script.py alone',
         'Comment-out migrated dunders in script.py',
         'Remove migrated dunders from script.py'],
        message='Script cleanup mode (applied after yaml write)',
    )
    if not cleanup_choice:
        script.exit()
    if cleanup_choice.startswith('Comment'):
        cleanup_mode = 'comment'
    elif cleanup_choice.startswith('Remove'):
        cleanup_mode = 'remove'

    merge_choice = forms.CommandSwitchWindow.show(
        ['YAML wins',
         'Script wins (overwrite YAML)',
         'Ask per-key on conflict'],
        message='Merge policy when bundle.yaml already has a key',
    )
    if not merge_choice:
        script.exit()
    if merge_choice.startswith('YAML'):
        policy = 'yaml_wins'
    elif merge_choice.startswith('Script'):
        policy = 'script_wins'
    else:
        policy = 'ask'

title = '### Migration preview' if dry_run else '### Migration started'
output.print_md(title)
output.print_md('- Target: `{}`'.format(target))
output.print_md('- Mode: `{}`'.format(run_choice))
output.print_md('- Cleanup: `{}`'.format(cleanup_choice))
output.print_md('- Merge: `{}`'.format(merge_choice))
if dry_run:
    output.print_md(
        '- Note: preview uses script-wins for conflicts; run Apply to choose cleanup and merge policy'
    )
output.print_md('')

total = migrated = skipped_no_change = errored = 0

for bundle_dir, script_path in iter_bundles(target):
    total += 1
    rel = op.relpath(bundle_dir, target)

    try:
        incoming = read_script_metadata(script_path)
    except Exception as ex:
        errored += 1
        output.print_md('- **ERROR** reading `{}`: `{}`'.format(rel, ex))
        continue

    if not incoming:
        skipped_no_change += 1
        continue

    bundle_yaml = op.join(bundle_dir, 'bundle.yaml')
    existing = None
    if op.isfile(bundle_yaml):
        try:
            existing = pyryaml.load_as_dict(bundle_yaml)
        except Exception as ex:
            errored += 1
            output.print_md('- **ERROR** loading existing yaml in `{}`: `{}`'.format(rel, ex))
            continue

    merged, changed, skipped = merge_yaml(
        existing, incoming, policy, rel, dry_run=dry_run,
    )
    if skipped:
        skipped_no_change += 1
        continue
    if not changed:
        skipped_no_change += 1
        continue

    key_list = ', '.join('`{}`'.format(k) for k in incoming.keys())
    if dry_run:
        migrated += 1
        output.print_md(
            '- Would migrate `{}` ({} key(s): {})'.format(rel, len(incoming), key_list)
        )
        continue

    try:
        pyryaml.dump_dict(merged, bundle_yaml)
    except Exception as ex:
        errored += 1
        output.print_md('- **ERROR** writing yaml in `{}`: `{}`'.format(rel, ex))
        continue

    if cleanup_mode:
        try:
            ok, warn = apply_script_cleanup(script_path, cleanup_mode)
            if warn:
                output.print_md('- WARN cleanup for `{}`: {}'.format(rel, warn))
            elif not ok:
                output.print_md('- WARN cleanup made no changes for `{}`'.format(rel))
        except Exception as ex:
            output.print_md('- WARN cleanup failed for `{}`: `{}`'.format(rel, ex))

    migrated += 1
    output.print_md('- Migrated `{}` ({} key(s))'.format(rel, len(incoming)))

output.print_md('')
output.print_md('### Done')
output.print_md('- Bundles scanned: **{}**'.format(total))
if dry_run:
    output.print_md('- Would migrate: **{}**'.format(migrated))
else:
    output.print_md('- Migrated: **{}**'.format(migrated))
output.print_md('- No changes: **{}**'.format(skipped_no_change))
output.print_md('- Errors: **{}**'.format(errored))
