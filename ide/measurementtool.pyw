import sys
import getopt


from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *
from pyview.ide.preferences import *
import pickle
import cPickle
import copy


from pyview.lib.patterns import ObserverWidget,KillableThread
if 'pyview.lib.ramps' in sys.modules:
  reload(sys.modules['pyview.lib.ramps'])
from pyview.lib.ramps import *
from pyview.config.parameters import *
from pyview.lib.datacube import Datacube
from pyview.helpers.datamanager import DataManager
from pyview.ide.codeeditor import CodeEditor
from pyview.helpers.coderunner import CodeRunner
from pyview.lib.classes import *
    
class RampModel(QAbstractItemModel):
  
  def __init__(self,root,editor = None,parent = None):
    QAbstractItemModel.__init__(self,parent)
    self._root = root
    self._rampList = []
    self._dropAction = Qt.MoveAction
    self._mimeData = None
        
  def dump(self):
    return {"root":self._root.tostring()}    
    
  def load(self,params):
    self._root = Ramp.fromstring(params["root"])
    
  def deleteRamp(self,index):
    parent = self.parent(index)
    
    ramp = self.getRamp(index)
    
    parentRamp = self.getRamp(parent)
    
    if parentRamp == None:
      parentRamp = self._root
    
    self.beginRemoveRows(parent,index.row(),index.row())
    
    parentRamp.removeChild(ramp)
    
    self.endRemoveRows()
    
  def getIndex(self,ramp):
    if ramp in self._rampList:
      return self._rampList.index(ramp)
    self._rampList.append(ramp)
    index = self._rampList.index(ramp)
    return index
    
  def getRamp(self,index):
    if not index.isValid():
      return self._root
    return self._rampList[index.internalId()]
    
  def parent(self,index):
    if index == QModelIndex():
      return QModelIndex()
    node = self.getRamp(index)
    if node == None:
      return QModelIndex()  
    if node.parent() == None:
      return QModelIndex()
    if node.parent().parent() == None:
      return QModelIndex()
    else:
      grandparent = node.parent().parent()
      row = grandparent.children().index(node.parent())
      return self.createIndex(row,0,self.getIndex(node.parent()))

  def hasChildren(self,index):
    ramp = self.getRamp(index)
    if ramp == None:
      return True
    if ramp.hasChildren():
      return True
    return False
    
  def data(self,index,role = Qt.DisplayRole):
    ramp = self.getRamp(index)
    if role == Qt.DisplayRole:
      return QVariant(ramp.name())
    return QVariant()
    
  def index(self,row,column,parent):
    parentRamp = self.getRamp(parent)
    if parentRamp == None:
      if row < len(self._root.children()):
        return self.createIndex(row,column,self.getIndex(self._root.children()[row]))
    elif row < len(parentRamp.children()):
      return self.createIndex(row,column,self.getIndex(parentRamp.children()[row]))
    return QModelIndex()
    
  def columnCount(self,parent):
    return 1

  def supportedDropActions(self):
    return Qt.MoveAction | Qt.CopyAction | Qt.LinkAction
    
  def setDropAction(self,action):
    self._dropAction = action
    
  def rowCount(self,parent):
    if not parent.isValid():
      return len(self._root.children())
    ramp = self.getRamp(parent)
    return len(ramp.children())    

  def flags(self,index):
    defaultFlags = QAbstractItemModel.flags(self,index)
    if index.isValid():
      return Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled | defaultFlags
    else:
      return Qt.ItemIsDropEnabled | defaultFlags

  def mimeData(self,indexes):
    self._mimeData = indexes
    return QAbstractItemModel.mimeData(self,indexes)

  def addRamp(self,ramp):
    self.beginInsertRows(QModelIndex(),0,0)
    self._root.insertChild(0,ramp)
    self.endInsertRows()
    
  def dropMimeData(self,data,action,row,column,parent):
    print "Ended in row %d" % row
    if row == -1:
      row = 0
    if data != None:
      parentRamp = self.getRamp(parent)
      if parentRamp == None or isinstance(parentRamp,RampReference):
        return False
      if self._dropAction == Qt.MoveAction:
        for index in self._mimeData:
          oldParent = index.parent()
          oldParentRamp = self.getRamp(oldParent)
          ramp = self.getRamp(index)
          rowOfChild = oldParentRamp.children().index(ramp)
          if oldParentRamp == parentRamp and rowOfChild == row:
            return False
          self.beginMoveRows(oldParent,rowOfChild,rowOfChild,parent,row)
          oldParentRamp.removeChild(ramp)
          parentRamp.insertChild(row,ramp)
          self.endMoveRows()
      elif self._dropAction == Qt.LinkAction:
        for index in self._mimeData:
          self.beginInsertRows(parent,row,row)
          ramp = self.getRamp(index)
          parentRamp.insertChild(row,RampReference(ramp))
          self.endInsertRows()
      else:
        for index in self._mimeData:
          self.beginInsertRows(parent,row,row)
          ramp = self.getRamp(index)
          if isinstance(ramp,RampReference):
            newRamp = RampReference(ramp)
          else:
            newRamp = copy.deepcopy(ramp)
          parentRamp.insertChild(row,newRamp)
          self.endInsertRows()
    return True

