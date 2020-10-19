"""tooltip."""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
#pylint: disable=missing-class-docstring,missing-function-docstring
#pylint: disable=unused-argument
from pyrevit.framework import List
from pyrevit import revit, DB
from pyrevit import script


output = script.get_output()

depth = 0


def log(msg):
    global depth
    msg = str(msg)

    if msg.startswith("+ "):
        depth += 1
        print("\t"*depth + msg)
        return

    if msg.startswith("- "):
        print("\t"*depth + msg)
        depth -= 1
        return

    print("\t"*depth + "| " + msg)


def log_element(doc, eid):
    el = doc.GetElement(eid)
    log("id={} name={} type={} category={}".format(
        eid.IntegerValue,
        revit.query.get_name(el),
        type(el),
        el.Category.Name if el.Category else "?"
        ))

def log_node(doc, node):
    if isinstance(node, DB.RenderNode):
        log(node.NodeName)

    if isinstance(node, DB.ElementNode):
        log(node.Document)
        log(node.ElementId)

    if isinstance(node, DB.ViewNode):
        log(revit.query.get_name(doc.GetElement(node.ViewId)))
        # log(node.LevelOfDetail)
        # log(node.GetCameraInfo())

    # if isinstance(node, DB.FaceNode):
    #     log(node.GetFace())

    # if isinstance(node, DB.FaceDetailNode):
    #     log(node.LineProperties)
    #     log(node.GetLinkTransform())
    #     log(node.GetInstanceTransform())

    # if isinstance(node, DB.FaceEdgeNode):
    #     log(node.GetFaceEdge())

    # if isinstance(node, DB.FaceSilhouetteNode):
    #     log(node.GetFace())

    # if isinstance(node, DB.GroupNode):
    #     log(node.GetSymbolId())
    #     log(node.GetTransform())

    # if isinstance(node, DB.ContentNode):
    #     log(node.GetAsset())
    #     log(node.GetTransform())

    # if isinstance(node, DB.LinkNode):
    #     log(node.GetDocument())

    # if isinstance(node, DB.MaterialNode):
    #     log(node.Color)
    #     log(node.Glossiness)
    #     log(node.HasOverriddenAppearance)
    #     log(node.MaterialId)
    #     log(node.Smoothness)
    #     log(node.ThumbnailFile)
    #     log(node.Transparency)
    #     log(node.GetAppearance())
    #     log(node.GetAppearanceOverride())

    # if isinstance(node, DB.PolymeshTopology):
    #     log(node.DistributionOfNormals)
    #     log(node.NumberOfFacets)
    #     log(node.NumberOfNormals)
    #     log(node.NumberOfPoints)
    #     log(node.NumberOfUVs)
    #     log(node.GetFacets())
    #     log(node.GetNormals())
    #     log(node.GetPoints())
    #     log(node.GetUVs())


class ExporterWatcher(DB.IExportContext):
    def __init__(self, doc):
        self._doc = doc

    def IsCanceled(self):
        return False

    def Start(self):
        log("+ start")

    def Finish(self):
        log("- finish")

    def OnViewBegin(self, node):
        log("+ view begin")
        log_node(self._doc, node)
        return DB.RenderNodeAction.Proceed

    def OnViewEnd(self, node):
        log("- view end")

    def OnElementBegin(self, eid):
        log("+ element begin")
        log_element(self._doc, eid)
        return DB.RenderNodeAction.Proceed

    def OnElementEnd(self, node):
        log("- element end")

    def OnElementBegin2D(self, node):
        log("+ element 2d begin")
        log_node(self._doc, node)
        return DB.RenderNodeAction.Proceed

    def OnElementEnd2D(self, node):
        log("- element 2d end")

    def OnFaceBegin(self, node):
        log("+ face begin")
        log_node(self._doc, node)
        return DB.RenderNodeAction.Proceed

    def OnFaceEnd(self, node):
        log("- face end")

    def OnFaceEdge2D(self, node):
        log("+ face edge 2d")
        log_node(self._doc, node)
        log("- face edge 2d")
        return DB.RenderNodeAction.Proceed

    def OnFaceSilhouette2D(self, node):
        log("+ face silhouette 2d")
        log_node(self._doc, node)
        log("- face silhouette 2d")
        return DB.RenderNodeAction.Proceed

    def OnInstanceBegin(self, node):
        log("+ instance begin")
        log_node(self._doc, node)
        return DB.RenderNodeAction.Proceed

    def OnInstanceEnd(self, node):
        log("- instance end")

    def OnLinkBegin(self, node):
        log("+ link begin")
        log_node(self._doc, node)
        return DB.RenderNodeAction.Proceed

    def OnLinkEnd(self, node):
        log("- link end")

    def OnLight(self, node):
        log("+ light")
        log_node(self._doc, node)
        log("- light")
        return DB.RenderNodeAction.Proceed

    def OnMaterial(self, node):
        log("+ material")
        log_node(self._doc, node)
        log("- material")
        return DB.RenderNodeAction.Proceed

    def OnPolymesh(self, node):
        log("+ polymesh")
        log_node(self._doc, node)
        log("- polymesh")
        return DB.RenderNodeAction.Proceed

    def OnRPC(self, node):
        log("+ rpc")
        log_node(self._doc, node)
        log("- rpc")
        return DB.RenderNodeAction.Proceed


cExt = DB.CustomExporter(revit.doc, ExporterWatcher(revit.doc))
# export active view
output.freeze()
cExt.Export(revit.active_view)
output.unfreeze()
