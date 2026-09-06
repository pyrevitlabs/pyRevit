using System;
using PyRevitLabs.UI.Client;

namespace PyRevitLoader
{
    /// <summary>
    /// Runtime-facing façade over the loader-owned isolated UI host session.
    /// </summary>
    public static class IsolatedUiService
    {
        private static UiHostSession _attachedSession;

        public static event EventHandler<IsolatedUiEventArgs> EventReceived;

        public static bool IsAvailable => UiHostIntegration.Session != null;

        internal static void Attach(UiHostSession session)
        {
            if (ReferenceEquals(_attachedSession, session))
                return;
            Detach(_attachedSession);
            _attachedSession = session;
            if (_attachedSession != null)
                _attachedSession.EventReceived += SessionEventReceived;
        }

        internal static void Detach(UiHostSession session)
        {
            if (session == null || !ReferenceEquals(_attachedSession, session))
                return;
            _attachedSession.EventReceived -= SessionEventReceived;
            _attachedSession = null;
        }
        private static void SessionEventReceived(object sender, UiHostEventArgs e)
        {
            UiHostIntegration.WriteLog(
                $"event method={e.Method} window={e.WindowId} value={e.Value ?? "-"}");
            EventReceived?.Invoke(
                null,
                new IsolatedUiEventArgs(e.Method, e.WindowId, e.Value));
        }

        private static UiHostSession RequireSession(string method, string windowId)
        {
            var session = UiHostIntegration.Session;
            if (session == null)
                throw new InvalidOperationException("Isolated UI host is not available.");
            return session;
        }

        public static void CreateWindow(
            string windowId,
            string title,
            string html,
            double width,
            double height,
            double left,
            double top)
        {
            RequireSession("output.create", windowId)
                .CreateOutputWindowAsync(windowId, title, html, width, height, left, top)
                .GetAwaiter().GetResult();
        }
        public static void AppendHtml(string windowId, string html) =>
            RequireSession("output.append", windowId)
                .AppendOutputHtmlAsync(windowId, html).GetAwaiter().GetResult();

        public static void ReplaceBody(string windowId, string html) =>
            RequireSession("output.replace_body", windowId)
                .ReplaceOutputBodyAsync(windowId, html).GetAwaiter().GetResult();

        public static void InjectHtml(string windowId, string target, string html) =>
            RequireSession("output.inject", windowId)
                .InjectOutputHtmlAsync(windowId, target, html).GetAwaiter().GetResult();

        public static void SetTitle(string windowId, string title) =>
            RequireSession("output.set_title", windowId)
                .SetOutputTitleAsync(windowId, title).GetAwaiter().GetResult();

        public static void SetVisibility(string windowId, bool visible) =>
            RequireSession("output.set_visibility", windowId)
                .SetOutputVisibilityAsync(windowId, visible).GetAwaiter().GetResult();

        public static void SetBounds(
            string windowId,
            double width,
            double height,
            double left,
            double top) =>
            RequireSession("output.set_bounds", windowId)
                .SetOutputBoundsAsync(windowId, width, height, left, top)
                .GetAwaiter().GetResult();
        public static void SetResizable(string windowId, bool resizable) =>
            RequireSession("output.set_resizable", windowId)
                .SetOutputResizableAsync(windowId, resizable).GetAwaiter().GetResult();

        public static void Focus(string windowId) =>
            RequireSession("output.focus", windowId)
                .FocusOutputAsync(windowId).GetAwaiter().GetResult();

        public static void Close(string windowId) =>
            RequireSession("output.close", windowId)
                .CloseOutputAsync(windowId).GetAwaiter().GetResult();

        public static void Navigate(string windowId, string url) =>
            RequireSession("output.navigate", windowId)
                .NavigateOutputAsync(windowId, url).GetAwaiter().GetResult();

        public static void SetProgress(
            string windowId,
            double current,
            double maximum,
            bool visible) =>
            RequireSession("output.progress", windowId)
                .SetOutputProgressAsync(windowId, current, maximum, visible)
                .GetAwaiter().GetResult();

        public static void SetIndeterminate(string windowId, bool state) =>
            RequireSession("output.indeterminate", windowId)
                .SetOutputIndeterminateAsync(windowId, state).GetAwaiter().GetResult();
        public static void AppendLog(string windowId, string level, string message) =>
            RequireSession("output.log", windowId)
                .AppendOutputLogAsync(windowId, level, message).GetAwaiter().GetResult();

        public static string GetHtml(string windowId) =>
            RequireSession("output.get_html", windowId)
                .GetOutputHtmlAsync(windowId).GetAwaiter().GetResult();

        public static string GetText(string windowId) =>
            RequireSession("output.get_text", windowId)
                .GetOutputTextAsync(windowId).GetAwaiter().GetResult();

        public static string ReadInput(
            string windowId,
            string mode,
            string value = null) =>
            RequireSession("output.read_input", windowId)
                .ReadOutputInputAsync(windowId, mode, value).GetAwaiter().GetResult();
    }

    public sealed class IsolatedUiEventArgs : EventArgs
    {
        public IsolatedUiEventArgs(string method, string windowId, string value)
        {
            Method = method;
            WindowId = windowId;
            Value = value;
        }

        public string Method { get; }
        public string WindowId { get; }
        public string Value { get; }
    }
}
