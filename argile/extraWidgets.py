from maya import cmds
from Qt import QtGui, QtCore, QtWidgets, QtCompat
from utils import toPyObject, getUiFile
from maya import OpenMayaUI

def toQt(mayaName, QtClass):
    """
    Given the name of a Maya UI element of any type, return the corresponding QWidget or QAction.
    If the object does not exist, returns None
    """
    ptr = OpenMayaUI.MQtUtil.findControl(mayaName)
    if ptr is None:
        ptr = OpenMayaUI.MQtUtil.findLayout(mayaName)
        if ptr is None:
            ptr = OpenMayaUI.MQtUtil.findMenuItem(mayaName)
    if ptr is not None:
        return QtCompat.wrapInstance(long(ptr), QtClass)


class toggleBlockSignals(object):
	def __init__(self, listWidgets, raise_error=True):
		self.listWidgets = listWidgets

	def __enter__(self):
		for widg in self.listWidgets:
			widg.blockSignals (True)
	def __exit__(self, exc_type, exc_val, exc_tb):
		for widg in self.listWidgets:
			widg.blockSignals (False)

# spinner connected to an attribute
class OLDspinnerWidget(QtWidgets.QWidget):

	def offsetSpin_mousePressEvent ( self,event):
		if cmds.objExists (self.theAttr) : 
			val = cmds.getAttr (self.theAttr)
			self.theSpinner.setValue ( val )
			QtWidgets.QDoubleSpinBox.mousePressEvent(self.theSpinner,event)

	def offsetSpin_wheelEvent ( self,event):
		if cmds.objExists (self.theAttr) : 
			val = cmds.getAttr (self.theAttr)
			self.theSpinner.setValue ( val )
			QtWidgets.QDoubleSpinBox.wheelEvent(self.theSpinner,event)

	def valueChangedFn(self,newVal) :
		if cmds.objExists (self.theAttr) and cmds.getAttr (self.theAttr, settable=True):
			cmds.setAttr (self.theAttr, newVal)

	def createWidget (self,singleStep = .1, precision = 2) :        
		#theWindowForQtObjects = getQTObject ()
		cmds.setParent ("tmpWidgetsWindow|qtLayoutObjects")
		self.floatField = cmds.floatField(  pre=precision , step = singleStep)
		#QtCompat.wrapInstance (self.floatField,QtWidgets.QWidget )
		self.theQtObject = toQt (self.floatField,QtWidgets.QWidget)
		#self.theQtObject = self.theWindowForQtObjects .children() [-1]  
		"""
		if qtLayoutObject :
			self.theQtObject = qtLayoutObject
		else : 
			self.theQtObject = toQtObject (self.floatField)
		"""

		self.theQtObject.setParent (self)
		self.theSpinner.lineEdit().hide()
		self.theQtObject.move (self.theSpinner.pos())
		self.theQtObject.show()

		#QtCore.QObject.connect(self.theSpinner, QtCore.SIGNAL("valueChanged(double)"), self.valueChangedFn)    
		self.theSpinner.valueChanged.connect (self.valueChangedFn)
		# set before click
		self.theSpinner.mousePressEvent = self.offsetSpin_mousePressEvent
		# set before spin
		self.theSpinner.wheelEvent = self.offsetSpin_wheelEvent
		self.theSpinner.resize (self.size())
		wdth = self.theSpinner.lineEdit().width () + 3
		self.theQtObject.resize  (wdth, self.height() )

	def doConnectAttrSpinner (self, theAttr ) :
		self.theAttr = theAttr 
		if cmds.objExists (self.theAttr) :  
			cmds.connectControl( self.floatField, self.theAttr )
			minValue, maxValue = -16777214,16777215

			listAtt = theAttr.split (".")
			att = listAtt [-1]
			node = ".".join(listAtt [:-1])

			if cmds.attributeQuery (att, node = node, maxExists=True): 
				maxValue, = cmds.attributeQuery (att, node = node, maximum=True)
			if cmds.attributeQuery (att, node = node, minExists=True) : 
				minValue, = cmds.attributeQuery (att, node = node, minimum=True)

			self.theSpinner.setRange (minValue,maxValue)

	def resizeEvent (self, event):
		self.theSpinner.resize (self.size())
		wdth = self.theSpinner.lineEdit().width () + 3
		self.theQtObject.resize  (wdth, self.height() )

	def __init__ (self, theAttr, singleStep = .1, precision = 2, theWindowForQtObjects=None):
		self.theWindowForQtObjects = theWindowForQtObjects
		super(spinnerWidget, self).__init__ ()   
		self.theAttr = theAttr
		self.theSpinner = QtWidgets.QDoubleSpinBox (self)
		self.theSpinner .setRange (-16777214,16777215)
		self.theSpinner .setSingleStep (singleStep)        
		self.theSpinner .setDecimals(precision)

		self.theSpinner .move(0,0)
		#self.setMinimumWidth(50)
		self.createWidget ( singleStep=singleStep, precision =precision)  
		self.doConnectAttrSpinner (theAttr)   

