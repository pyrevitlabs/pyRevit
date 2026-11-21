# Install extensions

Use the **Extensions** tool in the **pyRevit** panel to install third-party extensions.

!!! note "Screenshots"

    The screenshots on this page come from an older version of pyRevit. The steps are the same.

The Extensions window, shows all the registered extensions that you can install on your machine.

![](../assets/get-started/install-extensions/2019-08-28-08-44-00-autodesk-revit-2019-2-project1-rvt-floor-plan-level-1.png)

To install an extension, select the extension that you want, take a look at the information about that extension and the website, then click on the Install Extension button and select the destination (By default there is only one destination)

pyRevit will install the extension and will reload automatically.

Most extensions will add their own tab in Revit UI with their tools inside.

![](../assets/get-started/install-extensions/2019-08-28-08-46-53-autodesk-revit-2019-2-project1-rvt-floor-plan-level-1.png)

## Adding Extension Manually

To manually add an extension to pyRevit, open the pyRevit **Settings** and add the folder that contains the extension under **Custom Extension Directories**

![](../assets/get-started/install-extensions/2019-08-30-12-08-18-pyrevit-settings.png)

In this example the extension is called `Test.extension` and is inside the `gits` folder on the desktop. The folder to add is the parent, `gits`, not the `.extension` folder itself.

![](../assets/get-started/install-extensions/2019-12-03-14-15-24-pyrevit-settings.png)
