using System.Collections.Generic;

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
        public static char defaultsep = ';';
        public static string doctype = "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.01 Transitional//EN\" \"http://www.w3.org/TR/html4/loose.dtd\">";
        public static string dochead = "<head>" +
                                       "<meta http-equiv=\"X-UA-Compatible\" content=\"IE=Edge\" />" +
                                       "<meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\" />" +
                                       "<meta name=\"appversion\" content=\"{0}\" />" +
                                       "<meta name=\"rendererversion\" content=\"{1}\" />" +
                                       "<link rel=\"stylesheet\" href=\"file:///{2}\">" +
                                       "</head>";

        public static string defaultelement = "<div class=\"entry\"></div>";
        public static string errordiv = "<div class=\"errorentry\"></div>";
        public static string ipyerrtitle = "<strong>IronPython Traceback:</strong>";
        public static string irubyerrtitle = "<strong>IronRuby Traceback:</strong>";
        public static string clrerrtitle = "<strong>Script Executor Traceback:</strong>";
        public static string progressindicator = "<div class=\"progressindicator\" id=\"pbarcontainer\"></div>";
        public static string progressindicatorid = "pbarcontainer";
        public static string progressbar = "<div class=\"progressbar\" id=\"pbar\"></div>";
        public static string progressbarid = "pbar";
        public static string inlinewait = "<div class=\"inlinewait\" id=\"inlnwait\">\u280b Preparing results...</div>";
        public static string inlinewaitid = "inlnwait";
        public static List<string> inlinewaitsequence = new List<string> (){
            "\u280b Preparing results...",
            "\u2819 Preparing results...",
            "\u2838 Preparing results...",
            "\u28B0 Preparing results...",
            "\u28e0 Preparing results...",
            "\u28c4 Preparing results...",
            "\u2846 Preparing results...",
            "\u2807 Preparing results..."
        };
    }

    public static class ExecutionResultCodes
    {
        public static int Succeeded = 0;
        public static int SysExited = 1;
        public static int ExecutionException = 2;
        public static int CompileException = 3;
        public static int EngineNotImplementedException = 4;
        public static int ExternalInterfaceNotImplementedException = 5;
        public static int FailedLoadingContent = 6;
        public static int BadCommandArguments = 7;
        public static int UnknownException = 9;
    }
}
