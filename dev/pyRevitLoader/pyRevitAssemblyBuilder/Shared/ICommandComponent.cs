namespace pyRevitAssemblyBuilder.Shared
{
    public interface ICommandComponent
    {
        string Name { get; }
        string ScriptPath { get; }
        string Tooltip { get; }
        string UniqueId { get; }
        string ExtensionName { get; }
    }
}
