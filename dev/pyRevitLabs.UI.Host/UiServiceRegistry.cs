using PyRevitLabs.UI.Protocol;

internal interface IUiServiceHandler
{
    string ServiceName { get; }
    bool LogWireMessages { get; }
    Task<UiMessage> HandleAsync(UiMessage request);
}

internal sealed class UiServiceRegistry
{
    private readonly Dictionary<string, IUiServiceHandler> _handlers =
        new(StringComparer.Ordinal);

    public void Register(IUiServiceHandler handler)
    {
        if (handler == null)
            throw new ArgumentNullException(nameof(handler));
        if (string.IsNullOrWhiteSpace(handler.ServiceName))
            throw new ArgumentException("UI service name is required.", nameof(handler));
        if (!_handlers.TryAdd(handler.ServiceName, handler))
            throw new InvalidOperationException(
                $"UI service '{handler.ServiceName}' is already registered.");
    }

    public bool TryResolve(string? method, out IUiServiceHandler? handler)
    {
        handler = null;
        if (string.IsNullOrWhiteSpace(method))
            return false;

        var serviceName = UiMethods.GetService(method);
        return _handlers.TryGetValue(serviceName, out handler);
    }
}
