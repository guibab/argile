# -*- coding: utf-8 -*
##
#   :namespace  argile.argile
#
#   :remarks    GUI to work with the blurSculpt plugin
#   
#   :author     [author::guillaume@blur.com]
#   :author     [author::blur]
#   :date       03/22/17
#


# we import from blurdev.gui vs. QtWidgets becuase there are some additional management features for running the Dialog in multiple environments
#from blurdev.gui import Dialog

#from studio.gui.resource import Icons
from Qt import QtGui, QtCore, QtWidgets, QtCompat
from Qt.QtWidgets import QDialog

from . import extraWidgets, argileAddPose, storeXml
#reload (storeXml)
#reload (extraWidgets)
#reload(blurAddPose)

from functools import partial
from xml.dom import minidom
import xml.etree.ElementTree as ET
import codecs, os
from utils import toPyObject, getUiFile

#import blurdev
from maya import cmds, mel


def getIcon (iconNm):
	fileVar = os.path.realpath(__file__)	
	uiFolder, filename = os.path.split(fileVar)
	iconPth = os.path.join ( uiFolder, "img", iconNm+".png")
	return (QtGui.QIcon (iconPth))

	
_icons = { 
"disconnect":getIcon('disconnect'),
"fromScene":getIcon('fromScene'),
"toFrame":getIcon('toFrame'),
"refresh":getIcon('refresh'),
"publish":getIcon('publish'),
"Add" : getIcon('Add'), 
"Delete" : getIcon ('Delete'),
"empty" :  getIcon ('empty'),
"cancelEdit" : getIcon ('cancelEdit'),
"edit" : getIcon (r'edit'),
"gear" : getIcon (r'gear'),
"backUp" : getIcon ('backUp'),
"restore" : getIcon ('restore'),
"addFrame" : getIcon ('addFrame')
}


def orderMelList (listInd, onlyStr=True):
	#listInd = [49, 60, 61, 62, 80, 81, 82, 83, 100, 101, 102, 103, 113, 119, 120, 121, 138, 139, 140, 158, 159, 178, 179, 198, 230, 231, 250, 251, 252, 270, 271, 272, 273, 274, 291, 292, 293, 319, 320, 321, 360,361,362]
	listIndString = []
	listIndStringAndCount = []
	
	it = iter (listInd )    
	currentValue = it.next () 
	while True:
		try:
			firstVal = currentValue 
			theVal = firstVal
			while currentValue == theVal : 
				currentValue = it.next()
				theVal+=1            
			theVal-=1
			if firstVal != theVal :theStr = "{0}:{1}".format (firstVal, theVal )
			else : theStr = str(firstVal)
			listIndString .append (theStr)
			listIndStringAndCount .append ((theStr,theVal - firstVal + 1))
			
		except StopIteration:
			if firstVal != theVal :theStr = "{0}:{1}".format (firstVal, theVal )
			else : theStr = str(firstVal)
			listIndString .append (theStr)
			listIndStringAndCount .append ((theStr,theVal - firstVal + 1))        
			break
	if onlyStr : return listIndString
	else : return listIndStringAndCount


