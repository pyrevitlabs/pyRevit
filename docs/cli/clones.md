# Clones

#### Installing pyRevit

```powershell
pyrevit clone <clone_name> <deployment_name> [--dest=<dest_path>] [--branch=<branch_name>] [--log=<log_file>]
pyrevit clone <clone_name> --image=<image_url> [--dest=<dest_path>] [--log=<log_file>]
pyrevit clone <clone_name> [--dest=<dest_path>] [--source=<repo_url>] [--branch=<branch_name>] [--log=<log_file>] [--username=<username>] [--password=<password>]
```

`pyrevit` can maintain multiple clones of pyRevit on your system. In order to do so, it needs to assign a name to each clone (`<clone_name>`). You’ll set this name when cloning pyRevit or when adding an existing clone to `pyrevit` registry. From then on you can always refer to that clone by its name.

Let’s say I want one clone of pyRevit `master` branch as my master repo; one clone of pyRevit without the full git repository (much smaller download) as my main repo; and finally one clone of the `develop` branch of pyRevit as my development repo.

Let’s create the master clone first. This will be a full git repo of the master branch.

```powershell
# master is <clone_name> that we're providing to pyrevit cli
# we're not providing any value for <dest_path>, therefore pyrevit cli will clone
# pyRevit into the default path
$ pyrevit clone master
```

Now let’s create the main clone. This one does not include the full repository. It’ll be cloned from the ZIP archive provided by the Github repo:

```powershell
# we're providing the <dest_path> for this clone
# we're using the `base` deployment in this example which includes the base pyRevit tools
$ pyrevit clone main base --dest="C:\pyRevit\main"
```

- `<deployment_name>`: When provided the tool installs from the ZIP archive and NOT the complete git repo. This is the preferred method and is used with the native pyRevit installer. pyRevit has multiple deployments. These deployments are defined in the `pyRevitfile` inside the pyRevit repo, see [Deployments](../teams/deployments.md). Each deployment only deploys a subset of directories.

Now let’s create the final development clone. This is a full git repo.

```powershell
$ pyrevit clone dev --dest="C:\pyRevit\dev" --branch=develop
```

- `--branch=`: Specify a specific branch to be cloned

#### Installing Custom Clones

You can also use the clone command to install your own pyRevit clones from any git url. Provide `--source=<repo_url>` to clone from a git repo, or `--image=<archive_url>` to install from a ZIP archive. If you are cloning from a private repository, you can provide the `--username` and `--password` to the repo account as well.

```powershell
$ pyrevit clone mypyrevit --source="https://www.github.com/my-pyrevit.git" --dest="C:\pyRevit\mypyrevit" --branch=develop
```

Or install from a ZIP archive with `--image`:

```powershell
$ pyrevit clone mypyrevit --image="\\network\my-pyrevit.ZIP" --dest="C:\pyRevit\mypyrevit"
```

#### Maintaining Clones

You can see a list of registered clones using. Notice the full clones and the no-git clones are listed separately:

```powershell
$ pyrevit clones

==> Registered Clones (full git repos)
master | Branch: "master" | Version: "<version>" | Path: "<path>"
dev | Branch: "develop" | Version: "<version>" | Path: "C:\pyRevit\dev"

==> Registered Clones (deployed from archive/image)
main | Deploy: "base" | Branch: "master" | Version: "<version>" | Path: "C:\pyRevit\main"
```

Get info on a clone or open the path in file explorer:

```powershell
pyrevit clones (info | open) <clone_name>

$ pyrevit clones info master        # get info on master clone
$ pyrevit clones open dev           # open dev in file explorer
```

Get info on available engines and deployments in a clone:

```powershell
pyrevit clones deployments <clone_name>
pyrevit clones engines <clone_name>

$ pyrevit clones deployments dev    # print a list of deployments
$ pyrevit clones engines dev        # print a list of engines
```

Add existing clones (created without using `pyrevit`), remove, rename, and delete clones:

```powershell
pyrevit clones add <clone_name> <clone_path> [--log=<log_file>]
$ pyrevit clones add newclone "C:\Some\Path"     # register existing clone

pyrevit clones forget (--all | <clone_name>) [--log=<log_file>]
$ pyrevit clones forget newclone     # forget a clone (does not delete)
$ pyrevit clones forget --all        # for get all clones

pyrevit clones rename <clone_name> <clone_new_name> [--log=<log_file>]
$ pyrevit clones rename main base   # rename clone `main` to `base`

pyrevit clones delete [(--all | <clone_name>)] [--clearconfigs] [--log=<log_file>]
$ pyrevit clones delete base        # delete clone `base`
$ pyrevit clones delete --all       # delete all clones
$ pyrevit clones delete --all --clearconfigs    # delete all clones and the whole user configuration file
```

`--clearconfigs` deletes the entire user `pyRevit_config.ini`, including settings unrelated to the clones, so it only applies together with `--all`. Deleting a single clone always keeps the configuration and only removes that clone's registration; `--clearconfigs` is ignored there with a warning on stderr.

#### Managing Git Clones

Get info about branch, version and current head commit:

```powershell
$ pyrevit clones branch dev     # get current branch of `dev` clone
$ pyrevit clones version dev    # get current version of `dev` clone
$ pyrevit clones commit dev     # get current head commit of `dev` clone
$ pyrevit clones origin dev     # get origin url for `dev` clone
```

Setting current branch:

```powershell
pyrevit clones branch <clone_name> [<branch_name>] [--log=<log_file>]

$ pyrevit clones branch dev master  # changing current branch to master for `dev` clone
```

Setting current version:

```powershell
pyrevit clones version <clone_name> [<tag_name>] [--log=<log_file>]

$ pyrevit clones version dev <tag_name>  # changing current version of the `dev` clone to a release tag
```

Setting current head commit:

```powershell
pyrevit clones commit <clone_name> [<commit_hash>] [--log=<log_file>]

$ pyrevit clones commit dev b06ec244ce81f521115926924e7322b22b161b54  # changing current commit for `dev` clone
```

Setting origin remote url:

```powershell
pyrevit clones origin <clone_name> --reset [--log=<log_file>]
pyrevit clones origin <clone_name> [<origin_url>] [--log=<log_file>]

$ # changing origin remote url for `dev` clone
$ pyrevit clones origin dev https://www.git.com/repo.git  

$ # resetting origin remote url back to default for `dev` clone
$ pyrevit clones origin dev --reset
```

#### Updating Clones

The update command automatically updates full git clones using git pull and no-git clones by downloading and replacing all contents:

```powershell
pyrevit clones update (--all | <clone_name>) [--log=<log_file>]

$ pyrevit clones update --all       # update all clones
$ pyrevit clones update dev         # update `dev` clone only
```
