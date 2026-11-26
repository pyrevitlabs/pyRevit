# Bundle lib and bin

Each pyRevit bundle can include a `lib/` or `bin/` subdirectory that can contain modules, and binaries (respectively) required by the main bundle. These directories are intended to help making the bundles provide their own dependencies and be self-sufficient. Please be aware of the assembly version and namespace conflicts when loading multiple versions of the same dll assemblies in Revit environment.

When grouping Command Bundles inside UI Bundles, the path of the parent bundle `lib/` or `bin/` subdirectories are also included in the search path for all children directory. For example, a `lib/` subdirectory inside a **Panel Button** can contain all the necessary python modules for the child bundles.

```text
MyPanel.panel/
├── lib/
│   └── some_python_module.py
│
├── bin/
│   └── SomeRequired.dll
│
├── MyButton1.pushbutton/
├── MyButton2.pushbutton/
└── MyButton3.pushbutton/
```

### Python Bundles

The `lib/` subdirectory for bundles that include a python script can contain python modules, or binaries that are loaded by the main script.

### .NET Bundles

The `bin/` subdirectory can include dll assemblies required to dynamically compile the main script.

### Invoke Button Bundles

The `bin/` subdirectory can include dll assemblies referenced by the invoke bundle.
