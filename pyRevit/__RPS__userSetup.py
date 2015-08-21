import clr, sys, os, re
import os.path as op
import random as rnd
from datetime import datetime
import pickle as pl

clr.AddReference('PresentationCore')
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('System.Xml.Linq')

from System import *
from System.IO import *
from System.Reflection import *
from System.Reflection.Emit import *
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption
from System.Xml.Linq import XDocument

from Autodesk.Revit.UI import *
from Autodesk.Revit.Attributes import *
from System.Diagnostics import Process

verbose = True

def report( message ):
	global verbose
	if verbose:
		print( message )

def findHomeDirectory():
	try:
		#getting home directory from __file__ provided by RPS
		folder = os.path.dirname( __file__ )
		if folder.lower().endswith('.dll'):
			# nope - RpsAddin
			return os.path.dirname( folder )
		else:
			return folder
	except:
		settingFolder = Path.Combine( Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "RevitPythonShell" + revitVersion )
		settingsFile = Path.Combine( settingFolder, "RevitPythonShell.xml" )
		xdoc = XDocument.Load( settingsFile )
		return op.dirname( xdoc.Root.Element("StartupScript").Attribute("src").Value )

def findUserTempDirectory():
	tempFolder = os.getenv('Temp')
	return tempFolder

#EXCEPTIONS
class pyRevitException( Exception ):
	pass

class unknownAssembly( pyRevitException ):
	pass

class unknownFileNameFormat( pyRevitException ):
	pass

#SOOP CLASSES
class pyRevitUISettings():
	#settings - load from settings file in future
	pyRevitRibbonName = 'pyRevit'
	pyRevitAssemblyName = 'pyRevit'
	linkButtonTypeName = 'PushButton'
	pushButtonTypeName = 'PushButton'
	pulldownButtonTypeName = 'PulldownButton'
	stackedThreeTypeName = 'Stack3'
	splitButtonTypeName = 'SplitButton'

class buttonGraphics():
	def __init__( self, fileDir, fileName ):
		uri = Uri( op.join( fileDir, fileName ))
		self.smallIcon = BitmapImage()
		self.smallIcon.BeginInit()
		self.smallIcon.UriSource = uri
		self.smallIcon.CacheOption = BitmapCacheOption.OnLoad
		self.smallIcon.DecodePixelHeight = 16
		self.smallIcon.DecodePixelWidth = 16
		self.smallIcon.EndInit()
		self.icon = BitmapImage()
		self.icon.BeginInit()
		self.icon.UriSource = uri
		self.icon.CacheOption = BitmapCacheOption.OnLoad
		self.icon.EndInit()

class ScriptPanel():
	def __init__( self, fileDir, f ):
		fname, fext = op.splitext( op.basename( f ))
		if ScriptPanel.isScriptPanelDescriptorFile( fname, fext ):
			namePieces = fname.rsplit('_')
			namePiecesLength = len( namePieces )
			if namePiecesLength == 4 or namePiecesLength == 6:
				self.panelOrder, self.panelName = namePieces[0:2]
				self.panelOrder = int( self.panelOrder[:2] )
				report('Panel found: Type: {0}'.format(	self.panelName.ljust(20) ))
			else:
				raise unknownFileNameFormat()
		else:
			raise unknownFileNameFormat()
	@staticmethod
	def isScriptPanelDescriptorFile( fname, fext ):
		return ('.png' == fext.lower() and fname[0].isdigit())