import pyview.ide.mpl.backend_agg as mpl_backend

class RampTree(QTreeView):

  def __init__(self,parent = None):
    QTreeView.__init__(self,parent)
    self._editor = None
    self.setContextMenuPolicy(Qt.CustomContextMenu)
    self.connect(self, SIGNAL("customContextMenuRequested(const QPoint &)"), self.getContextMenu)

  def dropEvent(self,e):

    menu = QMenu()
    
    copyAction = menu.addAction("Copy")
    moveAction = menu.addAction("Move")
    linkAction = menu.addAction("Link")
      
    action = menu.exec_(self.viewport().mapToGlobal(e.pos()))
    
    model = self.model()
    
    if action == copyAction:
      model.setDropAction(Qt.CopyAction)
    elif action == moveAction:
      model.setDropAction(Qt.MoveAction)
    elif action == linkAction:
      model.setDropAction(Qt.LinkAction)

    QAbstractItemView.dropEvent(self,e)



  def renameRamp(self):

    selectedItems = self.selectedIndexes()
    if len(selectedItems) == 1:
      
      index = selectedItems[0]
      ramp = self.model().getRamp(index)
    
      if ramp == None or isinstance(ramp,RampReference):
        return
    
      dialog = QInputDialog()
      dialog.setWindowTitle("Change Ramp Name")
      dialog.setLabelText("New name")
      dialog.setTextValue(ramp.name())
      
      dialog.exec_()
      
      if dialog.result() == QDialog.Accepted:
        ramp.setName(str(dialog.textValue()))
      
    

  def deleteRamp(self):
  
    message = QMessageBox(QMessageBox.Question,"Confirm deletion","Are you sure that you want to delete this ramp?", QMessageBox.Yes | QMessageBox.No)
    
    message.exec_()
    
    if message.standardButton(message.clickedButton()) != QMessageBox.Yes:
      return 
  
    selectedItems = self.selectedIndexes()
    if len(selectedItems) == 1:
      self.model().deleteRamp(selectedItems[0])

  def getContextMenu(self,p):
    menu = QMenu()
    
    selectedItems = self.selectedIndexes()
    
    if len(selectedItems) == 1:
      renameAction = menu.addAction("Rename")
      self.connect(renameAction,SIGNAL("triggered()"),self.renameRamp)
      deleteAction = menu.addAction("Delete")
      self.connect(deleteAction,SIGNAL("triggered()"),self.deleteRamp)
      
    menu.exec_(self.viewport().mapToGlobal(p))
    
  def setTool(self,tool):
    self._tool = tool
    
  def selectionChanged(self,selected,deselected):
    if len(selected.indexes()) == 1:
      ramp = self.model().getRamp(selected.indexes()[0])
      if isinstance(ramp,RampReference):
        self._tool.setRamp(None)
      if self._tool != None:
        self._tool.setRamp(ramp)
    else:
      if self._tool != None:
        self._tool.setRamp(None)
    QTreeView.selectionChanged(self,selected,deselected)

