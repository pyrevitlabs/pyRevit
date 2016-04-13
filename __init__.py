import clr, sys, os, re
import os.path as op
import random as rnd
from datetime import datetime
import pickle as pl
import time

clr.AddReference('PresentationCore')
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('System.Xml.Linq')

from System import *
from System.IO import *
from System.Reflection import *
from System.Reflection.Emit import *
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption

from Autodesk.Revit.UI import *
from Autodesk.Revit.Attributes import *
from System.Diagnostics import Process

verbose = True

def report( message, title = False ):
	if title:
		print('-'*100 + '\n' + message + '\n' + '-'*100)
	else:
		print( message )

def reportv( message, title = False ):
	global verbose
	if verbose:
		report( message, title )
	# else:
		# time.sleep(.01)

def findHomeDirectory():
	#getting home directory from __file__ provided by RPL
	folder = os.path.dirname( __file__ )
	if folder.lower().endswith('.dll'):
		# nope - RplAddin
		folder = os.path.dirname( folder )
	sys.path.append( folder )
	return folder

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
	pyRevitAssemblyName = 'pyRevit'
	linkButtonTypeName = 'PushButton'
	pushButtonTypeName = 'PushButton'
	smartButtonTypeName = 'SmartButton'
	pulldownButtonTypeName = 'PulldownButton'
	stackedThreeTypeName = 'Stack3'
	splitButtonTypeName = 'SplitButton'
	tooltipParameter = '__doc__'
	userSetupKeyword = '__init__'
	reloadScriptsOverrideName = 'Settings_reloadScripts'
	masterTabName = 'master'

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

class ScriptTab():
	def __init__( self, tname, tfolder ):
		self.tabName = tname
		self.tabFolder = tfolder
		self.scriptPanels = []
		self.pyRevitUIPanels = {}
		self.pyRevitUIButtons = {}

	def adoptPanels( self, pyRevitScriptPanels ):
		for panel in pyRevitScriptPanels:
			if panel.tabName == self.tabName:
				reportv('\tcontains: {0}'.format( panel.panelName ))
				self.scriptPanels.append( panel )

	def getSortedScriptPanels( self ):
		return sorted( self.scriptPanels, key = lambda x: x.panelOrder )

	def hasScriptCommands( self ):
		hasCmds = False
		for p in self.scriptPanels:
			for g in p.scriptGroups:
				for sc in g.commands:
					hasCmds = True
		return hasCmds

class ScriptPanel():
	def __init__( self, fileDir, f, tabName):
		self.panelOrder = 0
		self.panelName = ''
		self.scriptGroups = []
		self.tabName = tabName
		
		fname, fext = op.splitext( op.basename( f ))
		if ScriptPanel.isScriptPanelDescriptorFile( fname, fext ):
			namePieces = fname.rsplit('_')
			namePiecesLength = len( namePieces )
			if namePiecesLength == 4 or namePiecesLength == 6:
				self.panelOrder, self.panelName = namePieces[0:2]
				self.panelOrder = int( self.panelOrder[:2] )
				reportv('Panel found: Type: {0}'.format( self.panelName.ljust(20) ))
			else:
				raise unknownFileNameFormat()
		else:
			raise unknownFileNameFormat()

	@staticmethod
	def isScriptPanelDescriptorFile( fname, fext ):
		return ('.png' == fext.lower() and fname[0].isdigit())

	def adoptGroups( self, pyRevitScriptGroups ):
		for group in pyRevitScriptGroups:
			if group.panelName == self.panelName and group.tabName == self.tabName:
				reportv('\tcontains: {0}'.format( group.groupName ))
				self.scriptGroups.append( group )

	def getSortedScriptGroups( self, panelName ):
		return sorted( self.scriptGroups, key = lambda x: x.groupOrder )

