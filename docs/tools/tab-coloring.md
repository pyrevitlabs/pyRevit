# Tab Coloring

pyRevit can colorize Revit tabs by the open document. Open **pyRevit Settings**, and activate the **Tab Colorizer** under **UI/UX** section.

![](../assets/tools/tab-coloring/revit-y57zkxv9zq.png)

Save settings and the open tabs will be colored by document

![](../assets/tools/tab-coloring/revit-z7xzjies6z.png)

You can use the Toggle Coloring tool to activate, deactivate the coloring in your current session.

![](../assets/tools/tab-coloring/2019-09-07-12-29-33-autodesk-revit-2019-2-project1-rvt-floor-plan-level-1.png)

### Setting Colorizer Theme

Select the styling option for *Project* and *Family* tabs separately:

![](../assets/tools/tab-coloring/revit-cx0hce9v6f.png)

You can select a series of color swatches under the "By Order" section to colorize the document tabs as they open:

![](../assets/tools/tab-coloring/revit-6hgqpazvan.png)

Under "By Filter", you can select a series of colors and Regular expression patterns to colorize tabs by their title. In the example below, all the tabs that match the regex pattern `Level \d`, will be colorized with magenta:

![](../assets/tools/tab-coloring/revit-r8fbzzewep.png)

![](../assets/tools/tab-coloring/revit-avqufsmsfh.png)

#### Developer Tip

If you want to know the id and assigned color for each document, SHIFT-Click on the Tab Coloring tool

![](../assets/tools/tab-coloring/2019-09-07-12-32-08-tab-coloring.png)
