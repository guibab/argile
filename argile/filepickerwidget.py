##
#   :namespace  python.blurdev.gui.widgets.filepickerwidget.filepickerwidget
#
#	:remarks	Defines the FilePickerWidget class
#	
#	:author		beta@blur.com
#	:author		Blur Studio
#	:date		10/06/10
#

from Qt.QtCore import Qt, Property, Signal, Slot
from Qt.QtGui import QColor
from Qt.QtWidgets import QApplication, QFileDialog, QHBoxLayout, QLineEdit, QToolButton, QWidget
from Qt import QtCompat
import os.path

resolvedStylesheetDefault = """QLineEdit {color: rgba%(fg)s;
	background: rgba%(bg)s;
}"""

class LineEdit(QLineEdit):
	def dragEnterEvent(self, event):
		if not self.isReadOnly():
			event.acceptProposedAction()
		else:
			super(LineEdit, self).dragEnterEvent(event)
	
	def dropEvent(self, event):
		mimeData = event.mimeData()
		if not self.isReadOnly() and mimeData.hasUrls():
			urlList = mimeData.urls()
			if urlList:
				fname = urlList[0].toLocalFile()
				self.setText(fname)
		event.acceptProposedAction()

class FilePickerWidget( QWidget ):
	filenamePicked 	= Signal(str)
	filenameChanged = Signal(str)
	filenameEdited	= Signal(str)
	
	def __init__( self, parent=None ):
		self._correctBackground = QColor(156, 206, 156, 255)
		self._correctForeground = QColor(Qt.white)
		self._inCorrectBackground = QColor(210, 156, 156, 255)
		self._inCorrectForeground = QColor(Qt.white)
		self._defaultLocation = ''
		QWidget.__init__( self, parent )
		
		self.uiFilenameTXT = LineEdit(self)
		self.uiPickFileBTN = QToolButton(self)
		self.uiPickFileBTN.setText('...')
		self.uiPickFileBTN.setToolTip('<html><head/><body><p>Browse to a file path.</p><p>Ctrl + LMB: Explore to current path.</p></body></html>')
		# Make this widget focusable and pass the widget focus to uiFilenameTXT
		self.setFocusProxy(self.uiFilenameTXT)
		self.setFocusPolicy(Qt.StrongFocus)
		layout = QHBoxLayout(self)
		layout.addWidget(self.uiFilenameTXT)
		layout.addWidget(self.uiPickFileBTN)
		layout.setContentsMargins(0, 0, 0, 0)
		self.setLayout(layout)
		
		self._caption = "Pick file..."
		self._filters = "All Files (*.*)"
		self._pickFolder = False
		self._openFile = False
		self._resolvePath = False
		#self._imageSequence = False
		self._resolved = False
		self._chosenPath = None
		#self._imageSequenceFormat = '{pre}[{firstNum}:{lastNum}]{post}'
			
		self.uiFilenameTXT.textChanged.connect( self.emitFilenameChanged )

		self.uiFilenameTXT.editingFinished.connect( self.emitFilenameEdited )
		self.uiPickFileBTN.clicked.connect( self.pickPath )
		self.resolvedStylesheet = resolvedStylesheetDefault
		
		self.resolve()
	
	def caption( self ):
		return self._caption

	def emitFilenameChanged( self ):
		self.resolve()
		if ( not self.signalsBlocked() ):
			self.filenameChanged.emit( self.uiFilenameTXT.text() )
	
	def emitFilenameEdited( self ):
		if ( not self.signalsBlocked() ):
			self.filenameEdited.emit( self.uiFilenameTXT.text() )
	
	def filePath( self ):
		# if it's an image sequence, return the last chosen image path
		return self._chosenPath or self.uiFilenameTXT.text()
	def filters( self ):
		return self._filters
	
	def isResolved( self ):
		return self._resolved		
	
	def openFile( self ):
		return self._openFile
	
	def pickFolder( self ):
		return self._pickFolder
	
	def pickPath( self ):
		initialPath = self.uiFilenameTXT.text() or self.defaultLocation
		initialPath = str (initialPath)
		while not os.path.exists(initialPath):
			if os.path.dirname(initialPath) == initialPath:
				break
			else:
				initialPath = os.path.dirname(initialPath)
		if QApplication.keyboardModifiers() == Qt.ControlModifier:
			import blurdev
			blurdev.osystem.explore(initialPath)
		else:
			if self._pickFolder:
				filepath = QFileDialog.getExistingDirectory(self, self._caption, initialPath)
			elif self._openFile:
				filepath, _ = QtCompat.QFileDialog.getOpenFileName(self, self._caption, initialPath, self._filters)
			else:
				filepath, _ = QtCompat.QFileDialog.getSaveFileName(self, self._caption, initialPath, self._filters)
			if filepath:
				self.uiFilenameTXT.setText( filepath )
				if ( not self.signalsBlocked() ):
					self.filenamePicked.emit( filepath )
	
	def resolve( self ):
		if self.resolvePath():
			path = self.uiFilenameTXT.text()
			if self._pickFolder:
				valid = os.path.isdir(path)
			else:
				valid = os.path.isfile(path)
			if valid:
				fg = self.correctForeground
				bg = self.correctBackground
				self._resolved = True
			else:
				fg = self.inCorrectForeground
				bg = self.inCorrectBackground
				self._resolved = False
				
			style = self.resolvedStylesheet % {'bg':bg.getRgb(), 'fg':fg.getRgb()}
		else:
			style = ''
			self._resolved = False
			
		self.uiFilenameTXT.setStyleSheet(style)
	
	def resolvePath( self ):
		return self._resolvePath
	
	def setCaption( self, caption ):
		self._caption = caption
	
	@Slot(str)
	def setFilePath( self, filePath ):
		self.uiFilenameTXT.setText( filePath )
		self.resolve()
		
	def setFilters( self, filters ):
		self._filters = filters
	
	def setOpenFile( self, state ):
		self._openFile = state
	
	def setPickFolder( self, state ):
		self._pickFolder = state
	
	@Slot(bool)
	def setNotResolvePath( self, state ):
		""" Set resolvePath to the oposite of state. """
		self.setResolvePath( not state )
	
	@Slot(bool)
	def setResolvePath( self, state ):
		self._resolvePath = state
		self.resolve()

	pyCaption		= Property( "QString", caption, setCaption )
	pyFilters		= Property( "QString", filters, setFilters )
	pyPickFolder	= Property( "bool", pickFolder, setPickFolder )
	pyOpenFile		= Property( "bool", openFile, setOpenFile )
	pyResolvePath	= Property( "bool", resolvePath, setResolvePath )
	#pyImageSequence	= Property( "bool", imageSequence, setImageSequence )
	pyFilePath		= Property( "QString", filePath, setFilePath )
	
	# Load the colors from the stylesheets
	@Property(QColor)
	def correctBackground(self):
		return self._correctBackground
	
	@correctBackground.setter
	def correctBackground(self, color):
		self._correctBackground = color
		self.resolve()
	
	@Property(QColor)
	def correctForeground(self):
		return self._correctForeground
	
	@correctForeground.setter
	def correctForeground(self, color):
		self._correctForeground = color
		self.resolve()

	@Property(QColor)
	def inCorrectBackground(self):
		return self._inCorrectBackground
	
	@inCorrectBackground.setter
	def inCorrectBackground(self, color):
		self._inCorrectBackground = color
		self.resolve()
	
	@Property(QColor)
	def inCorrectForeground(self):
		return self._inCorrectForeground
	
	@inCorrectForeground.setter
	def inCorrectForeground(self, color):
		self._inCorrectForeground = color
		self.resolve()
	
	@Property("QString")
	def defaultLocation(self):
	    return self._defaultLocation

	@defaultLocation.setter
	def defaultLocation(self, value):
		self._defaultLocation = str(value)
