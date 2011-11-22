import sys
import getopt
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *
import pickle
import cPickle
import copy
import yaml
import datetime
import time

from pyview.config.parameters import params
from pyview.ide.patterns import ObserverWidget
from pyview.lib.patterns import KillableThread
from pyview.config.parameters import *
from pyview.lib.datacube import Datacube
from pyview.helpers.datamanager import DataManager
from pyview.ide.editor.codeeditor import CodeEditor

from pyview.helpers.coderunner import CodeRunner
from pyview.lib.classes import *

class CodeSnippet(Subject):

  def __init__(self,name = "noname"):
    Subject.__init__(self)
    self._children = []
    self._name = name
    self._codeSnippet = ""
    self._parent = None

  def parent(self):
    return self._parent
    
  def codeSnippet(self):
    return self._codeSnippet
    
  def setCodeSnippet(self,codeSnippet):
    self._codeSnippet = codeSnippet
    
  def setParent(self,parent):
    self._parent = parent

  def tostring(self,usePickle = True):
    if usePickle:
      return pickle.dumps(self)
    state = dict()
    state["codeSnippet"] = self._codeSnippet
    state["name"] = self._name
    state["children"] = []
    for child in self.children():
      state["children"].append(child.tostring(usePickle = usePickle))
    return state

  def fromstring(cls,state,usePickle = True):
    if usePickle:
      return pickle.loads(state)
    ramp = CodeSnippet()
    ramp.setCodeSnippet(state["codeSnippet"])
    ramp.setName(state["name"])
    for child in state["children"]:
      ramp.addChild(CodeSnippet.fromstring(child,usePickle = usePickle))
    return ramp

  fromstring = classmethod(fromstring)

  def len(self):
    return len(self._children)

  def clear(self):
    self._children = []
    self.notify("clear")

  def name(self):
    return self._name
  
  def setName(self,name):
    self._name = name

  def children(self,name = None):
    if name == None:
      return self._children
    else:
      children = []
      for child in self._children:
        if child.name() == name:
          children.append(child)
      return children
      
  def root(self):
    currentNode = self
    while currentNode.parent() != None:
      currentNode = currentNode.parent()
    return currentNode

  def offspring(self,path):
    names = path.split("/")
    node = self
    while len(names)>0:
      name = names.pop(0)
      children = node.children(name)
      if len(children) == 0:
        return None
      else:
        node = children[0]
    return node
    
  def hasChildren(self):
    if len(self._children) > 0:
      return True
    return False
    
  def insertChild(self,index,child):
    if not child in self._children:
      self._children.insert(index,child)
      child.setParent(self)
      self.notify("insertChild",[index,child])
    
  def addChild(self,child):
    if not child in self._children:
      self._children.append(child)
      child.setParent(self)
      self.notify("addChild",child)
    
  def removeChild(self,child):
    for i in range(0,len(self._children)):
      if child == self._children[i]:
        del self._children[i]
        child.setParent(None)
        self.notify("removeChild",child)
        return
    
