from Qt import QtGui, QtCore, QtWidgets, QtCompat
from Qt.QtWidgets import QDialog
from utils import toPyObject, getUiFile

from . import extraWidgets
import codecs, re
import os

from maya import cmds, mel
from xml.dom import minidom
import xml.etree.ElementTree as ET



class StoreXml(QDialog):
	storewin = True

	def closeEvent (self, event):
		for el in self.parentWindow.toRestore:
			el.setEnabled (True)
		super(StoreXml, self).closeEvent(event)

	def setUpFilePicker (self, store = True):		
		# prepare the file picker
		with extraWidgets.toggleBlockSignals ([self.uiXmlStoreFile]) : 
			self.uiXmlStoreFile.setFilePath("")

		sceneName = cmds.file(q=True,sceneName=True)
		splt = sceneName.split("/")
		startDir = "/".join(splt [:-1])	
		self.uiXmlStoreFile._defaultLocation = startDir

		if store : 
			self.storewin = True
			self.uiDoStoreBTN.setText ("store xml")
			self.uiXmlStoreFile.pyOpenFile = False
			self.uiXmlStoreFile.pyCaption = QtCore.QString(u'Store xml...')
			self.uiDoStoreBTN.setEnabled (False)
			self.setWindowTitle ("Store xml file")		

		else : 
			self.storewin = False
			self.uiDoStoreBTN.setText ("restore selected frames")
			self.uiXmlStoreFile.pyOpenFile = True
			self.uiXmlStoreFile.pyCaption = QtCore.QString(u'select file to load from...')			
			self.setWindowTitle ("Restore from xml file")		


		self.uiAllFramesTW.setEnabled (self.storewin)	
		self.uiAllFramesTW.clear()
		self.uiAllFramesTW.setColumnCount(3)
		self.uiAllFramesTW.setHeaderLabels(["blurSculpt", u"pose", "frame", "isEmpty"])		
		self.setTreePretty ()

	def refreshTree(self, blurNode) :
		# fill the tree of frames

		dicVal = {"blurNode" : blurNode}
		posesIndices = map(int,cmds.getAttr  (blurNode+".poses",mi=True))

		# first store positions
		for logicalInd in posesIndices:
			dicVal ["indPose"] = logicalInd

			thePose = cmds.getAttr ("{blurNode}.poses[{indPose}].poseName".format (**dicVal))
			listDeformationsIndices = cmds.getAttr ("{blurNode}.poses[{indPose}].deformations".format (**dicVal), mi=True)
			if not listDeformationsIndices : 
				continue

			toAdd = []
			for logicalFrameIndex  in listDeformationsIndices : 
				dicVal["frameInd"] = logicalFrameIndex
				frame = cmds.getAttr ("{blurNode}.poses[{indPose}].deformations[{frameInd}].frame".format (**dicVal))
				mvtIndices =  cmds.getAttr ("{blurNode}.poses[{indPose}].deformations[{frameInd}].vectorMovements".format (**dicVal), mi=True)

				frameItem =  QtGui.QTreeWidgetItem()
				frameItem.setText (0, str(blurNode))
				frameItem.setText (1, str(thePose))
				frameItem.setText (2, str(frame))
				if not mvtIndices : 
					frameItem.setText (3, u"\u00D8")
					frameItem.setTextAlignment(3 , QtCore.Qt.AlignCenter )
				
				frameItem.setData (0, QtCore.Qt.UserRole, "{blurNode}.poses[{indPose}].deformations[{frameInd}]".format (**dicVal)) 
				toAdd.append ((frame, frameItem))

			for frame, frameItem in sorted (toAdd) :
				self.uiAllFramesTW.addTopLevelItem (frameItem)
		self.setTreePretty ()

	def setTreePretty (self) :
		self.uiAllFramesTW.setEnabled (True)
		for i in range (4) : self.uiAllFramesTW.resizeColumnToContents(i)
		vh = self.uiAllFramesTW.header ()
		self.uiAllFramesTW.selectAll()
		for i in range (4):
			wdt = self.uiAllFramesTW.columnWidth (i)
			self.uiAllFramesTW.setColumnWidth (i,wdt + 10)

	def buttonAction(self) : 
		if self.storewin : self.doStoreXml ()
		else : 
			self.doRetrieveSelection ()
			QtCore.QTimer.singleShot (0, self.parentWindow.refresh)   		

		self.close ()

	def doRetrieveSelection (self) :
		selectedItems = self.uiAllFramesTW.selectedItems () 
		dicFrames = {}
		listPoses = []
		for frameItem  in  selectedItems:
			frame_tag = frameItem.data (0, QtCore.Qt.UserRole).toPyObject()
			pose_tag = frameItem.data (1, QtCore.Qt.UserRole).toPyObject()
			poseName = pose_tag .get ("poseName")

			if poseName not in dicFrames :
				dicFrames [poseName] = [frame_tag]
				listPoses .append ( pose_tag )
			else : 
				dicFrames [poseName].append(frame_tag)

		print "do retrieve done"
		with extraWidgets.WaitCursorCtxt ():			
			self.retrieveblurXml ( dicFrames, listPoses)



	def retrieveblurXml (self, dicFrames, listPoses) : 		
		dicVal = {"blurNode" : self.parentWindow.currentBlurNode}

		pses = cmds.getAttr  (self.parentWindow.currentBlurNode+".poses",mi=True)
		dicPoses = {} 		
		newInd = 0
		if pses:
			posesIndices = map(int,pses)			
			for logicalInd in posesIndices:
				dicVal ["indPose"] = logicalInd
				poseName = cmds.getAttr ("{blurNode}.poses[{indPose}].poseName".format (**dicVal))
				dicPoses [poseName] = logicalInd
			newInd = max (posesIndices) + 1


		for pose_tag in listPoses:
			poseName = pose_tag .get ("poseName")
			print poseName 
			# access the pose Index
			if poseName not in dicPoses: # create it
				dicVal ["indPose"] = newInd
				cmds.setAttr  ("{blurNode}.poses[{indPose}].poseName".format (**dicVal), poseName,  type = "string")
				dicPoses[poseName] = newInd					
				newInd += 1
				# do the connection and type
				poseEnabled = pose_tag .get ("poseEnabled" ) == "True" 
				poseGain = float(pose_tag .get ("poseGain"))
				poseOffset = float(pose_tag .get ("poseOffset"))
				cmds.setAttr  ("{blurNode}.poses[{indPose}].poseEnabled".format (**dicVal), poseEnabled)
				cmds.setAttr  ("{blurNode}.poses[{indPose}].poseGain".format (**dicVal), poseGain)
				cmds.setAttr  ("{blurNode}.poses[{indPose}].poseOffset".format (**dicVal), poseOffset)

				deformType = int(pose_tag .get ("deformType"))
				cmds.setAttr ("{blurNode}.poses[{indPose}].deformationType".format (**dicVal), deformType)					
				poseMatrixConn = pose_tag .get ("poseMatrix")
				if cmds.objExists (poseMatrixConn ) : 
					try : 
						cmds.connectAttr (poseMatrixConn,"{blurNode}.poses[{indPose}].poseMatrix".format (**dicVal), f=True)
					except : pass
			else : 
				dicVal ["indPose"] = dicPoses [poseName]
		
		for poseName, listFrameTags in dicFrames.items(): 				
			dicVal ["indPose"] = dicPoses [poseName]
			dicFrames = {} 	
			newFrameInd = 0
			listDeformationsIndices = cmds.getAttr ("{blurNode}.poses[{indPose}].deformations".format (**dicVal), mi=True)
			if listDeformationsIndices : 
				for logicalFrameIndex  in listDeformationsIndices : 
					dicVal ["frameInd"] = logicalFrameIndex
					frame = cmds.getAttr ("{blurNode}.poses[{indPose}].deformations[{frameInd}].frame".format (**dicVal))
					dicFrames [frame]= logicalFrameIndex
				newFrameInd = max (listDeformationsIndices) + 1

			for frame_tag in listFrameTags : 
				frame = float(frame_tag .get ("frame") )
				if frame not in dicFrames : 
					dicVal["frameInd"] = newFrameInd
					newFrameInd +=1

					gain = float(frame_tag .get ("gain") )
					offset = float(frame_tag .get ("offset"))
					frameEnabled = frame_tag .get ("frameEnabled") == "True"
					cmds.setAttr ("{blurNode}.poses[{indPose}].deformations[{frameInd}].gain".format (**dicVal), gain)
					cmds.setAttr ("{blurNode}.poses[{indPose}].deformations[{frameInd}].offset".format (**dicVal), offset)								
					cmds.setAttr ("{blurNode}.poses[{indPose}].deformations[{frameInd}].frameEnabled".format (**dicVal), frameEnabled)
					cmds.setAttr ("{blurNode}.poses[{indPose}].deformations[{frameInd}].frame".format (**dicVal), frame)
				else : 
					dicVal["frameInd"] = dicFrames [frame]
					# first clear
					frameName = "{blurNode}.poses[{indPose}].deformations[{frameInd}]".format (**dicVal)
					mvtIndices =  cmds.getAttr (frameName+".vectorMovements", mi=True)
					if mvtIndices: 
						mvtIndices = map (int, mvtIndices )
						for indVtx in mvtIndices:
							cmds.removeMultiInstance(frameName+".vectorMovements[{0}]".format (indVtx), b=True)

				vector_tag = frame_tag.getchildren ()[0]
				for vectag in vector_tag.getchildren ():					
					index =int(vectag.get ("index" ))
					dicVal["vecInd"] = index
					value = vectag.get ("value")
					floatVal = map (float, value [1:-1].split(", "))
					cmds.setAttr ("{blurNode}.poses[{indPose}].deformations[{frameInd}].vectorMovements[{vecInd}]".format (**dicVal), *floatVal)



	def doStoreXml (self):
		inputPoseFramesIndices = {}
		selectedItems = self.uiAllFramesTW.selectedItems () 
		destinationFile = str (self.uiXmlStoreFile.filePath())

		if  selectedItems : 
			for frameItem  in  selectedItems:
				fullName = str(frameItem.data (0, QtCore.Qt.UserRole))
				poseInd, frameInd = [int (ind) for ind in re.findall(r'\b\d+\b', fullName)]
				if poseInd not in inputPoseFramesIndices  : 
					inputPoseFramesIndices [poseInd] = [frameInd]
				else : 
					inputPoseFramesIndices [poseInd].append (frameInd)

			with extraWidgets.WaitCursorCtxt ():			
				doc = minidom.Document()
				ALL_tag = doc.createElement("ALL")
				doc.appendChild(ALL_tag )

				created_tag = self.parentWindow.storeInfoBlurSculpt(doc, self.parentWindow.currentBlurNode,inputPoseFramesIndices = inputPoseFramesIndices )
				ALL_tag .appendChild (created_tag )

				with codecs.open(destinationFile, "w", "utf-8") as out:
					doc.writexml(out,indent="\n",addindent="\t",newl="")


	def readXmlFile (self) : 
		with extraWidgets.WaitCursorCtxt ():			
			if os.path.isfile(self.sourceFile ) :             
				tree = ET.parse(self.sourceFile  )
				root = tree.getroot()
				self.refreshTreeFromRoot (root)


	def refreshTreeFromRoot (self, root) :
		for blurNode_tag in root.getchildren():
			blurName = blurNode_tag.get ("name")
			for pose_tag in blurNode_tag.getchildren():
				poseName = pose_tag .get ("poseName")
				toAdd = []
				for frame_tag in pose_tag.getchildren ():
					frame = float(frame_tag .get ("frame") )
					vector_tag = frame_tag.getchildren ()[0]

					frameItem =  QtGui.QTreeWidgetItem()
					frameItem.setText (0, str(blurName))
					frameItem.setText (1, str(poseName))
					frameItem.setText (2, str(frame))
					if not vector_tag.getchildren() : 
						frameItem.setText (3, u"\u00D8")

					toAdd.append ((frame, frameItem))

					frameItem.setData (0, QtCore.Qt.UserRole, frame_tag) 
					frameItem.setData (1, QtCore.Qt.UserRole, pose_tag) 

				for frame, frameItem in sorted (toAdd) :
					self.uiAllFramesTW.addTopLevelItem (frameItem)				

		self.setTreePretty ()

	def fileIsPicked(self):
		print "File is Picked"
		if not self.storewin : 
			self.sourceFile = str (self.uiXmlStoreFile.filePath())
			self.readXmlFile ()
		else : 
			self.uiDoStoreBTN.setEnabled (True)


	#------------------- INIT ----------------------------------------------------
	def __init__(self, parent=None):
		super(StoreXml, self).__init__(parent)
		# load the ui

		#import __main__
		#self.parentWindow = __main__.__dict__["blurDeformWindow"] 		
		#blurdev.gui.loadUi( __file__, self )
		
		QtCompat.loadUi(getUiFile(__file__), self)
		self.parentWindow = parent
		#------------------------


		self.parentWindow.saveXmlWin = self

		self.setWindowFlags (QtCore.Qt.Tool|QtCore.Qt.WindowStaysOnTopHint )
		self.setWindowTitle ("Store xml file")		
		self.uiAllFramesTW.setSelectionMode( QtGui.QAbstractItemView.ExtendedSelection) 
		self.uiAllFramesTW.setAlternatingRowColors(True)

		self.uiDoStoreBTN.clicked.connect ( self.buttonAction )
		self.uiXmlStoreFile.filenameChanged.connect (self.fileIsPicked)

		#filenameChanged

