import sys
import clr
clr.AddReference('ProtoGeometry')
from Autodesk.DesignScript.Geometry import *

from random import randint

import os.path

import inspect

import unicodedata 

clr.AddReference("RevitServices")
import RevitServices
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager
from System.Collections.Generic import*

clr.AddReference("RevitAPIUI")
import Autodesk 
from Autodesk.Revit.UI import TaskDialog, IExternalEventHandler, ExternalEvent

clr.AddReference('RevitAPI')
import Autodesk
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB import BuiltInCategory

clr.AddReference('System.Drawing')
clr.AddReference('System.Windows.Forms')
import System.Drawing
import System.Windows.Forms

from System.Drawing import *
from System.Reflection import Assembly
from System.Windows.Forms import *

clr.AddReference('System.Data')
from System.Data import *

from System import Array
from System.Collections.Generic import *

class subscribeView(IExternalEventHandler):
	def __init__(self):
		self.registered = 1

	def Execute(self, uiapp):
		try:
			if self.registered == 1:
				self.registered = 0
				uiapp.ViewActivated += self.viewChanged
			else:
				self.registered = 1
				uiapp.ViewActivated -= self.viewChanged
		except Exception as e:
			pass
			
	def viewChanged(self, sender, e):
		if wndw.IsOpen == 1:
			if self.registered == 0:
				new_doc = e.Document
				if new_doc:
					new_uiapp = new_doc.Application
					if wndw:
						if not new_doc.Equals(doc):
							wndw.Close()
				#Update categories in dropdown
				new_view = getActiveView(e.Document)
				if new_view != 0:
					#Unsubcribe
					wndw._listBox2.SelectedIndexChanged -= wndw.lstselectedIndexChanged
					#Update categories for new view
					wndw.crt_view = new_view
					categ_inf_used_up = getCategoriesAndParametersInUsed(cat_excluded, wndw.crt_view)
					wndw._tableData = DataTable("Data")
					wndw._tableData.Columns.Add("Key", System.String)
					wndw._tableData.Columns.Add("Value", System.Object)
					names = [x._name for x in categ_inf_used_up]
					wndw._tableData.Rows.Add("Select a Category Here!", 0)
					[wndw._tableData.Rows.Add(key_, value_ ) for key_, value_ in zip(names, categ_inf_used_up)]
					wndw._categories.DataSource = wndw._tableData 
					wndw._categories.DisplayMember = "Key"
					#Vaciar range of values
					wndw._tableData3 = DataTable("Data")
					wndw._tableData3.Columns.Add("Key", System.String)
					wndw._tableData3.Columns.Add("Value", System.Object)
					wndw._listBox2.DataSource = wndw._tableData3
					wndw._listBox2.DisplayMember = "Key"
			
	def GetName(self):
		return "Subscribe View Changed Event"

class applyColors(IExternalEventHandler):
	def __init__(self):
		pass
		
	def Execute(self, uiapp):
		try:
			new_doc = uiapp.ActiveUIDocument.Document
			view = getActiveView(new_doc)
			if view != 0:
				solidFillId = None
				fElementCollector = FilteredElementCollector(new_doc).OfClass(FillPatternElement)
				for pat in fElementCollector:
					if pat.GetFillPattern().IsSolidFill:
						solidFillId = pat.Id
						break
				t = Transaction(new_doc, "Apply colors to elements")
				t.Start()
				sel_cat = wndw._categories.SelectedItem['Value']
				if sel_cat._cat.Id.IntegerValue == int(BuiltInCategory.OST_Rooms) or sel_cat._cat.Id.IntegerValue == int(BuiltInCategory.OST_MEPSpaces) or sel_cat._cat.Id.IntegerValue == int(BuiltInCategory.OST_Areas):
					#In case of rooms, spaces and areas. Check Color scheme is applied and if not
					if version > 2021:
						if str(wndw.crt_view.GetColorFillSchemeId(sel_cat._cat.Id)) == "-1":
							fColorScheme = FilteredElementCollector(new_doc).OfClass(ColorFillScheme).ToElements()
							if len(fColorScheme) > 0:
								for sch in fColorScheme:
									if sch.CategoryId.IntegerValue == sel_cat._cat.Id.IntegerValue:
										if len(sch.GetEntries()) > 0:
											wndw.crt_view.SetColorFillSchemeId(sel_cat._cat.Id, sch.Id)
											break
					else:
						wndw._txtBlock5.Visible = True
				else:
					wndw._txtBlock5.Visible = False
					
				for indx in range(wndw._listBox2.Items.Count):
					ogs = OverrideGraphicSettings().Dispose()
					ogs = OverrideGraphicSettings()
					color = Autodesk.Revit.DB.Color(wndw._listBox2.Items[indx]['Value']._n1, wndw._listBox2.Items[indx]['Value']._n2, wndw._listBox2.Items[indx]['Value']._n3)
					ogs.SetProjectionLineColor(color)
					ogs.SetSurfaceForegroundPatternColor(color);
					ogs.SetCutForegroundPatternColor(color);
					if solidFillId != None:
						ogs.SetSurfaceForegroundPatternId(solidFillId);
						ogs.SetCutForegroundPatternId(solidFillId)
					ogs.SetProjectionLinePatternId(ElementId(-1));
					for id in wndw._listBox2.Items[indx]['Value']._eleId:
						view.SetElementOverrides(id, ogs)
				t.Commit()
		except Exception as e:
			pass
			
	def GetName(self):
		return "Apply colors to elements"
		
