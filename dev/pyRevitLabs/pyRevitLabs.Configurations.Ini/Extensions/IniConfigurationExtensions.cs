namespace pyRevitLabs.Configurations.Ini.Extensions;

/// <summary>
/// <see cref="ConfigurationBuilder"/> extensions for registering INI-backed
/// configurations.
/// </summary>
public static class IniConfigurationExtensions
{
    /// <summary>
    /// Registers the INI file at <paramref name="configurationPath"/> under a
    /// name and returns the builder for chaining. The file need not exist yet.
    /// </summary>
    /// <param name="builder">Builder to add the source to.</param>
    /// <param name="configurationPath">Path to the INI file.</param>
    /// <param name="configurationName">
    /// Name to register it under. Use <see cref="ConfigurationService.DefaultConfigurationName"/>
    /// for the base configuration and a Revit version for an override.
    /// </param>
    /// <param name="readOnly">True to discard writes instead of persisting them.</param>
    /// <exception cref="ArgumentNullException"><paramref name="builder"/> is null.</exception>
    /// <exception cref="ArgumentException">A path or name argument is null or whitespace.</exception>
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
