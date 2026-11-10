using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace pyRevitDoctor {
    /// <summary>
    /// A pyRevit installer product record from <c>pyrevit-products.json</c>.
    /// </summary>
    /// <remarks>
    /// <see cref="Version"/> is kept as the raw string because build versions carry
    /// suffixes such as <c>+2233</c> or <c>-wip</c> that <see cref="System.Version"/> rejects.
    /// </remarks>
    public sealed class Product {
        [JsonPropertyName("product")]
        public string Name { get; init; }

        [JsonPropertyName("release")]
        public string Release { get; init; }

        [JsonPropertyName("version")]
        public string Version { get; init; }

        [JsonPropertyName("key")]
        public string Key { get; init; }
    }

    /// <summary>
    /// Parses the product list the doctor matches registry entries against.
    /// </summary>
    public static class ProductCatalog {
        static readonly JsonSerializerOptions ProductJsonOptions = new() {
            PropertyNameCaseInsensitive = true,
        };

        /// <summary>
        /// Parses a <c>pyrevit-products.json</c> document.
        /// </summary>
        /// <remarks>
        /// Accepts either line ending style; the build regenerates the file on Windows with CRLF.
        /// </remarks>
        /// <exception cref="JsonException">The document is not a JSON array of product records.</exception>
        public static List<Product> Parse(string productsJson) =>
            JsonSerializer.Deserialize<List<Product>>(productsJson, ProductJsonOptions) ?? new List<Product>();
    }
}
