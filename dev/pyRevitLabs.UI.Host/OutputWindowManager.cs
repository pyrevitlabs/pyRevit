using System.Diagnostics;
using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.Wpf;
using Microsoft.Win32;
using PyRevitLabs.UI.Protocol;

internal sealed class OutputWindowManager : IDisposable
{
    private readonly Action<string> _log;
    private readonly HostEventChannel _events;
    private readonly TaskCompletionSource<Dispatcher> _dispatcherReady =
        new(TaskCreationOptions.RunContinuationsAsynchronously);
    private readonly Dictionary<string, IsolatedOutputWindow> _windows = new();
    private readonly Thread _uiThread;

    public OutputWindowManager(Action<string> log, HostEventChannel events)
    {
        _log = log;
        _events = events;
        _uiThread = new Thread(RunUiThread)
        {
            IsBackground = true,
            Name = "pyRevit Isolated UI",
        };
        _uiThread.SetApartmentState(ApartmentState.STA);
        _uiThread.Start();
    }
    private void RunUiThread()
    {
        var dispatcher = Dispatcher.CurrentDispatcher;
        _dispatcherReady.TrySetResult(dispatcher);
        Dispatcher.Run();
    }

    public Task CreateAsync(
        string windowId,
        string title,
        string html,
        double width,
        double height,
        double left,
        double top) =>
        InvokeAsync(async () =>
        {
            if (_windows.TryGetValue(windowId, out var existing))
            {
                existing.Show();
                return;
            }

            var window = new IsolatedOutputWindow(windowId, _log, _events);
            _windows[windowId] = window;
            window.Closed += (_, _) => _windows.Remove(windowId);
            await window.InitializeAsync(title, html, width, height, left, top);
        });
    public Task AppendHtmlAsync(string windowId, string html) =>
        WithWindowAsync(windowId, window => window.AppendHtmlAsync(html));

    public Task ReplaceBodyAsync(string windowId, string html) =>
        WithWindowAsync(windowId, window => window.ReplaceBodyAsync(html));

    public Task InjectHtmlAsync(string windowId, string target, string html) =>
        WithWindowAsync(windowId, window => window.InjectHtmlAsync(target, html));

    public Task SetTitleAsync(string windowId, string title) =>
        WithWindowAsync(windowId, window => { window.Title = title; return Task.CompletedTask; });

    public Task SetVisibilityAsync(string windowId, bool visible) =>
        WithWindowAsync(windowId, window =>
        {
            if (visible) window.Show(); else window.Hide();
            return Task.CompletedTask;
        });

    public Task SetBoundsAsync(
        string windowId,
        double width,
        double height,
        double left,
        double top) =>
        WithWindowAsync(windowId, window =>
        {
            window.SetBounds(width, height, left, top);
            return Task.CompletedTask;
        });
    public Task SetResizableAsync(string windowId, bool resizable) =>
        WithWindowAsync(windowId, window =>
        {
            window.ResizeMode = resizable
                ? ResizeMode.CanResizeWithGrip
                : ResizeMode.NoResize;
            return Task.CompletedTask;
        });

    public Task FocusAsync(string windowId) =>
        WithWindowAsync(windowId, window =>
        {
            window.Show();
            window.Activate();
            window.Focus();
            return Task.CompletedTask;
        });

    public Task CloseAsync(string windowId) =>
        WithWindowAsync(windowId, window =>
        {
            window.Close();
            return Task.CompletedTask;
        });

    public Task NavigateAsync(string windowId, string url) =>
        WithWindowAsync(windowId, window => window.NavigateAsync(url));
    public Task SetProgressAsync(
        string windowId,
        double current,
        double maximum,
        bool visible) =>
        WithWindowAsync(windowId, window =>
        {
            window.SetProgress(current, maximum, visible);
            return Task.CompletedTask;
        });

    public Task SetIndeterminateAsync(string windowId, bool state) =>
        WithWindowAsync(windowId, window =>
        {
            window.SetIndeterminate(state);
            return Task.CompletedTask;
        });

