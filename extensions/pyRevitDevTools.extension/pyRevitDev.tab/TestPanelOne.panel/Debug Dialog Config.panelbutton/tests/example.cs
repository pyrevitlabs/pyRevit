// source:
// http://jprdintprev.autodesk.com/adn/servlet/devnote?siteID=4814862&id=14962863&preview=1&linkID=4900509

static RibbonPanel AddOnePanel()
{
    RibbonButton rb;
    RibbonPanelSource rps = new RibbonPanelSource();
    rps.Title = "Test One";
    RibbonPanel rp = new RibbonPanel();
    rp.Source = rps;

    rb = new RibbonButton();
    rb.Name = "Test Button";
    rb.ShowText = true;
    rb.Text = "Test Button";
    //Add the Button to the Tab
    rps.Items.Add(rb);

    //Create a Command Item that the Dialog Launcher can use,
    // for this test it is just a place holder.
    RibbonCommandItem rci = new RibbonCommandItem();
    rci.Name = "TestCommand";

    //assign the Command Item to the DialogLauncher which auto-enables
    // the little button at the lower right of a Panel, but where's the arrow
    // you see in the stock Ribbons?
    rps.DialogLauncher = rci;

    return rp;
}


RibbonButton dialogLauncherButton = new RibbonButton();
dialogLauncherButton.Name = "TestCommand"; 
rps.DialogLauncher = dialogLauncherButton;
