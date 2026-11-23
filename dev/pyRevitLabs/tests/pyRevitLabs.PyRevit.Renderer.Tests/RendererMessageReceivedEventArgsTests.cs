using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace PyRevitLabs.PyRevit.Renderer.Tests {
    /// <summary>
    /// Pins the neutral page-message payload, which keeps renderer consumers
    /// free of WebView2 types.
    /// </summary>
    [TestClass]
    [TestCategory("HostFree")]
    [TestCategory("Unit")]
    public class RendererMessageReceivedEventArgsTests {
        [TestMethod]
        public void PostedString_KeepsBothTheJsonLiteralAndTheText() {
            var args = new RendererMessageReceivedEventArgs("\"hello\"", "hello");

            Assert.AreEqual("\"hello\"", args.Json);
            Assert.AreEqual("hello", args.Text);
        }

        [TestMethod]
        public void PostedObject_HasJsonAndNoText() {
            var args = new RendererMessageReceivedEventArgs("{\"id\":1}", null);

            Assert.AreEqual("{\"id\":1}", args.Json);
            Assert.IsNull(args.Text);
        }
    }
}
