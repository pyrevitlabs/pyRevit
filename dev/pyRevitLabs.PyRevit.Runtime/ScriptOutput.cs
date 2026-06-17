using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Windows.Threading;
using Autodesk.Revit.UI;
using pyRevitLabs.NLog;
using pyRevitLabs.NLog.Config;
using pyRevitLabs.NLog.Targets;
using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Scripting-facing wrapper around an output window: rendering helpers
    /// (text, html, tables, charts, progress) plus window management.
    /// Commands get an instance bound to their runtime; session/startup
    /// output goes through a shared default instance.
    /// </summary>
    public sealed class ScriptOutput {
        private const string OutputTargetName = "pyrevit-runtime-output";
        private static readonly object SyncRoot = new object();
        private static ScriptOutput _default;
        private static bool _loggingConfigured;
        private static readonly System.Runtime.CompilerServices.ConditionalWeakTable<ScriptRuntime, ScriptOutput> _runtimeOutputs =
            new System.Runtime.CompilerServices.ConditionalWeakTable<ScriptRuntime, ScriptOutput>();

        private WeakReference<ScriptRuntime> _runtime;
        private ScriptConsole _window;
        private ScriptIO _outputStream;
        private UIApplication _uiApp;
        private bool _debugMode;
        private string _title;
        private string _outputId;
        private string _appVersion;
        private bool _hasErrors;
        private bool _isSessionOutput;
        private int _tableCounter;

        private ScriptOutput(UIApplication uiApp = null, bool debugMode = false) {
            _uiApp = uiApp;
            _debugMode = debugMode;
        }

        private ScriptOutput(ScriptRuntime runtime) {
            _runtime = new WeakReference<ScriptRuntime>(runtime);
            _uiApp = runtime.UIApp;
            _debugMode = runtime.ScriptRuntimeConfigs?.DebugMode ?? false;
            _title = runtime.ScriptData?.CommandName;
            _outputId = runtime.ScriptData?.CommandUniqueId;
        }

        /// <summary>Get the shared session output, creating it on first use.</summary>
        public static ScriptOutput GetDefault(UIApplication uiApp = null, bool debugMode = false) {
            lock (SyncRoot) {
                if (_default == null)
                    _default = new ScriptOutput(uiApp, debugMode);

                if (uiApp != null)
                    _default._uiApp = uiApp;
                if (debugMode)
                    _default._debugMode = true;

                return _default;
            }
        }

        /// <summary>
        /// Get the output bound to a command runtime. Startup scripts and a
        /// null runtime resolve to the shared session output.
        /// </summary>
        public static ScriptOutput GetForRuntime(ScriptRuntime runtime) {
            if (runtime == null || runtime.IsDisposed)
                return GetDefault();

            if (IsStartupRuntime(runtime))
                return GetDefault(runtime.UIApp, runtime.ScriptRuntimeConfigs?.DebugMode ?? false);

            return _runtimeOutputs.GetValue(runtime, r => new ScriptOutput(r));
        }

        private ScriptRuntime BoundRuntime {
            get {
                if (_runtime == null)
                    return null;

                ScriptRuntime runtime;
                return _runtime.TryGetTarget(out runtime)
                    && runtime != null
                    && !runtime.IsDisposed
                    ? runtime
                    : null;
            }
        }

        private static string GetRuntimeAppVersion(ScriptRuntime runtime) {
            if (runtime?.EnvDict == null)
                return null;

            return string.Format(
                "{0}:{1}:{2}",
                runtime.EnvDict.PyRevitVersion,
                runtime.EngineType == ScriptEngineType.CPython
                    ? runtime.EnvDict.PyRevitCPYVersion
                    : runtime.EnvDict.PyRevitIPYVersion,
                runtime.EnvDict.RevitVersion);
        }

        private void ApplyWindowIdentity(ScriptConsole outWindow) {
            if (string.IsNullOrEmpty(_appVersion) && _runtime != null) {
                ScriptRuntime runtime;
                if (_runtime.TryGetTarget(out runtime))
                    _appVersion = GetRuntimeAppVersion(runtime);
            }

            if (!string.IsNullOrEmpty(_title))
                outWindow.OutputTitle = _title;
            if (!string.IsNullOrEmpty(_outputId))
                outWindow.OutputId = _outputId;
            if (!string.IsNullOrEmpty(_appVersion))
                outWindow.AppVersion = _appVersion;
        }

        internal static ScriptOutput GetDefaultIfWindowReady() {
            lock (SyncRoot) {
                if (_default == null || _default._window == null || _default.IsWindowClosed)
                    return null;

                return _default;
            }
        }

        /// <summary>
        /// Route NLog messages into the session output window. Call once at
        /// session setup; the logging level is resolved at that moment.
        /// </summary>
        public static void ConfigureLogging() {
            lock (SyncRoot) {
                if (_loggingConfigured)
                    return;

                var minLevel = GetConfiguredMinLogLevel();

                var target = new ScriptOutputTarget {
                    Name = OutputTargetName,
                    Layout = "${level:uppercase=true} [${logger}] ${message}"
                };

                var config = LogManager.Configuration ?? new LoggingConfiguration();
                config.AddTarget(OutputTargetName, target);
                config.AddRule(minLevel, LogLevel.Fatal, target);
                LogManager.Configuration = config;
                _loggingConfigured = true;
            }
        }

        private static LogLevel GetConfiguredMinLogLevel() {
            try {
                var configuredLevel = PyRevitConfigs.GetLoggingLevel();
                if (configuredLevel == PyRevitLogLevels.Debug)
                    return LogLevel.Trace;
                if (configuredLevel == PyRevitLogLevels.Verbose)
                    return LogLevel.Info;
            }
            catch { }

            return LogLevel.Warn;
        }

        /// <summary>Apply a runtime's identity (title, id, version) to the session output window.</summary>
        public static void ConfigureForRuntime(ScriptRuntime runtime) {
            if (runtime == null)
                return;

            var output = GetDefault(runtime.UIApp, runtime.ScriptRuntimeConfigs?.DebugMode ?? false);
            var isStartupRuntime = IsStartupRuntime(runtime);
            output.Configure(
                runtime.UIApp,
                isStartupRuntime ? null : runtime.ScriptData?.CommandName,
                runtime.ScriptData?.CommandUniqueId,
                string.Format(
                    "{0}:{1}:{2}",
                    runtime.EnvDict.PyRevitVersion,
                    runtime.EngineType == ScriptEngineType.CPython
                        ? runtime.EnvDict.PyRevitCPYVersion
                        : runtime.EnvDict.PyRevitIPYVersion,
                    runtime.EnvDict.RevitVersion),
                runtime.ScriptRuntimeConfigs?.DebugMode ?? false,
                false);
        }

        internal static bool IsStartupRuntime(ScriptRuntime runtime) {
            return runtime?.ScriptData?.IsStartupScript ?? false;
        }

        internal static string GetStartupOutputPrefix(ScriptRuntime runtime) {
            if (!IsStartupRuntime(runtime))
                return null;

            var extensionName = runtime.ScriptData.CommandExtension;
            return string.IsNullOrEmpty(extensionName)
                ? null
                : string.Format("[{0}] ", extensionName);
        }

        public void Configure(
            UIApplication uiApp = null,
            string title = null,
            string outputId = null,
            string appVersion = null,
            bool debugMode = false,
            bool isSessionOutput = false) {
            if (uiApp != null)
                _uiApp = uiApp;
            if (debugMode)
                _debugMode = true;
            if (!string.IsNullOrEmpty(title))
                _title = title;
            if (!string.IsNullOrEmpty(outputId))
                _outputId = outputId;
            if (!string.IsNullOrEmpty(appVersion))
                _appVersion = appVersion;

            var outWindow = window;
            ApplyWindowIdentity(outWindow);
            if (isSessionOutput) {
                _isSessionOutput = true;
                outWindow.IsSessionOutput = true;
            }
        }

        public ScriptConsole window {
            get {
                var runtime = BoundRuntime;
                if (runtime != null) {
                    _window = runtime.OutputWindow;
                    return _window;
                }

                if (_window == null || _window.ClosedByUser) {
                    _window = new ScriptConsole(_debugMode, _uiApp);
                    if (string.IsNullOrEmpty(_window.OutputId))
                        _window.OutputId = "pyrevit-output";
                    ApplyWindowIdentity(_window);
                    // re-apply session state so a window reopened mid-session is still
                    // protected from close_other_outputs
                    _window.IsSessionOutput = _isSessionOutput;
                    _outputStream = null;
                }
                return _window;
            }
        }

        internal Dispatcher WindowDispatcher => _window?.Dispatcher;

        public ScriptIO output_stream {
            get {
                var runtime = BoundRuntime;
                if (runtime != null) {
                    _window = runtime.OutputWindow;
                    return runtime.OutputStream;
                }

                if (_outputStream == null) {
                    _outputStream = new ScriptIO(window);
                    _outputStream.PrintDebugInfo = _debugMode;
                }
                return _outputStream;
            }
        }

        public System.Windows.Forms.WebBrowser renderer => window.renderer;
        public string output_id => window.OutputId;
        public string output_uniqueid => window.OutputUniqueId;
        public bool is_closed_by_user => window.ClosedByUser;
        public string last_line => window.GetLastLine();
        public bool has_errors => _hasErrors;

        public bool debug_mode {
            get { return output_stream.PrintDebugInfo; }
            set {
                _debugMode = value;
                output_stream.PrintDebugInfo = value;
            }
        }

        private bool IsWindowClosed => _window != null && _window.ClosedByUser;

        public void mark_error() {
            _hasErrors = true;
        }

        public void write(string content) {
            if (content == null)
                return;

            output_stream.write(content);
        }

        private void write_html_entry(string content) {
            if (content == null)
                return;

            output_stream.WriteEntry(content);
        }

        public void write_line(string content) {
            write((content ?? string.Empty) + Environment.NewLine);
        }

        internal void write_log_record(string content, bool markError) {
            var dispatcher = System.Windows.Application.Current?.Dispatcher;
            if (dispatcher != null
                    && !dispatcher.HasShutdownStarted
                    && !dispatcher.HasShutdownFinished
                    && !dispatcher.CheckAccess()) {
                dispatcher.BeginInvoke(
                    new Action(() => write_log_record(content, markError)),
                    DispatcherPriority.Background);
                return;
            }

            if (markError)
                mark_error();
            write_line(content);
        }

        private void log_to_activity(Action<ScriptConsole> writeLog) {
            var dispatcher = System.Windows.Application.Current?.Dispatcher;
            if (dispatcher != null
                    && !dispatcher.HasShutdownStarted
                    && !dispatcher.HasShutdownFinished
                    && !dispatcher.CheckAccess()) {
                dispatcher.BeginInvoke(
                    new Action(() => log_to_activity(writeLog)),
                    DispatcherPriority.Background);
                return;
            }

            show_logpanel();
            writeLog(window);
        }

        public void log_debug(string message) {
            log_to_activity(output => output.activityBar.ConsoleLog(message));
        }

        public void log_success(string message) {
            log_to_activity(output => output.activityBar.ConsoleLogOK(message));
        }

        public void log_info(string message) {
            log_to_activity(output => output.activityBar.ConsoleLogInfo(message));
        }

        public void log_warning(string message) {
            log_to_activity(output => output.activityBar.ConsoleLogWarning(message));
        }

        public void log_deprecate(string message) {
            log_to_activity(output => output.activityBar.ConsoleLogWarning(message));
        }

        public void log_error(string message) {
            mark_error();
            log_to_activity(output => output.activityBar.ConsoleLogError(message));
        }

        public void log_critical(string message) {
            log_error(message);
        }

        public void self_destruct(int seconds) {
            if (!_hasErrors && seconds > 0)
                window.SelfDestructTimer(seconds);
        }

        public void set_session_output(bool isSessionOutput) {
            _isSessionOutput = isSessionOutput;
            window.IsSessionOutput = isSessionOutput;
        }

        public void close() { window.Close(); }
        public void hide() { window.Hide(); }
        public void show() { window.Show(); }
        public void lock_size() { window.LockSize(); }
        public void unlock_size() { window.UnlockSize(); }
        public void freeze() { output_stream.Flush(); window.Freeze(); }
        public void unfreeze() { window.Unfreeze(); }
        public void set_title(string title) { window.OutputTitle = title; }
        public string get_title() { return window.OutputTitle; }
        public void set_width(double width) { window.Width = width; }
        public double get_width() { return window.Width; }
        public void set_height(double height) { window.Height = height; }
        public double get_height() { return window.Height; }
        public void resize(double width, double height) { set_width(width); set_height(height); }
        public void center() {
            var workArea = System.Windows.SystemParameters.WorkArea;
            window.Left = workArea.Left + ((workArea.Width - window.Width) / 2);
            window.Top = workArea.Top + ((workArea.Height - window.Height) / 2);
        }

        public void set_font(string font_family, float font_size) {
            if (renderer != null)
                renderer.Font = new System.Drawing.Font(
                    font_family,
                    font_size,
                    System.Drawing.FontStyle.Regular,
                    System.Drawing.GraphicsUnit.Point);
        }

        public void set_icon(string iconpath) { window.SetIcon(iconpath); }
        public void reset_icon() { window.ResetIcon(); }
        public void focus() { window.FocusOutput(); }

        public void close_others(bool all_open_outputs = false) {
            ScriptConsoleManager.CloseActiveOutputWindows(
                window,
                all_open_outputs ? null : output_id);
        }

        public void save_contents(string dest_file) {
            if (string.IsNullOrEmpty(dest_file))
                return;
            output_stream.Flush();
            File.WriteAllText(dest_file, window.GetFullHtml());
        }

        public void open_url(string dest_url) {
            renderer?.Navigate(dest_url, false);
        }

        public void open_page(string dest_file) {
            show();
            if (string.IsNullOrEmpty(dest_file) || !File.Exists(dest_file)) {
                print_md(string.Format("### :warning: Page not found: `{0}`", dest_file ?? string.Empty));
                return;
            }
            open_url(new Uri(Path.GetFullPath(dest_file)).AbsoluteUri);
        }

        public void update_progress(float cur_value, float max_value) {
            window.UpdateActivityBar(cur_value, max_value);
        }

        public void reset_progress() {
            update_progress(0, 1);
        }

        public void hide_progress() {
            window.SetActivityBarVisibility(false);
        }

        public void unhide_progress() {
            window.SetActivityBarVisibility(true);
        }

        public void indeterminate_progress(bool state) {
            window.UpdateActivityBar(state);
        }

        public void show_logpanel() {
            window.SetActivityBarVisibility(true);
        }

        public void hide_logpanel() {
            window.SetActivityBarVisibility(false);
        }

        public void print_html(string html_str) {
            write_html_entry(ScriptConsoleConfigs.ToCustomHtmlTags(html_str ?? string.Empty));
        }

        public void print_code(string code_str) {
            var code = (code_str ?? string.Empty).Replace("    ", "&nbsp;&nbsp;&nbsp;&nbsp;");
            print_html(string.Format("<div class=\"code\">{0}</div>", code));
        }

        public void print_md(string md_str) {
            print_html(MarkdownToHtml(md_str ?? string.Empty));
        }

        public void print_image(string image_path) {
            print_html(string.Format("<span><img src=\"file:///{0}\"></span>", image_path));
        }

        public void insert_divider(string level = "") {
            print_md(string.Format("{0}\n-----", level ?? string.Empty));
        }

        public void next_page() {
            print_html("<div class=\"nextpage\"></div><div>&nbsp</div>");
        }

        public void print_table(object table_data, object columns = null, object formats = null, string title = "", string last_line_style = "") {
            var rows = ToRows(table_data);
            if (rows.Count == 0)
                return;

            if (!string.IsNullOrEmpty(last_line_style))
                add_style(string.Format("tr:last-child {{ {0} }}", last_line_style));

            var headers = ToList(columns);
            var formatList = ToList(formats);
            var maxCols = 0;
            foreach (var row in rows)
                maxCols = Math.Max(maxCols, row.Count);

            if (!string.IsNullOrEmpty(title))
                print_md("### " + title);

            var md = new StringBuilder();
            md.Append("|");
            for (var idx = 0; idx < maxCols; idx++)
                md.Append((idx < headers.Count ? headers[idx] : string.Empty) + "|");
            md.AppendLine();

            md.Append("|");
            for (var idx = 0; idx < maxCols; idx++)
                md.Append(":---|");
            md.AppendLine();

            foreach (var row in rows) {
                md.Append("|");
                for (var idx = 0; idx < maxCols; idx++) {
                    var value = idx < row.Count ? row[idx] : string.Empty;
                    if (idx < formatList.Count && !string.IsNullOrEmpty(formatList[idx]))
                        value = ApplyFormat(formatList[idx], value);
                    md.Append(value + "|");
                }
                md.AppendLine();
            }

            print_md(md.ToString());
        }

        public void print_html_table(
            object table_data,
            object columns = null,
            object formats = null,
            string title = "",
            string last_line_style = "",
            object column_head_align_styles = null,
            object column_data_align_styles = null,
            object column_widths = null,
            string column_vertical_border_style = null,
            string table_width_style = null,
            bool repeat_head_as_foot = false,
            bool row_striping = true) {
            var rows = ToRows(table_data);
            if (rows.Count == 0) {
                print_md("### :warning: No table_data list");
                return;
            }

            _tableCounter += 1;
            var tableId = _tableCounter;
            var headers = ToList(columns);
            var formatList = ToList(formats);
            var headAlign = ToList(column_head_align_styles);
            var dataAlign = ToList(column_data_align_styles);
            var widths = ToList(column_widths);
            var border = string.IsNullOrEmpty(column_vertical_border_style)
                ? string.Empty
                : string.Format(" style='{0}'", column_vertical_border_style);

            if (!row_striping)
                add_style(string.Format("tr.data-row-{0} {{ background-color: #ffffff }}", tableId));
            if (!string.IsNullOrEmpty(last_line_style))
                add_style(string.Format("tr.data-row-{0}:last-child {{ {1} }}", tableId, last_line_style));
            if (!string.IsNullOrEmpty(table_width_style))
                add_style(string.Format(".tab-{0} {{ width:{1} }}", tableId, table_width_style));

            for (var idx = 0; idx < headAlign.Count; idx++)
                add_style(string.Format(".head_title-{0}-{1} {{ text-align:{2} }}", tableId, idx, headAlign[idx]));
            for (var idx = 0; idx < dataAlign.Count; idx++)
                add_style(string.Format(".data_cell-{0}-{1} {{ text-align:{2} }}", tableId, idx, dataAlign[idx]));

            var html = new StringBuilder();
            html.AppendFormat("<table class='tab-{0}'>", tableId);
            if (widths.Count > 0) {
                html.Append("<colgroup>");
                foreach (var width in widths)
                    html.AppendFormat("<col style='width: {0}'>", width);
                html.Append("</colgroup>");
            }

            var headerHtml = BuildHtmlTableHeader(headers, tableId, border);
            html.Append(headerHtml);
            html.Append("<tbody>");
            foreach (var row in rows) {
                html.AppendFormat("<tr class='data-row-{0}'>", tableId);
                for (var idx = 0; idx < row.Count; idx++) {
                    var value = row[idx];
                    if (idx < formatList.Count && !string.IsNullOrEmpty(formatList[idx]))
                        value = ApplyFormat(formatList[idx], value);
                    html.AppendFormat("<td class='data_cell-{0}-{1}'{2}>{3}</td>", tableId, idx, border, value);
                }
                html.Append("</tr>");
            }

            if (repeat_head_as_foot && headers.Count > 0)
                html.Append(headerHtml);
            html.Append("</tbody></table>");

            if (!string.IsNullOrEmpty(title))
                print_md("### " + title);
            print_html(html.ToString());
        }

        public string get_head_html() {
            window.WaitReadyBrowser();
            var head = renderer?.Document?.GetElementsByTagName("head");
            return head != null && head.Count > 0 ? head[0].InnerHtml : string.Empty;
        }

        public void inject_to_head(string element_tag, string element_contents, object attribs = null) {
            InjectElement("head", element_tag, element_contents, attribs);
        }

        public void inject_to_body(string element_tag, string element_contents, object attribs = null) {
            InjectElement("body", element_tag, element_contents, attribs);
        }

        public void inject_script(string script_code, object attribs = null, bool body = false) {
            if (body)
                inject_to_body("script", script_code, attribs);
            else
                inject_to_head("script", script_code, attribs);
        }

        public void add_style(string style_code, object attribs = null) {
            inject_to_head("style", style_code, attribs);
        }

        private void InjectElement(string targetName, string elementTag, string contents, object attribs) {
            output_stream.Flush();
            window.WaitReadyBrowser();
            var document = renderer?.Document;
            if (document == null)
                return;

            var element = document.CreateElement(elementTag);
            if (!string.IsNullOrEmpty(contents))
                element.InnerHtml = contents;

            foreach (var attr in ToDictionary(attribs))
                element.SetAttribute(attr.Key, attr.Value);

            var targets = document.GetElementsByTagName(targetName);
            if (targets != null && targets.Count > 0)
                targets[0].AppendChild(element);
            window.WaitReadyBrowser();
        }

        private static string MarkdownToHtml(string markdown) {
            var html = new StringBuilder();
            var lines = markdown.Replace("\r\n", "\n").Replace('\r', '\n').Split('\n');
            var inList = false;

            foreach (var rawLine in lines) {
                var line = rawLine.TrimEnd();
                if (string.IsNullOrWhiteSpace(line)) {
                    if (inList) {
                        html.Append("</ul>");
                        inList = false;
                    }
                    continue;
                }

                if (line.Trim('-') == string.Empty && line.Length >= 3) {
                    if (inList) {
                        html.Append("</ul>");
                        inList = false;
                    }
                    html.Append("<hr />");
                    continue;
                }

                if (line.StartsWith("#")) {
                    if (inList) {
                        html.Append("</ul>");
                        inList = false;
                    }
                    var level = 0;
                    while (level < line.Length && line[level] == '#')
                        level++;
                    level = Math.Min(Math.Max(level, 1), 6);
                    html.AppendFormat("<h{0}>{1}</h{0}>", level, InlineMarkdown(line.Substring(level).Trim()));
                    continue;
                }

                if (line.StartsWith("- ") || line.StartsWith("* ")) {
                    if (!inList) {
                        html.Append("<ul>");
                        inList = true;
                    }
                    html.AppendFormat("<li>{0}</li>", InlineMarkdown(line.Substring(2).Trim()));
                    continue;
                }

                if (line.StartsWith("|") && line.EndsWith("|")) {
                    if (inList) {
                        html.Append("</ul>");
                        inList = false;
                    }
                    html.Append(MarkdownTableToHtml(lines));
                    break;
                }

                if (inList) {
                    html.Append("</ul>");
                    inList = false;
                }
                html.AppendFormat("<p>{0}</p>", InlineMarkdown(line));
            }

            if (inList)
                html.Append("</ul>");

            return html.ToString();
        }

        private static string MarkdownTableToHtml(IEnumerable<string> lines) {
            var rows = new List<string[]>();
            var aligns = new List<string>();
            foreach (var line in lines) {
                var trimmed = line.Trim();
                if (!(trimmed.StartsWith("|") && trimmed.EndsWith("|")))
                    continue;
                if (Regex.IsMatch(trimmed, @"^\|[:\-\s\|]+\|$")) {
                    foreach (var spec in trimmed.Trim('|').Split('|')) {
                        var s = spec.Trim();
                        var left = s.StartsWith(":");
                        var right = s.EndsWith(":");
                        if (left && right)
                            aligns.Add("center");
                        else if (right)
                            aligns.Add("right");
                        else if (left)
                            aligns.Add("left");
                        else
                            aligns.Add(string.Empty);
                    }
                    continue;
                }
                rows.Add(trimmed.Trim('|').Split('|'));
            }

            if (rows.Count == 0)
                return string.Empty;

            var html = new StringBuilder("<table>");
            html.Append("<thead><tr>");
            var headerCells = rows[0];
            for (var idx = 0; idx < headerCells.Length; idx++)
                html.AppendFormat("<th{0}>{1}</th>", AlignAttr(aligns, idx), InlineMarkdown(headerCells[idx].Trim()));
            html.Append("</tr></thead><tbody>");
            for (var rowIdx = 1; rowIdx < rows.Count; rowIdx++) {
                html.Append("<tr>");
                var cells = rows[rowIdx];
                for (var idx = 0; idx < cells.Length; idx++)
                    html.AppendFormat("<td{0}>{1}</td>", AlignAttr(aligns, idx), InlineMarkdown(cells[idx].Trim()));
                html.Append("</tr>");
            }
            html.Append("</tbody></table>");
            return html.ToString();
        }

        private static string AlignAttr(List<string> aligns, int idx) {
            if (idx < aligns.Count && !string.IsNullOrEmpty(aligns[idx]))
                return string.Format(" style='text-align:{0}'", aligns[idx]);
            return string.Empty;
        }

        private static string InlineMarkdown(string text) {
            var encoded = text ?? string.Empty;
            encoded = Regex.Replace(encoded, @"\*\*(.+?)\*\*", "<strong>$1</strong>");
            encoded = Regex.Replace(encoded, @"__(.+?)__", "<strong>$1</strong>");
            encoded = Regex.Replace(encoded, @"\*(.+?)\*", "<em>$1</em>");
            encoded = Regex.Replace(encoded, @"(?<!\w)_(.+?)_(?!\w)", "<em>$1</em>");
            encoded = Regex.Replace(encoded, @"`(.+?)`", "<code>$1</code>");
            return encoded;
        }

        private static string BuildHtmlTableHeader(List<string> columns, int tableUid, string borderStyle) {
            if (columns.Count == 0)
                return string.Empty;

            var html = new StringBuilder();
            html.AppendFormat("<thead><tr{0}>", borderStyle);
            for (var idx = 0; idx < columns.Count; idx++)
                html.AppendFormat("<th class='head_title-{0}-{1}' align='left'>{2}</th>", tableUid, idx, columns[idx]);
            html.Append("</tr></thead>");
            return html.ToString();
        }

        private static List<List<string>> ToRows(object value) {
            var rows = new List<List<string>>();
            if (value == null || value is string)
                return rows;

            var enumerable = value as IEnumerable;
            if (enumerable == null)
                return rows;

            foreach (var rowObj in enumerable)
                rows.Add(ToList(rowObj));
            return rows;
        }

        private static List<string> ToList(object value) {
            var items = new List<string>();
            if (value == null)
                return items;
            if (value is string) {
                items.Add((string)value);
                return items;
            }

            var enumerable = value as IEnumerable;
            if (enumerable == null) {
                items.Add(value.ToString());
                return items;
            }

            foreach (var item in enumerable)
                items.Add(item == null ? string.Empty : item.ToString());
            return items;
        }

        private static Dictionary<string, string> ToDictionary(object value) {
            var result = new Dictionary<string, string>();
            if (value == null)
                return result;

            var dictionary = value as IDictionary;
            if (dictionary != null) {
                foreach (DictionaryEntry entry in dictionary)
                    result[entry.Key.ToString()] = entry.Value?.ToString() ?? string.Empty;
                return result;
            }

            return result;
        }

        private static string ApplyFormat(string format, string value) {
            if (string.IsNullOrEmpty(format))
                return value;

            try {
                if (format.Contains("{}"))
                    return format.Replace("{}", value);
                return string.Format(format, value);
            }
            catch {
                return value;
            }
        }
    }

    public class ScriptOutputTarget : TargetWithLayout {
        [ThreadStatic]
        private static bool _emitting;

        protected override void Write(LogEventInfo logEvent) {
            try {
                var output = ScriptOutput.GetDefaultIfWindowReady();
                if (output == null)
                    return;

                var dispatcher = output.WindowDispatcher;
                if (dispatcher == null || dispatcher.HasShutdownStarted || dispatcher.HasShutdownFinished)
                    return;

                var rendered = Layout.Render(logEvent);
                var markError = logEvent.Level >= LogLevel.Error;

                if (dispatcher.CheckAccess()) {
                    DoWrite(output, markError, rendered);
                    return;
                }

                // NLog can emit from background work during startup; WPF output must
                // only be touched on its dispatcher thread.
                dispatcher.BeginInvoke(
                    new Action(() => {
                        try {
                            DoWrite(ScriptOutput.GetDefaultIfWindowReady(), markError, rendered);
                        }
                        catch { }
                    }),
                    DispatcherPriority.Background);
            }
            catch { }
        }

        private static void DoWrite(ScriptOutput output, bool markError, string rendered) {
            if (output == null || rendered == null || _emitting)
                return;

            _emitting = true;
            try {
                if (markError)
                    output.mark_error();
                output.write_line(rendered);
            }
            finally {
                _emitting = false;
            }
        }
    }
}
