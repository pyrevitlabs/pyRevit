namespace pyRevitLabs.Configurations.Ini.Extensions;

/// <summary>
/// <see cref="ConfigurationBuilder"/> extensions for registering INI-backed
/// configurations.
/// </summary>
public static class IniConfigurationExtensions
{
    /// <summary>
    /// Registers the INI file at <paramref name="configurationPath"/> and returns
    /// the builder for chaining. The file need not exist yet.
    /// </summary>
    /// <param name="builder">Builder to add the source to.</param>
    /// <param name="configurationPath">Path to the INI file.</param>
    /// <param name="readOnly">True to discard writes instead of persisting them.</param>
    /// <exception cref="ArgumentNullException"><paramref name="builder"/> is null.</exception>
    /// <exception cref="ArgumentException"><paramref name="configurationPath"/> is null or whitespace.</exception>
    public static ConfigurationBuilder AddIniConfiguration(
        this ConfigurationBuilder builder, string configurationPath, bool readOnly = default)
    {
        if (builder == null)
            throw new ArgumentNullException(nameof(builder));

        if (string.IsNullOrWhiteSpace(configurationPath))
            throw new ArgumentException("Value cannot be null or whitespace.", nameof(configurationPath));

        return builder.AddConfigurationSource(IniConfiguration.Create(configurationPath, readOnly));
    }
}
