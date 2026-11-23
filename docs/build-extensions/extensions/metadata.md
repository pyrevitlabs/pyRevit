# Extension metadata

The metadata about a UI extension is stored in an `extension.json` file in the extension root. The file is optional.

Settings for the extension as a bundle, such as its layout, go in a `bundle.yaml` file next to it. See [Bundle metadata](../bundles/metadata.md).

## The extension.json file

```json
{
    "type": "extension",
    "name": "pyRevitTools",
    "description": "IronPython Scripts for Autodesk Revit",
    "author": "Ehsan Iran-Nejad",
    "author_profile": "https://keybase.io/ein",
    "url": "https://github.com/pyrevitlabs/pyRevit.git",
    "website": "http://pyrevitlabs.github.io/pyRevit/",
    "image": "",
    "rocket_mode_compatible": "True",
    "default_enabled": "True",
    "templates": {
        "author": "Ehsan Iran-Nejad",
        "docpath": "https://www.youtube.com/watch?v="
    },
    "dependencies": []
}
```

| Key | Meaning |
|---|---|
| `type` | `extension` for a UI extension, `lib` for a library extension |
| `name`, `description`, `author`, `author_profile`, `url`, `website`, `image` | Shown in the Extensions manager |
| `rocket_mode_compatible` | Whether the extension can run in Rocket mode |
| `default_enabled` | Whether the extension is enabled when it is first found |
| `engine` | Python engine for the whole extension, for example `"cpython"` |
| `templates` | Values the child bundles can use in their metadata, see below |
| `dependencies` | Names of the extensions this one depends on |
| `authusers`, `authgroups` | Users and groups allowed to load the extension |

## Using Liquid Templates

Extensions can define template values for all their child bundles. These are key and value pairs under the `templates` key of the extension file. The child bundle files can use them in their own metadata.

For example, when the help URLs of the tools in an extension all point to YouTube videos, the common part of the URL can be defined once.

**Inside Extension File**

```json
"templates": {
    "youtube": "https://www.youtube.com/watch?v=",
    "author": "Ehsan Iran-Nejad"
}
```
