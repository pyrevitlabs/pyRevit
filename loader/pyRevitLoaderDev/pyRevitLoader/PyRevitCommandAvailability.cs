using System;
using Autodesk.Revit;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

namespace PyRevitLoader
{
    public abstract class PyRevitCommandCategoryAvail : IExternalCommandAvailability
    {
        public string _categoryName = "";

        public PyRevitCommandCategoryAvail(string contextString)
        {
            _categoryName = contextString;
        }

        public bool IsCommandAvailable(UIApplication uiApp, CategorySet selectedCategories)
        {
            // Categories allCats = uiApp.ActiveUIDocument.Document.Settings.Categories;
            if (selectedCategories.IsEmpty) return false;
            foreach(Category rvt_cat in selectedCategories){
                if (rvt_cat.Name != this._categoryName) return false;
            }
            return true;
        }
    }

    public abstract class PyRevitCommandSelectionAvail : IExternalCommandAvailability
    {
        public string _categoryName = "";

        public PyRevitCommandSelectionAvail(string contextString)
        {
            _categoryName = contextString;
        }

        public bool IsCommandAvailable(UIApplication uiApp, CategorySet selectedCategories)
        {
            if (selectedCategories.IsEmpty) return false;
            return true;
        }
    }

}
