# Extensions

#### Finding Extensions

```powershell
pyrevit extensions search <search_pattern>
pyrevit extensions (info | help | open) <extension_name>

$ pyrevit extensions search apex    # search for an extension with apex in name
$ pyrevit extensions info apex      # get info on extension with apex in name
```

- `<search_pattern>`: Regular Expression (REGEX) pattern to search for

#### Installing Extensions

```powershell
pyrevit extend <extension_name> [--dest=<dest_path>] [--branch=<branch_name>] [--log=<log_file>]

$ pyrevit extend pyApex --dest="C:\pyRevit\Extensions"     # install pyApex extension
```

- `--dest`: This is optional. If not provided, pyRevit attempts to install extension at the defautl third-party extension folder (usually `%appdata%/pyRevit/Extensions`). The destination directory will be added to pyRevit extensions search paths automatically and will be loaded on the next pyRevit reload.
- `--branch`: Optional. Specific branch of the extension repo to be installed. Defaults to `master` branch if not provided.

To installing your own extensions, you’ll need to specify what type if extension you’re installing (ui or lib) and provide the url:

```powershell
pyrevit extend (ui | lib) <extension_name> <repo_url> [--dest=<dest_path>] [--branch=<branch_name>] [--log=<log_file>] [(--username=<username> --password=<password> | --token=<auth_token>)] [--persist-credentials]

$ pyrevit extend ui MyExtension "https://www.github.com/my-extension.git" --dest="C:\pyRevit\Extensions"
```

!!! warning ""

    **Preferred:** `--token=<token>` use a fine grained token with proper scope

!!! warning ""

    **Deprecated in Github:**  If you are cloning your extension from a private repository, you can provide the `--username` and `--password` to the repo account as well.

#### Managing Installed Extensions

List all installed extensions:

```powershell
pyrevit extensions
```

Delete an extension completely using:

```powershell
pyrevit extensions delete <extension_name> [--log=<log_file>]

$ pyrevit extensions delete pyApex
```

Set origin url on an extension using:

```powershell
pyrevit extensions origin <extension_name> --reset [--log=<log_file>]
pyrevit extensions origin <extension_name> [<origin_url>] [--log=<log_file>]

$ # changing origin remote url for `pyApex` extension
$ pyrevit extensions origin pyApex https://www.git.com/repo.git  

$ # resetting origin remote url back to default for `pyApex` extension
$ pyrevit extensions origin pyApex --reset
```

Add, remove extension search paths for all your existing extensions:

```powershell
pyrevit extensions paths
pyrevit extensions paths forget --all [--log=<log_file>]
pyrevit extensions paths (add | forget) <extensions_path> [--log=<log_file>]

$ pyrevit extensions paths add "C:\pyRevit\MyExtensions"    # add a search path
$ pyrevit extensions paths forget --all         # forget all search paths
```

Enable or Disable an extension in pyRevit config file:

```powershell
pyrevit extensions (enable | disable) <extension_name> [--log=<log_file>]

$ pyrevit extensions enable pyApex
```

Getting info, opening help or installed directory:

```powershell
pyrevit extensions (info | help | open) <extension_name>

$ pyrevit extensions info apex      # get info on extension with apex in name
$ pyrevit extensions help apex      # open help page
$ pyrevit extensions open apex      # open path in file explorer
```

`info` and `help` search the extension sources first and then the installed extensions, so they also answer for an installed extension that no source lists.

#### Updating Extensions

```powershell
pyrevit extensions update (--all | <extension_name>) [--log=<log_file>]

$ pyrevit extensions update --all       # update all installed extension
$ pyrevit extensions update pyApex      # update pyApex extension
```

#### Managing Extensions Lookup Sources

`pyrevit` can lookup in other places when searching for extensions. This means that you can define a `json` file with all your private extensions and add the path to the `pyrevit` sources. Your extensions will show up in search results from then on and can be installed by their name:

```powershell
pyrevit extensions sources
pyrevit extensions sources forget --all [--log=<log_file>]
pyrevit extensions sources (add | forget) <source_json_or_url> [--log=<log_file>]

$ pyrevit extensions sources add "https://www.github.com/me/extensions.json"
```

- `<source_json_or_url>`: Can be a `json` file path or web url. `add` registers it, then reads it once and prints a warning when it cannot be reached or holds no extension list; the source stays registered.