class resetColors(IExternalEventHandler):
	def __init__(self):
		pass
		
	def Execute(self, uiapp):
		try:
			new_doc = uiapp.ActiveUIDocument.Document
			view = getActiveView(new_doc)
			if view != 0:
				ogs = OverrideGraphicSettings().Dispose()
				ogs = OverrideGraphicSettings()
				collector = FilteredElementCollector(new_doc, view.Id).WhereElementIsNotElementType().WhereElementIsViewIndependent().ToElements()
				t = Transaction(new_doc, "Reset colors in elements")
				t.Start()
				for ele in collector:
					view.SetElementOverrides(ele.Id, ogs)
				t.Commit()
		except Exception as e:
			pass
			
	def GetName(self):
		return "Reset colors in elements"

class createLegend(IExternalEventHandler):
	def __init__(self):
		pass
		
	def Execute(self, uiapp):
		try:
			new_doc = uiapp.ActiveUIDocument.Document
			#Get legend view
			collector = FilteredElementCollector(new_doc).OfClass(Autodesk.Revit.DB.View).ToElements()
			legends=[]
			for vw in collector:
				if vw.ViewType == ViewType.Legend:
					legends.Add(vw)
					break
			if len(legends)>0:
				#Duplicate existing legend
				t = Transaction(new_doc, "Create Legend")
				t.Start()
				trans = SubTransaction(new_doc)
				trans.Start()
				new_id_legend = legends[0].Duplicate(ViewDuplicateOption.Duplicate)
				newLegend = new_doc.GetElement(new_id_legend)
				i=1
				while True:
					try:
						newLegend.Name = unicode("Color Legend " + str(i))
						break
					except:
						i+=1
						if i == 1000:
							break
				trans.Commit()
				old_all_ele = FilteredElementCollector(new_doc, legends[0].Id).ToElements()
				ele_id_type = ElementId(0)
				for ele in old_all_ele:
					if ele.Id.IntegerValue != newLegend.Id.IntegerValue and ele.Category != None:
						if isinstance(ele, TextNote):
							ele_id_type = ele.GetTypeId()
							break
				if ele_id_type.IntegerValue == 0:
             		#Get any text in model
					all_text_notes = FilteredElementCollector(new_doc).OfClass(TextNoteType).ToElements()
					for ele in all_text_notes:
						ele_id_type = ele.Id
						break                  
				sel_cat = wndw._categories.SelectedItem['Value']
				sel_par = wndw._listBox1.SelectedItem['Value']
				list_max_X = []
				list_y = []
				#FilledRegionType
				filled_type=[]
				all_types = FilteredElementCollector(new_doc).OfClass(FilledRegionType).ToElements()
				for ty in all_types:
					pattern = new_doc.GetElement(ty.ForegroundPatternId)
					if pattern != None:
						if pattern.GetFillPattern().IsSolidFill:
							if ty.ForegroundPatternColor.IsValid:
								filled_type.Add(ty)
								break
				#Create Type if none is fill
				if len(filled_type) == 0 and len(all_types) > 0:
					it = 1
					#Duplicate existing fillregiontype
					while True:
						try:
							new_type = all_types[0].Duplicate("Fill Region " + str(it))
							break
						except:
							it +=1
							if it == 100:
								break
					#Create pattern		
					it = 1
					while True:
						try:
							new_pattern = FillPattern("Fill Pattern " + str(it), FillPatternTarget.Drafting, FillPatternHostOrientation.ToView, float(0), float(0.00001))
							new_elePat = FillPatternElement.Create(new_doc, new_pattern)
							break
						except:
							it +=1
							if it == 100:
								break
					#Assign to type
					new_type.ForegroundPatternId = new_elePat.Id
					filled_type.Add(new_type)
				#Create Text
				for vw_item in wndw._listBox2.Items:
					punto = XYZ(0,0,0)
					index = wndw._listBox2.Items.IndexOf(vw_item)
					if index !=0:
						punto = XYZ(0,fin_coord_y,0)
					item = vw_item['Value']
					text_line = sel_cat._name + " - " + sel_par._name + ":" + item._value
					new_text = TextNote.Create(new_doc, newLegend.Id, punto, text_line, ele_id_type)
					new_doc.Regenerate()
					prev_bbox = new_text.get_BoundingBox(newLegend)
					offset = (prev_bbox.Max.Y - prev_bbox.Min.Y)*0.25
					fin_coord_y = prev_bbox.Min.Y - offset
					list_max_X.Add(prev_bbox.Max.X)
					list_y.Add(fin_coord_y + offset)
					height = prev_bbox.Max.Y - prev_bbox.Min.Y
				ini_x = max(list_max_X)
				ogs = OverrideGraphicSettings()
				#Create filled color region
				for indx in range(len(list_y)):
					coord_y = list_y[indx]
					item = wndw._listBox2.Items[indx]['Value']
					point0 = XYZ(ini_x, coord_y, 0)
					point1 = XYZ(ini_x, coord_y + height, 0)
					point2 = XYZ(ini_x *1.5, coord_y + height, 0)
					point3 = XYZ(ini_x *1.5, coord_y, 0)
					line01 = Line.CreateBound(point0,point1)
					line12= Line.CreateBound(point1,point2)
					line23 = Line.CreateBound(point2,point3)
					line30 = Line.CreateBound(point3,point0)
					list_curveLoops = List[CurveLoop]()
					curveLoops = CurveLoop()
					curveLoops.Append(line01)
					curveLoops.Append(line12)
					curveLoops.Append(line23)
					curveLoops.Append(line30)
					list_curveLoops.Add(curveLoops)
					reg = FilledRegion.Create(new_doc, filled_type[0].Id, newLegend.Id, list_curveLoops)
					#Assign color filled region					
					color = Autodesk.Revit.DB.Color(item._n1, item._n2, item._n3)
					ogs.SetProjectionLineColor(color)
					ogs.SetSurfaceForegroundPatternColor(color);
					ogs.SetCutForegroundPatternColor(color);
					ogs.SetProjectionLinePatternId(ElementId(-1));
					newLegend.SetElementOverrides(reg.Id, ogs)
				t.Commit()
			else:
				task2 = TaskDialog("Color Elements by Parameter")
				task2.MainInstruction = "In order to create a new legend, you need to have at least one. Please, create a legend view."
				wndw.TopMost = False
				task2.Show()
				wndw.TopMost = True
		except Exception as e:
			pass
	def GetName(self):
		return "Create Legend"

