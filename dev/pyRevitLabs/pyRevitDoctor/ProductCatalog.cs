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
        /// Invariant: every returned product has a non-empty <see cref="Product.Key"/>. Registry matching
        /// relies on it, and an empty key would match unrelated installer entries by substring.
        /// </remarks>
        /// <exception cref="JsonException">
        /// The document is not a non-empty JSON array of product records, or a record is <c>null</c> or
        /// has no key.
        /// </exception>
        public static List<Product> Parse(string productsJson) {
            var products = JsonSerializer.Deserialize<List<Product>>(productsJson, ProductJsonOptions)
                ?? throw new JsonException("The product catalog must be a JSON array.");
            if (products.Count == 0)
                throw new JsonException("The product catalog is empty.");
            if (products.Exists(product => product == null || string.IsNullOrWhiteSpace(product.Key)))
                throw new JsonException("The product catalog contains a null record or a record without a key.");
            return products;
        }
    }
}