    public Task AppendLogAsync(string windowId, string level, string message) =>
        WithWindowAsync(windowId, window =>
        {
            window.AppendLog(level, message);
            return Task.CompletedTask;
        });

    public Task<string> GetHtmlAsync(string windowId) =>
        WithWindowResultAsync(windowId, window => window.GetHtmlAsync());

    public Task<string> GetTextAsync(string windowId) =>
        WithWindowResultAsync(windowId, window => window.GetTextAsync());
    public Task<string> ReadInputAsync(string windowId, string mode, string? value) =>
        WithWindowResultAsync(windowId, window => window.ReadInputAsync(mode, value));

    private async Task WithWindowAsync(
        string windowId,
        Func<IsolatedOutputWindow, Task> action)
    {
        await InvokeAsync(async () =>
        {
            if (!_windows.TryGetValue(windowId, out var window))
                throw new InvalidOperationException($"Output window '{windowId}' does not exist.");
            await action(window);
        });
    }

    private async Task<T> WithWindowResultAsync<T>(
        string windowId,
        Func<IsolatedOutputWindow, Task<T>> action)
    {
        return await InvokeAsync(async () =>
        {
            if (!_windows.TryGetValue(windowId, out var window))
                throw new InvalidOperationException($"Output window '{windowId}' does not exist.");
            return await action(window);
        });
    }
    private async Task InvokeAsync(Func<Task> action)
    {
        var dispatcher = await _dispatcherReady.Task;
        await dispatcher.InvokeAsync(action).Task.Unwrap();
    }

    private async Task<T> InvokeAsync<T>(Func<Task<T>> action)
    {
        var dispatcher = await _dispatcherReady.Task;
        return await dispatcher.InvokeAsync(action).Task.Unwrap();
    }

    public void Dispose()
    {
        if (!_dispatcherReady.Task.IsCompleted)
            return;

        var dispatcher = _dispatcherReady.Task.GetAwaiter().GetResult();
        dispatcher.Invoke(() =>
        {
            foreach (var window in _windows.Values.ToList())
                window.Close();
            _windows.Clear();
            dispatcher.BeginInvokeShutdown(DispatcherPriority.Normal);
        });
        _uiThread.Join(2000);
    }
}
internal sealed class IsolatedOutputWindow : Window
{
    private readonly string _windowId;
    private readonly Action<string> _log;
    private readonly HostEventChannel _events;
    private readonly WebView2 _browser = new();
    private readonly ProgressBar _progress = new();
    private readonly TextBox _logBox = new();
    private readonly DockPanel _inputPanel = new();
    private readonly TextBox _inputBox = new();
    private TaskCompletionSource<string>? _inputCompletion;

