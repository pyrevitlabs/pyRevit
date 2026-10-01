using System;
using System.Collections.Generic;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Events;
using pyRevitLabs.Json.Linq;

namespace Autodesk.Revit.DB {
    internal enum TransactionStatus { Uninitialized, Started, RolledBack, Committed }
    internal enum FailureSeverity { Warning, Error }
    internal enum FailureProcessingResult { Continue, ProceedWithRollBack }
    internal sealed class ElementId { }
    internal sealed class Category { public string Name { get; set; } }
    internal sealed class Element {
        public Category Category { get; set; }
        public string Name { get; set; }
    }
    internal sealed class Document {
        public string Title { get; set; } = "Test document";
        public string PathName { get; set; } = "";
        public bool IsValidObject { get; set; } = true;
        public bool IsLinked { get; set; }
        public bool IsReadOnly { get; set; }
        public bool IsModifiable { get; set; }
        public bool IsModified { get; set; }
        public bool HasView { get; set; }
        public bool CloseSucceeds { get; set; } = true;
        public bool ThrowOnRollback { get; set; }
        public bool ThrowOnDispose { get; set; }
        public TransactionStatus RollbackStatus { get; set; } = TransactionStatus.RolledBack;
        public TransactionStatus StartStatus { get; set; } = TransactionStatus.Started;
        public int RollbackCalls { get; set; }
        public bool Close(bool save) {
            if (save)
                throw new InvalidOperationException("Cleanup must never save.");
            if (CloseSucceeds)
                IsValidObject = false;
            return CloseSucceeds;
        }
        public Element GetElement(ElementId id) => new Element();
    }
    internal sealed class TransactionGroup : IDisposable {
        private readonly Document document;
        private TransactionStatus status;
        public TransactionGroup(Document document, string name) { this.document = document; }
        public TransactionStatus Start() => status = document.StartStatus;
        public bool HasStarted() => status != TransactionStatus.Uninitialized;
        public bool HasEnded() => status == TransactionStatus.RolledBack || status == TransactionStatus.Committed;
        public TransactionStatus RollBack() {
            document.RollbackCalls++;
            if (document.ThrowOnRollback)
                throw new InvalidOperationException("Rollback failed.");
            return status = document.RollbackStatus;
        }
        public void Assimilate() { status = TransactionStatus.Committed; }
        public void Dispose() {
            if (document.ThrowOnDispose)
                throw new InvalidOperationException("Dispose failed.");
        }
    }
    internal sealed class FailureMessage {
        public FailureSeverity GetSeverity() => FailureSeverity.Error;
        public string GetDescriptionText() => "Failure";
        public IEnumerable<ElementId> GetFailingElementIds() => new ElementId[0];
    }
    internal sealed class FailuresAccessor {
        public Document GetDocument() => null;
        public IEnumerable<FailureMessage> GetFailureMessages() => new FailureMessage[0];
        public string GetTransactionName() => "Test transaction";
        public void DeleteWarning(FailureMessage message) { }
    }
}
namespace Autodesk.Revit.DB.Events {
    internal class RevitAPIPreEventArgs : EventArgs {
        public bool Cancellable { get; set; } = true;
        public bool Cancelled { get; private set; }
        public void Cancel() { Cancelled = true; }
    }
    internal class DocumentEventArgs : RevitAPIPreEventArgs { public Document Document { get; set; } }
    internal sealed class DocumentSavingEventArgs : DocumentEventArgs { }
    internal sealed class DocumentSavingAsEventArgs : DocumentEventArgs { }
    internal sealed class DocumentClosingEventArgs : DocumentEventArgs { }
    internal sealed class DocumentSynchronizingWithCentralEventArgs : DocumentEventArgs { }
    internal sealed class DocumentCreatedEventArgs : DocumentEventArgs { }
    internal sealed class DocumentOpenedEventArgs : DocumentEventArgs { }
    internal sealed class FileExportingEventArgs : RevitAPIPreEventArgs { }
    internal sealed class ViewExportingEventArgs : RevitAPIPreEventArgs { }
    internal sealed class DocumentChangedEventArgs : EventArgs {
        public Document Document { get; set; }
        public IEnumerable<ElementId> Added { get; set; } = new[] { new ElementId() };
        public IEnumerable<ElementId> Deleted { get; set; } = new ElementId[0];
        public IEnumerable<ElementId> Modified { get; set; } = new ElementId[0];
        public Document GetDocument() => Document;
        public IEnumerable<ElementId> GetAddedElementIds() => Added;
        public IEnumerable<ElementId> GetDeletedElementIds() => Deleted;
        public IEnumerable<ElementId> GetModifiedElementIds() => Modified;
        public IEnumerable<string> GetTransactionNames() => new[] { "Test transaction" };
    }
    internal sealed class FailuresProcessingEventArgs : EventArgs {
        public FailuresAccessor GetFailuresAccessor() => new FailuresAccessor();
        public void SetProcessingResult(FailureProcessingResult result) { }
    }
}
namespace Autodesk.Revit.ApplicationServices {
    internal sealed class Application {
        public List<Document> Documents { get; } = new List<Document>();
        public event EventHandler<DocumentChangedEventArgs> DocumentChanged;
        public event EventHandler<FailuresProcessingEventArgs> FailuresProcessing;
        public event EventHandler<DocumentSavingEventArgs> DocumentSaving;
        public event EventHandler<DocumentSavingAsEventArgs> DocumentSavingAs;
        public event EventHandler<FileExportingEventArgs> FileExporting;
        public event EventHandler<ViewExportingEventArgs> ViewExporting;
        public event EventHandler<DocumentCreatedEventArgs> DocumentCreated;
        public event EventHandler<DocumentOpenedEventArgs> DocumentOpened;
        public event EventHandler<DocumentClosingEventArgs> DocumentClosing;
        public event EventHandler<DocumentSynchronizingWithCentralEventArgs> DocumentSynchronizingWithCentral;
        public void Open(Document document) {
            Documents.Add(document);
            DocumentOpened?.Invoke(this, new DocumentOpenedEventArgs { Document = document });
        }
        public void Create(Document document) {
            Documents.Add(document);
            DocumentCreated?.Invoke(this, new DocumentCreatedEventArgs { Document = document });
        }
        public void Change(
            Document document,
            IEnumerable<ElementId> added = null,
            IEnumerable<ElementId> deleted = null,
            IEnumerable<ElementId> modified = null) {
            DocumentChanged?.Invoke(this, new DocumentChangedEventArgs {
                Document = document,
                Added = added ?? new[] { new ElementId() },
                Deleted = deleted ?? new ElementId[0],
                Modified = modified ?? new ElementId[0],
            });
        }
        public bool Save(Document document) {
            var args = new DocumentSavingEventArgs { Document = document };
            DocumentSaving?.Invoke(this, args);
            return !args.Cancelled;
        }
        public bool SaveAs(Document document) {
            var args = new DocumentSavingAsEventArgs { Document = document };
            DocumentSavingAs?.Invoke(this, args);
            return !args.Cancelled;
        }
        public bool ExportFile() {
            var args = new FileExportingEventArgs();
            FileExporting?.Invoke(this, args);
            return !args.Cancelled;
        }
        public bool ExportView() {
            var args = new ViewExportingEventArgs();
            ViewExporting?.Invoke(this, args);
            return !args.Cancelled;
        }
        public bool Synchronize(Document document) {
            var args = new DocumentSynchronizingWithCentralEventArgs { Document = document };
            DocumentSynchronizingWithCentral?.Invoke(this, args);
            return !args.Cancelled;
        }
    }
}
namespace Autodesk.Revit.UI {
    internal sealed class UIApplication {
        public Autodesk.Revit.ApplicationServices.Application Application { get; } = new Autodesk.Revit.ApplicationServices.Application();
        public UIDocument ActiveUIDocument { get; set; }
    }
    internal sealed class UIDocument {
        public UIDocument(Document document) { Document = document; }
        public Document Document { get; }
        public List<int> GetOpenUIViews() => Document.HasView ? new List<int> { 1 } : new List<int>();
    }
}
namespace PyRevitLabs.PyRevit.Runtime.Agent {
    internal sealed class AgentDialogCapture {
        public AgentDialogCapture(Autodesk.Revit.UI.UIApplication app) { }
        public JArray Dialogs { get; } = new JArray();
        public void Disarm() { }
    }
    internal static class AgentIds {
        public static long ToValue(ElementId id) => 1;
    }
}
