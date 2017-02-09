namespace PyRevitBaseClasses
{
    public static class ExternalConfig
    {
        public static string doctype = "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01 Transitional//EN\" \"http://www.w3.org/TR/html4/loose.dtd\">";
        public static string htmlstyle = "font-size:9pt;font-family:Verdana;margin:0px 0px 15px 0px;padding:0px;height:100%";
        public static string defaultelement = "<div style=\"margin-top:4px;margin-bottom:4px;padding-right:8px;padding-left:8px;\"></div>";
        public static string errordiv = "<div style=\"background:#f9f2f4;color:#c7254e;padding:10px;\"></div>";
        public static string ipyerrtitle = "<strong>IronPython Traceback:</strong>";
        public static string dotneterrtitle = "<strong>Script Executor Traceback:</strong>";
        public static string progressbar = "<div style=\"position:fixed;bottom:0px;width:100%;height:8px;font-size:1pt;border:0px;background:#eeeeee;\"></div>";
        public static string progressbargraphstyle = "font-size:1pt;width:{0}%;height:8px;background:#b5d54b;border:0px;";
        public static string progressbargraphid = "graph";
    }
}
