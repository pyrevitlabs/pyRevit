# Bundle metadata

!!! tip ""

    **pyRevit History**: Initially, pyRevit bundles were all written in IronPython, and the metadata about the bundle were included inside the python code as global variables. For example, the `__title__` global variable would define a title for the tool in Revit UI. With the release of pyRevit 4.7, many more bundle types and languages were supported and a unified way was needed to provide this metadata. This page describes the unified Bundle Metadata File. The *in-script* global variables is still supported for IronPython for backward compatibility and convenience.  

    See [Anatomy of IronPython Scripts](../scripting/ironpython.md)  for more information on in-script global variables.

The most important data about a bundle is the **Bundle Type**, and the **Bundle Content** (script, or other types of content). The naming conventions is the mechanism to provide this information to pyRevit runtime. For example for an IronPython command bundle, the folder extension (`*.pushbutton`) defines the bundle type, and the `*script.py` file defines the bundle content to be executed.

## Bundle File

Bundle Metadata File (***Bundle File*** for short) is a [YAML](https://learnxinyminutes.com/docs/yaml/)  `*.yaml` file that provides the extended, and optional metadata about the bundle. This metadata is used to improve the user experience, and provide more information about the bundle requirements and dependencies to the pyRevit runtime.

### Improving Bundle User Experience

Bundle file can improve the user interface of a bundle, by providing a title, tooltip message, help url, and information about the authors. It is important to mention that the default UI title for a bundle is extracted from the bundle folder (`MyTool` in `MyTool.pushbutton`), but the bundle file can override that to define a better formatted name. One of the most popular cases for setting the title in a bundle file is when a line break (`\n`) is needed to better format the button name e.g. `My\nTool`.

```yaml
# bundle title
title: "Make\nPattern"

# title can also be in various locales
# pyRevit pulls the correct name based on Revit language
title:
  en_us: Test Bundle (Custom Title)
  chinese_s: 测试包

# bundle tooltip
tooltip: Create new patterns in Revit
# tooltip can also be in various locales
# pyRevit pulls the correct tooltip based on Revit language
tooltip:
  en_us: Create new patterns in Revit
  chinese_s: 创建新模式

# bundle highlighting ('new' or 'updated')
# Revit UI will show a orange marker on the button and a border around the tooltip
highlight: new      # highlight as new
highlight: updated  # highlight as updated

# bundle help url
help_url: "https://www.youtube.com/watch?v=H7b8hjHbauE&t=8s&list=PLc_1PNcpnV57FWI6G8Cd09umHpSOzvamf"
# help url can also be in various locales
# pyRevit pulls the correct help url based on Revit langauge
help_url:
  en_us: "https://www.youtube.com/watch?v=H7b8hjHbauE&t=8s&list=PLc_1PNcpnV57FWI6G8Cd09umHpSOzvamf"
  chinese_s: "https://www.youtube.com/watch?v=H7b8hjHbauE&t=8s&list=PLc_1PNcpnV57FWI6G8Cd09umHpSOzvamf"

# bundle author
author: Ehsan Iran-Nejad

# bundle author can also be a list of authors
authors:
  - John Doe
  - Ehsan Iran-Nejad
```

Use the locale codes below for the various languages

**Supported Locale Codes**

| Revit Language | Locale Codes |
|---|---|
| English USA | english,en\_us |
| English Great Britain | en\_gb |
| Deutsch / German | german,de\_de |
| español / Spanish | spanish,es\_es |
| français / French | french,fr\_fr |
| italiano / Italian | italian,it\_it |
| Nederlands / Dutch | dutch,nl\_be,nl\_nl |
| 简体中文 / Chinese Simplified | chinese,chinese\_s |
| 繁體中文 / Chinese Traditional | chinese,chinese\_t |
| 日本語 / Japanese | japanese,ja |
| 한국어 / Korean | korean,ko |
| Русский / Russian | russian,ru |
| Čeština / Czech | czech,cs |
| Polski / Polish | polish,pl |
| Magyar / Hungarian | hungarian,hu |
| Português do Brasil / Brazilian Portuguese | portuguese\_brazil,brazilian,portuguese,pt\_br,pt\_pt |
| Български / Bulgarian | bulgarian,bg |
| فارسی / Farsi | farsi,persian,fa |
| العربیه / Arabic | arabic,ar |
| Українська / Ukrainian | ukrainian,uk |

#### Context Directives

The bundle file can also set the execution context of the bundle. This helps activating the bundle, where the appropriate conditions are available. For example a bundle can request to be activated only when selection is available.

!!! tip ""

    See [Bundle Context](context.md) for more information on available context directives.

**Example**

```yaml
# context directives are listed under `context` key, the order does not matter
context:
  - Walls
  - Text Notes
```

### Bundle Layout

The bundle file can also set the order of all the childern bundles in the UI:

!!! tip ""

    See [Bundle Layout](layout.md) for more information on the layout directives.

**Example**

```yaml
layout:
  - PushButton A
  - PushButton B
  - PullDown A
```

### Bundle Environment Configs

#### Supported Revit Versions

Bundle file can define the range of Revit versions that support the bundle. pyRevit will not load the bundle if it is not supported under the running Revit. In the example below, the bundle will be loaded with Revit 2022 up to 2025 and is expected to work with the APIs for these versions.

```yaml
# minimium supported Revit version
min_revit_version: 2022

# maximum supported Revit version
max_revit_version: 2025
```

Bundle file can also set the state of the bundle. pyRevit user can decide whether to load the *Beta* bundles when starting Revit or not.

```yaml
is_beta: false
```

### Using Liquid Templates

Bundles can define template values for all their child command bundles (and IronPython global variables). These are key, value pairs that are set inside the bundle file. The child bundle files can user the liquid tags `{{ tag }}` to reuse these template values.

For example, imagine all the help URLs for a series of tools, all direct to YouTube videos. Considering that YouTube videos have similar URLs that are formatted as `https://www.youtube.com/watch?v=<video_id>`, and the only unique part is the `<video_id>`, a good way to simplify these URLs is to define the repeated part of the URL (`https://www.youtube.com/watch?v=`) as a template and reuse the value in help URLs of the child bundles. In the examples below the liquid template tag `{{youtube}}` will be replaced with the value of `youtube` defined in the parent bundle file (`https://www.youtube.com/watch?v=`) when pyRevit is loading.

**Inside Parent Bundle File**

```yaml
youtube: https://www.youtube.com/watch?v=
```

**Inside Child Bundle Files**

```yaml
help_url: "{{youtube}}H7b8hjHbauE"
# final help url: https://www.youtube.com/watch?v=H7b8hjHbauE
```

```yaml
help_url: "{{youtube}}po0lCldSGmk"
# final help url: https://www.youtube.com/watch?v=po0lCldSGmk
```

You can also group all your template values under the `templates` key. This cleans up the metadata files.

```yaml
templates:
  youtube: https://www.youtube.com/watch?v=
  author: Ehsan Iran-Nejad
```
