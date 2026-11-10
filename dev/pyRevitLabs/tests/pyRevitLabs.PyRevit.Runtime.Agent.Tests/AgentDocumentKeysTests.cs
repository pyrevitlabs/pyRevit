using Autodesk.Revit.DB;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    public sealed class AgentDocumentKeysTests {
        private readonly AgentDocumentKeys keys = new AgentDocumentKeys();

        [Fact]
        public void AnOpenDocumentKeepsItsKey() {
            var document = new Document();

            var key = keys.KeyOf(document);

            Assert.Equal(key, keys.KeyOf(document));
            Assert.Same(document, keys.Find(key));
        }

        [Fact]
        public void DocumentsWithTheSameTitleGetDifferentKeys() {
            var first = new Document { Title = "Model" };
            var second = new Document { Title = "Model" };

            Assert.NotEqual(keys.KeyOf(first), keys.KeyOf(second));
        }

        [Fact]
        public void AClosedDocumentsKeyNamesNothingAndIsNeverGivenAgain() {
            var closed = new Document { PathName = "C:\\models\\tower.rvt" };
            var key = keys.KeyOf(closed);
            closed.Close(false);

            var reopened = new Document { PathName = "C:\\models\\tower.rvt" };

            Assert.Null(keys.Find(key));
            Assert.NotEqual(key, keys.KeyOf(reopened));
        }

        [Fact]
        public void AKeyNoDocumentWasGivenNamesNothing() {
            keys.KeyOf(new Document());

            Assert.Null(keys.Find("doc-99"));
            Assert.Null(keys.Find(""));
            Assert.Null(keys.Find(null));
        }
    }
}