class ScriptGroup():
	def __init__( self, fileDir, f, tabName ):
		self.commands = []
		self.sourceDir = ''
		self.sourceFile = ''
		self.sourceFileName = '' 
		self.sourceFileExt = '.png'
		self.groupOrder = 0
		self.panelName = ''
		self.groupType = None
		self.groupName = ''
		self.buttonGraphics = None
		self.assemblyName = None
		self.assemblyClassName = None
		self.assemblyLocation = None
		self.tabName = tabName
		
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
				reportv('Script group found: Type: {0}  Name: {1} Parent Panel: {2}'.format(	self.groupType.ljust(20),
																								self.groupName.ljust(20),
																								self.panelName ))
				self.buttonGraphics = buttonGraphics( fileDir, f )
			#check to see if name has assembly information
			if len( namePieces ) == 6:
				self.assemblyName, self.assemblyClassName = namePieces[4:]
				try:
					self.assemblyName = ScriptGroup.findAssembly( self.assemblyName ).GetName().Name
					self.assemblyLocation = ScriptGroup.findAssembly( self.assemblyName ).Location
					reportv('                    Assembly.Class: {0}.{1}'.format(	self.assemblyName,
																					self.assemblyClassName ))
				except unknownAssembly:
					raise
		else:
			raise unknownFileNameFormat()

	def adoptCommands( self, pyRevitScriptCommands ):
		settings = pyRevitUISettings()
		for cmd in pyRevitScriptCommands:
			if cmd.scriptGroupName == self.groupName:
				if cmd.tabName == self.tabName or cmd.tabName == settings.masterTabName:
					reportv('\tcontains: {0}'.format( cmd.fileName ))
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
	def __init__( self, fileDir, f, tabName):
		self.filePath = ''
		self.fileName = ''
		self.tooltip = ''
		self.cmdName = ''
		self.scriptGroupName = ''
		self.className = ''
		self.iconFileName = ''
		self.buttonGraphics = None
		self.tabName = tabName
		
		fname, fext = op.splitext( op.basename( f ))
		settings = pyRevitUISettings()

		# custom name adjustments
		if settings.userSetupKeyword.lower() in fname.lower():
			fname = settings.reloadScriptsOverrideName

		if '_' != fname[0] and '.py' == fext.lower():
			self.filePath = fileDir
			self.fileName = f
			self.tooltip = fname + ' ' + fext.lower()
			docString = ScriptCommand.extractParameter( settings.tooltipParameter, self.getFullScriptAddress() )
			if docString != None:
				self.tooltip = self.tooltip + '\n' + docString
			namePieces = fname.rsplit('_')
			namePiecesLength = len( namePieces )
			if namePiecesLength == 2:
				self.scriptGroupName, self.cmdName = namePieces
				self.className = tabName + self.scriptGroupName + self.cmdName
				reportv('Script found: {0} Group: {1} CommandName: {2}'.format(	f.ljust(50),
																				self.scriptGroupName.ljust(20),
																				self.cmdName ))
				if op.exists( op.join( fileDir, fname + '.png' )):
					self.iconFileName = fname + '.png'
					self.buttonGraphics = buttonGraphics( fileDir, self.iconFileName )
				else:
					self.iconFileName = None
					self.buttonGraphics = None
			else:
				raise unknownFileNameFormat()
		else:
			raise unknownFileNameFormat()

	def getFullScriptAddress( self ):
		return op.join( self.filePath, self.fileName )

	def getScriptBaseName( self ):
		return self.scriptGroupName + '_' + self.cmdName

	@staticmethod
	def extractParameter( param, file ):
		finder = re.compile( param + '\s*\=\s*\'*\"*(.+?)[\'\"]', flags = re.DOTALL | re.IGNORECASE )
		with open( file, 'r') as f:
			values = finder.findall( f.read() )
			if values:
				return values[0].replace('\\n', '\n')
			else:
				return None