class RunWindow(QWidget,ObserverWidget):

  def __init__(self,editor,treeview,codeRunner,parent = None):
    QWidget.__init__(self,parent)
    ObserverWidget.__init__(self)
    
    self._editor = editor
    self._treeview = treeview
    self._codeRunner = codeRunner
    self._ramp = None

    rampButtons = QBoxLayout(QBoxLayout.LeftToRight)
    
    self.runButton = QPushButton("Run")
    self.pauseButton = QPushButton("Pause")
    self.stopButton = QPushButton("Stop")
    self.killButton = QPushButton("Terminate")

    self.rampName = QLabel("")

    rampButtons.addWidget(self.runButton)
    rampButtons.addWidget(self.pauseButton)
    rampButtons.addWidget(self.stopButton)
    rampButtons.addWidget(self.killButton)
    rampButtons.addStretch()

    self.rampProgress = QSlider(Qt.Horizontal)
    
    self.rampProgress.setMinimum(0)
    self.rampProgress.setMaximum(100)
    self.rampProgress.setValue(50)

    self.connect(self.runButton,SIGNAL("clicked()"),self.runRamp)
    self.connect(self.pauseButton,SIGNAL("clicked()"),self.pauseRamp)
    self.connect(self.stopButton,SIGNAL("clicked()"),self.stopRamp)
    self.connect(self.killButton,SIGNAL("clicked()"),self.killRamp)
    
    layout = QGridLayout()
    
    layout.addWidget(self.rampName)
    layout.addItem(rampButtons)
    layout.addWidget(self.rampProgress)
    
    self.setLayout(layout)
        
  def updatedGui(self,object,property,value = None):
    if object == self.ramp():
      self.updateInterface()
      if property == "currentValue":
        self.rampProgress.setEnabled(True)
        self.rampProgress.setValue(self.ramp().progress())    
      if property == "stopped":
        self.stopRamp()

  def ramp(self):
    if isinstance(self._ramp,RampReference):
      return self._ramp.ramp()
    else:
      return self._ramp

  def updateInterface(self):
  
    rampTreeStatus = True
    stopStatus = False
    pauseStatus = False
    runStatus = False    
    editorStatus = True
    
    ramp = self.ramp()
    
    if ramp != None:
      runStatus = True
      if ramp.isRunning():
        pauseStatus = True
        stopStatus = True
        runStatus = False
        editorStatus = False
        rampTreeStatus = False
      elif ramp.isPaused():
        pauseStatus = False
        stopStatus = True
        runStatus = True
        rampTreeStatus = True
        
    self._treeview.setEnabled(rampTreeStatus)
    self._editor.setEnabled(editorStatus)
    self.runButton.setEnabled(runStatus)
    self.pauseButton.setEnabled(pauseStatus)
    self.stopButton.setEnabled(stopStatus)
    
    if self._codeRunner.isExecutingCode(self):
      self.killButton.setEnabled(True)
    else:
      self.killButton.setEnabled(False)
    
  def setRamp(self,ramp):
    if self.ramp() != None:
      if self.ramp().isRunning() or self.ramp().isPaused():
        return
      self.ramp().detach(self)
    self._ramp = ramp
    if ramp != None:
      self.ramp().attach(self)
      self.rampName.setText("Running Ramp:" + self.ramp().name())

  def runRamp(self):
    if self.ramp() == None:
      return
    if self.ramp().isPaused():
      self.ramp().fullResume()
      return
    if self._codeRunner.isExecutingCode(self):
      return
    datacube = Datacube()
    manager = DataManager()
    manager.addDatacube(datacube)
    lv = dict()
    lv["lv"] = lv
    lv["gv"] = self._codeRunner.gv()
    lv["ramp"] = self._ramp
    lv["datacube"] = datacube
    code = """ramp.run(datacube = datacube,gv = gv,lv = lv)"""
    self._codeRunner.executeCode(code,self,"<ramp:%s>" % self._ramp.name(),lv = lv,gv = lv)
    
  def killRamp(self):
    if self._codeRunner.isExecutingCode(self):
      self._codeRunner.stopExecution(self)
    
  def pauseRamp(self):  
    if self.ramp() == None:
      return
    self.ramp().fullPause()
    
  def stopRamp(self):
    if self.ramp() == None:
      return
    self.ramp().fullStop()
    self.rampProgress.setValue(100)
    self._runRamp = None


class MeasurementTool(QMainWindow,ObserverWidget):

  def setRamp(self,ramp):
    self.rampEditor.setRamp(ramp)
    self.runWindow.setRamp(ramp)
    
  def onTimer(self):
    self.save()
      
  def __init__(self,codeRunner,parent = None):
    QMainWindow.__init__(self,parent)
    ObserverWidget.__init__(self)
    
    self._timer = QTimer(self)
    
    self._codeRunner = codeRunner
    
    self._timer.setInterval(1000*60)
    
    self._timer.start()
    
    self.connect(self._timer,SIGNAL("timeout()"),self.onTimer)
    
    self.setAttribute(Qt.WA_DeleteOnClose,True)
    
    self._runRamp = None
  
    self.preferences = Preferences(filename = "measurementtool")
  
    self.rampName = QLineEdit()
    self.addRampButton = QPushButton("Add Ramp")
    
    buttonsLayout = QBoxLayout(QBoxLayout.LeftToRight)
    buttonsLayout.addWidget(self.rampName)
    buttonsLayout.addWidget(self.addRampButton)
    buttonsLayout.addStretch()
    
    self.setWindowTitle("Measurement Tool")
    self.setMinimumSize(800,600)

    self.saveButton = QPushButton("Save")
    
    self.rampTree = RampTree()

    self.rampTree.setDragEnabled(True)
    self.rampTree.setDragDropMode(QAbstractItemView.InternalMove)

    widget = QWidget()
    
    self.rampEditor = RampEditor()
    self.rampTree.setTool(self)
    
    rightLayout = QBoxLayout(QBoxLayout.TopToBottom)
    
    self.runWindow = RunWindow(treeview = self.rampTree,codeRunner = codeRunner,editor = self.rampEditor)
    
    rightLayout.addWidget(self.runWindow)
    rightLayout.addWidget(self.rampEditor)
    
    layout = QGridLayout()
    layout.addWidget(self.rampTree,0,0,1,1)
    layout.addLayout(buttonsLayout,1,0,1,1)
    layout.addLayout(rightLayout,0,1,2,1)
    
    self.connect(self.rampName,SIGNAL("returnPressed()"),self.rampCreationRequested)

    widget.setLayout(layout)
    
    self.setCentralWidget(widget)
    
    self._root = ParameterRamp()
    
    self._rampModel = RampModel(self._root)
    self.rampTree.setModel(self._rampModel)

    self.restore()
    
  def currentRamp(self):
    return self._rampModel.getRamp(self.rampTree.currentIndex())
    
  def rampCreationRequested(self):
    name = str(self.rampName.text())

    ramp = ParameterRamp()
    ramp.setName(name)

    self._rampModel.addRamp(ramp)

  def save(self):
    dump = self._rampModel.dump()
    self.preferences.set("measurementTool.ramps",dump)
    self.preferences.save() 
    
  def restore(self):
    try:
      ramps = self.preferences.get("measurementTool.ramps")
      self._rampModel.load(ramps)  
    except KeyError:
      print sys.exc_info()
      print "Error"
    
  def closeEvent(self,e):
    print "Closing..."
    self.save()
    QMainWindow.closeEvent(self,e) 

