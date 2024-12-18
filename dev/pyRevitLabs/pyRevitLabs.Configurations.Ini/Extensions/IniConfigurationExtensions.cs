namespace pyRevitLabs.Configurations.Ini.Extensions;

public static class IniConfigurationExtensions
{
    public static ConfigurationBuilder AddIniConfiguration(
        this ConfigurationBuilder builder, string configurationPath, string conigurationName, bool readOnly = default)
    {
        if (builder == null)
            throw new ArgumentNullException(nameof(builder));

        if (string.IsNullOrWhiteSpace(configurationPath))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(configurationPath));
        
        if (string.IsNullOrWhiteSpace(conigurationName))
            throw new ArgumentException("Value cannot be null or empty.", nameof(conigurationName));

        return builder.AddConfigurationSource(conigurationName, IniConfiguration.Create(configurationPath, readOnly));
    }
}