# Proposal: Decouple UI Layout from Folder Structure



## Goals

- Reduce folder structure complexity
- Eliminate the direct connection between folder hierarchy and UI layout
- Allow admins (and optionally users) to customize layouts without forking
- Enable hiding tools and potentially combining tools from multiple repos
- Maintain full backward compatibility with existing extensions

---

## Current Structure

Extensions require a 4-level folder hierarchy (5! for stacks and button groups) that both stores tools and defines UI:

```
MyExtension.extension/
  MyTab.tab/
    MyPanel.panel/
      MyButton.pushbutton/
        bundle.yaml
        script.py
```

The folder name suffix determines the UI element type, and folder nesting determines the UI hierarchy.

---

## Proposed Structure

Decouple layout from tools by introducing layout YAML files at the extension root and a flat `tools/` directory.

```
MyExtension.extension/
  extension_layout.yaml       # declares tab/panel structure, references panel files
  MyPanel.panel.yaml          # panel-level tool layout (at extension root)
  OtherPanel.panel.yaml
  tools/                      # flat tool storage, subfolders for organization only
    MyButton.pushbutton/
      bundle.yaml
      script.py
    Utilities/                # plain subfolder for grouping (no postfix = ignored)
      AnotherTool.pushbutton/
        bundle.yaml
        script.py

```

### Extension Layout File (`extension_layout.yaml`)

Declares the full tab and panel structure. Panel layouts can be inlined or split into separate files for large extensions.

```yaml
extension:
  name: "My Extension"
  tabs:
    - name: "My Tab"
      panels:
        - name: "My Panel"
          layout_file: "MyPanel.panel.yaml"
        - name: "Small Panel"
          layout:                         # inline for simple panels
            - MyButton
            - AnotherTool
```

### Panel Layout File (`MyPanel.panel.yaml`)

```yaml
layout:
  - MyButton
  - AnotherTool
  - Spy                 # references Spy.pulldown (self-contained with children)
  - ">>>>>"             # existing slideout separator still supported
  - UtilityTool
```

### Tool Bundle (`bundle.yaml`)

One new optional field — `name` — used for layout reference. All other fields unchanged.

```yaml
name: "MyButton"          # optional: used for layout lookup; derived from folder name if absent
title: "My Button"
tooltip: "Does something useful"
context: zero-doc
author: "Author Name"
```

If `name` is absent, it is derived from the folder name by stripping the postfix
(e.g. `My Button.pushbutton` → `"My Button"`).

---



### Eliminated as Structural Folders (moved to YAML)

| Postfix  | Replacement                                               |
| -------- | --------------------------------------------------------- |
| `.tab`   | Declared in `extension_layout.yaml`                       |
| `.panel` | Declared in `extension_layout.yaml` or `.panel.yaml` file |
| `.stack` | Expressed as a grouping directive within a panel layout   |

---

## Tool Discovery

When `extension_layout.yaml` is present, pyRevit uses layout-based discovery:

1. Crawl `tools/` recursively
2. Skip plain subfolders (no recognized postfix) — these are organizational only
3. On finding a container tool (`.pulldown`, `.splitbutton`, `.splitpushbutton`):
   - Index it by `name` field or derived folder name
   - Crawl its children; those children belong to the container, not the flat index
4. On finding a leaf tool — index it and stop recursing
5. Build a name → component map used to resolve layout references

Tools in `tools/` that are not referenced by any layout file are silently ignored
(or optionally logged as a warning).

---

## Backward Compatibility

When `extension_layout.yaml` is **absent**, pyRevit falls back to the existing
folder-hierarchy discovery mode unchanged. Existing extensions require no modification.

This allows incremental adoption: a single extension can migrate tool-by-tool,
moving tools from `.tab` subfolders into `tools/` as desired, while keeping
`extension_layout.yaml` as the authoritative layout declaration.

---

## Settings UI

New options in the pyRevit Settings dialog:

- **Import Custom Layout** — load an `extension_layout.yaml` (or panel YAML) from disk,
  replacing the active layout for that extension. Enables admins to distribute a
  curated layout without touching extension source files.
- **Reset to Default Layout** — discard any imported layout and revert to the
  layout bundled with the extension.
- **Include Legacy Folders** (`yes` / `no`) — when enabled, pyRevit also crawls
  `.tab` subfolders alongside `tools/` and merges discovered tools into the index.
  Useful during incremental migration of an existing extension.

---

## CLI

New subcommands under `pyrevit extensions` (or a new `pyrevit layout` group):

```bash
# Generate an extension_layout.yaml from an existing legacy folder structure.
# Output can be used as a starting point for customization.
pyrevit layout generate <extension-name-or-path> [--output <file>]

# List all tools discoverable in an extension.
# --source controls where to look: tools (tools/ dir), legacy (.tab folders), or both
pyrevit layout list-tools <extension-name-or-path> [--source tools|legacy|both]
```

`generate` produces a layout file that exactly mirrors the current folder hierarchy,
giving extension authors a zero-effort migration path and giving admins a base to
customize from.

`list-tools` is primarily a diagnostic aid — useful for verifying what pyRevit can
see before authoring or debugging a layout file.

---

## Required Changes to `pyrevitlib`

### `pyrevitlib/pyrevit/extensions/genericcomps.py`

- Add `name` field parsing in `_read_bundle_metadata()`
- Add folder-name derivation fallback when `name` is absent

### `pyrevitlib/pyrevit/extensions/parser.py`

- Add `parse_tools_dir()`: recursive crawler for `tools/`, builds name → component index
- Add `parse_layout_file()`: reads `extension_layout.yaml` and `.panel.yaml` files
- Modify `_parse_for_components()` to dispatch to new layout-based path when layout file is detected

### `pyrevitlib/pyrevit/extensions/components.py`

- Update `Extension._update_from_directory()` to detect `extension_layout.yaml` and store layout config
- Update `Extension._calculate_extension_dir_hash()` to include `tools/` and layout files

### `pyrevitlib/pyrevit/extensions/extensionmgr.py`

- No structural changes required; the parser changes are transparent to this layer

### `pyrevitlib/pyrevit/loader/uimaker.py`

- No changes required; UI creation walks the same component tree regardless of how it was built
