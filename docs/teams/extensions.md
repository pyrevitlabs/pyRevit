# Distribute extensions

These functions continue the script from the [Team deployment guide](deployment-guide.md) and use the variables defined there.

## Installing pyRevit Extensions

Now let's create another function that installs the pyRevit extensions we need. Let's assume we need the **pyApex** pyRevit extension.

```powershell
# install extensions
function Install-Extensions() {
    # make sure the extensions folder exists. installed extensions are kept
    Confirm-Path $pyrevitexts

    # install extensions now
    Write-Output "Cloning Extensions..."
    pyrevit extend "pyApex" --dest=$pyrevitexts
}
```

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
