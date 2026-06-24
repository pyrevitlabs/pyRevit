namespace pyRevitLabs.Configurations.Ini.Extensions;

public static class IniConfigurationExtensions
{
    public static ConfigurationBuilder AddIniConfiguration(
        this ConfigurationBuilder builder, string configurationPath, string configurationName, bool readOnly = default)
    {
        if (builder == null)
            throw new ArgumentNullException(nameof(builder));

        if (string.IsNullOrWhiteSpace(configurationPath))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(configurationPath));

        if (string.IsNullOrWhiteSpace(configurationName))
            throw new ArgumentException("Value cannot be null or empty.", nameof(configurationName));

        return builder.AddConfigurationSource(configurationName, IniConfiguration.Create(configurationPath, readOnly));
    }
}
