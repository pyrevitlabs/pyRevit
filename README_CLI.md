# pyRevit Command Line Tool Help

##### Version 0.9.6.0

`pyrevit` is the command line tool, developed specifically to install and configure pyRevit in your production/development environment. Each section below showcases a specific set of functionality of the command line tool.

- [pyRevit Command Line Tool Help](#pyrevit-command-line-tool-help)
        - [Version 0.9.6.0](#version-0960)
  - [Getting Help](#getting-help)
    - [pyrevit CLI version](#pyrevit-cli-version)
    - [pyRevit Online Resources](#pyrevit-online-resources)
  - [Managing pyRevit clones](#managing-pyrevit-clones)
    - [Installing pyRevit](#installing-pyrevit)
      - [Installing Custom Clones](#installing-custom-clones)
    - [Maintaining Clones](#maintaining-clones)
      - [Managing Git Clones](#managing-git-clones)
      - [Updating Clones](#updating-clones)
    - [Attaching pyRevit to Installed Revits](#attaching-pyrevit-to-installed-revits)
  - [Managing pyRevit extensions](#managing-pyrevit-extensions)
    - [Finding Extensions](#finding-extensions)
    - [Installing Extensions](#installing-extensions)
    - [Managing Installed Extensions](#managing-installed-extensions)
      - [Updating Extensions](#updating-extensions)
    - [Managing Extensions Lookup Sources](#managing-extensions-lookup-sources)
  - [Getting Environment Info](#getting-environment-info)
  - [Configuring pyRevit](#configuring-pyrevit)
    - [Configuring Sensitive Tools](#configuring-sensitive-tools)
    - [Configuring Your Own Options](#configuring-your-own-options)
    - [Using Config as Seed](#using-config-as-seed)
  - [Extra Revit-Related Functionality](#extra-revit-related-functionality)
  - [Creating pyRevit extension bundles](#creating-pyrevit-extension-bundles)
    - [Creating your own bundle templates](#creating-your-own-bundle-templates)
  - [CLI Execution of Python Scripts](#cli-execution-of-python-scripts)
    - [Running a Script on Revit Models](#running-a-script-on-revit-models)
  - [Clear pyRevit Cache Files](#clear-pyrevit-cache-files)
  - [Logging CLI Debug Messages](#logging-cli-debug-messages)
  - [Creating Shortcuts](#creating-shortcuts)


## Getting Help
There is a lot of commands and options available in `pyrevit`. These functionalities are grouped by their function. This document will guide you in using these commands and options based on what you're trying to achieve. See the sections below. A full list can be obtained by running:

``` powershell
pyrevit help
pyrevit (-h | --help)

$ pyrevit help          # will take you to this page

$ pyrevit --help        # OR
$ pyrevit -h            # will print help to console
```

You can also list the help for any of the pyrevit cli commands:

``` powershell
pyrevit COMMAND --help

$ pyrevit clones --help

Manage pyRevit clones

    Usage:
        pyrevit clones [--help]
        pyrevit clones (info | open) <clone_name>
        pyrevit clones add <clone_name> <clone_path> [--log=<log_file>]
        pyrevit clones forget (--all | <clone_name>) [--log=<log_file>]
        pyrevit clones rename <clone_name> <clone_new_name> [--log=<log_file>]
        pyrevit clones delete [(--all | <clone_name>)] [--clearconfigs] [--log=<log_file>]
        pyrevit clones branch <clone_name> [<branch_name>] [--log=<log_file>]
        pyrevit clones version <clone_name> [<tag_name>] [--log=<log_file>]
        pyrevit clones commit <clone_name> [<commit_hash>] [--log=<log_file>]
        pyrevit clones origin <clone_name> --reset [--log=<log_file>]
        pyrevit clones origin <clone_name> [<origin_url>] [--log=<log_file>]
        pyrevit clones update (--all | <clone_name>) [--log=<log_file>] [--gui]
        pyrevit clones deployments <clone_name>
        pyrevit clones engines <clone_name>
```

### pyrevit CLI version

To determine the version of your installed `pyrevit` cli tool:

``` powershell
pyrevit (-V | --version)

$ pyrevit -V            # OR
$ pyrevit --version
 pyrevit v0.1.5.0
```

### pyRevit Online Resources

To access a variety of online resource on pyRevit, use these commands

``` powershell
pyrevit (blog | docs | source | youtube | support)

$ pyrevit blog      # pyRevit blog page
$ pyrevit docs      # pyRevit documentation
$ pyrevit source    # pyRevit source code
$ pyrevit youtube   # pyRevit YouTube channel
$ pyrevit support   # pyRevit suppport page for pyRevit patrons
```

## Managing pyRevit clones

### Installing pyRevit

``` powershell
pyrevit clone <clone_name> <deployment_name> [--dest=<dest_path>] [--source=<archive_url>] [--branch=<branch_name>] [--log=<log_file>]
pyrevit clone <clone_name> [--dest=<dest_path>] [--source=<repo_url>] [--branch=<branch_name>] [--log=<log_file>]
```
`pyrevit` can maintain multiple clones of pyRevit on your system. In order to do so, it needs to assign a name to each clone (`<clone_name>`). You'll set this name when cloning pyRevit or when adding an existing clone to `pyrevit` registry. From then on you can always refer to that clone by its name.

Let's say I want one clone of pyRevit `master` branch as my master repo; one clone of pyRevit without the full git repository (much smaller download) as my main repo; and finally one clone of the `develop` branch of pyRevit as my development repo.

Let's create the master clone first. This will be a full git repo of the master branch.

``` powershell
$ # master is <clone_name> that we're providing to pyrevit cli
$ # we're not providing any value for <dest_path>, therefore pyrevit cli will clone
$ # pyRevit into the default path (%APPDATA%/pyRevit)
$ pyrevit clone master
```

Now let's create the main clone. This one does not include the full repository. It'll be cloned from the ZIP archive provided by the Github repo:

``` powershell
$ # we're providing the <dest_path> for this clone
$ # we're using the `base` deployment in this example which includes the base pyRevit tools
$ pyrevit clone main base --dest="C:\pyRevit\main"
```

- `<deployment_name>`: When provided the tool installs from the ZIP archive and NOT the complete git repo. This is the preferred method and is used with the native pyRevit installer. pyRevit has multiple deployments. These deployments are defined in the [pyRevitfile](https://github.com/eirannejad/pyRevit/blob/develop/pyRevitfile) inside the pyRevit repo. Each deployment, only deploys a subset of directories.

Now let's create the final development clone. This is a full git repo.

``` powershell
$ pyrevit clone dev --dest="C:\pyRevit\dev" --branch=develop
```

- `--branch=`: Specify a specific branch to be cloned

#### Installing Custom Clones

You can also use the clone command to install your own pyRevit clones from any git url. This is done by providing `--source=<repo_url>` or `--source=<archive_url>` depending on if you're cloning from a git repo or an archive.

``` powershell
$ pyrevit clone mypyrevit --source="https://www.github.com/my-pyrevit.git" --dest="C:\pyRevit\mypyrevit" --branch=develop
```

Or install from a ZIP archive using `<deployment_name>`:

``` powershell
$ pyrevit clone mypyrevit base --source="\\network\my-pyrevit.ZIP" --dest="C:\pyRevit\mypyrevit"
```

### Maintaining Clones

You can see a list of registered clones using. Notice the full clones and the no-git clones are listed separately:

``` powershell
$ pyrevit clones

==> Registered Clones (full git repos)
Name: "master" | Path: "%APPDATA%\pyRevit\pyRevit"
Name: "dev" | Path: "C:\pyRevit\dev"

==> Registered Clones (deployed from archive)
Name: "main" | Path: "C:\pyRevit\main"
```

Get info on a clone or open the path in file explorer:

``` powershell
pyrevit clones (info | open) <clone_name>

$ pyrevit clones info master        # get info on master clone
$ pyrevit clones open dev           # open dev in file explorer
```

Get info on available engines and deployments in a clone:

``` powershell
pyrevit clones deployments <clone_name>
pyrevit clones engines <clone_name>

$ pyrevit clones deployments dev    # print a list of deployments
$ pyrevit clones engines dev        # print a list of engines
```

Add existing clones (created without using `pyrevit`), remove, rename, and delete clones:

``` powershell
pyrevit clones add <clone_name> <clone_path> [--log=<log_file>]
$ pyrevit clones add newclone "C:Some\Path"     # register existing clone

pyrevit clones forget (--all | <clone_name>) [--log=<log_file>]
$ pyrevit clones forget newclone     # forget a clone (does not delete)
$ pyrevit clones forget --all        # for get all clones

pyrevit clones rename <clone_name> <clone_new_name> [--log=<log_file>]
$ pyrevit clones rename main base   # rename clone `main` to `base`

pyrevit clones delete [(--all | <clone_name>)] [--clearconfigs] [--log=<log_file>]
$ pyrevit clones delete base        # delete clone `base`
$ pyrevit clones delete --all       # delete all clones
$ pyrevit clones delete --all --clearconfigs    # delete all clones and clear configurations
```

#### Managing Git Clones

Get info about branch, version and current head commit:

``` powershell
$ pyrevit clones branch dev     # get current branch of `dev` clone
$ pyrevit clones version dev    # get current version of `dev` clone
$ pyrevit clones commit dev     # get current head commit of `dev` clone
$ pyrevit clones origin dev     # get origin url for `dev` clone
```

Setting current branch:

``` powershell
pyrevit clones branch <clone_name> [<branch_name>] [--log=<log_file>]

$ pyrevit clones branch dev master  # changing current branch to master for `dev` clone
```

Setting current version:

``` powershell
pyrevit clones version <clone_name> [<tag_name>] [--log=<log_file>]

$ pyrevit clones version dev v4.6  # changing current version to v4.6 for `dev` clone
```

Setting current head commit:

``` powershell
pyrevit clones commit <clone_name> [<commit_hash>] [--log=<log_file>]

$ pyrevit clones commit dev b06ec244ce81f521115926924e7322b22b161b54  # changing current commit for `dev` clone
```

Setting origin remote url:

``` powershell
pyrevit clones origin <clone_name> --reset [--log=<log_file>]
pyrevit clones origin <clone_name> [<origin_url>] [--log=<log_file>]

$ # changing origin remote url for `dev` clone
$ pyrevit clones origin dev https://www.git.com/repo.git  

$ # resetting origin remote url back to default for `dev` clone
$ pyrevit clones origin dev --reset
```

#### Updating Clones

The update command automatically updates full git clones using git pull and no-git clones by downloading and replacing all contents:

``` powershell
pyrevit clones update (--all | <clone_name>) [--log=<log_file>]

$ pyrevit clones update --all       # update all clones
$ pyrevit clones update dev         # update `dev` clone only
```

### Attaching pyRevit to Installed Revits

`pyrevit` can detect the exact installed Revit versions on your machine. You can use the commands below to attach any pyRevit clone to any or all installed Revits. Make sure to specify the clone to be attached and the desired engine version:

``` powershell
pyrevit attach <clone_name> (latest | dynamosafe | <engine_version>) (<revit_year> | --installed | --attached) [--allusers] [--log=<log_file>]

$ pyrevit attach dev latest --installed       # attach `dev` clone to all installed Revits using latest engine
$ pyrevit attach dev 277 --installed       # attach `dev` clone to all installed Revits using 277 engine
$ pyrevit attach dev dynamosafe 2018       # attach `dev` clone to Revit 2018 using an engine that has no conflicts with Dynamo BIM
```

- `--alusers`: Use this switch to attach for all users. It creates the manifest files inside the `%PROGRAMDATA%/Autodesk/Revit/Addons` instead of `%APPDATA%/Autodesk/Revit/Addons`
- `--attached`: This options is helpful when updating existing attachments e.g. specifying a new engine but keeping the same attachments as before

List all the attachments:

``` powershell
$ pyrevit attached

==> Attachments
Autodesk Revit 2013 First Customer Ship | Clone: "dev" | Engine: "277"
Autodesk Revit 2014 First Customer Ship | Clone: "dev" | Engine: "277"
Autodesk Revit 2015 First Customer Ship | Clone: "dev" | Engine: "277"
Autodesk Revit 2016 First Customer Ship | Clone: "dev" | Engine: "277"
Autodesk Revit 2017 First Customer Ship | Clone: "dev" | Engine: "277"
Autodesk Revit 2018.3.1 | Clone: "dev" | Engine: "277"
Autodesk Revit 2019 First Customer Ship | Clone: "dev" | Engine: "277"
```

You can also switch between the attached clones using the switch command:

``` powershell
pyrevit switch <clone_name>

$ pyrevit attached

==> Attachments
Autodesk Revit 2018.3.1 | Clone: "base" | Engine: "279"
Autodesk Revit 2019 First Customer Ship | Clone: "dev" | Engine: "273"

$ pyrevit switch main

==> Attachments
Autodesk Revit 2018.3.1 | Clone: "main" | Engine: "279"
Autodesk Revit 2019 First Customer Ship | Clone: "main" | Engine: "273"
```

The switch command with detect all the existing attachments and will remap them to the new clone using the same engine.

Detaching pyRevit from a specific Revit version or all installed:

``` powershell
pyrevit detach (--all | <revit_year>) [--log=<log_file>]

$ pyrevit detach --all
$ pyrevit detach 2019
```

## Managing pyRevit extensions

### Finding Extensions

``` powershell
pyrevit extensions search <search_pattern>
pyrevit extensions (info | help | open) <extension_name>

$ pyrevit extensions search apex    # search for an extension with apex in name
$ pyrevit extensions info apex      # get info on extension with apex in name
```

- `<search_pattern>`: Regular Expression (REGEX) pattern to search for

### Installing Extensions

``` powershell
pyrevit extend <extension_name> [--dest=<dest_path>] [--branch=<branch_name>] [--log=<log_file>]

$ pyrevit extend pyApex "C:\pyRevit\Extensions"     # install pyApex extension
```

- `--dest`: This is optional. If not provided, pyRevit attempts to install extension at the defautl third-party extension folder (usually `%appdata%/pyRevit/Extensions`). The destination directory will be added to pyRevit extensions search paths automatically and will be loaded on the next pyRevit reload. 
- `--branch`: Optional. Specific branch of the extension repo to be installed. Defaults to `master` branch if not provided.

To installing your own extensions, you'll need to specify what type if extension you're installing (ui or lib) and provide the url:

``` powershell
pyrevit extend (ui | lib) <extension_name> <repo_url> [--dest=<dest_path>] [--branch=<branch_name>] [--log=<log_file>]

$ pyrevit extend ui MyExtension "https://www.github.com/my-extension.git" "C:\pyRevit\Extensions" 
```

List all installed extensions:

``` powershell
pyrevit extensions
```

### Managing Installed Extensions

Delete an extension completely using:

``` powershell
pyrevit extensions delete <extension_name> [--log=<log_file>]

$ pyrevit extensions delete pyApex
```

Set origin url on an extension using:

``` powershell
pyrevit extensions origin <extension_name> --reset [--log=<log_file>]
pyrevit extensions origin <extension_name> [<origin_url>] [--log=<log_file>]

$ # changing origin remote url for `pyApex` extension
$ pyrevit extensions origin pyApex https://www.git.com/repo.git  

$ # resetting origin remote url back to default for `pyApex` extension
$ pyrevit extensions origin pyApex --reset
```

Add, remove extension search paths for all your existing extensions:

``` powershell
pyrevit extensions paths
pyrevit extensions paths forget --all [--log=<log_file>]
pyrevit extensions paths (add | forget) <extensions_path> [--log=<log_file>]

$ pyrevit extensions paths add "C:\pyRevit\MyExtensions"    # add a search path
$ pyrevit extensions paths forget --all         # forget all search paths
```

Enable or Disable an extension in pyRevit config file:

``` powershell
pyrevit extensions (enable | disable) <extension_name> [--log=<log_file>]

$ pyrevit extensions enable pyApex
```

Getting info, opening help or installed directory:

``` powershell
pyrevit extensions (info | help | open) <extension_name>

$ pyrevit extensions info apex      # get info on extension with apex in name
$ pyrevit extensions help apex      # open help page
$ pyrevit extensions open apex      # open path in file explorer
```

#### Updating Extensions

``` powershell
pyrevit extensions update (--all | <extension_name>) [--log=<log_file>]

$ pyrevit extensions update --all       # update all installed extension
$ pyrevit extensions update pyApex      # update pyApex extension
```

### Managing Extensions Lookup Sources

`pyrevit` can lookup in other places when searching for extensions. This means that you can define a `json` file with all your private extensions and add the path to the `pyrevit` sources. Your extensions will show up in search results from then on and can be installed by their name:

``` powershell
pyrevit extensions sources
pyrevit extensions sources forget --all [--log=<log_file>]
pyrevit extensions sources (add | forget) <source_json_or_url> [--log=<log_file>]

$ pyrevit extensions sources add "https://www.github.com/me/extensions.json" 
```

- `<source_json_or_url>`: Can be a `json` file path or web url

## Getting Environment Info

Use `env` command to get info about the current `pyrevit` environment:

```
$ pyrevit env

==> Registered Clones (full git repos)
dev | Branch: "hotfix/clihelp" | Version: "4.6.13:e9da94781a34ecb002ad634fa95b6a075726913c" | Path: "C:\Users\LeoW10\Desktop\gits\pyRevit"

==> Registered Clones (deployed from archive)
release | Deploy: "basepublic" | Branch: "develop" | Version: "4.6.13" | Path: "C:\tmp\public"
crazy | Deploy: "core" | Branch: "develop" | Version: "Unknown" | Path: "C:\tmp\CrazyUser.??\core"
base | Deploy: "base" | Branch: "develop" | Version: "4.6.13" | Path: "C:\tmp\base"
core | Deploy: "core" | Branch: "develop" | Version: "Unknown" | Path: "C:\tmp\core"

==> Attachments
Autodesk Revit 2013 First Customer Ship | Clone: "dev" | Engine: "277"
Autodesk Revit 2014 First Customer Ship | Clone: "release" | Engine: "277"
Autodesk Revit 2015 First Customer Ship | Clone: "dev" | Engine: "277"
Autodesk Revit 2016 First Customer Ship | Clone: "dev" | Engine: "277"
Autodesk Revit 2017 First Customer Ship | Clone: "dev" | Engine: "277"
Autodesk Revit 2018.3.1 | Clone: "dev" | Engine: "277"
Autodesk Revit 2019.2 (Update) | Clone: "dev" | Engine: "277"

==> Installed UI Extensions
Name: "pyApex" | Repo: "" | Installed: "C:\tmp\exts\pyApex.extension"

==> Installed Library Extensions

==> Default Extension Search Path
C:\Users\LeoW10\AppData\Roaming\pyRevit\Extensions

==> Extension Search Paths
C:\tmp\exts
C:\Users\LeoW10\Desktop\gits
C:\Users\LeoW10\AppData\Roaming\pyRevit\Extensions

==> Extension Sources - Default
https://github.com/eirannejad/pyRevit/raw/master/extensions/extensions.json

==> Extension Sources - Additional

==> Installed Revits
Autodesk Revit 2013 First Customer Ship | Version: 12.2.21203 | Language: 1033 | Path: "C:\Program Files\Autodesk\Revit 2013\"
Autodesk Revit 2014 First Customer Ship | Version: 13.3.8151 | Language: 1033 | Path: "C:\Program Files\Autodesk\Revit Architecture 2014\"
Autodesk Revit 2015 First Customer Ship | Version: 15.0.136.0 | Language: 1033 | Path: "C:\Program Files\Autodesk\Revit 2015\"
Autodesk Revit 2016 First Customer Ship | Version: 16.0.428.0 | Language: 1033 | Path: "C:\Program Files\Autodesk\Revit 2016\"
Autodesk Revit 2017 First Customer Ship | Version: 17.0.416.0 | Language: 1033 | Path: "C:\Program Files\Autodesk\Revit 2017\"
Autodesk Revit 2018.3.1 | Version: 18.3.1.2 | Language: 1033 | Path: "C:\Program Files\Autodesk\Revit 2018\"
Autodesk Revit 2019.2 (Update) | Version: 19.2.0.65 | Language: 1033 | Path: "C:\Program Files\Autodesk\Revit 2019\"

==> Running Revit Instances

==> User Environment
Microsoft Windows 10 [Version 10.0.17134]
Executing User: LEO-W10\LeoW10
Active User: LEO-W10\LeoW10
Adming Access: Yes
%APPDATA%: "C:\Users\LeoW10\AppData\Roaming"
Latest Installed .Net Framework: "4.7.2"
Installed .Net Target Packs: v3.5 v4.0 v4.5 v4.5.1 v4.5.2 v4.6 v4.6.1 v4.7.1 v4.X
pyRevit CLI 0.9.0.0
```

## Configuring pyRevit

Use `config` command to configure pyRevit on your machine from an existing template configuration file:

``` powershell
pyrevit config <template_config_path> [--log=<log_file>]

$ pyrevit config "C:\myPyRevitTemplateConfig.ini"
```

Configuring core configurations:

``` powershell
pyrevit configs logs [(none | verbose | debug)] [--log=<log_file>]
$ pyrevit configs logs verbose      # set logging to verbose
```

``` powershell
pyrevit configs allowremotedll [(enable | disable)] [--log=<log_file>]
$ pyrevit configs allowremotedll enable  # allow remote dll loads in dotnet
```
``` powershell
pyrevit configs checkupdates [(enable | disable)] [--log=<log_file>]
$ pyrevit configs checkupdates enable  # enable check updates on startup
```
``` powershell
pyrevit configs autoupdate [(enable | disable)] [--log=<log_file>]
$ pyrevit configs autoupdate enable  # enable auto-update on startup
```
``` powershell
pyrevit configs rocketmode [(enable | disable)] [--log=<log_file>]
$ pyrevit configs rocketmode enable  # enable rocket mode
```
``` powershell
pyrevit configs filelogging [(enable | disable)] [--log=<log_file>]
$ pyrevit configs filelogging enable  # enable file logging
```
``` powershell
pyrevit configs loadbeta [(enable | disable)] [--log=<log_file>]
$ pyrevit configs loadbeta enable  # enable loading beta tools
```
``` powershell
pyrevit configs usagelogging
pyrevit configs usagelogging enable (file | server) <dest_path> [--log=<log_file>]
pyrevit configs usagelogging disable [--log=<log_file>]
$ pyrevit configs usagelogging enable file "C:\logs" # enable usage logging to file
$ pyrevit configs usagelogging enable server "http://server" # enable usage logging to server
```
``` powershell
pyrevit configs outputcss [<css_path>] [--log=<log_file>]
$ pyrevit configs outputcss "C:\myOutputStyle.css"  # setting custom output window styling
```

### Configuring Sensitive Tools

You can Enable/Disable a few tools in pyRevit configurations:

``` powershell
pyrevit configs usercanupdate [(Yes | No)] [--log=<log_file>]
pyrevit configs usercanextend [(Yes | No)] [--log=<log_file>]
pyrevit configs usercanconfig [(Yes | No)] [--log=<log_file>]
```

- `usercanupdate`: Enable/Disable Update tool in pyRevit main tools
- `usercanextend`: Enable/Disable Extensions tool in pyRevit main tools
- `usercanconfig`: Enable/Disable Settings tool in pyRevit main tools

### Configuring Your Own Options

Use the `configs` command to configure your custom config options. Specify the option in `section:option` format:

``` powershell
pyrevit configs <option_path> (enable | disable) [--log=<log_file>]
pyrevit configs <option_path> [<option_value>] [--log=<log_file>]

$ pyrevit configs mysection:myswitch enable      # set myswitch to True
$ pyrevit configs mysection:myvalue 12           # set myvalue to 12
```

### Using Config as Seed

Seed the configuration to `%PROGRAMDATA%/pyRevit` to be used as basis for pyRevit configurtions when configuring pyRevit using System account on a user machine:

``` powershell
pyrevit configs seed [--lock] [--log=<log_file>]
$ pyrevit configs seed
```
- `--lock`: Locks the file for current user only. pyRevit will now allow changing the configurations if the seed config file is not writable.

## Extra Revit-Related Functionality

List installed or running Revits:

``` powershell
pyrevit revits [--installed] [--log=<log_file>]

$ pyrevit revits --installed        # list installed revits
Autodesk Revit 2016 Service Pack 2 | Version: 16.0.490.0 | Language: 1033 | Path: "C:\Program Files\Autodesk\Revit 2016\"
Autodesk Revit 2018.3 | Version: 18.3.0.81 | Language: 1033 | Path: "C:\Program Files\Autodesk\Revit 2018\"
Autodesk Revit 2019.1 | Version: 19.1.0.112 | Language: 1033 | Path: "C:\Program Files\Autodesk\Revit 2019\"
```

Close all or specific running Revit:
``` powershell
pyrevit revits killall [<revit_year>] [--log=<log_file>]

$ pyrevit revits killall 2018   # close all Revit 2018s
```

Generate a report from `RVT` or `RFA` file info:

``` powershell
pyrevit revits fileinfo <file_or_dir_path> [--csv=<output_file>]

$ pyrevit revits fileinfo "C:\model.rvt"
Created in: Autodesk Revit 2018.3.1 (20180423_1000(x64))
Workshared: Yes
Central Model Path: \\central\path\Project3.rvt
Last Saved Path: C:\Downloads\Project3.rvt
Document Id: bfb3db00-ca65-4c6a-aa64-329761e5d0ca
Open Workset Settings: LastViewed
Document Increment: 2
```

- `file_or_dir_path`: could be a file or directory
- `--csv=`: Write output to specified CSV file


## Creating pyRevit extension bundles

You can use the `pyrevit init` commnd to quickly create pyRevit bundles based on pre-defined templates or your own templates:

``` powershell
Init pyRevit bundles

    Usage:
        pyrevit init (ui | lib) <extension_name> [--usetemplate] [--templates=<templates_path>]
        pyrevit init (tab | panel | panelopt | pull | split | splitpush | push | smart | command) <bundle_name> [--usetemplate] [--templates=<templates_path>]

# creates MyExtension.extension inside the current directory
$ pyrevit init ui "MyExtension"

# creates MyCommands.pulldown inside the current directory,
# using a predfined template
$ pyrevit init pull "MyCommands" --usetemplate

```

 - `--usetemplate`: Use pre-defined template to create the given bundle. This basically copies all the contents of the template bundle into the new bundle.
 - `--templates`: Templates directory. Optional. If empty, the default pyrevit templates `bin/templates` directory will be used.

### Creating your own bundle templates

Create a parent tempalte directory and create a series of subfolders for each template type. All bundle names should be `template` as shown below:

```
my-templates/
├── template.extension/
├── template.tab/
├── template.panel/
|   └── _layout
├── template.pulldown/
|   ├── icon.png
|   └── _layout
└── template.pushbutton/
    ├── window.xaml
    ├── script.py
    └── icon.png
```

The pass the `my-templates/` full path to the `--templates` option of the `init` command. Make sure to `--usetemplate` as well. pyrevit will use these templates to create your requested bundles.

## CLI Execution of Python Scripts

You can run a python script in any of the installed Revit versions from the command prompt.

``` powershell
pyrevit run <script_file> [--revit=<revit_year>]

$ pyrevit run "C:\myscript.py"

# the execution environment information will be printed after completion
==> Execution Environment
Execution Id: "51066afe-022c-4dba-bdc5-d35d451b998f"
Product: Autodesk Revit 2019 First Customer Ship | Version: 19.0.0.405 | Language: 1033 | Path: "C:\Program Files\Autodesk\Revit 2019\"
Clone: Name: "dev" | Path: "...\pyRevit"
Engine: KernelName:"IronPython" | Version: "277" | Path: "...\pyRevit\bin\engines\277" | Desc: "Compatible with RevitPythonShell" | Compatible: ""
Script: "C:\myscript.py"
Working Directory: "...\Temp\51066afe-022c-4dba-bdc5-d35d451b998f"
Journal File: "...\Temp\51066afe-022c-4dba-bdc5-d35d451b998f\PyRevitRunner_51066afe-022c-4dba-bdc5-d35d451b998f.txt"
Manifest File: "...\Temp\51066afe-022c-4dba-bdc5-d35d451b998f\PyRevitRunner.addin"
Log File: "...\Temp\51066afe-022c-4dba-bdc5-d35d451b998f\PyRevitRunner_51066afe-022c-4dba-bdc5-d35d451b998f.log"
```

- `--purge`: Runner creates a temporary directory under `%TEMP%` for this execution. Specifying this option, will clear the temporary files after completion. This is helpful when running a script over many files.

If `--revit` option is not specified, the run command will use the newest installed version of Revit to run the command. You can however specify the revsion of Revit e.g. `--revit=2018`

At either case, pyRevit uses the clone and engine verison that is attached to Revit, to run the script; So make sure that pyRevit is already attached to the Revit version you are intending to use.

All the pyrevit modules are accessible inside the script.

### Running a Script on Revit Models

You can also specify a single or multiple models to `pyrevit run` command. If a model is specified, the run command selects a version of Revit that is used to create that model by default. As the previous example, you can still manually specify which version of Revit to use. be aware that Revit will fail if the model version is newer, or needs to upgrade the model if it is an older version.


``` powershell
pyrevit run <script_file> <model_file> [--revit=<revit_year>] [--purge]

$ pyrevit run "C:\myscript.py" "C:\Model1.rvt"
$ pyrevit run "C:\myscript.py" "C:\All-My-Models.txt"

# target models will be listed at the end of env report
==> Target Models
C:\Users\LeoW10\Desktop\batchtest\Project_V19.rvt
C:\Users\LeoW10\Desktop\batchtest\Project_V18.rvt

```

- `<model_file>`: Path to a Revit model file OR a text file listing multiple models (one model per line).

**Important Note:**

**The run command does not attempt to open the model in Revit.** Opening a model is a complex process and has many configurations e.g. Opening central or detached, Workset configurations, etc. The run command uses a simple journal file to bootstrap Revit and it avoid using complex journal structures to provide configurations on opening models since journals are heavily GUI based and could easily break in the future. Revit API provides ample functionality on opening models. It's best practice to open the model inside your script.

The execution environment provides the global variable `__models__` set to a list of model file paths. Your script can read the models from this variable and attempt at opening each.

``` python
from pyrevit import HOST_APP

# __models__ is set to a list of model file paths
# __models__ = ['C:\model1.rvt']
for model in __models__:
    uidoc = HOST_APP.uiapp.OpenAndActivateDocument(model)
    doc = uidoc.Document
    # do something here with the document

```

The developer is assumed to undestand the complexity and memory needs of the target models. Hence the run command does not provide any functionality to run multiple Revit instances on a single machine since it has very limited information about the resource needs of the target models.

The pyrevit run is intended to provide a simple interface for execution of python scripts on Revit model(s) from command line. You can write your own python or PowerShell scripts that processes the list of your models, understands their resource needs and the available resources of the host machine, and starts one or many `pyrevit run` instances to execute the scripts on the models.


## Clear pyRevit Cache Files

Cache files are stored under `%APPDATA%/pyRevit/<revit-version>`. You can clear all or specific Revit version caches. Revit needs to be closed for this operaton since it keeps the files locked if it is open:

``` powershell
pyrevit caches clear (--all | <revit_year>) [--log=<log_file>]

$ pyrevit caches clear 2018     # clear all caches for Revit 2018
```

## Logging CLI Debug Messages

With many commands you can log the complete log messages to a log file:

``` powershell
$ pyrevit clone master --log="C:\logfile.txt"
```


## Creating Shortcuts

You can use the cli tool to create shortcuts in start menu for various tasks.

``` powershell
pyrevit cli addshortcut <shortcut_name> <shortcut_args> [--desc=<shortcut_description>] [--allusers]

$ pyrevit cli addshortcut "Update pyRevit" "clones update --all"
```

- `--desc`: Description for the Start menu shortcut
- `--alusers`: Create shortcut for all users or current user
