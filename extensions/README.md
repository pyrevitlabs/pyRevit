This is where pyRevit native extensions are located. pyRevit includes a gui extension manager that allows installation of registered extensions in this folder or in a user-selected folder. 

There are two extension types:

- **UI Extensions:** (.extension) contain tools that are available in Revit's user interface.
- **Library Extensions:** (.lib) contain IronPython modules that are shared between all extensions.

### Extension Definition File: `extensions.json`

Extensions need to be registered in this json database. The properties below, need to be defined for every extension.

- UI extensions need to set `"type": "extension"` and Library extensions should set `"type": "lib"`.
- `"dependencies"` should list the extension name for all required extensions


``` json
{
"extensions":
    [
        {
        "builtin": "True",
        "type": "extension",
        "name": "pyRevitTools",
        "description": "IronPython Scripts for Autodesk Revit",
        "author": "Ehsan Iran-Nejad",
        "author-url": "https://keybase.io/ein",
        "url": "https://github.com/eirannejad/pyRevit.git",
        "website": "http://eirannejad.github.io/pyRevit/",
        "image" : "",
        "dependencies": []
        }
    ]
}
```

-testing push
