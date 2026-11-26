# Bundle layout

!!! warning ""

    The separate `_layout` file is no longer read. Define the layout under the `layout` key of the bundle file (`bundle.yaml`), as shown here.  
    See [Bundle Metadata](metadata.md) for the other keys of the bundle file.

Bundle Layout is a method to provide directives on how the child bundles should be ordered in Revit UI.

```yaml
MyCommands.pulldown/
├── PushButton A.pushbutton
├── PushButton B.pushbutton
├── PushButton C.pushbutton
└── bundle.yaml                  # bundle metadata file contains the layout directives
```

For example, below are the layout directives for a UI bundle that includes a few other bundles. Buttons on the Revit UI will be placed according to this layout. The top-most bundles are created first (From left to right in Revit UI), following down the list.

```yaml
layout:
  - PushButton A
  - PushButton B
  - PullDown A
  - ---                    # see Separator Lines
  - PullDown B
  - Stack3 A
  - >>>                    # see Slide-out Panel
  - PushButton C
  - PullDown C
```

### Unlisted Bundles

A `layout` is also the list of what appears on the ribbon. A child bundle that it does not list is hidden, so you can keep a bundle in the extension without showing it. This applies to every bundle that has a `layout`, from a tab hiding panels to a pull-down or stack hiding buttons. A bundle without a `layout` shows all of its children.

Names must match the bundle folder name without its extension, including upper and lower case.

A hidden command is still built, so it can still be run from code. A `.nobutton` bundle does not need to be listed.

!!! warning ""

    pyRevit 6.0 to 7.1 also showed unlisted bundles, after the listed ones. If a button, panel or tab disappears after updating, add its name to the `layout`.

### Separator Lines
**Panel** and **Pull Down Bundle** layout files can contain a directive to place a vertical (in panels) or horizontal (in pull-downs) separator line in between buttons. `---` This line will add a separator to the interface. You can use more than 3 `-` characters. For example `----------` still works as a separator.

```yaml
layout:
  - PushButton A
  - PushButton B
  - PullDown A
  - ---
  - PushButton B
```

### Slide-out Panel
**Panel Bundle (Only)** layout file can contain a directive to place buttons inside the slide-out area of the panel. `>>>` Any bundle after this line will be created inside the slide-out. You can use more than 3 `>` characters. For example `>>>>>>>>>` still works as a slide-out

!!! warning ""

    `>>>` must be encapsulated inside double quotes as `">>>"` to comply with YAML format

```yaml
layout:
  - PushButton A
  - PushButton B
  - PullDown A
  - ">>>"
  - PushButton C
  - PullDown C
```

### Layout Directives

Layouts can also contain directives on renaming buttons, or their placement in relation to other buttons on the toolbar. This is especially helpful to direct pyRevit to place your buttons in relation to buttons from other extensions. These directives are placed inside the `[]`

- To rename a bundle add the **Title Directive** following this format →  `[title:<new name>]`
- To place your bundle before another bundle add the **Before Directive** following this format →  `[before:<other bundle name>]`
- To place your bundle after another bundle add the **After Directive** following this format →  `[after:<other bundle name>]`
- To place your bundle before all other bundles add the **BeforeAll Directive** following this format →  `[beforeall:]`
- To place your bundle after all other bundles add the **AfterAll Directive** following this format →  `[afterall:]`

```yaml
# examples
# title directive (\n is escape code for new line)
# this directive renames the bundle "Misc Tests" -> "Third-Party"
#                                                    " Unittests "
layout:
  - Misc Tests[title:Third-Party\nUnittests]

# before directive
# this directive places "Manage Tags" before "Modify"
layout:
  - Manage Tags[before:Modify]

# beforeall directive
# this directive places "pyRevit" before everything else
layout:
  - pyRevit[beforeall:]
```
