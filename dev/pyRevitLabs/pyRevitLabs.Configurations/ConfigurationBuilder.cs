using pyRevitLabs.Configurations.Abstractions;

namespace pyRevitLabs.Configurations;

/// <summary>
/// Assembles an <see cref="IConfigurationService"/> over a single configuration
/// source.
/// </summary>
public sealed class ConfigurationBuilder
{
    private readonly bool _readOnly;
    private IConfiguration? _configuration;

    /// <summary>
    /// Starts a new builder.
    /// </summary>
    /// <param name="readOnly">
    /// True to make the built service refuse every write, regardless of whether
    /// the configuration is itself writable.
    /// </param>
    public ConfigurationBuilder(bool readOnly)
    {
        _readOnly = readOnly;
    }

    /// <summary>
    /// Registers the configuration to serve and returns this builder for
    /// chaining.
    /// </summary>
    /// <exception cref="ArgumentNullException"><paramref name="configuration"/> is null.</exception>
    /// <exception cref="InvalidOperationException">A configuration is already registered.</exception>
    public ConfigurationBuilder AddConfigurationSource(IConfiguration configuration)
    {
        if (configuration == null)
            throw new ArgumentNullException(nameof(configuration));

        if (_configuration is not null)
            throw new InvalidOperationException("A configuration source is already registered.");

        _configuration = configuration;

        return this;
    }

    /// <summary>
    /// Creates the service over the registered configuration.
    /// </summary>
    /// <exception cref="InvalidOperationException">No configuration was registered.</exception>
    public IConfigurationService Build()
    {
        if (_configuration is null)
            throw new InvalidOperationException(
                "No configuration source was registered; call AddConfigurationSource before Build.");

        return ConfigurationService.Create(_readOnly, _configuration);
    }
}
