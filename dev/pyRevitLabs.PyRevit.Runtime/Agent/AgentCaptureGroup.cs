using System;

using Autodesk.Revit.DB;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Runs a capture in a transaction group that is always rolled back, so nothing it changes
    /// stays in the model.
    /// </summary>
    internal static class AgentCaptureGroup {
        /// <summary>
        /// Changes the model with <paramref name="prepare"/> in one transaction, exports what it
        /// returns with <paramref name="export"/>, and rolls the whole group back.
        /// </summary>
        /// <remarks>
        /// Throws <c>capture_failed</c> unless the group starts and the transaction commits; when the
        /// group did not start, no transaction is opened. A Revit
        /// <see cref="Autodesk.Revit.Exceptions.ApplicationException"/> becomes <c>capture_failed</c>
        /// with the text <paramref name="describeFailure"/> builds from its message; an
        /// <see cref="AgentException"/> from <paramref name="prepare"/> passes through.
        /// Invariant: once the group started, it is rolled back on every exit path.
        /// </remarks>
        internal static string Run<TTarget>(Document doc, string transactionName, Func<TTarget> prepare,
            Func<TTarget, string> export, Func<string, string> describeFailure) {
            using (var group = new TransactionGroup(doc, "pyRevit Agent capture")) {
                if (group.Start() != TransactionStatus.Started)
                    throw new AgentException("capture_failed", "Revit did not start the temporary capture group, so the view was not changed.");
                try {
                    TTarget target;
                    using (var transaction = new Transaction(doc, transactionName)) {
                        transaction.Start();
                        target = prepare();
                        var committed = transaction.Commit();
                        if (committed != TransactionStatus.Committed)
                            throw new AgentException("capture_failed", describeFailure($"Revit did not commit the temporary view change (status {committed})."));
                    }
                    return export(target);
                }
                catch (Autodesk.Revit.Exceptions.ApplicationException ex) {
                    throw new AgentException("capture_failed", describeFailure(ex.Message));
                }
                finally {
                    if (group.HasStarted() && !group.HasEnded())
                        group.RollBack();
                }
            }
        }
    }
}
