##
#   :remarks    GUI to work with the blurSculpt plugin
#   
#   :author     [author::email]
#   :author     [author::company]
#   :date       03/22/17
#
from Qt.QtWidgets import QApplication, QSplashScreen, QDialog, QMainWindow

def loadPluginCpp ():	
	from maya  import cmds
	import os

	fileVar = os.path.realpath(__file__)	
	uiFolder, filename = os.path.split(fileVar)
	dicVersionPth = {'2016 Extension 2' : '2016.5',
	'2016' : '2016',
	'2017' : '2017',
	}
	mayaVersion = cmds.about (v=True)
	if mayaVersion in dicVersionPth : 
		if cmds.pluginInfo("blurPostDeform", q=True, loaded=True) : 
			return True
		try :
			cmds.loadPlugin("blurPostDeform") 
			return True
		except : 
			plugPath = os.path.join ( uiFolder, "pluginCPP", dicVersionPth[mayaVersion],"blurPostDeform.mll")
			return cmds.loadPlugin(plugPath) 
	else : 
		cmds.error( "No plugin for maya version ", mayaVersion , " \nFAIL")
	return False

def getQTObject (mayaWindow): 
	from maya import cmds
	if not cmds.window("tmpWidgetsWindow", q=True,ex=True) :
		cmds.window ("tmpWidgetsWindow")    
		cmds.formLayout("qtLayoutObjects")
	for ind, el in enumerate (mayaWindow.children()):
		try : 
			title =el.windowTitle ()
			if title == "tmpWidgetsWindow" :
				break
		except : 
			continue
	return el
	
def runArgileDeformUI():
	from .argile import ArgileDeformDialog
	from maya.cmds import optionVar
	if loadPluginCpp () : 
		mayaWin  = rootWindow()
		rootWin = ArgileDeformDialog (mayaWin, getQTObject(mayaWin))
		rootWin.show()

		vals = optionVar (q="argileDeformWindow")
		if vals : 
			rootWin.move(vals[0], vals[1])
			rootWin.resize(vals[2], vals[3])
		else : 
			rootWin.move (0,0)

def rootWindow():
	"""
	Returns the currently active QT main window
	Only works for QT UI's like Maya
	"""
	# for MFC apps there should be no root window
	window = None
	if QApplication.instance():
		inst = QApplication.instance()
		window = inst.activeWindow()
		# Ignore QSplashScreen's, they should never be considered the root window.
		if isinstance(window, QSplashScreen):
			return None
		# If the application does not have focus try to find A top level widget
		# that doesn't have a parent and is a QMainWindow or QDialog
		if window == None:
			windows = []
			dialogs = []
			for w in QApplication.instance().topLevelWidgets():
				if w.parent() == None:
					if isinstance(w, QMainWindow):
						windows.append(w)
					elif isinstance(w, QDialog):
						dialogs.append(w)
			if windows:
				window = windows[0]
			elif dialogs:
				window = dialogs[0]

		# grab the root window
		if window:
			while True:
				parent = window.parent()
				if not parent:
					break
				if isinstance(parent, QSplashScreen):
					break
				window = parent

	return window