    public IsolatedOutputWindow(
        string windowId,
        Action<string> log,
        HostEventChannel events)
    {
        _windowId = windowId;
        _log = log;
        _events = events;
        WindowStartupLocation = WindowStartupLocation.Manual;
        ShowInTaskbar = true;
        BuildLayout();
        Closed += WindowClosed;
    }
    private void BuildLayout()
    {
        var grid = new Grid();
        grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        grid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
        grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
        grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

        _progress.Height = 4;
        _progress.Visibility = Visibility.Collapsed;
        Grid.SetRow(_progress, 0);

        Grid.SetRow(_browser, 1);

        _logBox.IsReadOnly = true;
        _logBox.MaxHeight = 120;
        _logBox.Visibility = Visibility.Collapsed;
        _logBox.VerticalScrollBarVisibility = ScrollBarVisibility.Auto;
        Grid.SetRow(_logBox, 2);

        BuildInputPanel();
        Grid.SetRow(_inputPanel, 3);

        grid.Children.Add(_progress);
        grid.Children.Add(_browser);
        grid.Children.Add(_logBox);
        grid.Children.Add(_inputPanel);
        Content = grid;
    }
    private void BuildInputPanel()
    {
        _inputPanel.Visibility = Visibility.Collapsed;
        _inputPanel.Margin = new Thickness(6);

        var submitButton = new Button
        {
            Content = "Submit",
            MinWidth = 70,
            Margin = new Thickness(6, 0, 0, 0),
        };
        submitButton.Click += (_, _) => CompleteInput(_inputBox.Text);

        var cancelButton = new Button
        {
            Content = "Cancel",
            MinWidth = 70,
            Margin = new Thickness(6, 0, 0, 0),
        };
        cancelButton.Click += (_, _) => CompleteInput(string.Empty);

        DockPanel.SetDock(cancelButton, Dock.Right);
        DockPanel.SetDock(submitButton, Dock.Right);
        _inputPanel.Children.Add(cancelButton);
        _inputPanel.Children.Add(submitButton);
        _inputPanel.Children.Add(_inputBox);
        _inputBox.KeyDown += (_, e) =>
        {
            if (e.Key == System.Windows.Input.Key.Enter)
                CompleteInput(_inputBox.Text);
        };
    }
    public async Task InitializeAsync(
        string title,
        string html,
        double width,
        double height,
        double left,
        double top)
    {
        Title = title;
        SetBounds(width, height, left, top);
        MinWidth = 400;
        MinHeight = 180;

        var userDataFolder = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "pyRevit",
            "IsolatedUI",
            "WebView2");
        Directory.CreateDirectory(userDataFolder);
        var options = new CoreWebView2EnvironmentOptions("--allow-file-access-from-files");
        var environment = await CoreWebView2Environment.CreateAsync(
            browserExecutableFolder: null,
            userDataFolder: userDataFolder,
            options: options);
        await _browser.EnsureCoreWebView2Async(environment);
        ConfigureBrowser();
        await NavigateToHtmlAsync(html);
        Show();
        _log($"output window created id={_windowId} title={title}");
    }
    private void ConfigureBrowser()
    {
        var settings = _browser.CoreWebView2.Settings;
        settings.AreDefaultContextMenusEnabled = true;
        settings.AreDevToolsEnabled = true;
        settings.IsStatusBarEnabled = false;
        _browser.CoreWebView2.NavigationStarting += BrowserNavigationStarting;
    }

    private async void BrowserNavigationStarting(
        object? sender,
        CoreWebView2NavigationStartingEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(e.Uri)
            || e.Uri.StartsWith("about:", StringComparison.OrdinalIgnoreCase)
            || e.Uri.StartsWith("data:", StringComparison.OrdinalIgnoreCase)
            || e.Uri.StartsWith("file:", StringComparison.OrdinalIgnoreCase))
            return;

        if (e.Uri.StartsWith("revit:", StringComparison.OrdinalIgnoreCase))
        {
            e.Cancel = true;
            await _events.SendAsync(UiMethods.Output.Navigate, _windowId, e.Uri);
            _log($"output navigation event id={_windowId} url={e.Uri}");
            return;
        }
        if (e.Uri.StartsWith("http:", StringComparison.OrdinalIgnoreCase)
            || e.Uri.StartsWith("https:", StringComparison.OrdinalIgnoreCase))
        {
            e.Cancel = true;
            try
            {
                Process.Start(new ProcessStartInfo(e.Uri) { UseShellExecute = true });
            }
            catch (Exception ex)
            {
                _log($"failed opening external url id={_windowId}: {ex.Message}");
            }
            return;
        }

        e.Cancel = true;
        _log($"blocked navigation id={_windowId} url={e.Uri}");
    }

    private async Task NavigateToHtmlAsync(string html)
    {
        var completion = new TaskCompletionSource<bool>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        void Handler(object? _, CoreWebView2NavigationCompletedEventArgs e) =>
            completion.TrySetResult(e.IsSuccess);
        _browser.CoreWebView2.NavigationCompleted += Handler;
        _browser.NavigateToString(html);
        await completion.Task;
        _browser.CoreWebView2.NavigationCompleted -= Handler;
    }
    public async Task AppendHtmlAsync(string html)
    {
        var encoded = JsonSerializer.Serialize(html);
        await _browser.ExecuteScriptAsync(
            "(() => {" +
            "const b=document.body;" +
            "const near=(window.innerHeight+window.scrollY)>=(b.scrollHeight-60);" +
            $"b.insertAdjacentHTML('beforeend',{encoded});" +
            "if(near) window.scrollTo(0,b.scrollHeight);" +
            "})()");
    }

    public async Task ReplaceBodyAsync(string html)
    {
        var encoded = JsonSerializer.Serialize(html);
        await _browser.ExecuteScriptAsync($"document.body.innerHTML={encoded}");
    }

    public async Task InjectHtmlAsync(string target, string html)
    {
        var encodedHtml = JsonSerializer.Serialize(html);
        var encodedTarget = JsonSerializer.Serialize(target);
        await _browser.ExecuteScriptAsync(
            $"document.querySelector({encodedTarget})?.insertAdjacentHTML('beforeend',{encodedHtml})");
    }
    public Task NavigateAsync(string url)
    {
        _browser.CoreWebView2.Navigate(url);
        return Task.CompletedTask;
    }

    public async Task<string> GetHtmlAsync()
    {
        var result = await _browser.ExecuteScriptAsync("document.documentElement.outerHTML");
        return JsonSerializer.Deserialize<string>(result) ?? string.Empty;
    }

    public async Task<string> GetTextAsync()
    {
        var result = await _browser.ExecuteScriptAsync("document.body.innerText");
        return JsonSerializer.Deserialize<string>(result) ?? string.Empty;
    }

    public void SetBounds(double width, double height, double left, double top)
    {
        if (width > 0) Width = width;
        if (height > 0) Height = height;
        if (!double.IsNaN(left) && !double.IsInfinity(left)) Left = left;
        if (!double.IsNaN(top) && !double.IsInfinity(top)) Top = top;
    }
    public void SetProgress(double current, double maximum, bool visible)
    {
        _progress.IsIndeterminate = false;
        _progress.Minimum = 0;
        _progress.Maximum = maximum > 0 ? maximum : 1;
        _progress.Value = Math.Max(0, Math.Min(current, _progress.Maximum));
        _progress.Visibility = visible ? Visibility.Visible : Visibility.Collapsed;
    }

    public void SetIndeterminate(bool state)
    {
        _progress.IsIndeterminate = state;
        _progress.Visibility = state ? Visibility.Visible : Visibility.Collapsed;
    }

    public void AppendLog(string level, string message)
    {
        _logBox.Visibility = Visibility.Visible;
        _logBox.AppendText($"[{level}] {message}{Environment.NewLine}");
        _logBox.ScrollToEnd();
    }

    public async Task<string> ReadInputAsync(string mode, string? value)
    {
        if (string.Equals(mode, "file", StringComparison.OrdinalIgnoreCase))
        {
            var dialog = new OpenFileDialog();
            return dialog.ShowDialog(this) == true ? dialog.FileName : string.Empty;
        }
        if (_inputCompletion != null)
            throw new InvalidOperationException("An input request is already active.");

        _inputBox.Text = value ?? string.Empty;
        _inputCompletion = new TaskCompletionSource<string>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        _inputPanel.Visibility = Visibility.Visible;
        _inputBox.Focus();
        _inputBox.SelectAll();
        return await _inputCompletion.Task;
    }

    private void CompleteInput(string value)
    {
        var completion = _inputCompletion;
        if (completion == null)
            return;
        _inputCompletion = null;
        _inputPanel.Visibility = Visibility.Collapsed;
        completion.TrySetResult(value);
    }

    private async void WindowClosed(object? sender, EventArgs e)
    {
        CompleteInput(string.Empty);
        if (_browser.CoreWebView2 != null)
            _browser.CoreWebView2.NavigationStarting -= BrowserNavigationStarting;
        await _events.SendAsync(UiMethods.Output.Closed, _windowId);
        _log($"output window closed id={_windowId}");
    }
}