class CodeSnippetModel(QAbstractItemModel):
  
  def __init__(self,root,editor = None,parent = None):
    QAbstractItemModel.__init__(self,parent)
    self._root = root
    self._codeSnippetList = []
    self._dropAction = Qt.MoveAction
    self._mimeData = None
    
  def headerData(self,section,orientation,role):
    if section == 1:
      return QVariant(QString(u"Measurement"))
        
  def dump(self,usePickle = True):
    return {"root":self._root.tostring(usePickle = usePickle)}    
    
  def load(self,params,usePickle = True):
    self.beginResetModel()
    self._root = CodeSnippet.fromstring(params["root"],usePickle = usePickle)
    self.endResetModel()
    
  def deleteCodeSnippet(self,index):
    parent = self.parent(index)
    
    codeSnippet = self.getCodeSnippet(index)
    
    parentCodeSnippet = self.getCodeSnippet(parent)
    
    if parentCodeSnippet == None:
      parentCodeSnippet = self._root
    
    self.beginRemoveRows(parent,index.row(),index.row())
    
    parentCodeSnippet.removeChild(codeSnippet)
    
    self.endRemoveRows()
    
  def getIndex(self,codeSnippet):
    if codeSnippet in self._codeSnippetList:
      return self._codeSnippetList.index(codeSnippet)
    self._codeSnippetList.append(codeSnippet)
    index = self._codeSnippetList.index(codeSnippet)
    return index
    
  def getCodeSnippet(self,index):
    if not index.isValid():
      return self._root
    return self._codeSnippetList[index.internalId()]
    
  def parent(self,index):
    if index == QModelIndex():
      return QModelIndex()
    node = self.getCodeSnippet(index)
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
    codeSnippet = self.getCodeSnippet(index)
    if codeSnippet == None:
      return True
    if codeSnippet.hasChildren():
      return True
    return False
    
  def data(self,index,role = Qt.DisplayRole):
    codeSnippet = self.getCodeSnippet(index)
    if role == Qt.DisplayRole:
      return QVariant(codeSnippet.name())
    return QVariant()
    
  def index(self,row,column,parent):
    parentCodeSnippet = self.getCodeSnippet(parent)
    if parentCodeSnippet == None:
      if row < len(self._root.children()):
        return self.createIndex(row,column,self.getIndex(self._root.children()[row]))
    elif row < len(parentCodeSnippet.children()):
      return self.createIndex(row,column,self.getIndex(parentCodeSnippet.children()[row]))
    return QModelIndex()
    
  def columnCount(self,parent):
    return 1

  def supportedDropActions(self):
    return Qt.MoveAction | Qt.CopyAction
    
  def setDropAction(self,action):
    self._dropAction = action
    
  def rowCount(self,parent):
    if not parent.isValid():
      return len(self._root.children())
    codeSnippet = self.getCodeSnippet(parent)
    return len(codeSnippet.children())    

  def flags(self,index):
    defaultFlags = QAbstractItemModel.flags(self,index)
    if index.isValid():
      return Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled | defaultFlags
    else:
      return Qt.ItemIsDropEnabled | defaultFlags

  def mimeData(self,indexes):
    self._mimeData = indexes
    return QAbstractItemModel.mimeData(self,indexes)

  def addCodeSnippet(self,codeSnippet):
    self.beginInsertRows(QModelIndex(),0,0)
    self._root.insertChild(0,codeSnippet)
    self.endInsertRows()
    
  def dropMimeData(self,data,action,row,column,parent):
    print "Ended in row %d" % row
    if row == -1:
      row = 0
    if data != None:
      parentCodeSnippet = self.getCodeSnippet(parent)
      if parentCodeSnippet == None:
        return False
      if self._dropAction == Qt.MoveAction:
        for index in self._mimeData:
          oldParent = index.parent()
          oldParentCodeSnippet = self.getCodeSnippet(oldParent)
          codeSnippet = self.getCodeSnippet(index)
          rowOfChild = oldParentCodeSnippet.children().index(codeSnippet)
          if oldParentCodeSnippet == parentCodeSnippet and rowOfChild == row:
            return False
          self.beginMoveRows(oldParent,rowOfChild,rowOfChild,parent,row)
          oldParentCodeSnippet.removeChild(codeSnippet)
          parentCodeSnippet.insertChild(row,codeSnippet)
          self.endMoveRows()
      else:
        for index in self._mimeData:
          self.beginInsertRows(parent,row,row)
          codeSnippet = self.getCodeSnippet(index)
          newCodeSnippet = copy.deepcopy(codeSnippet)
          parentCodeSnippet.insertChild(row,newCodeSnippet)
          self.endInsertRows()
    return True

import pyview.ide.mpl.backend_agg as mpl_backend

