using pyRevitDoctor;

namespace pyRevitDoctor.Tests;

/// <summary>
/// Regression coverage for pyrevitlabs/pyRevit#3927: <c>purge-installs</c> silently matched no
/// products because the embedded list is CRLF-encoded and its versions carry build suffixes.
/// </summary>
[Trait("Level", "Unit")]
[Trait("Environment", "HostFree")]
public class ProductCatalogTests {
    private const string BuildStampedProducts =
        "[\r\n" +
        "  {\r\n" +
        "    \"product\": \"pyRevit\",\r\n" +
        "    \"release\": \"7.0.0.26278+2233\",\r\n" +
        "    \"version\": \"7.0.0.26278+2233\",\r\n" +
        "    \"key\": \"f2a3da53-6f34-41d5-abbd-389ffa7f4d5f\"\r\n" +
        "  },\r\n" +
        "  {\r\n" +
        "    \"product\": \"pyRevit CLI MSI\",\r\n" +
        "    \"release\": \"6.4.0.26166+1546-wip\",\r\n" +
        "    \"version\": \"6.4.0.26166+1546-wip\",\r\n" +
        "    \"key\": \"0d5b2f7e-3c1a-4b8e-9f60-2a7d4c9e1b35\"\r\n" +
        "  }\r\n" +
        "]\r\n";

    /// <summary>
    /// Guards against the original regex parser, which loaded nothing from CRLF documents and
    /// could not represent versions such as <c>7.0.0.26278+2233</c>.
    /// </summary>
    [Fact]
    public void CrlfDocumentWithBuildSuffixedVersionsParsesEveryProduct() {
        var products = ProductCatalog.Parse(BuildStampedProducts);

        Assert.Collection(
            products,
            first => {
                Assert.Equal("pyRevit", first.Name);
                Assert.Equal("7.0.0.26278+2233", first.Version);
                Assert.Equal("f2a3da53-6f34-41d5-abbd-389ffa7f4d5f", first.Key);
            },
            second => {
                Assert.Equal("pyRevit CLI MSI", second.Name);
                Assert.Equal("6.4.0.26166+1546-wip", second.Version);
                Assert.Equal("0d5b2f7e-3c1a-4b8e-9f60-2a7d4c9e1b35", second.Key);
            });
    }

    /// <summary>
    /// Guards the contract between the doctor and <c>release/pyrevit-products.json</c>: every record
    /// the build seeds the embedded catalog from must load with a name, version and key.
    /// </summary>
    [Fact]
    public void ShippedProductTemplateParsesEveryRecord() {
        var json = File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "Fixtures", "pyrevit-products.json"));
        var expectedCount = json.Split("\"product\"").Length - 1;

        var products = ProductCatalog.Parse(json);

        Assert.Equal(expectedCount, products.Count);
        Assert.All(products, product => {
            Assert.False(string.IsNullOrWhiteSpace(product.Name));
            Assert.False(string.IsNullOrWhiteSpace(product.Version));
            Assert.False(string.IsNullOrWhiteSpace(product.Key));
        });
    }

    /// <summary>
    /// Guards registry matching: a missing, null or empty key would match unrelated installer
    /// entries by substring, and a null record would crash the purge loop.
    /// </summary>
    [Theory]
    [InlineData("null")]
    [InlineData("[null]")]
    [InlineData("[{\"product\": \"pyRevit\", \"release\": \"1.0\", \"version\": \"1.0\"}]")]
    [InlineData("[{\"product\": \"pyRevit\", \"release\": \"1.0\", \"version\": \"1.0\", \"key\": null}]")]
    [InlineData("[{\"product\": \"pyRevit\", \"release\": \"1.0\", \"version\": \"1.0\", \"key\": \"\"}]")]
    public void CatalogWithoutUsableKeysIsRejected(string productsJson) {
        Assert.Throws<System.Text.Json.JsonException>(() => ProductCatalog.Parse(productsJson));
    }
}
