from PyQt4.QtGui import * 
from PyQt4.QtCore import *


from pyview.gui.patterns import ObserverWidget
import pyview.helpers.instrumentsmanager 
from pyview.lib.classes import Debugger

class FrontPanel(Debugger,QMainWindow,QWidget,ObserverWidget):
  
  """
  A QT instrument frontpanel class depending on classes QMainWindow,QWidget, and ObserverWidget defined in pyview.gui.patterns.
  """
  
  def __init__(self,instrument,parent=None):
    Debugger.__init__(self)
    QMainWindow.__init__(self,parent)
    self.qw=QWidget(parent)
    self.setCentralWidget(self.qw)
    menubar=self.menuBar()
    myMenu=menubar.addMenu("&File")
    reloadCommand=myMenu.addAction("Reload instrument")
    reloadCommand=myMenu.addAction("Save state")
    restoreStateCommand=myMenu.addAction("Restore state")
    self.connect(reloadCommand,SIGNAL("triggered()"),self.reloadInstrument)
    self.connect(reloadCommand,SIGNAL("triggered()"),self.saveState)
    self.connect(restoreStateCommand,SIGNAL("triggered()"),self.restoreState)
    ObserverWidget.__init__(self)
    self.setInstrument(instrument)
    self._manager=pyview.helpers.instrumentsmanager.Manager()

  def setInstrument(self,instrument):
    """
    Set the instrument variable of the frontpanel.
    """
    self.instrument = instrument
    self.instrument.attach(self)
    
  def __del__(self):
    print "Detaching instrument..."
    self.instrument.detach(self)
    
  def hideEvent(self,e):
    print "Detaching instrument..."
    self.instrument.detach(self)
    QWidget.hideEvent(self,e)

  def closeEvent(self,e):
    print "Detaching instrument..."
    self.instrument.detach(self)
    QWidget.closeEvent(self,e)
    
  def showEvent(self,e):
    self.instrument.attach(self)
    QMainWindow.showEvent(self,e)

  def reloadInstrument(self):
    print "reloading instrument not coded..."

  def saveState(self):
    filename = QFileDialog.getSaveFileName(filter = "instrumentState (*.inst)")
    if filename != "":
      print filename
      self._manager.saveStateAs(filename=filename,instruments=[self.instrument.name()])

  def restoreState(self):
    filename = QFileDialog.getOpenFileName(filter = "instrumentState (*.inst)")
    if filename != "":
      self._manager.loadAndRestoreState(filename=filename,instruments=[self.instrument.name()])
    self


