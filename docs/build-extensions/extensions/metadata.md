# Extension metadata

The metadata about a UI Extension bundle - as shown above - is stored in a `extension.yaml` file inside the extension root.

## Extension File

Extension Metadata File (*Extension File* for short) is a [YAML](https://learnxinyminutes.com/docs/yaml/)  `*.yaml` file that provides the extended, and optional metadata about the extension. This metadata is used to improve the user experience, and provide more information about the extension type, requirements, and dependencies to the pyRevit runtime.

!!! warning ""

    extension.json file is deprecated and will be removed in the next pyRevit major release. Convert your JSON metadata files to YAML

### Defining the Extension Type

The most important part of the metadata is to define the extension type and requirements.

```yaml
# UI Extensions
type: extension
rocket_mode_compatible: true

# Library Extensions
type: extension

# Run Extensions
type: extension

# all extensions types can define a list of dependencies
# this is a list of other extensions, that this extension is dependent on
dependencies:
  - ExtensionName
  - ExtensionName
  - ...
```

### Improving Bundle User Experience

Extension file can improve the user interface of an extension, by providing a title, description, and information about the authors.

```yaml
name: pyRevitTools
description: IronPython Scripts for Autodesk Revit
author: Ehsan Iran-Nejad
author_profile: https://keybase.io/ein
url: https://github.com/pyrevitlabs/pyRevit.git
website: http://eirannejad.github.io/pyRevit/
image: https://ein.sh/pyRevit/pyRevitLogo.svg
```

### Using Liquid Templates

Extensions can define template values for all their child bundles (and IronPython global variables). These are key, value pairs that are set inside the extension file. The child bundle files can use the liquid templating tags `{{}}` to reuse these template values.

For example, imagine all the help URLs for a series of tools under an extension, all direct to YouTube videos. Considering that YouTube videos have similar URLs that are formatted as `https://www.youtube.com/watch?v=<video_id>`, and the only unique part is the `<video_id>`, a good way to simplify these URLs is to define the repeated part of the URL (`https://www.youtube.com/watch?v=`) as a template and reuse the value in help URLs of the child bundles. In the examples below the liquid template tag `{{youtube}}` will be replaced with the value of `youtube` defined in the extension file (`https://www.youtube.com/watch?v=`) when pyRevit is loading.

**Inside Extension File**

```yaml
youtube: https://www.youtube.com/watch?v=
```

You can also group all your template values under the `templates` key. This cleans up the metadata files.

```yaml
templates:
  youtube: https://www.youtube.com/watch?v=
  author: Ehsan Iran-Nejad
```
