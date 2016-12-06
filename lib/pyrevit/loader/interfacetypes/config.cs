namespace PyRevitBaseClasses
{
    class ExternalConfig
    {
        public string startupscript = ".\\pyRevitLoader.py";
        public string lib = "..\\..\\..\\..\\Lib";
        public string htmlstyle = "font-size:12;font-family:Verdana;";
        public string defaultelement = "<div></div>";
        public string errordiv = "<div style=&quot;background:#EEE;padding:10;&quot;></div>";
        public string ipyerrtitle = "<strong>IronPython Traceback:</strong>";
        public string dotneterrtitle = "<strong>Script Executor Traceback:</strong>";
    }
}
