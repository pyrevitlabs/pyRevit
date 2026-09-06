using System;

namespace PyRevitLabs.UI.Client;

/// <summary>
/// Process-local access point for UI services backed by the loader-owned host session.
/// </summary>
public static class UiHostClientContext
{
    private static readonly object SyncRoot = new object();
    private static UiHostSession? _session;
    private static UiOutputClient? _output;
    private static bool _enabled;

    public static event EventHandler<UiHostEventArgs>? EventReceived;

    public static bool IsEnabled
    {
        get { lock (SyncRoot) return _enabled; }
    }

    public static bool IsAvailable
    {
        get { lock (SyncRoot) return _session != null; }
    }

    public static UiOutputClient Output
    {
        get
        {
            lock (SyncRoot)
            {
                return _output
                    ?? throw new InvalidOperationException("UI host output service is not available.");
            }
        }
    }

    public static void Configure(bool enabled)
    {
        lock (SyncRoot)
            _enabled = enabled;
    }

    public static void Attach(UiHostSession session)
    {
        if (session == null)
            throw new ArgumentNullException(nameof(session));

        lock (SyncRoot)
        {
            if (ReferenceEquals(_session, session))
                return;

            DetachCurrent();
            _session = session;
            _output = new UiOutputClient(session);
            _session.EventReceived += SessionEventReceived;
        }
    }

    public static void Detach(UiHostSession? session = null)
    {
        lock (SyncRoot)
        {
            if (session != null && !ReferenceEquals(_session, session))
                return;
            DetachCurrent();
        }
    }

    private static void DetachCurrent()
    {
        if (_session != null)
            _session.EventReceived -= SessionEventReceived;
        _session = null;
        _output = null;
    }

    private static void SessionEventReceived(object? sender, UiHostEventArgs e) =>
        EventReceived?.Invoke(sender, e);
}
