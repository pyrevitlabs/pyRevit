# Distribute extensions

These functions continue the script from the [Team deployment guide](deployment-guide.md) and use the variables defined there.

## Installing pyRevit Extensions

Now let's create another function that installs the pyRevit extensions we need. Let's assume we need the **pyApex** pyRevit extension.

```powershell
# install extensions
function Install-Extensions() {
    # make sure the extensions folder exists. installed extensions are kept
    Confirm-Path $pyrevitexts

    # update the extension when it is already installed, install it otherwise
    if (Test-Path -LiteralPath (Join-Path $pyrevitexts "pyApex.extension")) {
        Write-Output "Updating Extensions..."
        pyrevit extensions update "pyApex"
    } else {
        Write-Output "Cloning Extensions..."
        pyrevit extend "pyApex" --dest=$pyrevitexts
    }
}
```

!!! warning ""

    `pyrevit extensions update` overwrites local edits to the tracked files of the extension. Do not edit a deployed extension in place: change it in its repository and deploy again.

## Customizing pyRevit for Your Team

If you need to deploy your own pyRevit core, or extensions, modify the command above as shown. See [Manage pyRevit clones](../cli/clones.md) to see all the options on the `clone` and `extend` commands used here

```powershell
# clone pyRevit now
Write-Output "Cloning Core..."
pyrevit clone $ourclonename --source=$ourpyrevitcore --dest=$pyrevitcoredest

# clone the pyRevit extension now
Write-Output "Cloning Extensions..."
pyrevit extend ui $ourextname $ourpyrevitext --dest=$pyrevitexts
```