class ScriptGroup():
	def __init__( self, fileDir, f ):
		self.commands = []
		fname, fext = op.splitext( op.basename( f ))
		if ScriptGroup.isScriptGroupDescriptorFile( fname, fext ):
			self.sourceDir = fileDir
			self.sourceFile = f
			self.sourceFileName = fname 
			self.sourceFileExt = fext 
			namePieces = fname.rsplit('_')
			namePiecesLength = len( namePieces )
			if namePiecesLength == 4 or namePiecesLength == 6:
				self.groupOrder, self.panelName, self.groupType, self.groupName = namePieces[0:4]
				self.groupOrder = int( self.groupOrder[2:] )
				report('Script group found: Type: {0}  Name: {1} Parent Panel: {2}'.format(	self.groupType.ljust(20),
																							self.groupName.ljust(20),
																							self.panelName ))
				self.buttonGraphics = buttonGraphics( fileDir, f )
			#check to see if name has assembly information
			if len( namePieces ) == 6:
				self.assemblyName, self.assemblyClassName = namePieces[4:]
				try:
					self.assemblyName = ScriptGroup.findAssembly( self.assemblyName ).GetName().Name
					self.assemblyLocation = ScriptGroup.findAssembly( self.assemblyName ).Location
					report('                    Assembly.Class: {0}.{1}'.format(	self.assemblyName,
																					self.assemblyClassName ))
				except unknownAssembly:
					self.assemblyName = None
					self.assemblyLocation = None
					self.assemblyClassName = None
					raise
		else:
			raise unknownFileNameFormat()

	def adoptCommands( self, pyRevitCommands ):
		for cmd in pyRevitCommands:
			if cmd.scriptGroupName == self.groupName:
				report('\tcontains: {0}'.format( cmd.fileName ))
				self.commands.append( cmd )
	def isLinkButton( self ):
		return self.assemblyName != None
	@staticmethod
	def isScriptGroupDescriptorFile( fname, fext ):
		return ('.png' == fext.lower() and fname[0].isdigit())
	@staticmethod
	def findAssembly( assemblyName ):
		for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
			if assemblyName in loadedAssembly.FullName:
				return loadedAssembly
		raise unknownAssembly()

class ScriptCommand():
	def __init__( self, fileDir, f ):
		fname, fext = op.splitext( op.basename( f ))
		self.tooltip = fname + ' ' + fext.lower()

		# custom name adjustments
		if fname == '__RPS__userSetup':
			fname = 'Settings_reloadScripts'
		elif '__WIP__' in fname:
			fname = fname.replace('__WIP__', 'WIP_')

		if '_' != fname[0] and '.py' == fext.lower():
			self.filePath = fileDir
			self.fileName = f
			namePieces = fname.rsplit('_')
			namePiecesLength = len( namePieces )
			if namePiecesLength == 2:
				self.scriptGroupName, self.cmdName = namePieces
				self.className = self.cmdName
				report('Script found: {0} Group: {1} CommandName: {2}'.format(	f.ljust(50),
																				self.scriptGroupName.ljust(20),
																				self.cmdName ))
				if op.exists( op.join( fileDir, fname + '.png' )):
					self.buttonGraphics = buttonGraphics( fileDir, fname + '.png' )
				else:
					self.buttonGraphics = None
		else:
			raise unknownFileNameFormat()

	def getFullScriptAddress( self ):
		return op.join( self.filePath, self.fileName )