class RampEditor(QWidget,ObserverWidget):
  
  def setRamp(self,root): 
    if isinstance(root,RampReference):
      self.tabs.setEnabled(False)
    else:
      self.tabs.setEnabled(True)
    self.setEnabled(True)
    self.root = root
    self.updateRampInfo()

  def updateRampInfo(self):
    if self.root != None:
      if isinstance(self.root,RampReference):
        self.rampRangeGenerator.setPlainText(self.root.initialization())
        return
      self.rampGenerator.setPlainText(self.root.generator())
      self.rampRangeGenerator.setPlainText(self.root.rangeGenerator())
      self.rampCode.setPlainText(self.root.code())
      self.rampFinish.setPlainText(self.root.finish())
    else:
      self.rampGenerator.setPlainText("")
      self.rampRangeGenerator.setPlainText("")
      self.rampCode.setPlainText("")
      self.rampFinish.setPlainText("")

  def updateRampProperty(self,property = None,all = False):
    if self.root == None:
      return
    if isinstance(self.root,RampReference):
      if  property == "rangeGenerator" or all:
        self.root.setInitialization(self.rampRangeGenerator.toPlainText())
      return
    if self.root.isRunning() and not self.root.isPaused():
      return
    if property == "code" or all:
      self.root.setCode(self.rampCode.toPlainText())
    if property == "finish" or all:
      self.root.setFinish(self.rampFinish.toPlainText())
    elif property == "generator" or all:
      self.root.setGenerator(self.rampGenerator.toPlainText())
    elif property == "rangeGenerator" or all:
      self.root.setRangeGenerator(self.rampRangeGenerator.toPlainText())
             
  def __init__(self,parent = None):
    QWidget.__init__(self,parent)
    ObserverWidget.__init__(self)
    self.root = None
    
    self.rampRangeGenerator = CodeEditor()
    self.rampCode = CodeEditor()
    self.rampGenerator = CodeEditor()
    self.rampFinish = CodeEditor()

    self.tabs = QTabWidget()
    
    self.tabs.addTab(self.rampGenerator,"Initialization")
    self.tabs.addTab(self.rampCode,"Code")
    self.tabs.addTab(self.rampFinish,"Cleanup")

    layout = QGridLayout()
    
    codeLayout = QGridLayout()
        
    self.rampRangeGenerator.setFixedHeight(100)
        
    layout.addWidget(QLabel("Generator"))
    layout.addWidget(self.rampRangeGenerator)
    layout.addWidget(self.tabs)
    
    self.connect(self.rampCode,SIGNAL("textChanged()"),lambda property = "code":self.updateRampProperty(property))
    self.connect(self.rampFinish,SIGNAL("textChanged()"),lambda property = "finish":self.updateRampProperty(property))
    self.connect(self.rampGenerator,SIGNAL("textChanged()"),lambda property = "generator":self.updateRampProperty(property))
    self.connect(self.rampRangeGenerator,SIGNAL("textChanged()"),lambda property = "rangeGenerator":self.updateRampProperty(property))
    
    self.rampCode.activateHighlighter()
    self.rampFinish.activateHighlighter()
    self.rampGenerator.activateHighlighter()    
    self.preferences = Preferences()
    self.setAttribute(Qt.WA_DeleteOnClose,True)
    self.updateRampInfo()
    self.setLayout(layout)
    
    