namespace pyRevitAssemblyBuilder.AssemblyMaker
{
    public class ExtensionAssemblyInfo
    {
        public string Name { get; }
        public string Location { get; }
        public bool IsReloading { get; }

        public ExtensionAssemblyInfo(string name, string location, bool isReloading)
        {
            Name = name;
            Location = location;
            IsReloading = isReloading;
        }

        public override string ToString()
        {
            return $"{Name} ({(IsReloading ? "Reloaded" : "Fresh")}) -> {Location}";
        }
    }
}