class pyRevitUISession():
	def __init__( self, homeDirectory, settingsClass ):
		self.loadedPyRevitScripts = []
		self.loadedPyRevitAssemblies = []
		self.pyRevitUIPanels = {}
		self.pyRevitUIButtons = {}
		self.scriptPanelsDict = {}
		self.scriptGroupsByPanelDict = {}
		self.pyRevitCommands = []
		self.homeDir = homeDirectory
		self.userTempFolder = findUserTempDirectory()
		self.rpsCommandLoader = None
		self.rps = None
		self.newAssemblyLocation = None
		self.settings = settingsClass

		# find homeDir and info on revit session
		report('Home Directory is: {0}'.format( self.homeDir ))
		self.revitVersion = __revit__.Application.VersionNumber

		#collect information about previously loaded assemblies
		report('Initializing python script loader...')
		self.findRPSCommandLoader()
		self.findLoadedPyRevitAssemblies()
		self.cleanupOldAssemblies()

		# find commands
		report('Searching for panels, groups, and scripts...')
		self.findScripts()
		#find script groups and assign commands
		self.findScriptPanelsAndGroups()

		#create assembly dll
		report('Building script executer assembly...')
		self.createAssmebly()

		#setting up UI
		report("Executer assembly saved.\nNow setting up ribbon, panels, and buttons...")
		self.createOrFindPyRevitPanels()
		report("Ribbon tab and panels are ready. Creating script group buttons...")
		self.createUI()

	def cleanupOldAssemblies( self ):
		revitInstances = list( Process.GetProcessesByName('Revit') )
		revitVersionStr = self.getRevitVersionStr()
		if len(revitInstances) > 1:
			report('Multiple Revit instance are running...Skipping DLL Cleanup')
		elif len(revitInstances) == 1 and not self.isReloadingScripts():
			report('Cleaning up old DLL files...')
			files = os.listdir( self.userTempFolder )
			for f in files:
				if f.startswith( self.settings.pyRevitAssemblyName + revitVersionStr ):
					try:
						os.remove( op.join( self.userTempFolder, f ))
						report('Dll Removed: {0}'.format( f ))
					except:
						report('Error deleting: {0}'.format( f ))

	def isReloadingScripts( self ):
		return len( self.loadedPyRevitAssemblies ) > 0

	def getRevitVersionStr( self ):
		return str( self.revitVersion )

	def findRPSCommandLoader( self ):
		report('Asking Revit for RevitPythonShell Command Loader class...')
		for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
			if "RevitPythonShell" in loadedAssembly.FullName:
				report('RPS Assembly found: {0}'.format( loadedAssembly.GetName().FullName ))
				self.rpsCommandLoader = loadedAssembly.GetType("RevitPythonShell.CommandLoaderBase")
				self.rps = loadedAssembly

	def findLoadedPyRevitAssemblies( self ):
		report('Asking Revit for previously loaded pyRevit assemblies...')
		for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
			if self.settings.pyRevitAssemblyName in loadedAssembly.FullName:
				report('Existing assembly found: {0}'.format( loadedAssembly.FullName ))
				self.loadedPyRevitAssemblies.append( loadedAssembly )
				self.loadedPyRevitScripts.extend( [ ct.Name for ct in loadedAssembly.GetTypes() ] )

	def getSortedScriptPanels( self ):
		return sorted( self.scriptPanelsDict.values(), key = lambda x: x.panelOrder )

	def getSortedScriptGroups( self, panelName ):
		return sorted( self.scriptGroupsByPanelDict[ panelName ], key = lambda x: x.groupOrder )

	def findScripts( self ):
		report('Searching current folder for scripts...')
		files = sorted( os.listdir( self.homeDir ))
		for f in files:
			#creating scriptCommands
			fname, fext = op.splitext( op.basename( f ))
			if '.py' == fext.lower():
				try:
					cmd = ScriptCommand( self.homeDir, f )
				except unknownFileNameFormat:
					report('Can not recognize name pattern. skipping: {0}'.format( f ))
					continue
				self.pyRevitCommands.append( cmd )

		if not len( self.pyRevitCommands ) > 0:
			report('No Scripts found...')

	def findScriptPanelsAndGroups( self ):
		report('Searching content folder for script groups ...')
		files = os.listdir( self.homeDir )
		for f in files:
			#creating scriptPanel and scriptGroup
			#creating scriptCommands
			fname, fext = op.splitext( op.basename( f ))
			if '.png' == fext.lower():
				try:
					scriptPanel = ScriptPanel( self.homeDir, f )
					if scriptPanel.panelName not in self.scriptPanelsDict:
						self.scriptPanelsDict[ scriptPanel.panelName ] = scriptPanel
				except unknownFileNameFormat:
					report('Can not recognize name pattern. skipping: {0}'.format( f ))
					continue

				try:
					scriptGroup = ScriptGroup( self.homeDir, f )
					scriptGroup.adoptCommands( self.pyRevitCommands )
					if scriptGroup.panelName not in self.scriptGroupsByPanelDict:
						self.scriptGroupsByPanelDict[ scriptGroup.panelName ] = [ scriptGroup ]
					else:
						self.scriptGroupsByPanelDict[ scriptGroup.panelName ].append( scriptGroup )
				except unknownFileNameFormat:
					report('Can not recognize name pattern. skipping: {0}'.format( f ))
					continue
				except unknownAssembly:
					report('Unknown assembly error. Skipping: {0}'.format( f ))
					continue

	def createAssmebly( self ):
		# create DLL folder
		# dllFolder = Path.Combine( self.homeDir, self.settings.pyRevitAssemblyName )
		# if not os.path.exists( dllFolder ):
			# os.mkdir( dllFolder )
		dllFolder = self.userTempFolder
		# make assembly name
		generatedAssemblyName = self.settings.pyRevitAssemblyName + self.getRevitVersionStr() + datetime.now().strftime('_%y%m%d%H%M%S')
		dllName = generatedAssemblyName + ".dll"
		# create assembly
		windowsAssemblyName = AssemblyName( Name = generatedAssemblyName, Version = Version(1,0,0,0))
		assemblyBuilder = AppDomain.CurrentDomain.DefineDynamicAssembly( windowsAssemblyName, AssemblyBuilderAccess.RunAndSave, dllFolder)
		moduleBuilder = assemblyBuilder.DefineDynamicModule( generatedAssemblyName , dllName )
		
		# create command classes
		for cmd in self.pyRevitCommands:
			typebuilder = moduleBuilder.DefineType( cmd.className, TypeAttributes.Class | TypeAttributes.Public, self.rpsCommandLoader )
			
			# add RegenerationAttribute to type
			regenerationConstrutorInfo = clr.GetClrType(RegenerationAttribute).GetConstructor( Array[Type]((RegenerationOption,)) )              
			regenerationAttributeBuilder = CustomAttributeBuilder(regenerationConstrutorInfo, Array[object]((RegenerationOption.Manual,)))
			typebuilder.SetCustomAttribute(regenerationAttributeBuilder)

			# add TransactionAttribute to type
			transactionConstructorInfo = clr.GetClrType(TransactionAttribute).GetConstructor( Array[Type]((TransactionMode,)) )
			transactionAttributeBuilder = CustomAttributeBuilder(transactionConstructorInfo, Array[object]((TransactionMode.Manual,)))
			typebuilder.SetCustomAttribute(transactionAttributeBuilder)
			
			#call base constructor with script path
			ci = self.rpsCommandLoader.GetConstructor(Array[Type]((str,)))
			constructorBuilder = typebuilder.DefineConstructor(MethodAttributes.Public, CallingConventions.Standard, Array[Type](()))
			gen = constructorBuilder.GetILGenerator()
			gen.Emit(OpCodes.Ldarg_0)					# Load "this" onto eval stack
			gen.Emit(OpCodes.Ldstr, cmd.getFullScriptAddress() )				# Load the path to the command as a string onto stack
			gen.Emit(OpCodes.Call, ci)					# call base constructor (consumes "this" and the string)
			gen.Emit(OpCodes.Nop)						# Fill some space - this is how it is generated for equivalent C# code
			gen.Emit(OpCodes.Nop)
			gen.Emit(OpCodes.Nop)
			gen.Emit(OpCodes.Ret)  
			typebuilder.CreateType()

		# save final assembly
		assemblyBuilder.Save( dllName )
		self.newAssemblyLocation = Path.Combine( dllFolder, dllName )

	def createOrFindPyRevitPanels( self ):
		report("Searching for existing pyRevit panel...")
		try:
			pyRevitRibbonPanels = {p.Name:p for p in __revit__.GetRibbonPanels( self.settings.pyRevitRibbonName )}
		except:
			report("Creating pyRevit ribbon...")
			pyRevitRibbon = __revit__.CreateRibbonTab( self.settings.pyRevitRibbonName )
			pyRevitRibbonPanels = {p.Name:p for p in __revit__.GetRibbonPanels( self.settings.pyRevitRibbonName )}
			
			report("Searching for scripts panels...")
		for panel in self.getSortedScriptPanels():
			if panel.panelName in pyRevitRibbonPanels.keys():
				report("Existing panel found: {0}".format( panel.panelName ))
				self.pyRevitUIPanels[ panel.panelName ] = pyRevitRibbonPanels[ panel.panelName ]
				self.pyRevitUIButtons[ panel.panelName ] = list( pyRevitRibbonPanels[ panel.panelName ].GetItems() )
			else:
				report("Creating scripts panel: {0}".format( panel.panelName ))
				newPanel = __revit__.CreateRibbonPanel( self.settings.pyRevitRibbonName, panel.panelName )
				self.pyRevitUIPanels[ panel.panelName ] = newPanel
				self.pyRevitUIButtons[ panel.panelName ] = []

	def createUI( self ):
		newButtonCount = updatedButtonCount = 0
		for scriptPanel in self.getSortedScriptPanels():
			pyRevitRibbonPanel = self.pyRevitUIPanels[ scriptPanel.panelName ]
			pyRevitRibbonItemsDict = {b.Name:b for b in self.pyRevitUIButtons[ scriptPanel.panelName ]}
			report('Creating\\Updating ribbon items for panel: {0}'.format( scriptPanel.panelName ))
			for scriptGroup in self.getSortedScriptGroups( scriptPanel.panelName ):
				#PulldownButton or SplitButton
				if scriptGroup.groupType == self.settings.pulldownButtonTypeName or scriptGroup.groupType == self.settings.splitButtonTypeName:
					#PulldownButton
					if scriptGroup.groupType == self.settings.pulldownButtonTypeName:
						if scriptGroup.groupName not in pyRevitRibbonItemsDict:
							report('\tCreating pulldown button group: {0}'.format( scriptGroup.groupName ))
							ribbonItem = pyRevitRibbonPanel.AddItem( PulldownButtonData( scriptGroup.groupName, scriptGroup.groupName ))
						else:
							report('\tUpdating pulldown button group: {0}'.format( scriptGroup.groupName ))
							ribbonItem = pyRevitRibbonItemsDict.pop( scriptGroup.groupName )

					#SplitButton
					elif scriptGroup.groupType == self.settings.splitButtonTypeName:
						if scriptGroup.groupName not in pyRevitRibbonItemsDict.keys():
							report('\tCreating split button group: {0}'.format( scriptGroup.groupName ))
							ribbonItem = pyRevitRibbonPanel.AddItem( SplitButtonData( scriptGroup.groupName, scriptGroup.groupName ))
						else:
							report('\tUpdating split button group: {0}'.format( scriptGroup.groupName ))
							ribbonItem = pyRevitRibbonItemsDict.pop( scriptGroup.groupName )

					ribbonItem.Image = scriptGroup.buttonGraphics.smallIcon
					ribbonItem.LargeImage = scriptGroup.buttonGraphics.icon
					existingRibbonItemPushButtonsDict = {b.ClassName:b for b in ribbonItem.GetItems()}

					for cmd in scriptGroup.commands:
						if cmd.className not in existingRibbonItemPushButtonsDict:
							report('\t\tCreating push button: {0}'.format( cmd.className ))
							buttonData = PushButtonData( cmd.className, cmd.cmdName, self.newAssemblyLocation , cmd.className )
							buttonData.ToolTip = cmd.tooltip
							if cmd.buttonGraphics:
								buttonData.LargeImage = cmd.buttonGraphics.icon
							else:
								buttonData.LargeImage = scriptGroup.buttonGraphics.icon
							ribbonItem.AddPushButton( buttonData )
							newButtonCount += 1
						else:
							report('\t\tUpdating push button: {0}'.format( cmd.className ))
							pushButton = existingRibbonItemPushButtonsDict.pop( cmd.className )
							pushButton.ToolTip = cmd.tooltip
							pushButton.Enabled = True
							if cmd.buttonGraphics:
								pushButton.LargeImage = cmd.buttonGraphics.icon
							else:
								pushButton.LargeImage = scriptGroup.buttonGraphics.icon
							updatedButtonCount += 1
					for orphanedButtonName, orphanedButton in existingRibbonItemPushButtonsDict.items():
						report('\tDisabling orphaned button: {0}'.format( orphanedButtonName ))
						orphanedButton.Enabled = False

				#StackedButtons
				elif scriptGroup.groupType == self.settings.stackedThreeTypeName:
					report('\tCreating\\Updating 3 stacked buttons: {0}'.format( scriptGroup.groupType ))
					stackCommands = []
					for cmd in scriptGroup.commands:
						if cmd.className not in pyRevitRibbonItemsDict:
							report('\t\tCreating stacked button: {0}'.format( cmd.className ))
							buttonData = PushButtonData( cmd.className, cmd.cmdName, self.newAssemblyLocation , cmd.className )
							buttonData.ToolTip = cmd.tooltip
							if cmd.buttonGraphics:
								buttonData.Image = cmd.buttonGraphics.smallIcon
							else:
								buttonData.Image = scriptGroup.buttonGraphics.smallIcon
							stackCommands.append( buttonData )
							newButtonCount += 1
						else:
							report('\t\tUpdating stacked button: {0}'.format( cmd.className ))
							ribbonItem = pyRevitRibbonItemsDict.pop( cmd.className )
							ribbonItem.AssemblyName = self.newAssemblyLocation
							ribbonItem.ClassName = cmd.className
							ribbonItem.Enabled = True
							updatedButtonCount += 1
							if cmd.buttonGraphics:
								ribbonItem.Image = cmd.buttonGraphics.smallIcon
							else:
								ribbonItem.Image = scriptGroup.buttonGraphics.smallIcon
					if len( stackCommands ) == 3:
						pyRevitRibbonPanel.AddStackedItems( *stackCommands )

				#PushButton
				elif scriptGroup.groupType == self.settings.pushButtonTypeName and not scriptGroup.isLinkButton():
					try:
						cmd = scriptGroup.commands.pop()
						if cmd.className not in pyRevitRibbonItemsDict:
							report('\tCreating push button: {0}'.format( cmd.className ))
							ribbonItem = pyRevitRibbonPanel.AddItem( PushButtonData( cmd.className, cmd.cmdName, self.newAssemblyLocation , cmd.className ))
							newButtonCount += 1
						else:
							report('\tUpdating push button: {0}'.format( cmd.className ))
							ribbonItem = pyRevitRibbonItemsDict.pop( cmd.className )
							ribbonItem.AssemblyName = self.newAssemblyLocation
							ribbonItem.ClassName = cmd.className
							ribbonItem.Enabled = True
							updatedButtonCount += 1
						ribbonItem.Image = scriptGroup.buttonGraphics.smallIcon
						ribbonItem.LargeImage = scriptGroup.buttonGraphics.icon
					except:
						report('\tPushbutton has no associated scripts. Skipping {0}'.format( scriptGroup.sourceFile ))
						continue

				#LinkButton
				elif scriptGroup.groupType == self.settings.linkButtonTypeName and scriptGroup.isLinkButton():
					if scriptGroup.groupName not in pyRevitRibbonItemsDict:
						report('\tCreating push button link to other assembly: {0}'.format( scriptGroup.groupName ))
						ribbonItem = pyRevitRibbonPanel.AddItem( PushButtonData( scriptGroup.groupName, scriptGroup.groupName, scriptGroup.assemblyLocation , scriptGroup.assemblyName + '.' + scriptGroup.assemblyClassName ))
						newButtonCount += 1
					else:
						report('\tUpdating push button link to other assembly: {0}'.format( scriptGroup.groupName ))
						ribbonItem = pyRevitRibbonItemsDict.pop( scriptGroup.groupName )
						ribbonItem.AssemblyName = scriptGroup.assemblyLocation
						ribbonItem.ClassName = scriptGroup.assemblyName + '.' + scriptGroup.assemblyClassName
						ribbonItem.Enabled = True
						updatedButtonCount += 1
					ribbonItem.Image = scriptGroup.buttonGraphics.smallIcon
					ribbonItem.LargeImage = scriptGroup.buttonGraphics.icon

			#now disable all orphaned buttons in this panel
			for orphanedRibbonItemName, orphanedRibbonItem in pyRevitRibbonItemsDict.items():
				report('\tDisabling orphaned ribbon item: {0}'.format( orphanedRibbonItemName ))
				orphanedRibbonItem.Enabled = False

		#final report
		report("\n\n{0} buttons created...\n{1} buttons updated...\n\n".format( newButtonCount, updatedButtonCount ))


#MAIN
thisSession = pyRevitUISession( findHomeDirectory(), pyRevitUISettings() )

#FINAL REPORT
report('All done...')