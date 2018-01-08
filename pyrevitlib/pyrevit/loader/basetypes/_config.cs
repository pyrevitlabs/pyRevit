using System;

namespace PyRevitBaseClasses
{
    public static class DomainStorageKeys
    {
        public static string pyRevitEnvVarsDictKey = "pyRevitEnvVarsDict";
        public static string pyRevitIpyEnginesDictKey = "pyRevitIpyEngines";
        public static string pyRevitIpyEngineDefaultStreamCfgKey = "pyRevitIpyEngineDefaultStreamCfg";
        public static string pyRevitOutputWindowsDictKey = "pyRevitOutputWindowsDict";
        public static string pyRevitServerViewFunctionsDictKey = "pyRevitServerViewFunctionsDict";
    }

    public static class ExternalConfig
    {
        public static string doctype = "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01 Transitional//EN\" \"http://www.w3.org/TR/html4/loose.dtd\">" +
                                       "<head>" +
                                       "<meta http-equiv=\"X-UA-Compatible\" content=\"IE=9\" />" +
                                       "<link rel=\"stylesheet\" href=\"{0}\">" +
                                       "</head>";

        public static string defaultelement = "<div class=\"entry\"></div>";
        public static string errordiv = "<div class=\"errorentry\"></div>";
        public static string ipyerrtitle = "<strong>IronPython Traceback:</strong>";
        public static string dotneterrtitle = "<strong>Script Executor Traceback:</strong>";
        public static string progressindicator = "<div class=\"progressindicator\"></div>";
        public static string progressbar = "<div class=\"progressbar\" id=\"pbar\"></div>";
        public static string progressbarid = "pbar";
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
