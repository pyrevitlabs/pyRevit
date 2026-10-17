## Proposing an External pyRevit Extension

If your tool is too specific to be included in the main pyRevit toolset, you can still share it as an external extension so others can discover and install it.

See [Extensions](extensions.md) for how to structure and author the extension itself; this page covers listing it in the catalog.

### Steps

1. Structure your repository so the `.tab` folder is at the root.
2. Include an `extension.json` file in your repo.
3. Create a branch from the pyRevit repository.
4. Navigate to `extensions/extensions.json`.
5. Add your extension entry to the `"extensions"` list.
6. Open a pull request against the `develop` branch.

### Example Entry

A typical entry in `extensions/extensions.json` looks like this:

    {
        "builtin": "False",
        "type": "extension",
        "rocket_mode_compatible": "True",
        "name": "YourExtensionName",
        "description": "Short description of what your extension does",
        "author": "Your Name or Organization",
        "author_profile": "https://github.com/your-profile",
        "url": "https://github.com/yourname/your-extension.git",
        "website": "https://your-project-website-or-repo",
        "image": "",
        "dependencies": []
    }

### Review Process

Once you submit the PR, we'll review your extension and its metadata against the
[acceptance criteria](#acceptance-criteria) below. If everything checks out, we'll
add it to the directory so others can easily find and use it. It's worth running
through the list before you open your PR, since it's what we'll be doing too.

### Acceptance Criteria

To keep the catalog safe and reliable for everyone, every listed extension needs to
meet the requirements below. The recommended items aren't blockers, but they make
your extension feel at home in pyRevit and may come up as review feedback.

#### Required

- **Open source.** The repository URL in `extensions.json` must be publicly
  accessible and contain the full source code of the extension.
- **Source for all compiled binaries.** Any `.dll` shipped in a `bin/` folder must
  have its source available in the same repository (or a clearly linked one).
  Binary-only extensions can't be reviewed for security and won't be accepted.
- **Valid structure.** As described in the steps above, the `.tab` folder sits at
  the repository root, and the bundle layout follows the conventions in
  [Extensions](extensions.md) (`*.pushbutton`, `*.panel`, etc.).
- **`extension.json` manifest.** Include an `extension.json` at the extension root
  declaring `name`, `description`, `author`, `url`, and `dependencies` (an empty
  list if there are none).
- **Correct catalog entry.** The entry in `extensions/extensions.json` must be
  complete and accurate. Set `rocket_mode_compatible` to `"True"` only if you've
  verified the extension works in rocket mode.
- **License.** The repository must include a license file.
- **Working installation.** The extension must install and load without errors via
  `pyrevit extend` on a supported Revit version.
- **English titles and tooltips.** Provide `title` and `tooltip` in `bundle.yaml`
  with at least an `en_us` entry.

#### Recommended

- **Dark theme support.** Provide an `icon.dark.png` alongside every `icon.png`,
  and `background_dark` colors for any `*.panel` bundle that sets a custom
  `background`.
- **Additional languages.** Where feasible, offer `title` and `tooltip` as locale
  maps (e.g. `en_us`, `fr_fr`, `de_de`) beyond English.
- **Revit version bounds.** Declare `min_revit_version` / `max_revit_version` in
  `bundle.yaml` when the tool depends on version-specific API behavior.
- **Usage context.** Set `context` in `bundle.yaml` so buttons are greyed out when
  they can't run (e.g. `doc-project`, `selection`), rather than failing at click
  time.
- **Accurate dependency lists.** Keep the `dependencies` array identical in
  `extension.json` and the `extensions.json` entry, listing any required library
  extensions (`*.lib`).
- **Documentation.** Include a `README` and, ideally, a `*help.*` file or
  `help_url` in `bundle.yaml` so users can reach documentation from the tooltip.
- **No side effects on load.** `startup.py` should not make network calls, write
  outside the extension folder, or change the user's pyRevit configuration without
  disclosure.