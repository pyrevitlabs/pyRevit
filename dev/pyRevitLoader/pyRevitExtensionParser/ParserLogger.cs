namespace pyRevitExtensionParser
{
    public interface IParserLogger
    {
        void Debug(string message);
        void Info(string message);
        void Warning(string message);
        void Error(string message);
    }
}
