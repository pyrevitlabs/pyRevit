#nullable enable
using pyRevitAssemblyBuilder.SessionManager;

namespace pyRevitAssemblyBuilder.UIManager
{
    /// <summary>
    /// Surfaces why a smart button, ComboBox or CheckBox script failed to load.
    /// </summary>
    /// <remarks>
    /// The executors live in the IronPython-specific pyRevitLoader assembly, which this assembly cannot
    /// reference, so their <c>Message</c> property is read by reflection. They report script problems
    /// through a delegate that the initializers route to the debug or info level; reading
    /// <c>Message</c> after each call is what makes a failed script visible at the default log level.
    /// Invariant: keep the property name in sync with <c>SmartButtonExecutor</c>, <c>ComboBoxExecutor</c>
    /// and <c>CheckBoxExecutor</c> in <c>dev/pyRevitLoader/Source</c>.
    /// </remarks>
    internal static class ExecutorFailure
    {
        private const string MessagePropertyName = "Message";

        /// <summary>
        /// Logs the executor's failure of its last call, if any, as an error naming the bundle.
        /// </summary>
        internal static void ReportIfFailed(object executor, string bundleKind, string bundleName, ILogger logger)
        {
            var message = executor.GetType().GetProperty(MessagePropertyName)?.GetValue(executor) as string;
            if (!string.IsNullOrEmpty(message))
                logger.Error($"{bundleKind} '{bundleName}' failed to load its script: {message}");
        }
    }
}