class values_info():
	def __init__(self, para, val, id, n1, n2, n3):
		self._par = para
		self._value = val
		self._name = strip_accents(para.Definition.Name)
		self._eleId = List[ElementId]()
		self._eleId.Add(id)
		self._n1 = n1
		self._n2 = n2
		self._n3 = n3
		self._colour = Color.FromArgb(self._n1, self._n2, self._n3)

class para_info():
	def __init__(self, type, para):
		self._type = type
		self._rl_par = para
		self._par = para.Definition
		self._name = strip_accents(para.Definition.Name)

class categ_info():
	def __init__(self, cat, param):
		self._name = strip_accents(cat.Name)
		self._cat = cat
		self._intId = cat.Id.IntegerValue
		self._par = param

def getActiveView(ac_doc):
	sel_View = ac_doc.ActiveView
	if sel_View.ViewType == ViewType.ProjectBrowser or sel_View.ViewType == ViewType.SystemBrowser:
		sel_View = ac_doc.GetElement(uidoc.GetOpenUIViews()[0].ViewId)
	if not sel_View.CanUseTemporaryVisibilityModes():
		task2 = TaskDialog("Color Elements by Parameter")
		task2.MainInstruction = "Visibility settings cannot be modified in " + str(sel_View.ViewType) + " views. Please, change your current view."
		try:
			wndw.TopMost = False
		except:
			pass
		task2.Show()
  		try:
			wndw.TopMost = True
		except:
			pass
		return 0
	else:
		return sel_View

def getValuePar(para):
	value = ""
	if para.StorageType == StorageType.Double:
		value = para.AsValueString()
	elif para.StorageType == StorageType.ElementId:
		id_val = para.AsElementId()
		if id_val.IntegerValue >= 0:
			value = Element.Name.__get__(doc.GetElement(id_val))
		else:
			value ="None"
	elif para.StorageType == StorageType.Integer:
		if version > 2021:
			type = para.Definition.GetDataType()
			if SpecTypeId.Boolean.YesNo == type:
				if para.AsInteger()==1:
					value = "True"
				else:
					value = "False"
			else:
				value = para.AsValueString()
		else:
			type = para.Definition.ParameterType
			if ParameterType.YesNo == type:
				if para.AsInteger()==1:
					value = "True"
				else:
					value = "False"
			else:
				value = para.AsValueString()
	elif para.StorageType == StorageType.String:
		value = para.AsString()
	else:
		value = "N/A"
	return value

def strip_accents(text):
	return ''.join(char for char in unicodedata.normalize('NFKD', text) if unicodedata.category(char) != 'Mn')

def randomColor():
	r = randint(0, 230)
	g = randint(0, 230)
	b = randint(0, 230)
	return r,g,b

def getRangeOfValues(category, param, new_view):
	for sample_bic in System.Enum.GetValues(BuiltInCategory):
		if category._intId == int(sample_bic):
			bic = sample_bic
			break
	collector = FilteredElementCollector(doc, new_view.Id).OfCategory(bic).WhereElementIsNotElementType().WhereElementIsViewIndependent().ToElements()
	list_values=[]
	#Iterar todos los elementos y conseguir valores unicos
	for ele in collector:
		ele_par = ele
		if param._type == 1:
			ele_par = doc.GetElement(ele.GetTypeId())
		for pr in ele_par.Parameters:
			if pr.Definition.Name == param._par.Name:
				valor = getValuePar(pr)
				if valor == "" or valor == None:
					valor = "N/A"
				match = [x for x in list_values if x._value == valor]
				if len(match) > 0:
					match[0]._eleId.Add(ele.Id)
				else:
					while True:
						r,g,b=randomColor()
						match = [x for x in list_values if x._n1 == r and x._n2 == g and x._n3 == b]
						if len(match) == 0:
							val = values_info(pr, valor, ele.Id, r, g, b)
							list_values.Add(val)
							break
				break
	copy = [x for x in list_values if x._value == "N/A"]
	if len(copy) > 0:
		list_values.Remove(copy[0])	
	#Ordenar
	list_values.sort(key=lambda x: x._value, reverse=False)
	if len(list_values) > 1:
		try:
			first_value = list_values[0]._value
			indx_del = getIndexUnits(first_value)
			if indx_del ==0:
				list_values = sorted(list_values, key=lambda x: float(x._value))
			elif indx_del<len(first_value) and indx_del !=-1:
				list_values = sorted(list_values, key=lambda x: float(x._value[:-indx_del]))
		except Exception as e:
			pass
	if len(copy) > 0 and len(copy[0]._eleId) > 0:
		list_values.Add(copy[0])
	return list_values


