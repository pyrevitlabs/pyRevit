using Autodesk.Revit.DB;
using PyRevitLabs.PyRevit.Runtime.Agent;

namespace PyRevitLabs.PyRevit.Runtime.Agent.Tests {
    [Trait("Environment", "HostFree")]
    [Trait("Level", "Unit")]
    public sealed class AgentCommitSentinelTests {
        [Fact]
        public void UnsavedDocumentsWithTheSameTitleKeepTheirOwnCommits() {
            var first = new Document { Title = "Project1" };
            var second = new Document { Title = "Project1" };
            var lost = new ElementId();
            AgentCommitSentinel.Remember(first, "run-first", "First", new[] { lost });
            AgentCommitSentinel.Remember(second, "run-second", "Second", new[] { new ElementId() });
            first.Deleted.Add(lost);

            Assert.Null(AgentCommitSentinel.Check(second, afterRollback: false));
            Assert.Contains("run-first", AgentCommitSentinel.Check(first, afterRollback: false));
            Assert.Null(AgentCommitSentinel.Check(first, afterRollback: false));
        }

        [Fact]
        public void ACommitToAnotherDocumentDoesNotReplaceTheSample() {
            var project = new Document { PathName = @"C:\a.rvt" };
            var family = new Document { PathName = @"C:\b.rfa" };
            var lost = new ElementId();
            AgentCommitSentinel.Remember(project, "run-project", "Project", new[] { lost });
            AgentCommitSentinel.Remember(family, "run-family", "Family", new[] { new ElementId() });
            project.Deleted.Add(lost);

            Assert.Contains("run-project", AgentCommitSentinel.Check(project, afterRollback: true));
        }

        [Fact]
        public void ClosedDocumentsAreForgotten() {
            var closed = new Document();
            var lost = new ElementId();
            AgentCommitSentinel.Remember(closed, "run-closed", "Closed", new[] { lost });
            closed.Deleted.Add(lost);
            closed.IsValidObject = false;

            Assert.Null(AgentCommitSentinel.Check(new Document(), afterRollback: false));
            closed.IsValidObject = true;
            Assert.Null(AgentCommitSentinel.Check(closed, afterRollback: false));
        }
    }
}
