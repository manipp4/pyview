import sys
import getopt
import os
import os.path
import weakref
import gc
import time


from pyview.gui.coderunner import execInGui

from pyview.gui.mpl.canvas import *


from pyview.lib.classes import *
from pyview.lib.patterns import *
from pyview.gui.patterns import ObserverWidget
from pyview.gui.graphicalCommands import *
from pyview.helpers.loopsmanager import LoopManager as lm
from pyview.gui.graphicalCommands import *
from pyview.config.parameters import params

import numpy


class LoopList(QTreeWidget):

  def mouseDoubleClickEvent(self,e):
    QTreeWidget.mouseDoubleClickEvent(self,e)
    #self.emit(SIGNAL("showFrontPanel()"))
    
class LoopsArea(QMainWindow,ObserverWidget):

  def __init__(self,parent = None):
    QMainWindow.__init__(self,parent)
    ObserverWidget.__init__(self)
    
    self.setWindowTitle("Loops")
    
    self._windows = dict()
    
    self.setAutoFillBackground(False)
    
    self._loopsArea = QMdiArea(self)

    self._loopsArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    self._loopsArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    self.setCentralWidget(self._loopsArea)


class LoopsPanel(QWidget,ObserverWidget):
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
    if property == "addLoop":
      self.addLoop(value)
    if property == "removeLoop":
      self.removeLoop(value)
    if property == "updateLoop":
      self.updateLoop(value)
  
  def ref(self,loop):
    return weakref.ref(loop)
  
  def __init__(self,parent = None):
    QMainWindow.__init__(self,parent)
    ObserverWidget.__init__(self)
    self.setAttribute(Qt.WA_DeleteOnClose,True)
    
    self.initializeIcons()
    self._items=dict()
    self._loopsmanager = lm()
    self._loopsmanager.attach(self)
    self._globals = globals
    self._selectedLoop = None
    self._loopsArea = LoopsArea()


    self.setMinimumHeight(200)
    settings = QSettings()
        
    layout = QGridLayout()    
    self.setWindowTitle("Loops")
    
    #iconsBarW = QWidget()
    #self._iconsBar = QGridLayout(iconsBarW)
    #layout.addWidget(iconsBarW)
    self.setWindowIcon(self._icons['loop'])
    self._iconsBar = QGridLayout() 
    
    
    
    self.playPauseButton=QPushButton()
    self.playPauseButton.setIcon(self._icons['pause'])
    self.connect(self.playPauseButton,SIGNAL("clicked()"),self.playPause)
    self._iconsBar.addWidget(self.playPauseButton,0,0)
    
    self.stopButton=QPushButton()
    self.stopButton.setIcon(self._icons['stop'])
    self.connect(self.stopButton,SIGNAL("clicked()"),self.stop)
    self._iconsBar.addWidget(self.stopButton,0,1)
    
    self.reverseButton=QPushButton()
    self.reverseButton.setIcon(self._icons['reverse'])
    self.connect(self.reverseButton,SIGNAL("clicked()"),lambda:self.modifyStepCoeff(-1) )
    self._iconsBar.addWidget(self.reverseButton,0,2)
    
    self.divideStepCoeffButton=QPushButton()
    self.divideStepCoeffButton.setIcon(self._icons['slow'])
    self.connect(self.divideStepCoeffButton,SIGNAL("clicked()"),lambda :self.modifyStepCoeff(0.5))
    self._iconsBar.addWidget(self.divideStepCoeffButton,0,3)
    
    self.changeStepButton=QPushButton()
    self.changeStepButton.setIcon(self._icons['ask'])
    self.connect(self.changeStepButton,SIGNAL("clicked()"), self.changeStep)
    self._iconsBar.addWidget(self.changeStepButton,0,3)
    
    self.doubleStepCoeffButton=QPushButton()
    self.doubleStepCoeffButton.setIcon(self._icons['fwd'])
    self.connect(self.doubleStepCoeffButton,SIGNAL("clicked()"),lambda :self.modifyStepCoeff(2))
    self._iconsBar.addWidget(self.doubleStepCoeffButton,0,4)
    
    self.deleteButton=QPushButton()
    self.deleteButton.setIcon(self._icons['trash'])
    self.connect(self.deleteButton,SIGNAL("clicked()"), self.delete)
    self._iconsBar.addWidget(self.deleteButton,0,8)
    
    
    layout.addLayout(self._iconsBar,0,0)
    
    
    
    self.looplist = QTreeWidget() 
    self.looplist.setSelectionMode(QAbstractItemView.SingleSelection)
    self.columns=["Name","Value","Start","Stop","Step","Index"]
    self.looplist.setHeaderLabels(self.columns)
    self.connect(self.looplist,SIGNAL("currentItemChanged(QTreeWidgetItem *,QTreeWidgetItem *)"),self.selectLoop)
    
    

    layout.addWidget(self.looplist,1,0)
#    self.updateInstrumentsList()
    self._updated=False
    self.setLayout(layout)
#    self.updateStateList()

    for loop in self._loopsmanager._loops:
      self.addLoop(loop)
  
  def selectLoop(self,current,last):
    if current!=None:
      self._selectedLoop = current._loop()
      self.updateLoop(self._selectedLoop)
      
      

  def updateLoop(self,loop=None):
    if loop!=None:
      l,item = self._items[self.ref(loop)]
      item.setText(0,str(loop._name))
      if not loop._value==None: item.setText(1,str(loop._value))
      item.setText(2,str(loop._start))
      if not loop._stop==None: item.setText(3,str(loop._stop))
      if not loop._step==None: item.setText(4,str(loop._step))
      item.setText(5,str(loop._index))
      for i in range(0,len(self.columns)):
        self.looplist.resizeColumnToContents(i)
      
    if self._selectedLoop!=None:
      if self._selectedLoop._paused == True:
        self.playPauseButton.setIcon(self._icons['play'])
      else:
        self.playPauseButton.setIcon(self._icons['pause'])
    else:
      self.playPauseButton.setIcon(self._icons['pause'])
    return
  
  def addLoop(self,loop):
    if self.ref(loop) in self._items:
      return
    item = QTreeWidgetItem()
    item._loop=self.ref(loop)
    loop.attach(self)
    self._items[self.ref(loop)]=[loop,item]
    self.looplist.insertTopLevelItem(self.looplist.topLevelItemCount(),item)
    self.updateLoop(loop)

    
  def removeLoop(self,loop):
    l,item = self._items[self.ref(loop)]
    self.looplist.indexOfTopLevelItem(item)
    self.looplist.takeTopLevelItem(self.looplist.indexOfTopLevelItem(item))
    del self._items[self.ref(loop)]
    if self._selectedLoop==loop:
      self._selectedLoop=None
    self.updateLoop()

  def playPause(self):
    if self._selectedLoop!=None:
      if self._selectedLoop._paused:
        self._selectedLoop.play()
      else:
        self._selectedLoop.pause()    
      self.updateLoop(self._selectedLoop)
    
  def stop(self):
    self._selectedLoop._toDelete=True
    
  def modifyStepCoeff(self,coeff):
    if self._selectedLoop!=None:
      self._selectedLoop._step*=coeff
      self.updateLoop(self._selectedLoop)
  
  def changeStep(self):
    if self._selectedLoop!=None:
      ns,b=userAskValue("New step?","New step?")
      if b:
        self._selectedLoop._step=ns
      else:
        print "wrong step entered"
      
      self.updateLoop(self._selectedLoop)
  
      
  def delete(self):
    self._loopsmanager.removeLoop(self._selectedLoop)
    