def getCategoriesAndParametersInUsed(cat_exc, acti_view):
	#Get All elements and filter unneeded
	collector = FilteredElementCollector(doc, acti_view.Id).WhereElementIsNotElementType().WhereElementIsViewIndependent().ToElements()
	list_cat = []
	for ele in collector:
		if ele.Category != None:
			current_int_cat_id = ele.Category.Id.IntegerValue
			if not current_int_cat_id in cat_exc:
				if not any(x._intId == current_int_cat_id for x in list_cat):
					list_parameters=[]
					#Instance parameters
					for par in ele.Parameters:
						if par.Definition.BuiltInParameter != BuiltInParameter.ELEM_CATEGORY_PARAM and par.Definition.BuiltInParameter != BuiltInParameter.ELEM_CATEGORY_PARAM_MT:
							list_parameters.Add(para_info(0, par))
					typ = ele.Document.GetElement(ele.GetTypeId())
					#Type parameters
					if typ != None:
						for par in typ.Parameters:
							if par.Definition.BuiltInParameter != BuiltInParameter.ELEM_CATEGORY_PARAM and par.Definition.BuiltInParameter != BuiltInParameter.ELEM_CATEGORY_PARAM_MT:
								list_parameters.Add(para_info(1, par))
					#Sort and add
					list_parameters.sort(key=lambda x: x._name.upper(), reverse=False)
					list_cat.Add(categ_info(ele.Category,list_parameters))
	list_cat.sort(key=lambda x: x._name, reverse=False)
	return list_cat
					