class spinnerWidget2(QtWidgets.QDoubleSpinBox):
	
	def updateValToAttr (self) : 
		if cmds.objExists (self.theAttr) :
			self.setValue (cmds.getAttr (self.theAttr))
			
	def doValueChanged (self, newVal) :			
		if cmds.objExists (self.theAttr) :
			cmds.setAttr (self.theAttr, newVal)
			print self.theAttr, newVal
	
	def __init__ (self, theAttr, singleStep = .1, precision = 2):
		super(spinnerWidget2 , self).__init__(None)        
		self.theAttr = theAttr
		self.setSingleStep (singleStep)        
		self.setDecimals(precision)
		self.updateValToAttr ()
		self.valueChanged.connect (self.doValueChanged)

# spinner connected to an attribute

class KeyFrameBtn (QtWidgets.QPushButton):
	_colors = {
		"redColor" :'background-color: rgb(154, 10, 10);',
		"redLightColor" : 'background-color: rgb(255, 153, 255);',
		"blueColor" :'background-color: rgb(10, 10, 154);',
		"blueLightColor" : 'background-color: rgb(153,255, 255);'
		}
	pressedColor = 'background-color: rgb(255, 255, 255);'

	def delete (self) : 
		self.theTimeSlider.listKeys.remove(self)
		self.deleteLater ()
		#sip.delete(self)
		
	def mouseMoveEvent(self,event):
		#print "begin  mouseMove event"

		controlShitPressed =  event.modifiers () == QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier
		shiftPressed = controlShitPressed or event.modifiers () == QtCore.Qt.KeyboardModifiers(QtCore.Qt.ShiftModifier)        
		
		Xpos =  event.globalX () - self.globalX + self.prevPos.x()
		theKey = (Xpos - self.startPos )/self.oneKeySize
		if not shiftPressed : theKey = int(theKey)  
		theTime = theKey + self.startpb
		
		if theTime < self.start : theTime = self.start
		elif   theTime > self.end : theTime = self.end
		  
		if shiftPressed :  self.theTime = round(theTime,3)
		else : self.theTime = int (theTime)
		self.updatePosition()

		#print "end  mouseMove event"
		super (KeyFrameBtn, self ).mouseMoveEvent(event)
	
	def mousePressEvent(self,event):
		#print "begin  mousePress event"
		controlShitPressed =  event.modifiers () == QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier
		controlPressed = controlShitPressed or event.modifiers () == QtCore.Qt.ControlModifier
		shiftPressed = controlShitPressed or event.modifiers () == QtCore.Qt.KeyboardModifiers(QtCore.Qt.ShiftModifier)
		
		if shiftPressed : offsetKey = 0.001
		else : offsetKey = 1

		self.duplicateMode = controlPressed
		
		if not self.checked : 
			self.select(addSel = controlPressed )
		if event.button() == QtCore.Qt.RightButton :
			index = self.theTimeSlider.listKeys.index (self)
			itemFrame = self.mainWindow.uiFramesTW.topLevelItem (index)

			self.mainWindow.clickedItem =itemFrame    
			self.mainWindow.popup_menu.exec_(event.globalPos())        

		elif event.button() == QtCore.Qt.LeftButton  :         

			self.globalX = event.globalX ()  
			self.prevPos =  self.pos()
			self.prevTime = self.theTime
			
			startpb = cmds.playbackOptions  (q=True,minTime=True)
			endpb = cmds.playbackOptions  (q=True,maxTime=True)
			
			self.startPos = self.theTimeSlider .width () / 100. * .5 
			self.oneKeySize =  (self.theTimeSlider .width () - self.startPos *2.) / (endpb-startpb+1.)
					 
			self.setStyleSheet (self.pressedColor)
	
			#self.mainWindow.listKeysToMove = [(el, el.theTime) for el in self.theTimeSlider.getSortedListKeysObj() if el.checked ]
							
			self.start = startpb
			self.end = endpb            
			self.startpb = startpb

			if self.duplicateMode : 
				self.theTimeSlider.addDisplayKey (self.prevTime, isEmpty = self.isEmpty)

			"""
			super (KeyFrameBtn, self ).mousePressEvent (event)
		else : 
			super (KeyFrameBtn, self ).mousePressEvent (event)
			"""
		#print "end mousePress event"

	def mouseReleaseEvent(self,event):
		super (KeyFrameBtn, self ).mouseReleaseEvent (event)
		if self.prevTime != self.theTime :   
			
			if self.duplicateMode : 
				self.mainWindow.duplicateFrame (self.prevTime,self.theTime)
			else : 
				#poseName = cmds.getAttr (self.mainWindow.currentPose+".poseName")
				#listDeformationsFrame = cmds.blurSculpt (self.mainWindow.currentBlurNode,query = True,listFrames = True, poseName=str(poseName) )
				listDeformationsFrame = self.mainWindow.getListDeformationFrames ()

				if self.theTime in listDeformationsFrame :
					self.mainWindow.refresh ()
				else :
					cmds.undoInfo (undoName="moveSeveralKeys",openChunk = True)         
					self.updatePosition ()
					self.doChangeTime ()
					cmds.undoInfo (undoName="moveSeveralKeys",closeChunk = True)            

	def doChangeTime (self):
		index = self.theTimeSlider.listKeys.index (self)
		itemFrame = self.mainWindow.uiFramesTW.topLevelItem (index)
		itemFrame.setText (0,str(self.theTime))
		# check if refresh is necessary
		self.mainWindow.refreshListFramesAndSelect (  self.theTime)         

	def enterEvent(self,event):    
		super (KeyFrameBtn, self ).enterEvent (event)
		self.setFocus()
		self.setStyleSheet (self.lightColor)

	def leaveEvent(self,event):
		super (KeyFrameBtn, self ).leaveEvent (event)
		
		if self.checked : self.setStyleSheet (self.lightColor)
		else : self.setStyleSheet (self.baseColor)        
	
	def select (self, addSel = False, selectInTree=True):
		if not addSel : 
			for el in self.theTimeSlider.listKeys :
				el.checked = False
				el.setStyleSheet (el.baseColor)
		self.checked = True
		cmds.evalDeferred (self.setFocus)        

		# select in parent : 
		if selectInTree : 
			with  toggleBlockSignals ([self.mainWindow.uiFramesTW] ):
				index = self.theTimeSlider.listKeys.index (self)
				itemFrame = self.mainWindow.uiFramesTW.topLevelItem (index)
				self.mainWindow.uiFramesTW.setCurrentItem(itemFrame)                    
		self.setStyleSheet (self.lightColor)
	
	def updatePosition (self, startPos=None,oneKeySize=None, start=None, end = None ):
		if start == None or end == None :
			start = cmds.playbackOptions  (q=True,minTime=True)
			end = cmds.playbackOptions  (q=True,maxTime=True)
			
		isVisible = self.theTime >= start and self.theTime <= end        
							
		self.setVisible (isVisible )                
		if isVisible:
			if oneKeySize == None or startPos == None :
				theTimeSlider_width = self.theTimeSlider .width ()  
				startPos =  theTimeSlider_width / 100. * .5            
				oneKeySize =  (theTimeSlider_width - startPos*2.) / (end -start+1.)
			 
			Xpos = (self.theTime - start ) *  oneKeySize  + startPos 
			self.move (Xpos , 15)
			if oneKeySize < 6 : self. resize (6, 40)
			else : self. resize (oneKeySize, 40)            

	def __init__ (self, theTime, theTimeSlider, isEmpty = False):
		super(KeyFrameBtn , self).__init__(None)        
		self.checked = False
		if isEmpty : 
			self.baseColor = self._colors["blueColor"]
			self.lightColor = self._colors["blueLightColor"]
		else:            
			self.baseColor = self._colors["redColor"]
			self.lightColor = self._colors["redLightColor"]

		self.isEmpty = isEmpty
		self.duplicateMode = False

		self.setCursor (QtGui.QCursor (QtCore.Qt.SplitHCursor))
		if theTime == int(theTime) : self.theTime = int(theTime)
		else : self.theTime = theTime 
		
		self.theTimeSlider = theTimeSlider
		self.mainWindow = theTimeSlider.mainWindow
				
		self.setParent (self.theTimeSlider)
		self.resize (6,40)
		self.setStyleSheet (self.baseColor)            
		
		cmds.evalDeferred (self.updatePosition )
		self.show()
	