class CodeSnippetTree(QTreeView):

  def __init__(self,parent = None):
    QTreeView.__init__(self,parent)
    self._editor = None
    self.setContextMenuPolicy(Qt.CustomContextMenu)
    self.connect(self, SIGNAL("customContextMenuRequested(const QPoint &)"), self.getContextMenu)

  def dropEvent(self,e):

    menu = QMenu()
    
    copyAction = menu.addAction("Copy")
    moveAction = menu.addAction("Move")
      
    action = menu.exec_(self.viewport().mapToGlobal(e.pos()))
    
    model = self.model()
    
    if action == copyAction:
      model.setDropAction(Qt.CopyAction)
    else:
      model.setDropAction(Qt.MoveAction)

    QAbstractItemView.dropEvent(self,e)

  def renameCodeSnippet(self):

    selectedItems = self.selectedIndexes()
    if len(selectedItems) == 1:
      
      index = selectedItems[0]
      codeSnippet = self.model().getCodeSnippet(index)
    
      if codeSnippet == None:
        return
    
      dialog = QInputDialog()
      dialog.setWindowTitle("Change CodeSnippet Name")
      dialog.setLabelText("New name")
      dialog.setTextValue(codeSnippet.name())
      
      dialog.exec_()
      
      if dialog.result() == QDialog.Accepted:
        codeSnippet.setName(str(dialog.textValue()))
      
  def deleteCodeSnippet(self):
  
    message = QMessageBox(QMessageBox.Question,"Confirm deletion","Are you sure that you want to delete this codeSnippet?", QMessageBox.Yes | QMessageBox.No)
    
    message.exec_()
    
    if message.standardButton(message.clickedButton()) != QMessageBox.Yes:
      return 
  
    selectedItems = self.selectedIndexes()
    if len(selectedItems) == 1:
      self.model().deleteCodeSnippet(selectedItems[0])

  def getContextMenu(self,p):
    menu = QMenu()
    selectedItems = self.selectedIndexes()
    if len(selectedItems) == 1:
      renameAction = menu.addAction("Rename")
      self.connect(renameAction,SIGNAL("triggered()"),self.renameCodeSnippet)
      deleteAction = menu.addAction("Delete")
      self.connect(deleteAction,SIGNAL("triggered()"),self.deleteCodeSnippet)
    menu.exec_(self.viewport().mapToGlobal(p))
    
  def setTool(self,tool):
    self._tool = tool
    
  def selectionChanged(self,selected,deselected):
    if len(selected.indexes()) == 1:
      codeSnippet = self.model().getCodeSnippet(selected.indexes()[0])
      if self._tool != None:
        self._tool.setCodeSnippet(codeSnippet)
    else:
      if self._tool != None:
        self._tool.setCodeSnippet(None)
    QTreeView.selectionChanged(self,selected,deselected)

class RunWindow(QWidget,ObserverWidget):

  def onTimer(self):
    self.updateInterface()

  def __init__(self,editor,treeview,codeRunner,parent = None):
    QWidget.__init__(self,parent)
    ObserverWidget.__init__(self)

    self._timer = QTimer(self)
    self._timer.setInterval(1000)
    self._timer.start()
    self.connect(self._timer,SIGNAL("timeout()"),self.onTimer)
    
    self._editor = editor
    self._treeview = treeview
    self._codeRunner = codeRunner
    self._codeSnippet = None

    codeSnippetButtons = QBoxLayout(QBoxLayout.LeftToRight)
    
    self.runButton = QPushButton("Run")
    self.killButton = QPushButton("Terminate")

    codeSnippetButtons.addWidget(self.runButton)
    codeSnippetButtons.addWidget(self.killButton)
    codeSnippetButtons.addStretch()
    
    self.connect(self.runButton,SIGNAL("clicked()"),self.runCodeSnippet)
    self.connect(self.killButton,SIGNAL("clicked()"),self.killCodeSnippet)
    
    layout = QGridLayout()
    layout.addItem(codeSnippetButtons)
    
    self.setLayout(layout)
        
  def codeSnippet(self):
    return self._codeSnippet

  def updateInterface(self):
  
    codeSnippetTreeStatus = True
    runStatus = False    
    editorStatus = True
    
    codeSnippet = self.codeSnippet()
    
    if codeSnippet != None:
      runStatus = True
      if self._codeRunner.isExecutingCode(self):
        runStatus = False
        editorStatus = False
        codeSnippetTreeStatus = False
      else:
        runStatus = True
        codeSnippetTreeStatus = True
        
    self._treeview.setEnabled(codeSnippetTreeStatus)
    self._editor.setEnabled(editorStatus)
    self.runButton.setEnabled(runStatus)
    
    if self._codeRunner.isExecutingCode(self):
      self.killButton.setEnabled(True)
    else:
      self.killButton.setEnabled(False)
    
  def setCodeSnippet(self,codeSnippet):
    self._codeSnippet = codeSnippet

  def runCodeSnippet(self):
    if self.codeSnippet() == None:
      return
    if self._codeRunner.isExecutingCode(self):
      return
    datacube = Datacube()
    manager = DataManager()
    manager.addDatacube(datacube)
    lv = dict()
    gv = self._codeRunner.gv()
    lv["data"] = datacube
    lv["dataManager"] = manager
    lv["kwargs"] = dict()
    
    def executeCodeSnippet(path,root = self.codeSnippet().root(),*args,**kwargs):
      snippet = root.offspring(path)
      if snippet == None:
        raise AttributeError("Code snippet \"%s\" not found!" % path)
      lv["kwargs"] = kwargs
      lv["args"] = args
      exec snippet.codeSnippet() in gv,lv
      
    def loadArguments():
      for argument in lv["kwargs"]:
        lv[argument] = lv["kwargs"][argument]
    
      
    lv["execute"] = executeCodeSnippet
    lv["loadArguments"] = loadArguments
    
    self._codeRunner.executeCode(self.codeSnippet().codeSnippet(),self,"<codeSnippet:%s>" % self._codeSnippet.name(),lv = lv)
    self.updateInterface()
    
  def killCodeSnippet(self):
    if self._codeRunner.isExecutingCode(self):
      self._codeRunner.stopExecution(self)