class Form_cats(Form):
	def __init__(self, categories, ext_ev, uns_ev, s_view, reset_event, ev_legend):
		self.IsOpen = 1
		self.legend_ev = ev_legend
		self.reset_ev = reset_event
		self.crt_view = s_view
		self.event = ext_ev
		self.uns_event = uns_ev
		self.uns_event.Raise()
		self.categs = categories
		list_par = []
		list_values = []
		self.width_par = 1
		self._tableData = DataTable("Data")
		self._tableData.Columns.Add("Key", System.String)
		self._tableData.Columns.Add("Value", System.Object)
		names = [x._name for x in self.categs]
		self._tableData.Rows.Add("Select a Category Here!", 0 )
		[self._tableData.Rows.Add(key_, value_ ) for key_, value_ in zip(names, self.categs)]
		self.out = []
		self.InitializeComponent()
	
	def InitializeComponent(self):
		self._categories = System.Windows.Forms.ComboBox()
		self._listBox1 = System.Windows.Forms.CheckedListBox()
		self._listBox2 = System.Windows.Forms.ListBox()
		self._button1 = System.Windows.Forms.Button()
		self._button2 = System.Windows.Forms.Button()
		self._button3 = System.Windows.Forms.Button()
		self._button4 = System.Windows.Forms.Button()
		self._button5 = System.Windows.Forms.Button()
		self._txtBlock2 = System.Windows.Forms.Label()
		self._txtBlock3 = System.Windows.Forms.Label()
		self._txtBlock4 = System.Windows.Forms.Label()
		self._txtBlock5 = System.Windows.Forms.Label()
		self.SuspendLayout()
		# 
		# TextBlock2
		# 
		self._txtBlock2.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._txtBlock2.Location = System.Drawing.Point(12, 10)
		self._txtBlock2.Name = "txtBlock2"
		self._txtBlock2.Size = System.Drawing.Size(120, 20)
		self._txtBlock2.Text = "Category:"
		# 
		# comboBox1 Cat
		# 
		self._categories.Anchor = System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Right
		self._categories.Location = System.Drawing.Point(12, 27)
		self._categories.Name = "dropDown"
		self._categories.DataSource = self._tableData 
		self._categories.DisplayMember = "Key"
		self._categories.Size = System.Drawing.Size(310, 244)
		self._categories.DropDownWidth = 150
		self._categories.DropDownStyle = ComboBoxStyle.DropDownList
		self._categories.SelectedIndexChanged += self.UpdateFilter
		# 
		# TextBlock3
		# 
		self._txtBlock3.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._txtBlock3.Location = System.Drawing.Point(12, 53)
		self._txtBlock3.Name = "txtBlock3"
		self._txtBlock3.Size = System.Drawing.Size(120, 13)
		self._txtBlock3.Text = "Parameters:"
		# 
		# checkedListBox1
		# 
		self._listBox1.Anchor = System.Windows.Forms.AnchorStyles.Top |  System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._listBox1.FormattingEnabled = True
		self._listBox1.CheckOnClick = True
		self._listBox1.HorizontalScrollbar = True
		self._listBox1.Location = System.Drawing.Point(12, 70)
		self._listBox1.Name = "checkedListBox1"
		self._listBox1.DisplayMember = "Key"
		self._listBox1.Size = System.Drawing.Size(310, 170)
		self._listBox1.ItemCheck += self.checkItem
		# 
		# TextBlock4
		# 
		self._txtBlock4.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._txtBlock4.Location = System.Drawing.Point(12, 245)
		self._txtBlock4.Name = "txtBlock4"
		self._txtBlock4.Size = System.Drawing.Size(120, 13)
		self._txtBlock4.Text = "Values:"
		# 
		# TextBlock5
		# 
		self._txtBlock5.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Left
		self._txtBlock5.Location = System.Drawing.Point(12, 557)
		self._txtBlock5.Name = "txtBlock5"
		self._txtBlock5.Size = System.Drawing.Size(310, 27)
		self._txtBlock5.Text = "*Spaces may require you to apply a color scheme in the view."
		self._txtBlock5.ForeColor = Color.Red
		self._txtBlock5.Font = Font("Arial", 8, FontStyle.Underline)
		self._txtBlock5.Visible = False
		# 
		# checkedListBox2
		# 
		self._listBox2.Anchor = System.Windows.Forms.AnchorStyles.Top |  System.Windows.Forms.AnchorStyles.Left | System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._listBox2.FormattingEnabled = True
		self._listBox2.HorizontalScrollbar = True
		self._listBox2.Location = System.Drawing.Point(12, 262)
		self._listBox2.Name = "listBox2"
		self._listBox2.DisplayMember = "Key"
		self._listBox2.Size = System.Drawing.Size(310, 280)
		self._listBox2.DrawMode = DrawMode.OwnerDrawFixed
		self._listBox2.DrawItem += self.ColourItem
		# 
		# button1
		# 
		self._button1.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._button1.Location = System.Drawing.Point(222, 572)
		self._button1.Name = "button1"
		self._button1.Size = System.Drawing.Size(100, 27)
		self._button1.Text = "Apply Colors"
		self._button1.UseVisualStyleBackColor = True
		self._button1.Click += self.Button1Click
		# 
		# button2
		# 
		self._button2.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._button2.Location = System.Drawing.Point(12, 572)
		self._button2.Name = "button2"
		self._button2.Size = System.Drawing.Size(100, 27)
		self._button2.Text = "Reset All Colors"
		self._button2.UseVisualStyleBackColor = True
		self._button2.Click += self.Button2Click
		# 
		# button3
		# 
		self._button3.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._button3.Location = System.Drawing.Point(167, 538)
		self._button3.Name = "button3"
		self._button3.Size = System.Drawing.Size(156, 20)
		self._button3.Text = "Random Colors"
		self._button3.UseVisualStyleBackColor = True
		self._button3.Click += self.Button3Click
		# 
		# button4
		# 
		self._button4.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._button4.Location = System.Drawing.Point(11, 538)
		self._button4.Name = "button4"
		self._button4.Size = System.Drawing.Size(156, 20)
		self._button4.Text = "Gradient Colors"
		self._button4.UseVisualStyleBackColor = True
		self._button4.Click += self.Button4Click
		# 
		# button4
		# 
		self._button5.Anchor = System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right
		self._button5.Location = System.Drawing.Point(223, 243)
		self._button5.Name = "button5"
		self._button5.Size = System.Drawing.Size(100, 20)
		self._button5.Text = "↓ Create Legend"
		self._button5.UseVisualStyleBackColor = True
		self._button5.Click += self.Button5Click
		# 
		# Form24
		# 
		self.TopMost = True
		self.ShowInTaskbar = False
		self.ClientSize = System.Drawing.Size(334, 610)
		self.MaximizeBox = 0
		self.MinimizeBox = 0
		self.CenterToScreen() 
		self.FormBorderStyle = FormBorderStyle.FixedSingle
		self.Controls.Add(self._button1)
		self.Controls.Add(self._button2)
		self.Controls.Add(self._button3)
		self.Controls.Add(self._button4)
		self.Controls.Add(self._button5)
		self.Controls.Add(self._categories)
		self.Controls.Add(self._txtBlock2)
		self.Controls.Add(self._txtBlock3)
		self.Controls.Add(self._txtBlock4)
		self.Controls.Add(self._txtBlock5)
		self.Controls.Add(self._listBox1)
		self.Controls.Add(self._listBox2)
		self.Name = "Color Elements By Parameter"
		self.Text = "Color Elements By Parameter"
		iconFilename = 'C:\\NONICAPRO\\OtherFiles\\System\\Nonicafavicon.ICO'
		if not os.path.exists(iconFilename):
			iconFilename = 'C:\\NONICA\\OtherFiles\\System\\Nonicafavicon.ICO'
		icon = Icon(iconFilename)
		self.Icon = icon
		self.Closing += self.closingEvent
		self.ResumeLayout(False)
		
	def Button1Click(self, sender, e):
		if self._listBox2.Items.Count > 0:
			self.event.Raise()
	
	def Button2Click(self, sender, e):
		self.reset_ev.Raise()
	
	def Button3Click(self, sender, e):
		#Reassign Random colors
		try:
			checkindex = self._listBox1.CheckedIndices 
			for indx in checkindex:
				self._listBox1.SetItemChecked(indx, False)
				self._listBox1.SetItemChecked(indx, True)
		except:
			pass		
	
	def Button4Click(self, sender, e):
		self._listBox2.SelectedIndexChanged -= self.lstselectedIndexChanged
		try:
			list_values=[]
			number_items = len(self._listBox2.Items)
			if number_items > 2:
				stColor = self._listBox2.Items[0]['Value']._colour
				endColor = self._listBox2.Items[number_items-1]['Value']._colour
				list_colors = self.getGradientColors(stColor, endColor, number_items)
				for indx in range(len(self._listBox2.Items)):
					item = self._listBox2.Items[indx]['Value']
					item._n1 = abs(list_colors[indx][1])
					item._n2 = abs(list_colors[indx][2])
					item._n3 = abs(list_colors[indx][3])
					item._colour = Color.FromArgb(item._n1, item._n2, item._n3)
					list_values.Add(item)
				self._tableData3 = DataTable("Data")
				self._tableData3.Columns.Add("Key", System.String)
				self._tableData3.Columns.Add("Value", System.Object)
				vl_par = [x._value for x in list_values]
				[self._tableData3.Rows.Add(key_, value_ ) for key_, value_ in zip(vl_par, list_values)]	
				self._listBox2.DataSource = self._tableData3
				self._listBox2.DisplayMember = "Key"
				self._listBox2.SelectedIndex = -1
		except Exception as e:
			pass
		self._listBox2.SelectedIndexChanged += self.lstselectedIndexChanged
	
	def Button5Click(self, sender, e):
		if self._listBox2.Items.Count > 0:
			self.legend_ev.Raise()
	
	def getGradientColors(self, startColor, endColor, steps):
		aStep = float((endColor.A - startColor.A) / steps)
		rStep = float((endColor.R - startColor.R) / steps)
		gStep = float((endColor.G - startColor.G) / steps)
		bStep = float((endColor.B - startColor.B) / steps)
		colorList=[]
		for index in range(steps):
			a = startColor.A + int(aStep * index)-1;
			r = startColor.R + int(rStep * index)-1;
			g = startColor.G + int(gStep * index)-1;
			b = startColor.B + int(bStep * index)-1;
			if a < 0:
				a=0
			if r < 0:
				r=0
			if g < 0:
				g=0
			if b < 0:
				b=0
			colorList.Add([a,r,g,b])
		return colorList
	
	def closingEvent(self, sender, e):
		self.IsOpen = 0
		self.uns_event.Raise()
	
	def lstselectedIndexChanged(self, sender, e):
		#Ask colour
		if sender.SelectedIndex != -1:
			clr_dlg = ColorDialog()
			clr_dlg.AllowFullOpen = True
			if clr_dlg.ShowDialog() == DialogResult.OK:
				sender.SelectedItem['Value']._n1 = clr_dlg.Color.R
				sender.SelectedItem['Value']._n2 = clr_dlg.Color.G
				sender.SelectedItem['Value']._n3 = clr_dlg.Color.B
				sender.SelectedItem['Value']._colour = Color.FromArgb(clr_dlg.Color.R, clr_dlg.Color.G, clr_dlg.Color.B)
			self._listBox2.SelectedIndex = -1
		
	def ColourItem(self, sender, e):
		cnt = e.Index
		g = e.Graphics
		textDevice = sender.Items[e.Index]['Key']
		if cnt == self._listBox2.SelectedIndex:
			color = Color.White
			font_color = Color.Black
		else:
			color = sender.Items[e.Index]['Value']._colour
			font_color = Color.White
		e.DrawBackground()
		g.FillRectangle(SolidBrush(color), e.Bounds)
		TextRenderer.DrawText(g, textDevice, Font("Arial", 9, FontStyle.Bold), e.Bounds, font_color)
		e.DrawFocusRectangle()
		
	def checkItem(self, sender, e):
		#Only one element can be selected
		for indx in range(self._listBox1.Items.Count):
			if indx != e.Index:
				self._listBox1.SetItemChecked(indx, False)
		try:
			self._listBox2.SelectedIndexChanged -= self.lstselectedIndexChanged
		except:
			pass
		sel_cat = self._categories.SelectedItem['Value']
		sel_param = sender.Items[e.Index]['Value']
		if sel_cat != None and sel_cat != 0:
			self._tableData3 = DataTable("Data")
			self._tableData3.Columns.Add("Key", System.String)
			self._tableData3.Columns.Add("Value", System.Object)
			if e.NewValue == CheckState.Unchecked:
				self._listBox2.DataSource = self._tableData3
				self._listBox2.DisplayMember = "Key"
			else:
				rng_val = getRangeOfValues(sel_cat, sel_param, self.crt_view)
				vl_par = [x._value for x in rng_val]
				g = self._listBox2.CreateGraphics()
				width = [int(g.MeasureString(x,self._listBox2.Font).Width) for x in vl_par]
				self._listBox2.HorizontalExtent = max(width) + 50;
				[self._tableData3.Rows.Add(key_, value_ ) for key_, value_ in zip(vl_par, rng_val)]	
				self._listBox2.DataSource = self._tableData3
				self._listBox2.DisplayMember = "Key"
				self._listBox2.SelectedIndex = -1
				self._listBox2.SelectedIndexChanged += self.lstselectedIndexChanged
    	
	def UpdateFilter(self, sender, e):
		#Update param listbox
		sel_cat = sender.SelectedItem['Value']
		self._tableData2 = DataTable("Data")
		self._tableData2.Columns.Add("Key", System.String)
		self._tableData2.Columns.Add("Value", System.Object)
		self._tableData3 = DataTable("Data")
		self._tableData3.Columns.Add("Key", System.String)
		self._tableData3.Columns.Add("Value", System.Object)
		if sel_cat != 0 and sender.SelectedIndex != 0:
			names_par = [x._name for x in sel_cat._par]
			[self._tableData2.Rows.Add(key_, value_ ) for key_, value_ in zip(names_par, sel_cat._par)]	
			self._listBox1.DataSource = self._tableData2
			self._listBox1.DisplayMember = "Key"
			for indx in range(self._listBox1.Items.Count):
				self._listBox1.SetItemChecked(indx, False)
			self._listBox2.DataSource = self._tableData3
		else:
			self._listBox1.DataSource = self._tableData2
			self._listBox2.DataSource = self._tableData3