class TheTimeSlider (QtWidgets.QWidget):
	
	def deleteKeys (self):
		#print "deleteKeys"
		toDelete = []+self.listKeys
		for keyFrameBtn in toDelete:
		   keyFrameBtn.delete () 
		self.listKeys = []

	def getSortedListKeysObj (self):
		return sorted (self.listKeys, key=lambda ky : ky.theTime )        
	
	def addDisplayKey (self, theTime, isEmpty=False):
		keyFrameBtn = KeyFrameBtn (theTime, self, isEmpty=isEmpty) 
		self.listKeys .append ( keyFrameBtn )
		return keyFrameBtn 
		
	def updateKeys (self):
		#print "updateKeys"
		listKeys = self.getSortedListKeysObj ()
		listKeys .reverse()
		theTimeSlider_width = self.width ()
		
		start = cmds.playbackOptions  (q=True,minTime=True)
		end = cmds.playbackOptions  (q=True,maxTime=True)         
		startPos =  theTimeSlider_width / 100. * .5            
		oneKeySize =  (theTimeSlider_width - startPos*2.) / (end -start+1.)
		
		for keyObj in listKeys : keyObj.updatePosition (startPos = startPos ,oneKeySize = oneKeySize, start =start, end = end)

	def resizeEvent (self,e):
		self.theTimePort.resize(e.size().width(),30)
		self.updateKeys ()
		super(TheTimeSlider, self).resizeEvent (e)    
	  
	def __init__ (self, mainWindow):                    
		super(TheTimeSlider , self).__init__(None)
		self.mainWindow = mainWindow
		
		self.listKeys = []
		#self.theTimePort = timePort.theTimePort
		#self.mayaMainWindow = timePort.mayaWindowLayout        

		#theWindowForQtObjects = getQTObject ()
		theWindowForQtObjects = self.mainWindow.theWindowForQtObjects
		cmds.setParent ("tmpWidgetsWindow|qtLayoutObjects")        
		# cmds.setParent ("MayaWindow|formLayout1|qtLayoutObjects")
		cmdsTimePort = cmds.timePort( 'skinFixingTimePort', w=10, h=20, snap=True, globalTime=True,enableBackground=True, bgc = [.5,.5,.6])
		# self.theTimePort = gui_utils.qtLayoutObject.children() [-1]                
		self.theTimePort = theWindowForQtObjects .children() [-1]  

		
		self.theTimePort.setParent (self)
		self.theTimePort.show()
		
		self.setMaximumHeight (40) 
		self.setMinimumHeight (40)

class WaitCursorCtxt(object):
	def __init__(self, raise_error=True):
		self.raise_error = raise_error        
	def __enter__(self):
		cmds.waitCursor (state=True)
	def __exit__(self, exc_type, exc_val, exc_tb):
		if cmds.waitCursor (q=True, state=True) : cmds.waitCursor (state=False)



"""

		theWindowForQtObjects = getQTObject ()

		cmds.setParent ("tmpWidgetsWindow|qtLayoutObjects")        
		# cmds.setParent ("MayaWindow|formLayout1|qtLayoutObjects")
		cmdsTimePort = cmds.timePort( 'skinFixingTimePort', w=10, h=20, snap=True, globalTime=True,enableBackground=True, bgc = [.5,.5,.6])
		# self.theTimePort = gui_utils.qtLayoutObject.children() [-1]                
		self.theTimePort = theWindowForQtObjects .children() [-1]  

		
		self.theTimePort.setParent (self)
"""