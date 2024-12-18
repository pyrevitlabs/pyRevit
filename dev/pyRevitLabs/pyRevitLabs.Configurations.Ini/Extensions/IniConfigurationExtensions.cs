namespace pyRevitLabs.Configurations.Ini.Extensions;

public static class IniConfigurationExtensions
{
    public static ConfigurationBuilder AddIniConfiguration(this ConfigurationBuilder builder, string configurationPath, bool readOnly = default)
    {
        if (builder == null)
            throw new ArgumentNullException(nameof(builder));

        if (string.IsNullOrWhiteSpace(configurationPath))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(configurationPath));

        return builder.AddConfigurationSource(IniConfiguration.Create(configurationPath, readOnly));
    }
}