def getIndexUnits(str_value):
	for let in str_value[::-1]:
		if let.isdigit():
			return str_value[::-1].index(let)
	return -1

doc = DocumentManager.Instance.CurrentDBDocument
uidoc = DocumentManager.Instance.CurrentUIApplication.ActiveUIDocument
app = doc.Application
version = int(app.VersionNumber)
uiapp = DocumentManager.Instance.CurrentUIApplication

sel_View = getActiveView(doc)
if sel_View !=0:
	#Categories to exclude
	cat_excluded = [int(BuiltInCategory.OST_RoomSeparationLines), int(BuiltInCategory.OST_Cameras), int(BuiltInCategory.OST_CurtainGrids), int(BuiltInCategory.OST_Elev), int(BuiltInCategory.OST_Grids), int(BuiltInCategory.OST_IOSModelGroups), int(BuiltInCategory.OST_Views), int(BuiltInCategory.OST_SitePropertyLineSegment), int(BuiltInCategory.OST_SectionBox), int(BuiltInCategory.OST_ShaftOpening), int(BuiltInCategory.OST_BeamAnalytical), int(BuiltInCategory.OST_StructuralFramingOpening), int(BuiltInCategory.OST_MEPSpaceSeparationLines), int(BuiltInCategory.OST_DuctSystem), int(BuiltInCategory.OST_Lines), int(BuiltInCategory.OST_PipingSystem), int(BuiltInCategory.OST_Matchline), int(BuiltInCategory.OST_CenterLines), int(BuiltInCategory.OST_CurtainGridsRoof), int(BuiltInCategory.OST_SWallRectOpening), -2000278]
	#Get categories in used
	categ_inf_used = getCategoriesAndParametersInUsed(cat_excluded, sel_View)
	#Window
	event_handler = applyColors()
	ext_event = ExternalEvent.Create(event_handler)
	
	event_handler_uns = subscribeView()
	ext_event_uns = ExternalEvent.Create(event_handler_uns)
	
	event_handler_reset = resetColors()
	ext_event_reset = ExternalEvent.Create(event_handler_reset)
	event_handler_Legend = createLegend()
	ext_event_legend = ExternalEvent.Create(event_handler_Legend)
	wndw = Form_cats(categ_inf_used, ext_event, ext_event_uns, sel_View, ext_event_reset, ext_event_legend)
	wndw._categories.SelectedIndex = -1
	wndw.Show()
