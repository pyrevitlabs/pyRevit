using Build.Helpers;
using Build.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
public sealed class ProductDataHelperTests
{
    private const string LegacyProductJson =
        """
        [
          {
            "product": "pyRevit",
            "release": "4.8.16.24121+2117",
            "version": "4.8.16.24121+2117",
            "key": "c8a4b720-9699-4a03-bc67-273bab978723"
          },
          {
            "product": "pyRevit CLI",
            "release": "4.8.16.24121+2117",
            "version": "4.8.16.24121+2117",
            "key": "11111111-1111-1111-1111-111111111111"
          }
        ]
        """;

    [TestMethod]
    public void LoadProducts_deserializes_legacy_lowercase_json()
    {
        var path = WriteTempJson(LegacyProductJson);

        var products = ProductDataHelper.LoadProducts(path);

        Assert.HasCount(2, products);
        Assert.AreEqual("pyRevit", products[0].Product);
        Assert.AreEqual("4.8.16.24121+2117", products[0].Release);
        Assert.AreEqual("4.8.16.24121+2117", products[0].Version);
        Assert.AreEqual("c8a4b720-9699-4a03-bc67-273bab978723", products[0].Key);
        Assert.AreEqual("pyRevit CLI", products[1].Product);
    }

    [TestMethod]
    public void LoadProducts_reads_committed_pyrevit_products_json()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "Fixtures", "pyrevit-products.json");
        Assert.IsTrue(File.Exists(path), "Expected fixture copy of release/pyrevit-products.json.");

        var products = ProductDataHelper.LoadProducts(path);

        Assert.IsGreaterThan(0, products.Count);
        Assert.IsTrue(products.All(product => !string.IsNullOrWhiteSpace(product.Product)));
        Assert.IsTrue(products.All(product => !string.IsNullOrWhiteSpace(product.Version)));
        Assert.IsTrue(products.All(product => !string.IsNullOrWhiteSpace(product.Key)));
    }

    [TestMethod]
    public void InsertProduct_inserts_cli_entries_without_null_reference()
    {
        var products = ProductDataHelper.LoadProducts(WriteTempJson(LegacyProductJson));
        var newVersion = "6.4.0.26166+1220";

        ProductDataHelper.InsertProduct(
            products,
            new ProductRecord("pyRevit", newVersion, newVersion, Guid.NewGuid().ToString()),
            cli: false);
        ProductDataHelper.InsertProduct(
            products,
            new ProductRecord("pyRevit CLI", newVersion, newVersion, Guid.NewGuid().ToString()),
            cli: true);

        Assert.AreEqual(newVersion, products[0].Version);
        Assert.AreEqual("pyRevit CLI", products[2].Product);
        Assert.AreEqual(newVersion, products[2].Version);
    }

    [TestMethod]
    public void SaveProducts_round_trips_legacy_json_shape()
    {
        var path = WriteTempJson(LegacyProductJson);
        var products = ProductDataHelper.LoadProducts(path);
        var outputPath = Path.Combine(Path.GetTempPath(), "pyrevit-products-" + Guid.NewGuid().ToString("N") + ".json");

        ProductDataHelper.SaveProducts(outputPath, products);
        var roundTripped = ProductDataHelper.LoadProducts(outputPath);

        Assert.HasCount(products.Count, roundTripped);
        Assert.AreEqual(products[0].Product, roundTripped[0].Product);
        Assert.AreEqual(products[0].Key, roundTripped[0].Key);
        var outputJson = File.ReadAllText(outputPath);
        Assert.Contains("\"product\"", outputJson);
        Assert.Contains("4.8.16.24121+2117", outputJson);
        Assert.DoesNotContain("\\u002B", outputJson);
    }

    [TestMethod]
    public void SaveProducts_writes_plus_sign_literally()
    {
        var products = new List<ProductRecord>
        {
            new("pyRevit", "4.8.9.21359+1855", "4.8.9.21359+1855", "5d419b28-c737-4fd3-9c33-6da59628a443"),
        };
        var outputPath = Path.Combine(Path.GetTempPath(), "pyrevit-products-" + Guid.NewGuid().ToString("N") + ".json");

        ProductDataHelper.SaveProducts(outputPath, products);
        var outputJson = File.ReadAllText(outputPath);

        Assert.Contains("4.8.9.21359+1855", outputJson);
        Assert.DoesNotContain("\\u002B", outputJson);
    }

    [TestMethod]
    public void SeedProductsFromTemplate_copies_template_to_bin_path()
    {
        var templatePath = Path.Combine(AppContext.BaseDirectory, "Fixtures", "pyrevit-products.json");
        var outputDir = Path.Combine(Path.GetTempPath(), "pyrevit-bin-" + Guid.NewGuid().ToString("N"));
        var dataPath = Path.Combine(outputDir, "pyrevit-products.json");

        ProductDataHelper.SeedProductsFromTemplate(templatePath, dataPath);

        Assert.IsTrue(File.Exists(dataPath));
        var products = ProductDataHelper.LoadProducts(dataPath);
        Assert.IsGreaterThan(0, products.Count);
        Assert.IsTrue(products.All(product => !string.IsNullOrWhiteSpace(product.Product)));
    }

    [TestMethod]
    public void SeedProductsFromTemplate_throws_when_template_missing()
    {
        var dataPath = Path.Combine(Path.GetTempPath(), "pyrevit-products-" + Guid.NewGuid().ToString("N") + ".json");
        var missingTemplate = Path.Combine(Path.GetTempPath(), "missing-template-" + Guid.NewGuid().ToString("N") + ".json");

        Assert.ThrowsExactly<FileNotFoundException>(() =>
            ProductDataHelper.SeedProductsFromTemplate(missingTemplate, dataPath));
    }

    [TestMethod]
    public void SeedProductsFromTemplate_skips_when_destination_exists()
    {
        var templatePath = Path.Combine(AppContext.BaseDirectory, "Fixtures", "pyrevit-products.json");
        var dataPath = WriteTempJson(LegacyProductJson);
        var originalJson = File.ReadAllText(dataPath);

        ProductDataHelper.SeedProductsFromTemplate(templatePath, dataPath);

        Assert.AreEqual(originalJson, File.ReadAllText(dataPath));
    }

    private static string WriteTempJson(string json)
    {
        var path = Path.Combine(Path.GetTempPath(), "pyrevit-products-" + Guid.NewGuid().ToString("N") + ".json");
        File.WriteAllText(path, json);
        return path;
    }
}