class pyRevitUISession():
	def __init__( self, homeDirectory, settingsClass ):
		self.loadedPyRevitScripts = []
		self.loadedPyRevitAssemblies = []
		self.pyRevitScriptPanels = []
		self.pyRevitScriptGroups = []
		self.pyRevitScriptCommands = []
		self.pyRevitScriptTabs = []
		self.homeDir = homeDirectory
		self.userTempFolder = findUserTempDirectory()
		self.commandLoaderClass = None
		self.commandLoaderAssembly = None
		self.newAssemblyLocation = None
		self.settings = settingsClass
		self.revitVersion = __revit__.Application.VersionNumber
		
		report('Home Directory is: {0}'.format( self.homeDir ))
		
		#collect information about previously loaded assemblies
		report('Initializing python script loader...')
		res = self.findCommandLoaderClass()
		if res:
			self.findLoadedPyRevitAssemblies()
			self.cleanupOldAssemblies()

			# find commands, script groups and assign commands
			self.createReloadButton( self.homeDir )
			report('Searching for tabs, panels, groups, and scripts...')
			self.findScriptTabs( self.homeDir )

			#create assembly dll
			report('Building script executer assembly...')
			self.createAssmebly()

			#setting up UI
			report('Executer assembly saved. Creating pyRevit UI.')
			self.createPyRevitUI()
		else:
			report('pyRevit load failed...')

	def cleanupOldAssemblies( self ):
		revitInstances = list( Process.GetProcessesByName('Revit') )
		revitVersionStr = self.getRevitVersionStr()
		if len(revitInstances) > 1:
			reportv('Multiple Revit instance are running...Skipping DLL Cleanup')
		elif len(revitInstances) == 1 and not self.isReloadingScripts():
			reportv('Cleaning up old DLL files...')
			files = os.listdir( self.userTempFolder )
			for f in files:
				if f.startswith( self.settings.pyRevitAssemblyName + revitVersionStr ):
					try:
						os.remove( op.join( self.userTempFolder, f ))
						reportv('Existing .Dll Removed: {0}'.format( f ))
					except:
						reportv('Error deleting .DLL file: {0}'.format( f ))

	def isReloadingScripts( self ):
		return len( self.loadedPyRevitAssemblies ) > 0

	def getRevitVersionStr( self ):
		return str( self.revitVersion )

	def findCommandLoaderClass( self ):
		#tries to find the revitpythonloader assembly first
		reportv('Asking Revit for RevitPythonLoader Command Loader class...')
		for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
			if 'RevitPythonLoader' in loadedAssembly.FullName:
				reportv('RPL Assembly found: {0}'.format( loadedAssembly.GetName().FullName ))
				self.commandLoaderClass = loadedAssembly.GetType('RevitPythonLoader.CommandLoaderBase')
				self.commandLoaderAssembly = loadedAssembly
				return True

		#if revitpythonloader doesn't exist tries to find the revitpythonshell assembly
		reportv('Can not find RevitPythonLoader. Asking Revit for RevitPythonShell Command Loader class instead...')
		for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
			if 'RevitPythonShell' in loadedAssembly.FullName:
				reportv('RPS Assembly found: {0}'.format( loadedAssembly.GetName().FullName ))
				self.commandLoaderClass = loadedAssembly.GetType('RevitPythonShell.CommandLoaderBase')
				self.commandLoaderAssembly = loadedAssembly
				return True
		
		reportv('Can not find RevitPythonShell either. Aborting load...')
		self.commandLoaderClass = None
		self.commandLoaderAssembly = None
		return None

	def findLoadedPyRevitAssemblies( self ):
		reportv('Asking Revit for previously loaded pyRevit assemblies...')
		for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
			if self.settings.pyRevitAssemblyName in loadedAssembly.FullName:
				reportv('Existing assembly found: {0}'.format( loadedAssembly.FullName ))
				self.loadedPyRevitAssemblies.append( loadedAssembly )
				self.loadedPyRevitScripts.extend( [ ct.Name for ct in loadedAssembly.GetTypes() ] )

	def findScriptCommands( self, tabDir, tabName):
		reportv('Searching tab folder for scripts...')
		files = sorted( os.listdir( tabDir ))
		for f in files:
			#creating scriptCommands
			fname, fext = op.splitext( op.basename( f ))
			if '.py' == fext.lower():
				try:
					cmd = ScriptCommand( tabDir, f, tabName)
					self.pyRevitScriptCommands.append( cmd )
				except unknownFileNameFormat:
					reportv('Can not recognize name pattern. skipping: {0}'.format( f ))
					continue
				except:
					reportv('Something is wrong. skipping: {0}'.format( f ))
					continue

		if not len( self.pyRevitScriptCommands ) > 0:
			report('No Scripts found...')

	def findScriptGroups( self, tabDir, tabName):
		reportv('Searching content folder for script groups ...')
		self.findScriptCommands( tabDir, tabName )
		files = os.listdir( tabDir )
		for f in files:
			#creating ScriptGroup list and adopting ScriptCommands
			fname, fext = op.splitext( op.basename( f ))
			if '.png' == fext.lower():
				try:
					scriptGroup = ScriptGroup( tabDir, f, tabName)
					scriptGroup.adoptCommands( self.pyRevitScriptCommands )
					self.pyRevitScriptGroups.append( scriptGroup )
				except unknownFileNameFormat:
					if f in [x.iconFileName for x in self.pyRevitScriptCommands ]:
						reportv('Skipping script icon file: {0}'.format( f ))
						continue
					else:
						reportv('Can not recognize name pattern. skipping: {0}'.format( f ))
						continue
				except unknownAssembly:
					reportv('Unknown assembly error. Skipping: {0}'.format( f ))
					continue

	def findScriptPanels( self, tabDir, tabName ):
		reportv('Searching content folder for script panels ...')
		self.findScriptGroups( tabDir, tabName )
		files = os.listdir( tabDir )
		for f in files:
			#creating ScriptPanel list and adopting ScriptGroups
			fname, fext = op.splitext( op.basename( f ))
			if '.png' == fext.lower():
				try:
					scriptPanel = ScriptPanel( tabDir, f, tabName )
					collectedScriptPanels = [ (x.panelName, x.tabName) for x in self.pyRevitScriptPanels]
					if (scriptPanel.panelName, scriptPanel.tabName) not in collectedScriptPanels:
						scriptPanel.adoptGroups( self.pyRevitScriptGroups )
						self.pyRevitScriptPanels.append( scriptPanel )
				except unknownFileNameFormat:
					if f in [x.iconFileName for x in self.pyRevitScriptCommands ]:
						reportv('Skipping script icon file: {0}'.format( f ))
						continue
					else:
						reportv('Can not recognize name pattern. skipping: {0}'.format( f ))
						continue

	def findScriptTabs( self, rootDir ):
		for dirName in os.listdir( rootDir ):
			fullTabPath = op.join( rootDir, dirName )
			if op.isdir( fullTabPath ) and ( '_' not in dirName ):
				reportv('\n')
				reportv('Searching fo scripts under: {0}'.format( fullTabPath ), title = True)
				tabNames = [x.tabName for x in self.pyRevitScriptTabs ]
				if dirName not in tabNames:
					scriptTab = ScriptTab( dirName, fullTabPath )
					self.findScriptPanels( fullTabPath, scriptTab.tabName )
					reportv('\nTab found: {0}'.format( scriptTab.tabName ))
					scriptTab.adoptPanels( self.pyRevitScriptPanels )
					self.pyRevitScriptTabs.append( scriptTab )
					sys.path.append( fullTabPath )
					reportv('\n')
			else:
				continue

	def createReloadButton( self, rootDir ):
		reportv('Creating "Reload Scripts" button...')
		for fname in os.listdir( rootDir ):
			fullTabPath = op.join( rootDir, fname )
			if not op.isdir( fullTabPath ) and self.settings.userSetupKeyword in fname:
				try:
					cmd = ScriptCommand( rootDir, fname, self.settings.masterTabName )
					self.pyRevitScriptCommands.append( cmd )
					reportv('Reload button added.\n')
				except Exception as e:
					reportv('\nCould not create reload command.\n')
					# report(e)
					continue

	def createAssmebly( self ):
		# create DLL folder
		# dllFolder = Path.Combine( self.homeDir, self.settings.pyRevitAssemblyName )
		# if not os.path.exists( dllFolder ):
			# os.mkdir( dllFolder )
		dllFolder = self.userTempFolder
		# make assembly name
		generatedAssemblyName = self.settings.pyRevitAssemblyName + self.getRevitVersionStr() + datetime.now().strftime('_%y%m%d%H%M%S')
		dllName = generatedAssemblyName + '.dll'
		# create assembly
		windowsAssemblyName = AssemblyName( Name = generatedAssemblyName, Version = Version(1,0,0,0))
		reportv('Generated assembly name for this session: {0}'.format( generatedAssemblyName ))
		reportv('Generated windows assembly name for this session: {0}'.format( windowsAssemblyName ))
		reportv('Generated DLL name for this session: {0}'.format( dllName ))
		assemblyBuilder = AppDomain.CurrentDomain.DefineDynamicAssembly( windowsAssemblyName, AssemblyBuilderAccess.RunAndSave, dllFolder)
		moduleBuilder = assemblyBuilder.DefineDynamicModule( generatedAssemblyName , dllName )
		
		# create command classes
		for cmd in self.pyRevitScriptCommands:
			typebuilder = moduleBuilder.DefineType( cmd.className, TypeAttributes.Class | TypeAttributes.Public, self.commandLoaderClass )
			
			# add RegenerationAttribute to type
			regenerationConstrutorInfo = clr.GetClrType(RegenerationAttribute).GetConstructor( Array[Type]((RegenerationOption,)) )              
			regenerationAttributeBuilder = CustomAttributeBuilder(regenerationConstrutorInfo, Array[object]((RegenerationOption.Manual,)))
			typebuilder.SetCustomAttribute(regenerationAttributeBuilder)

			# add TransactionAttribute to type
			transactionConstructorInfo = clr.GetClrType(TransactionAttribute).GetConstructor( Array[Type]((TransactionMode,)) )
			transactionAttributeBuilder = CustomAttributeBuilder(transactionConstructorInfo, Array[object]((TransactionMode.Manual,)))
			typebuilder.SetCustomAttribute(transactionAttributeBuilder)
			
			#call base constructor with script path
			ci = self.commandLoaderClass.GetConstructor(Array[Type]((str,)))
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
		reportv('Searching for existing pyRevit panels...')
		for scriptTab in self.pyRevitScriptTabs:
			#creates pyRevitRibbonPanels for existing or newly created panels
			try:
				pyRevitRibbonPanels = {p.Name:p for p in __revit__.GetRibbonPanels( scriptTab.tabName )}
			except:
				if scriptTab.hasScriptCommands():
					reportv('Creating pyRevit ribbon...')
					pyRevitRibbon = __revit__.CreateRibbonTab( scriptTab.tabName )
					pyRevitRibbonPanels = {p.Name:p for p in __revit__.GetRibbonPanels( scriptTab.tabName )}
				else:
					reportv('pyRevit ribbon found but does not include any scripts. Skipping: {0}'.format( scriptTab.tabName ))
			reportv('Searching for panels...')
			for panel in scriptTab.getSortedScriptPanels():
				if panel.panelName in pyRevitRibbonPanels.keys():
					reportv('Existing panel found: {0}'.format( panel.panelName ))
					scriptTab.pyRevitUIPanels[ panel.panelName ] = pyRevitRibbonPanels[ panel.panelName ]
					scriptTab.pyRevitUIButtons[ panel.panelName ] = list( pyRevitRibbonPanels[ panel.panelName ].GetItems() )
				else:
					reportv('Creating scripts panel: {0}'.format( panel.panelName ))
					newPanel = __revit__.CreateRibbonPanel( scriptTab.tabName, panel.panelName )
					scriptTab.pyRevitUIPanels[ panel.panelName ] = newPanel
					scriptTab.pyRevitUIButtons[ panel.panelName ] = []

	def createUI( self ):
		newButtonCount = updatedButtonCount = 0
		for scriptTab in self.pyRevitScriptTabs:
			for scriptPanel in scriptTab.getSortedScriptPanels():
				pyRevitRibbonPanel = scriptTab.pyRevitUIPanels[ scriptPanel.panelName ]
				pyRevitRibbonItemsDict = {b.Name:b for b in scriptTab.pyRevitUIButtons[ scriptPanel.panelName ]}
				reportv('Creating\\Updating ribbon items for panel: {0}'.format( scriptPanel.panelName ))
				for scriptGroup in scriptPanel.getSortedScriptGroups( scriptPanel.panelName ):
					#PulldownButton or SplitButton
					if scriptGroup.groupType == self.settings.pulldownButtonTypeName or scriptGroup.groupType == self.settings.splitButtonTypeName:
						#PulldownButton
						if scriptGroup.groupType == self.settings.pulldownButtonTypeName:
							if scriptGroup.groupName not in pyRevitRibbonItemsDict:
								reportv('\tCreating pulldown button group: {0}'.format( scriptGroup.groupName ))
								ribbonItem = pyRevitRibbonPanel.AddItem( PulldownButtonData( scriptGroup.groupName, scriptGroup.groupName ))
							else:
								reportv('\tUpdating pulldown button group: {0}'.format( scriptGroup.groupName ))
								ribbonItem = pyRevitRibbonItemsDict.pop( scriptGroup.groupName )

						#SplitButton
						elif scriptGroup.groupType == self.settings.splitButtonTypeName:
							if scriptGroup.groupName not in pyRevitRibbonItemsDict.keys():
								reportv('\tCreating split button group: {0}'.format( scriptGroup.groupName ))
								ribbonItem = pyRevitRibbonPanel.AddItem( SplitButtonData( scriptGroup.groupName, scriptGroup.groupName ))
							else:
								reportv('\tUpdating split button group: {0}'.format( scriptGroup.groupName ))
								ribbonItem = pyRevitRibbonItemsDict.pop( scriptGroup.groupName )

						ribbonItem.Image = scriptGroup.buttonGraphics.smallIcon
						ribbonItem.LargeImage = scriptGroup.buttonGraphics.icon
						existingRibbonItemPushButtonsDict = {b.ClassName:b for b in ribbonItem.GetItems()}

						for cmd in scriptGroup.commands:
							if cmd.className not in existingRibbonItemPushButtonsDict:
								reportv('\t\tCreating push button: {0}'.format( cmd.className ))
								buttonData = PushButtonData( cmd.className, cmd.cmdName, self.newAssemblyLocation , cmd.className )
								buttonData.ToolTip = cmd.tooltip
								if cmd.buttonGraphics:
									buttonData.LargeImage = cmd.buttonGraphics.icon
								else:
									buttonData.LargeImage = scriptGroup.buttonGraphics.icon
								ribbonItem.AddPushButton( buttonData )
								newButtonCount += 1
							else:
								reportv('\t\tUpdating push button: {0}'.format( cmd.className ))
								pushButton = existingRibbonItemPushButtonsDict.pop( cmd.className )
								pushButton.ToolTip = cmd.tooltip
								pushButton.Enabled = True
								if cmd.buttonGraphics:
									pushButton.LargeImage = cmd.buttonGraphics.icon
								else:
									pushButton.LargeImage = scriptGroup.buttonGraphics.icon
								updatedButtonCount += 1
						for orphanedButtonName, orphanedButton in existingRibbonItemPushButtonsDict.items():
							reportv('\tDisabling orphaned button: {0}'.format( orphanedButtonName ))
							orphanedButton.Enabled = False

					#StackedButtons
					elif scriptGroup.groupType == self.settings.stackedThreeTypeName:
						reportv('\tCreating\\Updating 3 stacked buttons: {0}'.format( scriptGroup.groupType ))
						stackCommands = []
						for cmd in scriptGroup.commands:
							if cmd.className not in pyRevitRibbonItemsDict:
								reportv('\t\tCreating stacked button: {0}'.format( cmd.className ))
								buttonData = PushButtonData( cmd.className, cmd.cmdName, self.newAssemblyLocation , cmd.className )
								buttonData.ToolTip = cmd.tooltip
								if cmd.buttonGraphics:
									buttonData.Image = cmd.buttonGraphics.smallIcon
								else:
									buttonData.Image = scriptGroup.buttonGraphics.smallIcon
								stackCommands.append( buttonData )
								newButtonCount += 1
							else:
								reportv('\t\tUpdating stacked button: {0}'.format( cmd.className ))
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
								reportv('\tCreating push button: {0}'.format( cmd.className ))
								ribbonItem = pyRevitRibbonPanel.AddItem( PushButtonData( cmd.className, scriptGroup.groupName, self.newAssemblyLocation , cmd.className ))
								newButtonCount += 1
							else:
								reportv('\tUpdating push button: {0}'.format( cmd.className ))
								ribbonItem = pyRevitRibbonItemsDict.pop( cmd.className )
								ribbonItem.AssemblyName = self.newAssemblyLocation
								ribbonItem.ClassName = cmd.className
								ribbonItem.Enabled = True
								updatedButtonCount += 1
							ribbonItem.ToolTip = cmd.tooltip
							ribbonItem.Image = scriptGroup.buttonGraphics.smallIcon
							ribbonItem.LargeImage = scriptGroup.buttonGraphics.icon
						except:
							reportv('\tPushbutton has no associated scripts. Skipping {0}'.format( scriptGroup.sourceFile ))
							continue

					#SmartButton
					elif scriptGroup.groupType == self.settings.smartButtonTypeName and not scriptGroup.isLinkButton():
						try:
							cmd = scriptGroup.commands.pop()
							if cmd.className not in pyRevitRibbonItemsDict:
								reportv('\tCreating push button: {0}'.format( cmd.className ))
								ribbonItem = pyRevitRibbonPanel.AddItem( PushButtonData( cmd.className, scriptGroup.groupName, self.newAssemblyLocation , cmd.className ))
								newButtonCount += 1
							else:
								reportv('\tUpdating push button: {0}'.format( cmd.className ))
								ribbonItem = pyRevitRibbonItemsDict.pop( cmd.className )
								ribbonItem.AssemblyName = self.newAssemblyLocation
								ribbonItem.ClassName = cmd.className
								ribbonItem.Enabled = True
								updatedButtonCount += 1
							ribbonItem.ToolTip = cmd.tooltip
							importedScript = __import__( cmd.getScriptBaseName() )
							importedScript.selfInit( __revit__, cmd.getFullScriptAddress(), ribbonItem )
						except:
							reportv('\tSmart button has no associated scripts. Skipping {0}'.format( scriptGroup.sourceFile ))
							continue

					#LinkButton
					elif scriptGroup.groupType == self.settings.linkButtonTypeName and scriptGroup.isLinkButton():
						if scriptGroup.groupName not in pyRevitRibbonItemsDict:
							reportv('\tCreating push button link to other assembly: {0}'.format( scriptGroup.groupName ))
							ribbonItem = pyRevitRibbonPanel.AddItem( PushButtonData( scriptGroup.groupName, scriptGroup.groupName, scriptGroup.assemblyLocation , scriptGroup.assemblyName + '.' + scriptGroup.assemblyClassName ))
							newButtonCount += 1
						else:
							reportv('\tUpdating push button link to other assembly: {0}'.format( scriptGroup.groupName ))
							ribbonItem = pyRevitRibbonItemsDict.pop( scriptGroup.groupName )
							ribbonItem.AssemblyName = scriptGroup.assemblyLocation
							ribbonItem.ClassName = scriptGroup.assemblyName + '.' + scriptGroup.assemblyClassName
							ribbonItem.Enabled = True
							updatedButtonCount += 1
						ribbonItem.Image = scriptGroup.buttonGraphics.smallIcon
						ribbonItem.LargeImage = scriptGroup.buttonGraphics.icon

				#now disable all orphaned buttons in this panel
				for orphanedRibbonItemName, orphanedRibbonItem in pyRevitRibbonItemsDict.items():
					reportv('\tDisabling orphaned ribbon item: {0}'.format( orphanedRibbonItemName ))
					orphanedRibbonItem.Enabled = False

		#final report
		reportv('\n\n')
		report('{0} buttons created...\n{1} buttons updated...\n\n'.format( newButtonCount, updatedButtonCount ))

	def createPyRevitUI( self ):
		#setting up UI
		reportv('Now setting up ribbon, panels, and buttons...')
		self.createOrFindPyRevitPanels()
		reportv('Ribbon tab and panels are ready. Creating script groups and command buttons...')
		self.createUI()
		reportv('All UI items have been added...')

#MAIN
__window__.Width = 1100
#find pyRevit home directory and initialize current session
thisSession = pyRevitUISession( findHomeDirectory(), pyRevitUISettings() )