OUT = 0
"""
This script is based on ColorSplasher by BIMOne. 
All original code is licensed under MIT License, however all modifications and improvements are licensed under a different license agreement included below:
################################
MIT License
Copyright (c) 2021 BIM One Inc.
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
################################
License Agreement
For the use of this script
This License Agreement (this “Agreement” of this “License Agreement”) is made and effective as of the current date (the “Commencement Date”) by and between Nonica by Estudio Alonso Candau SLP a company organized and existing in Spain with a registered address at Avd.Chafarinas 16 Puerto Rey Vera, Almeria (“Licensor”) and yourself (“Licensee”).
WHEREAS:
1.	Licensee wishes to obtain access and use this script (hereinafter, the “Asset”), and
2.	Licensor is willing to grant to the Licensee a non-exclusive, non-transferable License to use the Asset for the term and specific purpose set forth in this Agreement,
NOW, THEREFORE, your access to and use of the Service is conditioned on your acceptance of and compliance with these Terms and Conditions. These Terms and Conditions apply to all visitors, users and others who access or use this script.
1. Definitions
1.1 “Agreement” means this License Agreement including the attached Schedule.
1.2 “Confidential Information” means information that:
a. is by its nature confidential;
b. is designated in writing by Licensor as confidential;
c. the Licensee knows or reasonably ought to know is confidential;
d. Information comprised in or relating to any Intellectual Property Rights of Licensor.
1.3 “Asset” means the Asset provided by Licensor as specified in Item 6 of the Schedule in the form as stated in Item 7 of the Schedule.
1.4 “Intellectual Property Rights” means all rights in and to any copyright, trademark, trading name, design, patent, know how (trade secrets) and all other rights resulting from intellectual activity in the industrial, scientific, literary or artistic field and any application or right to apply for registration of any of these rights and any right to protect or enforce any of these rights, as further specified in clause 5.
1.5 “Party” means a person or business entity who has executed this Agreement; details of the Parties are specified in Item 2 of the Schedule.
1.6 “Term” means the term of this Agreement commencing on the Commencement Date as specified in Item 4 of the Schedule and expiring on the Expiry Date specified in Item 5 of the Schedule.
2. License Grant
2.1 Licensor grants to the Licensee a non-exclusive, non-transferable License for the Term to use the Asset for the specific purpose specified in this Agreement, subject to the terms and conditions set out in this Agreement.
3. Charges
3.1 In consideration of the Licensor providing the License under clause 2 of this License Agreement, the Licensee agrees to pay Licensor the amount of the License Charge as specified in Item 9 of the Schedule.
4. Licensee’s Obligations
4.1 The Licensee cannot use the Asset, for purposes other than as specified in this Agreement and in Item 8 of the Schedule.
4.2 The Licensee may permit its employees to use the Asset for the purposes described in Item 8, provided that the Licensee takes all necessary steps and imposes the necessary conditions to ensure that all employees using the Asset do not commercialise or disclose the contents of it to any third person, or use it other than in accordance with the terms of this Agreement.
4.3 The Licensee will not distribute, sell, License or sub-License, let, trade or expose for sale the Asset to a third party.
4.4 No copies of the Asset are to be made other than as expressly approved by Licensor.
4.5 No changes to the Asset or its content may be made by Licensee.
4.6 The Licensee will provide technological and security measures to ensure that the Asset which the Licensee is responsible for is physically and electronically secure from unauthorised use or access.
4.7 Licensee shall ensure that the Asset retains all Licensor copyright notices and other proprietary legends and all trademarks or service marks of Licensor.
5. Intellectual Property Rights
5.1 All Intellectual Property Rights over and in respect of the Asset are owned by Licensor. The Licensee does not acquire any rights of ownership in the Asset.
6. Limitation of Liability
6.1 The Licensee acknowledges and agrees that neither Licensor nor its board members, officers, employees or agents, will be liable for any loss or damage arising out of or resulting from Licensor’s provision of the Asset under this Agreement, or any use of the Asset by the Licensee or its employees; and Licensee hereby releases Licensor to the fullest extent from any such liability, loss, damage or claim.
7. Confidentiality
7.1 Neither Party may use, disclose or make available to any third party the other Party’s Confidential Information, unless such use or disclosure is done in accordance with the terms of this Agreement.
7.2 Each Party must hold the other Party’s Confidential Information secure and in confidence, except to the extent that such Confidential Information:
a. is required to be disclosed according to the requirements of any law, judicial or legislative body or government agency; or
b. was approved for release in writing by the other Party, but only to the extent of and subject to such conditions as may be imposed in such written authorisation.
7.3 This clause 7 will survive termination of this Agreement.
8. Disclaimers & Release
8.1 To the extent permitted by law, Licensor will in no way be liable to the Licensee or any third party for any loss or damage, however caused (including through negligence) which may be directly or indirectly suffered in connection with any use of the Asset.
8.2 The Asset is provided by Licensor on an “as is” basis.
8.3 Licensor will not be held liable by the Licensee in any way, for any loss, damage or injury suffered by the Licensee or by any other person related to any use of the Asset or any part thereof.
8.4 Notwithstanding anything contained in this Agreement, in no event shall Licensor be liable for any claims, damages or loss which may arise from the modification, combination, operation or use of the Asset with Licensee computer programs.
8.5 Licensor does not warrant that the Asset will function in any environment.
8.6 The Licensee acknowledges that: a. The Asset has not been prepared to meet any specific requirements of any party, including any requirements of Licensee; and b. it is therefore the responsibility of the Licensee to ensure that the Asset meets its own individual requirements.
8.7 To the extent permitted by law, no express or implied warranty, term, condition or undertaking is given or assumed by Licensor, including any implied warranty of merchantability or fitness for a particular purpose.
9. Indemnification
9.1 The Licensee must indemnify, defend and hold harmless Licensor, its board members, officers, employees and agents from and against any and all claims (including third party claims), demands, actions, suits, expenses (including attorney’s fees) and damages (including indirect or consequential loss) resulting in any way from:
a. Licensee’s and Licensee’s employee’s use or reliance on the Asset,
b. any breach of the terms of this License Agreement by the Licensee or any Licensee employee, and
c. any other act of Licensee.
9.2 This clause 9 will survive termination of this Agreement.
10. Waiver
10.1 Any failure or delay by either Party to exercise any right, power or privilege hereunder or to insist upon observance or performance by the other of the provisions of this License Agreement shall not operate or be construed as a waiver thereof.
11. Governing Law
11.1 This Agreement will be construed by and governed in accordance with the laws of Spain. The Parties submit to exclusive jurisdiction of the courts of Spain.
12. Termination
12.1 This Agreement and the License granted herein commences upon the Commencement Date and is granted for the Term, unless otherwise terminated by Licensor in the event of any of the following:
a. if the Licensee is in breach of any term of this License Agreement and has not corrected such breach to Licensor’s reasonable satisfaction within 7 days of Licensor’s notice of the same;
b. if the Licensee becomes insolvent, or institutes (or there is instituted against it) proceedings in bankruptcy, insolvency, reorganization or dissolution, or makes an assignment for the benefit of creditors; or
c. the Licensee is in breach of clause 5 or 7 of this Agreement.
12.2 Termination under this clause shall not affect any other rights or remedies Licensor may have.
14. Assignment
14.1 Licensee shall not assign any rights of this License Agreement, without the prior written consent of Licensor.
15. Notices
15.1 All notices required under this Agreement shall be in writing and shall be deemed given (i) when delivered personally; (ii) five (5) days after mailing, when sent certified mail, return receipt requested and postage prepaid; or (iii) one (1) business day after dispatch, when sent via a commercial overnight carrier, fees prepaid. All notices given by either Party must be sent to the address of the other as first written above (unless otherwise changed by written notice).
16. Counterparts
16.1 This Agreement may be executed in any number of counterparts, each of which shall be deemed to be an original and all of which taken together shall constitute one instrument.
17. Severability
17.1 The Parties recognize the uncertainty of the law with respect to certain provisions of this Agreement and expressly stipulate that this Agreement will be construed in a manner that renders its provisions valid and enforceable to the maximum extent possible under applicable law. To the extent that any provisions of this Agreement are determined by a court of competent jurisdiction to be invalid or unenforceable, such provisions will be deleted from this Agreement or modified so as to make them enforceable and the validity and enforceability of the remainder of such provisions and of this Agreement will be unaffected.
18. Entire Agreement
18.1 This Agreement contains the entire agreement between the Parties and supersedes any previous understanding, commitments or agreements, oral or written. Further, this Agreement may not be modified, changed, or otherwise altered in any respect except by a written agreement signed by both Parties.
IN WITNESS WHEREOF, this Agreement, including the attached Schedule, was signed by the Parties under the hands of their duly authorized representatives and made effective as of the current date.
Nonica by Estudio Alonso Candau SLP,
Signature
02/05/2021
Jaime Alonso Candau
Please contact hello@nonica.io with any further doubt/request.
Your signatureby using and accessing this script.
Signed by accepting these terms.
Current date.

"""