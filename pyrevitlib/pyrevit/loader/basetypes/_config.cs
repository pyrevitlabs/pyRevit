namespace PyRevitBaseClasses
{
    public static class ExternalConfig
    {
        public static string doctype = "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01 Transitional//EN\" \"http://www.w3.org/TR/html4/loose.dtd\"><head><meta http-equiv=\"X-UA-Compatible\" content=\"IE=9\" /></head>";
        public static string htmlstyle = "font-size:9pt;font-family:Verdana;margin:0px 0px 15px 0px;padding:0px;height:100%;scrollbar-base-color:#EEE;scrollbar-face-color:#DDD;scrollbar-highlight-color:#EEE;scrollbar-shadow-color:#EEE;scrollbar-track-color:#EEE;scrollbar-arrow-color:#666;";
        public static string defaultelement = "<div style=\"margin-top:3px;margin-bottom:3px;padding-right:6px;padding-left:6px;\"></div>";
        public static string errordiv = "<div style=\"margin-top:10px;padding:6px;border-top:5px solid #c7254e;background:#f9f2f4;color:#c7254e;\"></div>";
        public static string ipyerrtitle = "<strong>IronPython Traceback:</strong>";
        public static string dotneterrtitle = "<strong>Script Executor Traceback:</strong>";
        public static string progressbar = "<div style=\"position:fixed;bottom:0px;width:100%;height:8px;font-size:1pt;border:0px;background:#EEE;\"></div>";
        public static string progressbargraphstyle = "font-size:1pt;width:{0}%;height:8px;background:#b5d54b;border:0px;";
        public static string progressbargraphid = "graph";
        public static string pyrevitconsolesappdata = "pyRevitConsoles";
    }

    public static class ExecutionErrorCodes
    {
        public static int Succeeded = 0;
        public static int SysExited = 1;
        public static int ExecutionException = 2;
        public static int CompileException = 3;
        public static int UnknownException = 9;
    }
}
