using Autodesk.Revit.UI;


namespace PyRevitBaseClasses
{
    public class OutputWindowManager
    {
        private readonly UIApplication _revit;

        public OutputWindowManager(UIApplication revit)
        {
            _revit = revit;
        }
    }
}
