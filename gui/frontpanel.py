from PyQt4.QtGui import * 
from PyQt4.QtCore import *


from pyview.gui.patterns import ObserverWidget
import pyview.helpers.instrumentsmanager 

class FrontPanel(QMainWindow,QWidget,ObserverWidget):
#class FrontPanel(QMainWindow,QWidget,ObserverWidget):
  
  """
  A QT instrument frontpanel.
  """
  
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


  def __init__(self,instrument,parent=None):
    QMainWindow.__init__(self,parent)
    self.qw=QWidget(parent)
    self.setCentralWidget(self.qw)
    menubar=self.menuBar()
    myMenu=menubar.addMenu("Options")
    reloadButton=myMenu.addAction("Reload instrument")
    saveStateButton=myMenu.addAction("Save state")
    restoreStateButton=myMenu.addAction("Restore state")
    self.connect(reloadButton,SIGNAL("triggered()"),self.reloadInstrument)
    self.connect(saveStateButton,SIGNAL("triggered()"),self.saveState)
    self.connect(restoreStateButton,SIGNAL("triggered()"),self.restoreState)
    ObserverWidget.__init__(self)
    self.setInstrument(instrument)
    self._manager=pyview.helpers.instrumentsmanager.Manager()