class ArgileDeformDialog(QDialog):
	addTimeLine = True

	currentBlurNode = ""
	currentGeom = ""
	currentPose = ""

	def removeSelectedVerticesFromFrame (self) :
		selectedVertices = cmds.ls (sl=True, fl=True) 
		if not selectedVertices : return
		verticesIndToDelete = [int(el.split("[")[-1].split("]")[0]) for el in selectedVertices  if el.startswith (self.currentGeom)]
		if not verticesIndToDelete : return
		selectedFrames = self.uiFramesTW.selectedItems()
		if not selectedFrames: return
		for frameItem in selectedFrames:
			frameName=  str(frameItem.data (0, QtCore.Qt.UserRole))
			mvtIndices =  cmds.getAttr (frameName+".vectorMovements", mi=True)
			if mvtIndices: 
				mvtIndices = map (int, mvtIndices )
				toDeleteSet = set (verticesIndToDelete).intersection (set (mvtIndices ) )
				for indVtx in toDeleteSet:
					cmds.removeMultiInstance(frameName+".vectorMovements[{0}]".format (indVtx), b=True)

	def getListDeformationFrames (self) :
		poseName = cmds.getAttr (self.currentPose+".poseName")
		defIndices = cmds.getAttr (self.currentPose+".deformations", mi=True)
		if not defIndices : defIndices = []
		listDeformationsIndices = map(int,defIndices)        
		listDeformationsFrame =	[cmds.getAttr (self.currentPose+".deformations[{0}].frame".format (ind ) ) for ind in listDeformationsIndices]

		#listDeformationsFrame = cmds.blurSculpt (self.currentBlurNode,query = True,listFrames = True, poseName=str(poseName) )
		return listDeformationsFrame

	#---------------- All the Adds --------------------------------------------------------------
	def addDeformer (self) :
		with extraWidgets.WaitCursorCtxt ():
			newBlurSculpt = cmds.blurSculpt()		
			self.currentBlurNode = newBlurSculpt		
			geom = self.getGeom (self.currentBlurNode, transform = True) 		
			self.currentGeom = geom
			self.currentPose = ""
			self.refresh()

	def addNewPose (self, poseName, local = False, poseTransform = "", withRefresh = True):
		#geom, = cmds.listConnections (currentBlurNode, s=False, d=True, type = "mesh")
		dicCmd = {"poseName" : poseName, "addPose":True}

		if local and poseTransform.strip() not in ["N/A", ""] : 
			poseTransformExists = cmds.ls (poseTransform)
			if poseTransformExists : 
				dicCmd ["poseTransform"] = poseTransform

		cmds.blurSculpt (self.currentBlurNode,**dicCmd)

		poseList = cmds.getAttr (self.currentBlurNode+".poses", mi=True)
		self.currentPose = "{0}.poses[{1}]".format ( self.currentBlurNode, max(poseList))

		deformationType = 0 if local else 1 # maya type
		cmds.setAttr (self.currentPose+".deformationType",deformationType )		

		if withRefresh : self.refreshListPoses (selectLast = True)
		#self.selectPose (poseName)

	def doDuplicate (self ):
		frameIndex = float(self.clickedItem.text (0))
		result = cmds.promptDialog(
				title='Duplicate Frame',
				message='Enter new Frame:',
				button=['OK', 'Cancel'],
				defaultButton='OK',
				cancelButton='Cancel',
				dismissString='Cancel')

		if result == 'OK':
			text = cmds.promptDialog(query=True, text=True)
			try : 
				newTime = float (text)
			except :
				return
			self.duplicateFrame (frameIndex, newTime)

	def duplicateFrame (self,prevTime, currTime):
		with extraWidgets.WaitCursorCtxt ():		
			poseName = cmds.getAttr (self.currentPose+".poseName")
			listDeformationsIndices = map(int,cmds.getAttr (self.currentPose+".deformations", mi=True))        

			dicVal = {"pose" : self.currentPose}

			listDeformationsFrame = {}
			for ind in listDeformationsIndices : 
				dicVal ["ind"] = ind
				frame = cmds.getAttr ("{pose}.deformations[{ind}].frame".format (**dicVal))
				listDeformationsFrame [frame ] = ind

			if prevTime not in listDeformationsFrame : return
			oldIndex = listDeformationsFrame[prevTime]

			dicVal ["frame"] = max(listDeformationsIndices)+1
			dicVal ["prevFrame"] = oldIndex

			#currTime = cmds.currentTime (q=True)

			for att in ["gain", "offset", "frameEnabled"] : 
				val = cmds.getAttr  ("{pose}.deformations[{prevFrame}].".format (**dicVal)+att)
				cmds.setAttr ("{pose}.deformations[{frame}].".format (**dicVal)+att, val)
			cmds.setAttr ("{pose}.deformations[{frame}].frame".format (**dicVal),currTime)


			indicesVectorMvt = cmds.getAttr  ("{pose}.deformations[{prevFrame}].vectorMovements".format (**dicVal), mi=True)
			if indicesVectorMvt:
				for ind in indicesVectorMvt:
					dicVal ["vecInd"] = ind
					val,= cmds.getAttr  ("{pose}.deformations[{prevFrame}].vectorMovements[{vecInd}]".format (**dicVal))
					cmds.setAttr  ("{pose}.deformations[{frame}].vectorMovements[{vecInd}]".format (**dicVal), *val)		

		QtCore.QTimer.singleShot (0, partial (self.refresh ,selectTime = True, selTime =currTime)   )		


	def addNewFrame (self) :        
		cmds.selectMode (object=True)
		selection = cmds.ls (sl=True)
		if len (selection)!=1 : 
			if cmds.objExists (self.resForDuplicate):
				meshToAddAsFrame = self.resForDuplicate	
			else : 
				cmds.confirmDialog (m="error select only one mesh")
				return		
		else : 
			meshToAddAsFrame = selection[0]
			if self.keepShapes : 
				self.resForDuplicate = meshToAddAsFrame # keep for later renaming 

		if meshToAddAsFrame == self.currentGeom : 
			self.addEmptyFrame ()
			return

		# get the index
		if self.currentPose  == "" : 
			res = cmds.confirmDialog ( m="select a pose in the poses list  (left)")
			return

		currTime = cmds.currentTime (q=True)
		dicVal = {"blurNode" : self.currentBlurNode, "currentPose":self.currentPose}
		poseName = cmds.getAttr (self.currentPose+".poseName")

		#listDeformationsFrame = cmds.blurSculpt (self.currentBlurNode,query = True,listFrames = True, poseName=poseName )
		listDeformationsFrame = self.getListDeformationFrames ()
		if not listDeformationsFrame : listDeformationsFrame = []
		listDeformationsIndices = cmds.getAttr ("{currentPose}.deformations".format (**dicVal), mi=True) or []


		if currTime in listDeformationsFrame:
			# empty it the channel
			self.clearVectorMvts (currTime)

		cmds.blurSculpt (self.currentGeom,addAtTime=meshToAddAsFrame, poseName = poseName, offset = self.offset)        
		#theBasePanel = self.doIsolate (state=0)  
		cmds.hide (meshToAddAsFrame)
		self.exitEditMode ()
		
		self.refresh (selectTime = True, selTime =currTime)   
	 
	def clearVectorMvts (self, currTime) : 
		listDeformationsIndices = map(int,cmds.getAttr (self.currentPose+".deformations", mi=True) or [])        		
		listDeformationsFrame = self.getListDeformationFrames ()		
		frameIndex = listDeformationsIndices[listDeformationsFrame.index (currTime)]
		
		dicVal = {"blurNode" : self.currentBlurNode, "currentPose":self.currentPose}
		dicVal["indDeform"] = frameIndex

		indices = cmds.getAttr ("{currentPose}.deformations[{indDeform}].vectorMovements".format (**dicVal) , mi=True)
		if indices : 
			for indVtx in indices :    
				dicVal ["vtx"] = indVtx
				cmds.removeMultiInstance("{currentPose}.deformations[{indDeform}].vectorMovements[{vtx}]".format (**dicVal), b=True)

	def addEmptyFrame (self) :
		poseName = cmds.getAttr (self.currentPose+".poseName")
		listDeformationsIndices = map(int,cmds.getAttr (self.currentPose+".deformations", mi=True) or [])        
		currTime = cmds.currentTime (q=True)

		dicVal = {"pose" : self.currentPose}
		dicVal ["frame"] = max(listDeformationsIndices)+1
		listDeformationsFrame = self.getListDeformationFrames ()

		if currTime in listDeformationsFrame:
			res = cmds.confirmDialog (title ="clear frame", m="frame {0} exists, do you want to clear mvts?\nNo Undo".format(currTime),b=("Yes","No"), defaultButton='Yes', cancelButton='No', dismissString='No')
			if res == "Yes" :
				self.clearVectorMvts (currTime)
		else : 
			cmds.setAttr ("{pose}.deformations[{frame}].frame".format (**dicVal), currTime)
			cmds.setAttr ("{pose}.deformations[{frame}].gain".format (**dicVal), 1.0)

		#self.refreshListFrames ()
		self.refresh (selectTime = True, selTime =currTime)   

	def delete_frame(self) :
		framesToDelete = sorted([float(currentFrameItem.text(0)) for currentFrameItem in self.uiFramesTW.selectedItems() ]		)
		framesToDelete = map (str, framesToDelete)
		
		res = cmds.confirmDialog (title ="delete", m="Do you want to delete the frames {0}?\nNo Undo".format(framesToDelete),b=("Yes","No"), defaultButton='Yes', cancelButton='No', dismissString='No')
		if res == "Yes" :
			for currentFrameItem in self.uiFramesTW.selectedItems() :
				toDelete = str(currentFrameItem.data (0, QtCore.Qt.UserRole))			
				cmds.removeMultiInstance(toDelete, b=True)
			self.refresh ()

	def delete_pose (self) : 
		if cmds.objExists (self.currentPose)  :
			poseName = cmds.getAttr (self.currentPose+".poseName")		
			res = cmds.confirmDialog (title ="delete", m="Do you want to delete the pose [{0}]?\nNo Undo".format(poseName),b=("Yes","No"), defaultButton='Yes', cancelButton='No', dismissString='No')
			if res == "Yes" :
				cmds.removeMultiInstance(self.currentPose, b=True)
				self.currentPose = ""
				self.refresh ()

	def delete_sculpt (self) : 
		res = cmds.confirmDialog (title ="delete", m="Do you want to delete the blurNode [{0}]?\nNo Undo".format(self.currentBlurNode),b=("Yes","No"), defaultButton='Yes', cancelButton='No', dismissString='No')
		if res == "Yes" :
			cmds.delete (self.currentBlurNode)
			self.currentBlurNode = ""
			self.currentGeom = ""
			self.currentPose = ""
			self.refresh ()

	#----------------- ARRAY CHANGE FUNCTIONS -------------------------------
	def isValidName (self,theName,  oldName = "") : 
		listPoses = cmds.blurSculpt (self.currentBlurNode,query = True, listPoses=True)        
		if not listPoses : listPoses = []
		if listPoses and oldName : 
			if oldName in listPoses : 
				listPoses.remove (oldName)
		return theName not in listPoses

	def renamePose (self,item, column) : 
		newName = item.text(0)
		blurPose=  str(item.data (0, QtCore.Qt.UserRole))

		prevName = cmds.getAttr (blurPose+".poseName")
		if newName != prevName:
			if self.isValidName (newName, oldName= prevName) : 
				cmds.setAttr (blurPose+".poseName", newName, type = "string")
			else : 
				with extraWidgets.toggleBlockSignals ([self.uiPosesTW]) :
					item.setText(0,str(prevName))
				

		# check state
		isChecked = item.checkState(column) == QtCore.Qt.Checked
		prevVal = cmds.getAttr (blurPose+".poseEnabled")
		if isChecked != prevVal:
			cmds.setAttr (blurPose+".poseEnabled", isChecked)

	def refreshListFramesAndSelect ( self, timeToSelect) : 
		poseName = str(cmds.getAttr (self.currentPose+".poseName"))
		#listDeformationsFrame = sorted (cmds.blurSculpt (self.currentBlurNode,query = True,listFrames = True, poseName=str(poseName) ))
		listDeformationsFrame = sorted (self.getListDeformationFrames ())
		listCurrentFrames = [float(self.uiFramesTW.topLevelItem (i).text(0)) for i in range (self.uiFramesTW.topLevelItemCount())]
		if listCurrentFrames  != listDeformationsFrame :
			self.refreshListFrames ( )
			cmds.evalDeferred (partial(self.selectFrameTime , timeToSelect))

	def selectFrameTime (self,timeToSelect ) : 
		selectionDone = False
		for i in range (self.uiFramesTW.topLevelItemCount()):
			itemFrame = self.uiFramesTW.topLevelItem (i)
			theTime = float(itemFrame.text(0))
			if theTime ==  timeToSelect:
				self.uiFramesTW.setCurrentItem(itemFrame)
				selectionDone = True                    
				break
		if not selectionDone : self.uiFramesTW.selectionModel().clearSelection()

	def refreshPoseInfo (self,item, prevItem):
		blurPose=  str(item.data (0, QtCore.Qt.UserRole))		
		self.currentPose = blurPose
		self.refreshListFrames ( )
		
		deformationType = cmds.getAttr (blurPose+".deformationType")
		if deformationType == 0 :
			inConnections = cmds.listConnections (blurPose+".poseMatrix", s=True, d=False)
			if not inConnections : val = "N/A"
			else :  val = inConnections[0]
			self.uiTransformLE.setText (val)
			self.uiLocalDeformationRB.setChecked (True)
		else : 
			self.uiTangentDeformationRB.setChecked (True)
		self.uiTransformLE.setVisible (deformationType == 0)
		self.uiMatLBL.setVisible (deformationType == 0)
		self.uiPickTransformBTN.setVisible (deformationType == 0)
		self.uiDisconnectMatrixBTN.setVisible (deformationType == 0)

	def connectMatrix (self) :
		selection = cmds.ls (sl=True, tr=True)
		if selection : 
			self.uiTransformLE.setText (selection[0])
			cmds.connectAttr  (selection[0]+".matrix", self.currentPose+".poseMatrix", f=True)

	def disConnectMatrix (self) :
		inConnections = cmds.listConnections (self.currentPose+".poseMatrix", s=True, d=False, p=True)
		if inConnections : 
			cmds.disconnectAttr (inConnections[0], self.currentPose+".poseMatrix")
		self.uiTransformLE.setText ("N/A")

	def isValidFrame(self,newFrame,  oldFrame = -1) : 
		poseName = str(cmds.getAttr (self.currentPose+".poseName"))
		#listDeformationsFrame = cmds.blurSculpt (self.currentBlurNode,query = True,listFrames = True, poseName=str(poseName) )
		listDeformationsFrame = self.getListDeformationFrames ()

		if not listDeformationsFrame : listDeformationsFrame = []
		if listDeformationsFrame and oldFrame : 
			if oldFrame in listDeformationsFrame : 
				listDeformationsFrame.remove (oldFrame)
		return newFrame not in listDeformationsFrame

	def changeTheFrame (self,item, column) :		
		newFrame = item.text(0)
		try :
			floatFrame = float(newFrame)
		except ValueError:  
			cmds.confirmDialog (m= "not a float",title = "ERROR")
			return
		frameChannel = str(item.data (0, QtCore.Qt.UserRole) )
		oldFrame = cmds.getAttr (frameChannel+".frame")
		changeOccured = False
		if floatFrame != oldFrame :
			if self.isValidFrame(floatFrame,  oldFrame = oldFrame):
				cmds.setAttr (frameChannel+".frame", floatFrame)
				changeOccured =True
			else : 
				with extraWidgets.toggleBlockSignals ([self.uiFramesTW]) :
					item.setText(0,str(oldFrame)) 
		# check state
		isChecked = item.checkState(0) == QtCore.Qt.Checked
		prevVal = cmds.getAttr (frameChannel+".frameEnabled")
		#print "check",isChecked ,  prevVal
		if isChecked != prevVal:
			cmds.setAttr (frameChannel+".frameEnabled", isChecked)

		if changeOccured : 
			self.refreshListFramesAndSelect ( floatFrame) 
	
	def selectFrameInTimeLine (self):				
		with extraWidgets.toggleBlockSignals ([self.uiFramesTW]) :
			first = True
			selectedItems = self.uiFramesTW.selectedItems() 
			for item in selectedItems: 
				#indexFrame = self.uiFramesTW.indexOfTopLevelItem (item)	
				indexFrame = self.uiFramesTW.indexFromItem(item).row()
				self.blurTimeSlider.listKeys [indexFrame].select (addSel = not first, selectInTree = False)	
				first=False
	

	#---------------------- display of ARRAY --------------------------------------
	def addKeyToTimePort (self, listDeformationsFrame):
		if self.addTimeLine : 
			self.blurTimeSlider.deleteKeys ()
			for keyTime, isEmpty in listDeformationsFrame:
				self.blurTimeSlider.addDisplayKey(keyTime, isEmpty = isEmpty)		

	def refreshListFrames (self):		
		poseName = str(cmds.getAttr (self.currentPose+".poseName"))
		#self.changeTheFrame[int].itemChanged 

		with extraWidgets.toggleBlockSignals ([self.uiFramesTW]) :

			self.uiFramesTW.clear()
			self.uiFramesTW.setColumnCount(4)
			self.uiFramesTW.setHeaderLabels(["frame", u"\u00D8", "gain", "offset"])

			#listDeformationsFrame = cmds.blurSculpt (self.currentBlurNode,query = True,listFrames = True, poseName=str(poseName) )
			listDeformationsFrame = self.getListDeformationFrames ()
			listFramesViewPort = []
			if listDeformationsFrame : 
				listDeformationsIndices = cmds.getAttr (self.currentPose+".deformations", mi=True)
				if not listDeformationsIndices : listDeformationsIndices = []

				listDeformationsFrameandIndices = [( listDeformationsFrame[i], listDeformationsIndices[i]) for i in range (len (listDeformationsFrame))]
				listDeformationsFrameandIndices .sort()
				for deformFrame, logicalFrameIndex  in listDeformationsFrameandIndices : 
					frameItem =  QtWidgets.QTreeWidgetItem()
					frameItem.setText (0, str(deformFrame))
					frameItem.setFlags(frameItem.flags() | QtCore.Qt.ItemIsEditable| QtCore.Qt.ItemIsUserCheckable)

					checkState = cmds.getAttr (self.currentPose+".deformations[{0}].frameEnabled".format (logicalFrameIndex))
					if checkState : frameItem.setCheckState(0,QtCore.Qt.Checked)
					else :  frameItem.setCheckState(0,QtCore.Qt.Unchecked)

					frameItem.setData (0, QtCore.Qt.UserRole, self.currentPose+".deformations[{0}]".format (logicalFrameIndex)) 
					frameItem.setText (2, "0.")
					frameItem.setText (3, "0.")

					vectorMovementsIndices = cmds.getAttr (self.currentPose+".deformations[{0}].vectorMovements".format (logicalFrameIndex), mi=True)
					if not vectorMovementsIndices :
						frameItem .setBackground(0,QtGui.QBrush(self.blueCol))
						frameItem.setText (1, u"\u00D8")
						listFramesViewPort.append ((deformFrame, True))
					else : 
						listFramesViewPort.append ((deformFrame, False))

					self.uiFramesTW.addTopLevelItem (frameItem)
					newWidgetGain = extraWidgets.spinnerWidget (self.currentPose+".deformations[{0}].gain".format (logicalFrameIndex), singleStep = 0.1, precision = 2)			
					newWidgetGain.setMinimumHeight (20)
					newWidgetOffset = extraWidgets.spinnerWidget (self.currentPose+".deformations[{0}].offset".format (logicalFrameIndex), singleStep = 0.1, precision = 2)			
					self.uiFramesTW.setItemWidget (frameItem,2,newWidgetGain)
					self.uiFramesTW.setItemWidget (frameItem,3,newWidgetOffset)

			if self.addTimeLine : self. addKeyToTimePort (listFramesViewPort)
			
			vh = self.uiFramesTW.header ()
			vh.setStretchLastSection(False)
			
			QtCompat.setSectionResizeMode(vh, QtWidgets.QHeaderView.Stretch)
			QtCompat.setSectionResizeMode(vh,0, QtWidgets.QHeaderView.Stretch)
			self.uiFramesTW.setColumnWidth (1,20)
			QtCompat.setSectionResizeMode(vh,1, QtWidgets.QHeaderView.Fixed)
			self.uiFramesTW.setColumnWidth (2,50)
			QtCompat.setSectionResizeMode(vh,2, QtWidgets.QHeaderView.Fixed)
			self.uiFramesTW.setColumnWidth (3,50)
			QtCompat.setSectionResizeMode(vh,3, QtWidgets.QHeaderView.Fixed)
			cmds.evalDeferred (partial (self.uiFramesTW.setColumnWidth,1,20))
			cmds.evalDeferred (partial (self.uiFramesTW.setColumnWidth,2,50))
			cmds.evalDeferred (partial (self.uiFramesTW.setColumnWidth,3,50))			
			"""
			vh.setResizeMode(QtWidgets.QHeaderView.Stretch)	
			vh.setResizeMode(0,QtWidgets.QHeaderView.Stretch) 
			self.uiFramesTW.setColumnWidth (1,20)
			vh.setResizeMode(1,QtWidgets.QHeaderView.Fixed) 
			self.uiFramesTW.setColumnWidth (2,50)
			vh.setResizeMode(2,QtWidgets.QHeaderView.Fixed) 
			self.uiFramesTW.setColumnWidth (3,50)
			vh.setResizeMode(3,QtWidgets.QHeaderView.Fixed) 
			cmds.evalDeferred (partial (self.uiFramesTW.setColumnWidth,1,20))
			cmds.evalDeferred (partial (self.uiFramesTW.setColumnWidth,2,50))
			cmds.evalDeferred (partial (self.uiFramesTW.setColumnWidth,3,50))
			"""

