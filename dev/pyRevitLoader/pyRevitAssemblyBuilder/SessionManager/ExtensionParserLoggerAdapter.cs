#nullable enable
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    public class ExtensionParserLoggerAdapter : IParserLogger
    {
        private readonly ILogger _logger;

        public ExtensionParserLoggerAdapter(ILogger logger)
        {
            _logger = logger;
        }

        public void Debug(string message)
        {
            _logger.Debug(message);
        }

        public void Info(string message)
        {
            _logger.Info(message);
        }

        public void Warning(string message)
        {
            _logger.Warning(message);
        }

        public void Error(string message)
        {
            _logger.Error(message);
        }
    }
}
