import sys
import getopt
import os
import os.path
import weakref
import gc
import time
import inspect

from pyview.gui.coderunner import execInGui

from pyview.gui.mpl.canvas import *
from functools import partial

from pyview.lib.classes import *
from pyview.lib.patterns import *
from pyview.gui.patterns import ObserverWidget
from pyview.gui.graphicalCommands import *
from pyview.config.parameters import params

import numpy

class VariablePanel(QMainWindow,ObserverWidget):
  def initializeIcons(self):
    self._icons = dict()
    
    iconFilenames = {
      "pause"               :'/actions/player_pause.png',
      "play"                :'/actions/player_play.png',
      "reverse"             :'/actions/player_reverse.png',
      "stop"                :'/actions/player_stop.png',
      "slow"                :'/actions/player_end.png',
      "fwd"                 :'/actions/player_fwd.png',
      "ask"                 :'/actions/player_ask.png',
      "trash"               :'/filesystems/trashcan_full.png',
      "loop"                :'/actions/recur.png',
      }
    
    basePath = params['path']+params['directories.crystalIcons']

    for key in iconFilenames:
      self._icons[key] = QIcon(basePath+iconFilenames[key])


  def updatedGui(self,subject,property = None,value = None):
    return
  
  def selectThread(self,current,last):
    if not current == None:
      self._thread = current
      self._props.setThread(self._thread.id)
      self._variablesList.setThread(self._thread.id)

  def updatePressed(self):
    self._threadList.updateThreadList()
    self._variablesList.updateVariableList()


  def __init__(self,parent = None,globals = {}):
    QMainWindow.__init__(self,parent)
    ObserverWidget.__init__(self)

    self._globals = globals


    self._workingDirectory = None
    
    self.setStyleSheet("""
    QTreeWidget:Item {padding:6;} 
    QTreeView:Item {padding:6;}""")

    self.setWindowTitle("Variables Manager")
    self.setAttribute(Qt.WA_DeleteOnClose,True)

    splitter = QSplitter(Qt.Horizontal)


    self._thread = None

    self._threadList = ThreadList(parent =self,globals = globals)

    self._updateButton=QPushButton("Update")

    self.connect(self._updateButton,SIGNAL("clicked()"),self.updatePressed)

    self._variablesList = VariablesList(parent =self,globals = globals)
    self._props = ThreadProperties(parent =self,globals = globals)
    self.connect(self._threadList,SIGNAL("currentItemChanged(QTreeWidgetItem *,QTreeWidgetItem *)"),self.selectThread)

    self.tabs = QTabWidget() 
   
    splitter.addWidget(self._threadList)
    splitter.addWidget(self._updateButton)
    splitter.addWidget(self.tabs)
    
    self.setCentralWidget(splitter)
    self.tabs.addTab(self._props,"Properties")
    self.tabs.addTab(self._variablesList,"Variables")


class ThreadList(QTreeWidget,ObserverWidget):  

  def __init__(self,parent = None,globals={}):
    QTreeWidget.__init__(self,parent)
    ObserverWidget.__init__(self)

    self._parent=parent
    self.setSelectionMode(QAbstractItemView.SingleSelection)
    self.setSortingEnabled(True)

    self._globals=globals

    self._coderunner=self._globals["__coderunner__"]
    self.updateThreadList()



  def updateThreadList(self):
    threadsId=self._coderunner.status().keys()

    self.clear()
    self.setHeaderLabels(["Name","ID"])

    for threadId in threadsId:
      thread=self._coderunner.status()[threadId] 
      item=QTreeWidgetItem()
      item.setText(0,str(thread["filename"]))
      item.setText(1,str(threadId))
      item.id=threadId
      self.insertTopLevelItem(0,item)


def clearLayout(layout):
  for i in range(layout.count()): layout.takeAt(0).widget().close()#layout.removeWidget(layout.itemAt(i).widget())

class VariablesList(QWidget,ObserverWidget):
  def __init__(self,parent = None,globals = {}):
    QScrollArea.__init__(self,parent)
    ObserverWidget.__init__(self)
    self._globals = globals
    self._coderunner=self._globals["__coderunner__"]
    self._thread = None

    
    layout = QFormLayout()
    self.setAttribute(Qt.WA_DeleteOnClose,True)
    self.variables = QLineEdit()
    self.variables.setReadOnly(True)


    self.setLayout(layout)

  def valueChanged(self,item):
    old=self._coderunner._lv[self._threadId][item]
    try:
      self._coderunner._lv[self._threadId][item]=old.__new__(type(old),str(self.variables[item].text()))
    except ValueError: 
      messageBox = QMessageBox(QMessageBox.Information,"Type Error","Value does not match previous data type")
      messageBox.exec_()
      self.variables[item].setText(str(old))

  def setThread(self,threadId):
    self._threadId=threadId
    self.updateVariableList()

  def updateVariableList(self):
    layout=self.layout()
    clearLayout(layout)
    self.variables = dict()
    index=0
    lv=self._coderunner._lv[self._threadId]
    for item in sorted(lv.keys()):
      listSkipped=["ismodule","isclass","ismethod","isfunction","isgeneratorfunction","isgenerator","istraceback","isframe","iscode","isbuiltin","isroutine","isabstract","ismethoddescriptor","isdatadescriptor","isgetsetdescriptor","ismemberdescriptor"]
      otherSkipped=["gv","__builtins__","__file__"]
      a=False
      for test in listSkipped:
        a=a or getattr(inspect,test)(lv[item])
      for test in otherSkipped:
        a=a or item==test
      if a==False:
        self.variables[item]=QLineEdit()
        self.variables[item].name=item
        self.variables[item].setText(str(lv[item]))
        self.variables[item].setReadOnly(False)
        self.variables[item].returnPressed.connect(partial(self.valueChanged,item=item))
#        self.connect(self.variables[item],SIGNAL("textEdited(QString)"),self.valueChanged,item=item)
        layout.addRow(item,self.variables[item])
        #layout.addWidget(QLabel(item))
        #layout.addWidget(self.variables[item])


class ThreadProperties(QWidget,ObserverWidget):
  def __init__(self,parent = None,globals = {}):
    QWidget.__init__(self,parent)
    ObserverWidget.__init__(self)
    layout = QGridLayout()
    
    self._globals = globals
    self._thread = None
    self._coderunner=self._globals["__coderunner__"]
    self.name = QLineEdit()
    self.filename = QLineEdit()
    self.filename.setReadOnly(True)
    self.failed = QLineEdit()
    self.isRunning = QLineEdit()
    self.failed.setReadOnly(True)
    self.isRunning.setReadOnly(True)
        
    layout.addWidget(QLabel("Name"))
    layout.addWidget(self.name)
    layout.addWidget(QLabel("Filename"))
    layout.addWidget(self.filename)
    layout.addWidget(QLabel("failed"))
    layout.addWidget(self.failed)
    layout.addWidget(QLabel("isRunning"))
    layout.addWidget(self.isRunning)
    
    self.setLayout(layout)
        
  def setThread(self,threadId):
    thread=self._coderunner.status()[threadId] 
    self.filename.setText(str(thread['filename']))
    self.failed.setText(str(thread['failed']))
    self.isRunning.setText(str(thread['isRunning']))