#        vv.setResizeMode(QtWidgets.QHeaderView.Stretch)


	def refreshListPoses (self, selectLast =False) : 
		with extraWidgets.toggleBlockSignals ([self.uiPosesTW]) :

			self.currentPose = ""
			self.uiPosesTW.clear()
			self.uiFramesTW.clear()

			self.uiPosesTW.setColumnCount(3)
			self.uiPosesTW.setHeaderLabels(["pose", "gain", "offset"])


			listPoses = cmds.blurSculpt (self.currentBlurNode,query = True, listPoses=True)        
			if not listPoses : return
			#print "list Poses is " + listPoses
			dicVal = {"blurNode" : self.currentBlurNode}

			posesIndices = map(int,cmds.getAttr  (self.currentBlurNode+".poses",mi=True))
			#for indNm, thePose in enumerate(listPoses) :        
			#	logicalInd =posesIndices [indNm]
			for logicalInd in posesIndices:
				dicVal ["indPose"] = logicalInd
				thePose = cmds.getAttr ("{blurNode}.poses[{indPose}].poseName".format (**dicVal))

				channelItem =  QtWidgets.QTreeWidgetItem()			
				channelItem.setText (0, thePose)
				channelItem.setText (1, "0.")
				channelItem.setText (2, "0.")

				channelItem.setFlags (channelItem.flags () | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsSelectable| QtCore.Qt.ItemIsEditable)

				# store the logical index
				dicVal ["indPose"] = logicalInd
				checkState = cmds.getAttr ("{blurNode}.poses[{indPose}].poseEnabled".format (**dicVal))
				if checkState : channelItem.setCheckState(0,QtCore.Qt.Checked)
				else :  channelItem.setCheckState(0,QtCore.Qt.Unchecked)

				self.uiPosesTW.addTopLevelItem (channelItem)
				# store for delation
				channelItem.setData (0, QtCore.Qt.UserRole, "{blurNode}.poses[{indPose}]".format (**dicVal)) 

				newWidgetGain = extraWidgets.spinnerWidget ("{blurNode}.poses[{indPose}].poseGain".format (**dicVal), singleStep = 0.1, precision = 2)			
				newWidgetGain.setMinimumHeight (20)
				newWidgetOffset = extraWidgets.spinnerWidget ("{blurNode}.poses[{indPose}].poseOffset".format (**dicVal), singleStep = 0.1, precision = 2)			
				self.uiPosesTW.setItemWidget (channelItem,1,newWidgetGain)
				self.uiPosesTW.setItemWidget (channelItem,2,newWidgetOffset)

			vh = self.uiPosesTW.header ()
			vh.setStretchLastSection(False)
			QtCompat.setSectionResizeMode(vh, QtWidgets.QHeaderView.Stretch)
			QtCompat.setSectionResizeMode(vh,0, QtWidgets.QHeaderView.Stretch)
			self.uiPosesTW.setColumnWidth (1,50)
			QtCompat.setSectionResizeMode(vh,1, QtWidgets.QHeaderView.Fixed)
			self.uiPosesTW.setColumnWidth (2,50)
			QtCompat.setSectionResizeMode(vh,2, QtWidgets.QHeaderView.Fixed)
			cmds.evalDeferred (partial (self.uiPosesTW.setColumnWidth,1,50))
			cmds.evalDeferred (partial (self.uiPosesTW.setColumnWidth,2,50))
		
		if len (listPoses) > 0 :
			if selectLast : self.uiPosesTW.setCurrentItem(channelItem )					
			else : self.uiPosesTW.setCurrentItem( self.uiPosesTW.topLevelItem (0))					


	def changedSelection (self, item, preItem) : 
		#blurdev.debug.debugMsg( "hello "  +  item.row (), blurdev.debug.DebugLevel.High)
		self.currentBlurNode = str(item.text(0))
		self.currentGeom =  str(item.text(1))
		self.blurTimeSlider.deleteKeys ()
		self.refreshListPoses ()

	def fillTreeOfBlurNodes (self) : 
		with extraWidgets.toggleBlockSignals ([self.uiBlurNodesTW]) :
			self.uiBlurNodesTW.clear()
			self.uiBlurNodesTW.setColumnCount(2)
			self.uiBlurNodesTW.setHeaderLabels(["blurSculpt", "mesh"])
			self.uiBlurNodesTW.setExpandsOnDoubleClick (False)

			blurNodes = cmds.ls (type = 'blurSculpt')
			for blrNode in blurNodes:
				geom = self.getGeom (blrNode, transform = True) 
				channelItem =  QtWidgets.QTreeWidgetItem()
				channelItem.setText (0, blrNode)
				channelItem.setText (1, geom)
				self.uiBlurNodesTW.addTopLevelItem (channelItem )

		for i in range(2) : self.uiBlurNodesTW.resizeColumnToContents(i)       


	def doubleClickChannel (self,item,column):    	
		toSelect =  str(item.text ( column))
		if cmds.objExists (toSelect) : cmds.select (toSelect)

	def getGeom (self, currentBlurNode, transform = False) : 
		futureHistory = cmds.listHistory(currentBlurNode, f=True, af=True)
		if futureHistory:
			meshHist = cmds.ls (futureHistory, type = "mesh")
			if transform  :
				prt,= cmds.listRelatives (meshHist[0], path=True, p=True )
				return prt
			return meshHist [0]
		return ""

	def selectFromScene (self) :
		currentSel = cmds.ls (sl=True)        
		if len (currentSel) == 1 :         
			obj = currentSel
			hist = cmds.listHistory (obj)
			if hist : blurSculpts= cmds.ls(hist , type = "blurSculpt")        

			if hist and blurSculpts: 
				blurNodes = cmds.ls (type = 'blurSculpt')
				ind = blurNodes.index (blurSculpts[0])
				item = self.uiBlurNodesTW.topLevelItem  (ind)
				self.uiBlurNodesTW.setCurrentItem(item )
				#index = self.uiBlurNodesTW.model().index(ind, 0)
				#self.uiBlurNodesTW.selectionModel().setCurrentIndex (index, QtWidgets.QItemSelectionModel.selectedRows)
			else : ind = -1

	# ----------------------- EDIT MODE  --------------------------------------------------
	def enterEditMode (self) : 
		self.resForDuplicate,  = cmds.duplicate (self.currentGeom, name = "TMPEDIT")
		cmds.select (self.currentGeom)
		cmds.HideSelectedObjects ()
		cmds.select (self.resForDuplicate)
		#cmds.selectMode (component=True)

	def exitEditMode (self) :		
		if cmds.objExists (self.resForDuplicate) and not self.keepShapes  :
			cmds.delete (self.resForDuplicate)
			self.resForDuplicate = ""		
			doRename = False
		else : doRename = True

		if doRename and cmds.objExists (self.resForDuplicate):  
			poseName = cmds.getAttr (self.currentPose+".poseName")
			newName = "{0}_{1}_f{2}_".format  (self.currentBlurNode, poseName,int (cmds.currentTime (q=True)))
			cmds.rename (self.resForDuplicate, newName)

		cmds.showHidden (self.currentGeom, a=True)			
		cmds.selectMode (object=True)
	#------------------- REFRESH ----------------------------------------------------
	   
	def refresh (self, selectTime = False, selTime = 0.) :
		#cmds.warning ("REFRESH CALLED")
		#self.uiBlurNodesTW.blockSignals (True) ;
		with extraWidgets.toggleBlockSignals ([self.uiBlurNodesTW, self.uiPosesTW, self.uiFramesTW]) :
			self.uiPosesTW.clear()
			self.uiFramesTW.clear()

			#self.currentBlurNode = ""
			#self.currentGeom = ""
			currentPose = self.currentPose 

			self.uiPosesTW.setColumnCount(3)
			self.uiPosesTW.setHeaderLabels(["pose", "gain", "offset"])
			self.uiFramesTW.setColumnCount(4)
			self.uiFramesTW.setHeaderLabels(["frame", u"\u00D8", "gain", "offset"])

			self.fillTreeOfBlurNodes ()

			blurNodes = cmds.ls (type = 'blurSculpt')

			if self.currentBlurNode in blurNodes:
				ind = blurNodes.index (self.currentBlurNode)		
				item = self.uiBlurNodesTW.topLevelItem  (ind)
				self.uiBlurNodesTW.setCurrentItem(item )

				foundPose = False
				for i in range( self.uiPosesTW.topLevelItemCount ()) :
					itemPose = self.uiPosesTW.topLevelItem (i)
					thePose=  str(itemPose.data (0, QtCore.Qt.UserRole))		
					if thePose == currentPose : 
						foundPose = True
						self.uiPosesTW.setCurrentItem(itemPose )					
						break
				#print "foundPose " + str(foundPose )
				if not foundPose and currentPose != "" : 
					self.currentPose = ""
					self.uiPosesTW.selectionModel().clearSelection()

			else :
				self.currentBlurNode = ""
				self.currentGeom = ""
				self.currentPose = ""

		if selectTime  : self.selectFrameTime (selTime) 

		
	def resizePoseInfo(self, checkState):
		if checkState : self.uiPoseGB.setMaximumHeight (1000)
		else :self.uiPoseGB.setMaximumHeight (20)

	#------------------- POPUP ----------------------------------------------------
	def create_popup_menu(self, parent=None):
		self.popup_menu = QtWidgets.QMenu(parent)
		self.popup_menu.addAction(_icons["toFrame"],"jumpToFrame", self.jumpToFrame)
		self.popup_menu.addAction("duplicate frame", self.doDuplicate)
		self.popup_menu.addAction("select influenced vertices", self.selectVertices)
		self.popup_menu.addAction("remove selected vertices (NO UNDO)", self.removeSelectedVerticesFromFrame)
		self.popup_menu.addAction( _icons["Delete"],"delete (NO UNDO)", self.delete_frame)		


		self.popup_option = QtWidgets.QMenu(parent)
		newAction = self.popup_option.addAction("keep Shapes", self.doKeepShapes)
		newAction.setCheckable(True)
		self.popup_option.addAction(_icons["backUp"], "backUp all Shapes", self.backUp)
		self.popup_option.addAction(_icons["restore"], "restore from backUp", self.restoreBackUp)
		self.popup_option.addAction("store xml file", self.callSaveXml)
		self.popup_option.addAction("retrieve xml file", self.callOpenXml)		
		self.popup_option.addAction("set distance offset [{0}]".format (self.offset), self.setDistanceOffset)		

		if cmds.optionVar (exists = "blurScluptKeep") : 
			setChecked = cmds.optionVar ( q="blurScluptKeep") == 1
		else : 
			setChecked = False
		self.keepShapes = setChecked
		newAction.setChecked(setChecked)

		self.uiOptionsBTN.clicked.connect (self.clickedPopMenuMousePressEvent)

	def setDistanceOffset (self) :
		cmds.promptDialog(m="set distance", text="{0}".format(self.offset))
		val = cmds.promptDialog(q=True, text=True)
		try :
			val = float(val)
			self.offset = val
			self.popup_option.actions()[5].setText ("set distance offset [{0}]".format (self.offset))
			cmds.optionVar (floatValue = ["argileScluptOffset", self.offset])
		except : 
			pass

	def clickedPopMenuMousePressEvent (self) : 
		wPos = 	QtGui.QCursor.pos()
		self.popup_option.exec_(wPos)

	def popMenuMousePressEvent (self, event):		
		self.popup_option.exec_(event.globalPos())

	def storeXmlFileOfPoses (self) : 
		sceneName = cmds.file(q=True,sceneName=True)
		splt = sceneName.split("/")
		startDir = "/".join(splt [:-1])		
		res = cmds.fileDialog2(fileMode=0,dialogStyle=1,caption="save data",startingDirectory = startDir)
		if res :
			destinationFile = res.pop()
			if not destinationFile.endswith (".xml") :
				destinationFile = destinationFile .split (".")[0]+'.xml'
			
		else : return

		print 'destinationFile = "{0}"'.format (destinationFile)
		with extraWidgets.WaitCursorCtxt ():			
			doc = minidom.Document()
			ALL_tag = doc.createElement("ALL")
			doc.appendChild(ALL_tag )
			blurNodes  = cmds.ls (type ="blurSculpt" )
			#for blurNode in blurNodes : 
			#	created_tag = self.storeInfoBlurSculpt(doc, blurNode )
			#	ALL_tag .appendChild (created_tag )

			created_tag = self.storeInfoBlurSculpt(doc, self.currentBlurNode )
			ALL_tag .appendChild (created_tag )

			with codecs.open(destinationFile, "w", "utf-8") as out:
				doc.writexml(out,indent="\n",addindent="\t",newl="")

	def retrieveXml (self):
		sceneName = cmds.file(q=True,sceneName=True)
		splt = sceneName.split("/")
		startDir = "/".join(splt [:-1])		
		res = cmds.fileDialog2(fileMode=1,dialogStyle=1,caption="retrieve data",startingDirectory = startDir)

		if res :
			with extraWidgets.WaitCursorCtxt ():			
				sourceFile = res.pop()   
				if os.path.isfile(sourceFile ) :             
					tree = ET.parse(sourceFile  )
					root = tree.getroot()
					self.retrieveblurXml (root)

	def retrieveblurXml (self, root) : 		
		dicVal = {"blurNode" : self.currentBlurNode}

		pses = cmds.getAttr  (self.currentBlurNode+".poses",mi=True)
		dicPoses = {} 		
		newInd = 0
		if pses:
			posesIndices = map(int,pses)			
			for logicalInd in posesIndices:
				dicVal ["indPose"] = logicalInd
				poseName = cmds.getAttr ("{blurNode}.poses[{indPose}].poseName".format (**dicVal))
				dicPoses [poseName] = logicalInd
			newInd = max (posesIndices) + 1


		for blurNode_tag in root.getchildren():
			blurName = blurNode_tag.get ("name")
			print blurName
			for pose_tag in blurNode_tag.getchildren():
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
				#
				dicFrames = {} 	
				newFrameInd = 0
				listDeformationsIndices = cmds.getAttr ("{blurNode}.poses[{indPose}].deformations".format (**dicVal), mi=True)
				if listDeformationsIndices : 
					for logicalFrameIndex  in listDeformationsIndices : 
						frame = cmds.getAttr ("{blurNode}.poses[{indPose}].deformations[{frameInd}].frame".format (**dicVal))
						dicFrames [frame]= logicalFrameIndex
					newFrameInd = max (listDeformationsIndices) + 1

				for frame_tag in pose_tag.getchildren ():
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


	def storeInfoBlurSculpt (self, doc, blurNode, inputPoseFramesIndices= {}) : 
		blurNode_tag = doc.createElement("blurSculpt")
		blurNode_tag.setAttribute ("name",blurNode)    
		geom = self.getGeom (blurNode, transform = True) 
		blurNode_tag.setAttribute ("geom",geom)

		listPoses = cmds.blurSculpt (blurNode,query = True, listPoses=True)        
		if not listPoses : return blurNode_tag
		dicVal = {"blurNode" : blurNode}

		posesIndices = map(int,cmds.getAttr  (blurNode+".poses",mi=True))
		if inputPoseFramesIndices : 
			posesIndices = inputPoseFramesIndices.keys()


		# first store positions
		for logicalInd in posesIndices:
			dicVal ["indPose"] = logicalInd

			thePose = cmds.getAttr ("{blurNode}.poses[{indPose}].poseName".format (**dicVal))
			poseAttr = "{blurNode}.poses[{indPose}].poseEnabled".format (**dicVal)
			poseGain = "{blurNode}.poses[{indPose}].poseGain".format (**dicVal)
			poseOffset = "{blurNode}.poses[{indPose}].poseOffset".format (**dicVal)
			isEnabled = cmds.getAttr (poseAttr)
			poseGainVal =  cmds.getAttr (poseGain)
			poseOffsetVal =  cmds.getAttr (poseOffset)

			pose_tag = doc.createElement("pose")
			pose_tag .setAttribute ("poseEnabled",str(isEnabled) )
			pose_tag .setAttribute ("poseGain",str(poseGainVal) )
			pose_tag .setAttribute ("poseOffset",str(poseOffsetVal) )
			pose_tag .setAttribute ("poseName",str(thePose) )

			blurNode_tag.appendChild (pose_tag)

			deformType = cmds.getAttr ("{blurNode}.poses[{indPose}].deformationType".format (**dicVal))
			pose_tag .setAttribute ("deformType",str(deformType) )

			inConnections = cmds.listConnections ("{blurNode}.poses[{indPose}].poseMatrix".format (**dicVal), s=True, d=False, p=True)
			if not inConnections : val = "N/A"
			else :  val = inConnections[0]
			pose_tag .setAttribute ("poseMatrix",str(val) )						

			listDeformationsIndices = cmds.getAttr ("{blurNode}.poses[{indPose}].deformations".format (**dicVal), mi=True)
			if inputPoseFramesIndices : 
				listDeformationsIndices = inputPoseFramesIndices [logicalInd]

			if not listDeformationsIndices : 
				continue

			for logicalFrameIndex  in listDeformationsIndices : 
				dicVal["frameInd"] = logicalFrameIndex
				frame = cmds.getAttr ("{blurNode}.poses[{indPose}].deformations[{frameInd}].frame".format (**dicVal))

				# store vals --------------------------------------------------------------------------------------------
				gain = "{blurNode}.poses[{indPose}].deformations[{frameInd}].gain".format (**dicVal)
				offset = "{blurNode}.poses[{indPose}].deformations[{frameInd}].offset".format (**dicVal)
				gainVal =  cmds.getAttr (gain)
				offsetVal =  cmds.getAttr (offset)

				frameEnabled = "{blurNode}.poses[{indPose}].deformations[{frameInd}].frameEnabled".format (**dicVal)
				frameEnabledVal = cmds.getAttr (frameEnabled)

				frame_tag = doc.createElement("frame")
				frame_tag .setAttribute ("frame",str(frame) )
				frame_tag .setAttribute ("gain",str(gainVal) )
				frame_tag .setAttribute ("offset",str(offsetVal) )
				frame_tag .setAttribute ("frameEnabled",str(frameEnabledVal) )

				pose_tag.appendChild (frame_tag)

				mvtIndices =  cmds.getAttr ("{blurNode}.poses[{indPose}].deformations[{frameInd}].vectorMovements".format (**dicVal), mi=True)
				vector_tag = doc.createElement("vectorMovements")
				frame_tag.appendChild (vector_tag)
				if mvtIndices: 
					mvtIndices = map (int, mvtIndices )
					for vecInd in mvtIndices:
						dicVal["vecInd"] = vecInd
						mvt, = cmds.getAttr ("{blurNode}.poses[{indPose}].deformations[{frameInd}].vectorMovements[{vecInd}]".format (**dicVal))
						vectag = doc.createElement("vectorMovements")
						vectag.setAttribute ("index", str(vecInd) )
						vectag.setAttribute ("value", str(mvt) )
						vector_tag.appendChild (vectag)

		return blurNode_tag

	def backUp (self):
		blurGrp = cmds.createNode ("transform", n="{0}_".format (self.currentBlurNode))
		listPoses = cmds.blurSculpt (self.currentBlurNode,query = True, listPoses=True)        
		if not listPoses : return
		dicVal = {"blurNode" : self.currentBlurNode}

		posesIndices = map(int,cmds.getAttr  (self.currentBlurNode+".poses",mi=True))

		# first store positions
		storedStates = {}
		for logicalInd in posesIndices:			
			dicVal ["indPose"] = logicalInd
			poseAttr = "{blurNode}.poses[{indPose}].poseEnabled".format (**dicVal)
			isEnabled = cmds.getAttr (poseAttr)
			cmds.setAttr (poseAttr, False)
			
			storedStates[poseAttr]= isEnabled

			poseGain = "{blurNode}.poses[{indPose}].poseGain".format (**dicVal)
			poseOffset = "{blurNode}.poses[{indPose}].poseOffset".format (**dicVal)
			poseGainVal =  cmds.getAttr (poseGain)
			poseOffsetVal =  cmds.getAttr (poseOffset)
			cmds.setAttr (poseGain, 1.0)
			cmds.setAttr (poseOffset, 0.0)

			storedStates[poseGain]= poseGainVal
			storedStates[poseOffset]= poseOffsetVal

		for logicalInd in posesIndices:
			dicVal ["indPose"] = logicalInd
			thePose = cmds.getAttr ("{blurNode}.poses[{indPose}].poseName".format (**dicVal))
			thePoseGrp = cmds.createNode ("transform", n="{0}_{1}_".format (self.currentBlurNode, thePose), p=blurGrp)

			cmds.addAttr( thePoseGrp , longName="deformationType", attributeType="enum", enumName="local:tangent:")
			cmds.setAttr( thePoseGrp+".deformationType", edit=True, keyable=True)
			deformType = cmds.getAttr ("{blurNode}.poses[{indPose}].deformationType".format (**dicVal))
			cmds.setAttr( thePoseGrp+".deformationType", deformType)

			inConnections = cmds.listConnections ("{blurNode}.poses[{indPose}].poseMatrix".format (**dicVal), s=True, d=False, p=True)
			if not inConnections : val = "N/A"
			else :  val = inConnections[0]
			cmds.addAttr( thePoseGrp , longName="poseMatrix", dataType="string")
			cmds.setAttr( thePoseGrp+".poseMatrix", edit=True, keyable=True)
			cmds.setAttr( thePoseGrp+".poseMatrix",val, type = "string")
			

			listDeformationsIndices = cmds.getAttr ("{blurNode}.poses[{indPose}].deformations".format (**dicVal), mi=True)
			if not listDeformationsIndices : 
				continue
			poseAttr = "{blurNode}.poses[{indPose}].poseEnabled".format (**dicVal)
			cmds.setAttr (poseAttr, True)


			# add attributes -------------------------------------------------------------------------------------			
			for att in ["poseGain", "poseOffset", "poseEnabled"] : 
				if att == "poseEnabled" : 
					cmds.addAttr( thePoseGrp , longName=att, attributeType="bool")
				else : 
					cmds.addAttr( thePoseGrp , longName=att, attributeType="float")
				cmds.setAttr( thePoseGrp+"."+att, edit=True, keyable=True)
				dicVal ["att"] = att
				realAtt = "{blurNode}.poses[{indPose}].{att}".format (**dicVal) 
				val = storedStates [realAtt]#cmds.getAttr (realAtt)
				cmds.setAttr  (thePoseGrp+"."+att, val)
				inConn = cmds.listConnections (realAtt, s=True, d=False, c=True, scn=False)
				if inConn : cmds.connectAttr (inConn[0], thePoseGrp+"."+att)


			# for all frames -------------------------------------------------------------------------------------
			for logicalFrameIndex  in listDeformationsIndices : 
				dicVal["frameInd"] = logicalFrameIndex
				frame = cmds.getAttr ("{blurNode}.poses[{indPose}].deformations[{frameInd}].frame".format (**dicVal))

				# store vals --------------------------------------------------------------------------------------------
				gain = "{blurNode}.poses[{indPose}].deformations[{frameInd}].gain".format (**dicVal)
				offset = "{blurNode}.poses[{indPose}].deformations[{frameInd}].offset".format (**dicVal)
				gainVal =  cmds.getAttr (gain)
				offsetVal =  cmds.getAttr (offset)
				cmds.setAttr (gain, 1.0)
				cmds.setAttr (offset, 0.0)

				storedStates[gain]=gainVal
				storedStates[offset]= offsetVal

				frameEnabled = "{blurNode}.poses[{indPose}].deformations[{frameInd}].frameEnabled".format (**dicVal)
				frameEnabledVal = cmds.getAttr (frameEnabled)
				cmds.setAttr (frameEnabled, True) 

				storedStates[frameEnabled]= frameEnabledVal
				# end vals --------------------------------------------------------------------------------------------
				cmds.currentTime (frame)

				frameName = "{0}_{1}_f{2}_".format (self.currentBlurNode, thePose, int(frame))

				frameDup,  = cmds.duplicate (self.currentGeom, name = frameName)
				frameDup = cmds.parent (frameDup, thePoseGrp)
				cmds.hide (frameDup)
				frameDup = str (frameDup[0])
				# add attributes -------------------------------------------------------------------------------------
				
				for att in ["gain", "offset", "frameEnabled"] : 
					if att == "frameEnabled" : 
						cmds.addAttr( frameDup , longName=att, attributeType="bool")
					else : 
						cmds.addAttr( frameDup , longName=att, attributeType="float")
					cmds.setAttr( frameDup+"."+att, edit=True, keyable=True)
					dicVal ["att"] = att
					realAtt = "{blurNode}.poses[{indPose}].deformations[{frameInd}].{att}".format (**dicVal) 
					val = storedStates [realAtt]#cmds.getAttr (realAtt)
					cmds.setAttr  (frameDup+"."+att, val)
					inConn = cmds.listConnections (realAtt, s=True, d=False, c=True, scn=False)
					if inConn : cmds.connectAttr (inConn[0], frameDup+"."+att)


		# restoreVals
		for attr, val in storedStates.items() : cmds.setAttr (attr, val)

	def restoreBackUp (self):
		selectedGeometries = [el for el in cmds.ls (sl=True, tr=True, l=True) if cmds.listRelatives (el, type="mesh")]
		if not  selectedGeometries : 
			cmds.confirmDialog (t="Fail", m="select geometries to restore")
			return

		dicVal = {"blurNode" : self.currentBlurNode}

		posesIndices = cmds.getAttr  (self.currentBlurNode+".poses",mi=True)
		if posesIndices : 
			posesIndices = map(int,posesIndices)
			poseNames = [cmds.getAttr ("{blurNode}.poses[{i}].poseName".format ( i=i, **dicVal)) for i in posesIndices]
		else :
			posesIndices = []
			poseNames = [cmds.getAttr ("{blurNode}.poses[{i}].poseName".format ( i=i, **dicVal)) for i in posesIndices]
		
		toRestore = {}

		for geom in selectedGeometries:
			geomlongSplitted = geom.split ("|") [-1]
			split = geomlongSplitted.split("_")
			blurNode = split[0]
			frame = split[-2]
			poseName = "_".join (split[1:-2])
			frame = float(frame[1:])
			print blurNode, frame, poseName

			if poseName not in poseNames : 
				prt = cmds.listRelatives (geom, parent=True, path = True)
				local = True
				poseTransform = ""
				if prt : prt = prt[0]
				if prt and cmds.attributeQuery("deformationType", node=prt, ex=True): 
					local = cmds.getAttr (prt+".deformationType") == 0

				self.addNewPose ( poseName, local = local, poseTransform = poseTransform, withRefresh = False)

				posesIndices = map(int,cmds.getAttr  (self.currentBlurNode+".poses",mi=True))
				poseNames = [cmds.getAttr ("{blurNode}.poses[{i}].poseName".format ( i=i, **dicVal)) for i in posesIndices]
				dicVal ["indPose"] = posesIndices[poseNames.index (poseName)]

				if prt and cmds.attributeQuery("poseMatrix", node=prt, ex=True):
					poseMatrixConn = cmds.getAttr (prt+".poseMatrix")
					if cmds.objExists (poseMatrixConn ) : 
						try : 
							cmds.connectAttr (poseMatrixConn,"{blurNode}.poses[{indPose}].poseMatrix".format (**dicVal), f=True)
						except : pass
				# store attributes --------------------
				if prt  :
					for att in ["poseGain", "poseOffset", "poseEnabled"] : 
						if cmds.attributeQuery(att, node=prt, ex=True):
							dicVal ["att"] = att
							toRestore ["{blurNode}.poses[{indPose}].{att}".format (**dicVal)] = prt+"."+att
			else :
				dicVal ["indPose"] = posesIndices[poseNames.index (poseName)]

			cmds.currentTime (frame)
			prevIndices = cmds.getAttr ("{blurNode}.poses[{indPose}].deformations".format (**dicVal), mi=True)
			if not prevIndices : prevIndices=[]
			# add the pose
			cmds.blurSculpt (self.currentGeom,addAtTime=geom, poseName = poseName, offset = self.offset)		

			postIndices = cmds.getAttr ("{blurNode}.poses[{indPose}].deformations".format (**dicVal), mi=True)
			diffSet = set(postIndices) - set(prevIndices)
			dicVal["frameInd"] = diffSet.pop()
			# store attributes --------------------
			for att in  ["gain", "offset", "frameEnabled"] : 
				if cmds.attributeQuery(att, node=geom, ex=True):
					dicVal ["att"] = att
					toRestore ["{blurNode}.poses[{indPose}].deformations[{frameInd}].{att}".format (**dicVal)] = geom+"."+att



		# restore attributes --------------------
		for attDest, attSrc in toRestore.items () : 
			val = cmds.getAttr (attSrc)
			cmds.setAttr (attDest, val)
			inConn = cmds.listConnections (attSrc, s=True, d=False, c=True, scn=False)
			if inConn : cmds.connectAttr (inConn[0], attDest, f=True)

		cmds.evalDeferred (self.refresh )

	def doKeepShapes (self) :
		self.keepShapes =self.popup_option.actions()[0].isChecked()
		intVal = 1 if self.keepShapes else 0
		cmds.optionVar ( intValue=("blurScluptKeep",intVal))
		 
	def on_context_menu(self, event): 
		pos = event.pos ()
		self.popContextMenu(pos)

	def popContextMenu (self, pos) : 
		self.clickedItem = self.uiFramesTW.itemAt(pos)        
		self.popup_menu.multiSelection = len (self.uiFramesTW.selectedItems())>1		
		for i in range (0,4) : self.popup_menu.actions() [i].setVisible (not self.popup_menu.multiSelection )
		self.popup_menu.exec_(self.uiFramesTW.mapToGlobal (pos)	+ QtCore.QPoint(0,20))

	def jumpToFrame (self) :
		frameIndex = float(self.clickedItem.text (0))
		cmds.currentTime (frameIndex)
	
	def selectVertices (self) :
		frameChannel = str(self.clickedItem.data (0, QtCore.Qt.UserRole) )
		vertices = cmds.getAttr (frameChannel+".vectorMovements", mi=True)
		if vertices : 
			with extraWidgets.WaitCursorCtxt ():
				#toSelect = ["{0}.vtx[{1}]".format (self.currentGeom, vtx) for vtx in vertices]
				toSelect = ["{0}.vtx[{1}]".format (self.currentGeom, el) for el in orderMelList(vertices)]

				cmds.select (toSelect)            
		else : 
			cmds.select (clear=True)

	#------------------- EXTERNAL CALL ----------------------------------------------------
	def callAddPose (self) :		
		self.toRestore = []
		for el in self.__dict__.values () :
			try :
				if self.isEnabled ():
					el.setEnabled (False)
					self.toRestore .append (el)
			except : 
				continue
		#blurdev.launch(blurAddPose.BlurAddPose, instance=True)
		#self.addPoseWin.refreshWindow ()
		argileAddPose.ArgileAddPose ( self)
		self.addPoseWin.show ()
		self.addPoseWin.refreshWindow ()
		
	addPoseWin = None

	def callSaveXml (self) :	
		self.toRestore = []
		for el in self.__dict__.values () :
			try :
				if self.isEnabled ():
					el.setEnabled (False)
					self.toRestore .append (el)
			except : 
				continue
		#blurdev.launch(storeXml.StoreXml, instance=True)

		storeXml.StoreXml (self)
		self.saveXmlWin.show ()

		self.saveXmlWin.setEnabled (True)
		self.saveXmlWin.setUpFilePicker (store=True)
		self.saveXmlWin.refreshTree(self.currentBlurNode)

	def callOpenXml (self) :	
		self.toRestore = []
		for el in self.__dict__.values () :
			try :
				if self.isEnabled ():
					el.setEnabled (False)
					self.toRestore .append (el)
			except : 
				continue

		#blurdev.launch(storeXml.StoreXml, instance=True)
		storeXml.StoreXml (self)
		self.saveXmlWin.show ()

		self.saveXmlWin.setEnabled (True)
		self.saveXmlWin.setUpFilePicker (store=False)
		
	#------------------- INIT ----------------------------------------------------
	def __init__(self, parent=None):
		super(ArgileDeformDialog, self).__init__(parent)

		if cmds.optionVar (exists = "argileScluptOffset") : 
			self.offset = cmds.optionVar ( q="argileScluptOffset") 
		else : 
			self.offset = 0.001

		
		# load the ui
		#import __main__
		QtCompat.loadUi(getUiFile(__file__), self)

		self.setWindowFlags  (QtCore.Qt.Window)
		self.setWindowTitle  ("argile")


		for nameBtn in ["PoseBTN", "FrameBTN", "BlurNodeBTN"] : 
			for nm in ["Add", "Delete"] :
				btn =self.__dict__["ui{0}{1}".format(nm, nameBtn)]
				btn.setIcon (_icons[nm])
				if (nameBtn,nm) ==  ("FrameBTN", "Add") :btn.setIcon (_icons["addFrame"]) 
				btn.setText ("")

		for nm in  ["BlurNodes", "Frames", "Poses"] :
			self.__dict__["ui"+nm+"TW"].setRootIsDecorated (False)

		self.blueCol = QtGui.QColor(50, 50, 100) 		

		self.uiDisconnectMatrixBTN.setIcon (_icons["disconnect"])
		self.uiDisconnectMatrixBTN.setText ("")

		self.uiRefreshBTN.setIcon (_icons["refresh"])
		self.uiRefreshBTN.setText ("")
		self.uiFromSelectionBTN.setIcon (_icons["fromScene"])
		self.uiFromSelectionBTN.setText ("")
		self.uiEmptyFrameBTN.setIcon (_icons["empty"])
		self.uiEmptyFrameBTN.setText ("")

		self.uiEditModeBTN.setIcon (_icons["edit"])
		self.uiExitEditModeBTN.setIcon (_icons["cancelEdit"])

		self.uiOptionsBTN.setIcon (_icons["gear"])
		self.uiOptionsBTN.setText ("")

		self.uiFramesTW.setSelectionMode( QtWidgets.QAbstractItemView.ExtendedSelection) 

		self.create_popup_menu ()
		#self.uiFramesTW.contextMenuEvent = self.on_context_menu
		self.uiFramesTW.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
		self.uiFramesTW.customContextMenuRequested.connect(self.popContextMenu)


		self.uiPoseGB.toggled.connect ( self.resizePoseInfo )

		self.uiRefreshBTN.clicked.connect ( self.refresh )
		self.uiFromSelectionBTN.clicked.connect ( self.selectFromScene )
		self.uiEmptyFrameBTN.clicked.connect ( self.addEmptyFrame )

		# - delete  
		self.uiDeleteBlurNodeBTN.clicked.connect ( self.delete_sculpt)
		self.uiDeleteFrameBTN.clicked.connect ( self.delete_frame)
		self.uiDeletePoseBTN.clicked.connect ( self.delete_pose)

		# - Add
		self.uiAddBlurNodeBTN.clicked.connect (  self.addDeformer)
		self.uiAddFrameBTN.clicked.connect (  self.addNewFrame)
		self.uiAddPoseBTN.clicked.connect (  self.callAddPose)
		self.uiEditModeBTN.clicked.connect (  self.enterEditMode)
		self.uiExitEditModeBTN.clicked.connect (  self.exitEditMode)
		
		self.uiPickTransformBTN.clicked.connect ( self.connectMatrix )
		self.uiDisconnectMatrixBTN.clicked.connect ( self.disConnectMatrix )

		self.uiBlurNodesTW.itemDoubleClicked.connect ( self.doubleClickChannel )
		
		# time slider part 
		if self.addTimeLine : 
			self.blurTimeSlider = extraWidgets.TheTimeSlider (self)
			self.layout() .addWidget (self.blurTimeSlider )
		#cmds.evalDeferred (self.refreshForShow )
		self.uiPoseGB.setChecked (False)

		self.uiPosesTW.currentItemChanged.connect (self.refreshPoseInfo)
		self.uiPosesTW.itemChanged.connect (self.renamePose)		
		self.uiBlurNodesTW.currentItemChanged.connect (self.changedSelection)		
		self.uiFramesTW.itemChanged.connect (self.changeTheFrame)

		self.uiFramesTW.itemSelectionChanged.connect (self.selectFrameInTimeLine)
		

	def selectProximityKey (self) : 
		currTime = cmds.currentTime (q=True)
		self.selectFrameTime (currTime)

	def addtheCallBack (self) :
		#print "ADD Call Back"
		self.playBackScript = cmds.scriptJob( e= ["playbackRangeChanged",self.blurTimeSlider.updateKeys ], protected=True)
		self.timeSliderChange = cmds.scriptJob( e= ["timeChanged",self.selectProximityKey ], protected=True)

	def deleteScriptJob (self):
		#print "Delete Call Back"
		cmds.scriptJob( kill=self.playBackScript, force=True)
		cmds.scriptJob( kill=self.timeSliderChange, force=True)


	def refreshForShow (self) : 
		#print "CALLING REFRESH OPENING"
		if self.addTimeLine : 
			self.addtheCallBack ()
			self.blurTimeSlider.deleteKeys ()


		self.currentBlurNode = ""
		self.currentGeom = ""
		self.currentPose = ""	
		self.resForDuplicate = ""	

		cmds.evalDeferred (self.refresh )

	def showEvent (self, event) :
		self.refreshForShow ()
		super(ArgileDeformDialog, self).showEvent(event)

	def closeEvent (self, event) :
		if self.addTimeLine :self.deleteScriptJob ()

		pos = self.pos()
		size = self.size()
		cmds.optionVar (clearArray= "argileDeformWindow")
		for el in pos.x (), pos.y(), size.width(), size.height() : 
			cmds.optionVar (intValueAppend = ("argileDeformWindow", el))

		super(ArgileDeformDialog, self).closeEvent(event)

"""
		validNickname = QtCore.QRegExp ("^[0-9]*$")        
		validator = QtWidgets.QRegExpValidator (validNickname ,self.main_ui.resolution_le)

"""