class MeasurementTool(QMainWindow,ObserverWidget):

  def setCodeSnippet(self,codeSnippet):
    self.codeSnippetEditor.setCodeSnippet(codeSnippet)
    self.runWindow.setCodeSnippet(codeSnippet)
    
  def onTimer(self):
    self.save()
    
  def saveMeasurementsAs(self):
    filename = QFileDialog.getSaveFileName(filter = "YAML(*.yml *.yaml)")
    if not filename == '':      
      self.save(filename)
      print "Successfully saved the measurements at %s" % filename
    
  def openMeasurements(self):
    MyMessageBox = QMessageBox()
    MyMessageBox.setWindowTitle("Warning!")
    MyMessageBox.setText("Do you really want read the measurements from a file? All unsaved changes will be lost.")
    yes = MyMessageBox.addButton("Yes",QMessageBox.YesRole)
    no = MyMessageBox.addButton("No",QMessageBox.NoRole)
    MyMessageBox.exec_()
    choice = MyMessageBox.clickedButton()
    if choice == no:
      return
    filename = QFileDialog.getOpenFileName(filter = "YAML(*.yml *.yaml)")
    if not filename == '':      
      self.restore(filename)
            
  def __init__(self,codeRunner,parent = None):
    QMainWindow.__init__(self,parent)
    ObserverWidget.__init__(self)
    
    self._timer = QTimer(self)
    
    self._codeRunner = codeRunner
    
    self._timer.setInterval(1000*60)
    
    menuBar = self.menuBar()
    
    measurementsMenu = menuBar.addMenu("Measurements")
    
    openAction = measurementsMenu.addAction("Open...")
    saveAsAction = measurementsMenu.addAction("Save As...")
    
    self.connect(openAction,SIGNAL("triggered()"),self.openMeasurements)
    self.connect(saveAsAction,SIGNAL("triggered()"),self.saveMeasurementsAs)
    
    self._timer.start()
    
    self.connect(self._timer,SIGNAL("timeout()"),self.onTimer)
    
    self.setAttribute(Qt.WA_DeleteOnClose,True)
    
    self._runCodeSnippet = None
  
    self.codeSnippetName = QLineEdit()
    self.addCodeSnippetButton = QPushButton("Add CodeSnippet")
    
    buttonsLayout = QBoxLayout(QBoxLayout.LeftToRight)
    buttonsLayout.addWidget(self.codeSnippetName)
    buttonsLayout.addWidget(self.addCodeSnippetButton)
    buttonsLayout.addStretch()
    
    self.setWindowTitle("Measurement Tool")
    self.setMinimumSize(800,600)

    self.saveButton = QPushButton("Save")
    
    self.codeSnippetTree = CodeSnippetTree()

    self.codeSnippetTree.setDragEnabled(True)
    self.codeSnippetTree.setDragDropMode(QAbstractItemView.InternalMove)

    widget = QWidget()
    
    self.codeSnippetEditor = CodeSnippetEditor()
    self.codeSnippetTree.setTool(self)
    
    rightLayout = QBoxLayout(QBoxLayout.TopToBottom)
    
    self.runWindow = RunWindow(treeview = self.codeSnippetTree,codeRunner = codeRunner,editor = self.codeSnippetEditor)
    
    rightLayout.addWidget(self.runWindow)
    rightLayout.addWidget(self.codeSnippetEditor)
    
    layout = QGridLayout()
    layout.addLayout(buttonsLayout,0,0,1,1)
    layout.addWidget(self.codeSnippetTree,1,0,1,1)
    layout.addLayout(rightLayout,0,1,2,1)
    
    self.connect(self.codeSnippetName,SIGNAL("returnPressed()"),self.codeSnippetCreationRequested)
    self.connect(self.addCodeSnippetButton,SIGNAL("clicked()"),self.codeSnippetCreationRequested)

    widget.setLayout(layout)
    
    self.setCentralWidget(widget)
    
    self._root = CodeSnippet()
    
    self._codeSnippetModel = CodeSnippetModel(self._root)
    self.codeSnippetTree.setModel(self._codeSnippetModel)

    self.restore()

    settings = QSettings()

    print "Backing up measurements..."
    self.save(path = params["directories.setup"]+"\\config\\ramps-%s.yaml" % str(datetime.date.today()))
    settings.setValue("MeasurementTool/backupTime",time.time())
  
    
  def currentCodeSnippet(self):
    return self._codeSnippetModel.getCodeSnippet(self.codeSnippetTree.currentIndex())
    
  def codeSnippetCreationRequested(self):
    name = str(self.codeSnippetName.text())
    codeSnippet = CodeSnippet()
    codeSnippet.setName(name)
    self._codeSnippetModel.addCodeSnippet(codeSnippet)

  def save(self,path = params["directories.setup"]+"\\config\\ramps.yaml"):
    rampFile = open(path,"w")
    stringdump = self._codeSnippetModel.dump(usePickle = False)
    string = yaml.dump(stringdump)
    rampFile.write(string)
    rampFile.close()
    
  def restore(self,path = params["directories.setup"]+"\\config\\ramps.yaml"):
    try:
      rampFile = open(path,"r")
      string = rampFile.read()
      rampFile.close()
      ramps = yaml.load(string)
      if ramps == None:
        return
      self._codeSnippetModel.load(ramps,usePickle = False)  
    except KeyError:
      print sys.exc_info()
      print "Error"    
      
  def closeEvent(self,e):
    print "Closing..."
    self.save()
    QMainWindow.closeEvent(self,e) 

class CodeSnippetEditor(QWidget,ObserverWidget):
  
  def setCodeSnippet(self,root): 
    self.setEnabled(True)
    self.root = root
    self.updateCodeSnippetInfo()

  def updateCodeSnippetInfo(self):
    if self.root != None:
      self.codeEditor.setPlainText(unicode(self.root.codeSnippet()))
    else:
      self.codeEditor.setPlainText("")

  def updateCodeSnippetProperty(self,property = None,all = False):
    if self.root == None:
      return
    if property == "codeSnippet" or all:
      self.root.setCodeSnippet(unicode(self.codeEditor.toPlainText()))
             
  def __init__(self,parent = None):
    QWidget.__init__(self,parent)
    ObserverWidget.__init__(self)
    self.root = None
    
    self.codeEditor = CodeEditor(lineWrap = False)

    layout = QGridLayout()
    
    codeSnippetLayout = QGridLayout()
        
    layout.addWidget(self.codeEditor)
    self.connect(self.codeEditor,SIGNAL("textChanged()"),lambda property = "codeSnippet":self.updateCodeSnippetProperty(property))
    self.codeEditor.activateHighlighter()
    self.updateCodeSnippetInfo()
    self.setLayout(layout)
    
    