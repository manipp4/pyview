#*******************************************************************************
# DataManager Frontpanel                                  .                    *
#*******************************************************************************

#**************************************
#Imports

import sys
import getopt
import os
import os.path
import weakref
import gc
import time
import warnings

from pyview.gui.coderunner import execInGui

#from pyview.gui.mpl.canvas import *
#reload(sys.modules['pyview.gui.mpl.canvas'])
#from pyview.gui.mpl.canvas import *

#from matplotlib import colors,cm
#from mpl_toolkits.mplot3d import Axes3D


import pyview.helpers.datamanager as dm            # DATAMANAGER
from pyview.lib.datacube import *                  # DATACUBE
from pyview.lib.classes import *
from pyview.lib.patterns import *
from pyview.gui.datacubeview import *              # DATACUBEVIEW
reload(sys.modules['pyview.gui.datacubeview'])     # DATACUBEVIEW
from pyview.gui.datacubeview import *              # DATACUBEVIEW
from pyview.gui.patterns import ObserverWidget
from pyview.gui.graphicalCommands import *
from pyview.gui.plotter import Plot2DWidget,Plot3DWidget # PLOTTER

import numpy

#*******************************************
# Plugin or Helper initialization
 
def startPlugin(ide,*args,**kwargs):
  """
  This function initializes the plugin
  """
  if hasattr(ide,"instrumentsTab"):
    ide.tabs.removeTab(ide.tabs.indexOf(ide.instrumentsTab))
  instrumentsTab = InstrumentsPanel()
  ide.instrumentsTab = instrumentsTab
  ide.tabs.addTab(instrumentsTab,"Instruments")
  ide.tabs.setCurrentWidget(instrumentsTab)

# Global module variable plugin
plugin = dict()
plugin["name"] = "Data Manager"
plugin["version"] = "0.4"
plugin["author.name"] = "Andreas Dewes-V. Schmitt - D. Vion"
plugin["author.email"] = "andreas.dewes@gmail.com"
plugin["functions.start"] = startPlugin
plugin["functions.stop"] = None
plugin["functions.restart"] = None
plugin["functions.preferences"] = None

#********************************************
#  DataTreeView class
#********************************************

class DataTreeView(QTreeWidget,ObserverWidget,debugger):
    
    def __init__(self,parent = None):
        debugger.__init__(self)
        QTreeWidget.__init__(self,parent)
        ObserverWidget.__init__(self)
        self._parent=parent
        self._items = dict()
        self._manager = dm.DataManager()           # attach  dataManager to this dataTreeview, i.e. dataTreeView receives message from datamanager  
        self.debugPrint('attaching ',self._manager,' to ',self)
        self._manager.attach(self)
        self.setHeaderLabels(["Name"])
        for cube in self._manager.datacubes():
          self.addDatacube(cube,None)
        self.itemDoubleClicked.connect(self.renameCube)
   
    def renameCube(self):
        if self._parent!=None: self._parent.renameCube()

    def ref(self,cube):
        return weakref.ref(cube)

    def contextMenuEvent(self, event):    
        menu = QMenu(self)
        addRenameAction = menu.addAction("Rename datacube...")
        menu.addSeparator()
        addChildAction = menu.addAction("Add child from file...")
        addNewChildAction = menu.addAction("Add new child")
        menu.addSeparator()
        removeAction = menu.addAction("Remove")
        menu.addSeparator()
        saveAsAction = menu.addAction("Save as...")
        menu.addSeparator()
        markAsGoodAction = menu.addAction("Mark as Good")
        markAsBadAction = menu.addAction("Mark as Bad")
        action = menu.exec_(self.viewport().mapToGlobal(event.pos()))
        if action == addRenameAction:
          if self._parent!=None: self._parent.renameCube()
        elif action == addChildAction:
          if self._parent!=None: self._parent.addChild(new=False)
        if action == addNewChildAction:
          if self._parent!=None: self._parent.addChild(new=True)
        elif action == removeAction:
          if self._parent!=None: self._parent.removeCube()
        elif action==saveAsAction :
          if self._parent!=None: self._parent.saveCubeAs()
        elif action == markAsGoodAction:
          if self._parent!=None: self._parent.markAsGood()
        elif  action== markAsBadAction:
          if self._parent!=None: self._parent.markAsBad()

    def selectCube(self,cube):
        self.debugPrint("in DataTreeView.selectCube(datacube) with datacube =",cube)
        if self.ref(cube) in self._items:
          item = self._items[self.ref(cube)]
          self.setCurrentItem(item)

    def addCube(self,cube,parent):
        self.debugPrint("in DataTreeView.addCube(cube) with cube =",cube, "and cube's parent =",parent)
        if self.ref(cube) in self._items:     # does not add a cube reference already present
          return
        item = QTreeWidgetItem()
        item.setText(0,str(cube.name()))
        item._cube = self.ref(cube)
        self.debugPrint('attaching ',cube,' to ',self)
        cube.attach(self)
        self._items[self.ref(cube)]= item
        if parent == None:
          self.insertTopLevelItem(0,item)
        else:
          self._items[self.ref(parent)].addChild(item)
        for child in cube.children():
          self.addCube(child,cube)
      
    def removeItem(self,item):
        self.debugPrint("in DataTreeView.removeItem(item) with item =",item)
        if item.parent() == None:
          self.takeTopLevelItem(self.indexOfTopLevelItem(item))
        else:
          item.parent().removeChild(item)  
  
    def removeCube(self,cube,parent):
        self.debugPrint("in DataTreeView.removecube(datacube) with datacube =",cube)
        if parent == None:
          item = self._items[self.ref(cube)]
          self.takeTopLevelItem(self.indexOfTopLevelItem(item))
        else:
          item = self._items[self.ref(parent)]
          child = self._items[self.ref(cube)]
          item.takeChild(item.indexOfChild(child))
        del self._items[self.ref(cube)]
        cube.detach(self)
    
    def updateCube(self,cube):
        self.debugPrint("in DataTreeView.updatecube(cube) with cube =",cube)
        item = self._items[self.ref(cube)]
        item.setText(0,cube.name())          
      
    def initTreeView(self):
        self.debugPrint("in DataTreeView.initTreeView()")
        self.clear()
        dataManager = dm.DataManager()
        for cube in dataManager.datacubes():
          self.addCube(cube,None)
    
    def updatedGui(self,subject,property = None,value = None):
        self.debugPrint("in DataTreeView.updatedGui with subject=",subject," property=", property,' and value =',value)
        if property == "addDatacube":
          cube=value
          self.addCube(cube,None)
          if self._parent._cube==cube:   # select the cube in the datatreeview if it is the current cube in the datamanager GUI
            self.selectCube(cube)
        elif property == "addChild":
          child = value
          self.addCube(child,subject)
          self._parent.propagateAddChild(subject,value)  # Trick from Denis to propagate the notification that a Child has been added. Subject is the parent, value is the child.
        elif property == "name":
          self.updateCube(subject)
        elif property == "removeDatacube":
          self.removeCube(value,None)
        elif property == "removeChild":
          self.removeCube(value,subject)
        else:
          self.debugPrint("not managed")

#********************************************
#  DatacubeProperties class

class DatacubeProperties(QWidget,ObserverWidget,debugger):
  
    def updateBind(self):
        name = str(self.bindName.text())
        self._globals[name] = self._cube
  
    def __init__(self,parent = None,globals = {}):
        debugger.__init__(self)
        QWidget.__init__(self,parent)
        ObserverWidget.__init__(self)
        layout = QGridLayout()
        
        self._globals = globals
        self._cube = None
        self.name = QLineEdit()
        self.filename = QLineEdit()
        self.filename.setReadOnly(True)
        self.tags = QLineEdit()
        self.description = QTextEdit()

        self.parameters,self.attributes = QTableWidget(20,2),QTableWidget(20,2)
        for widg in [self.parameters,self.attributes]:
            widg.setColumnWidth (0, 160)
            widg.setColumnWidth (1, 160)
            widg.setHorizontalHeaderLabels(["Key","Value"])
        self.parameters.setEditTriggers(QAbstractItemView.AllEditTriggers)
        self.attributes.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.bindName = QLineEdit()
        self.updateBindButton = QPushButton("Update / Set")
        self.updateBindButton.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Maximum)
        self.connect(self.updateBindButton,SIGNAL("clicked()"),self.updateBind)
        
        #font = self.description.currentFont()
        #font.setPixelSize(12)
        #self.description.setFont(font  )
        
        subLayout1=QBoxLayout(QBoxLayout.LeftToRight)
        subLayout1.setSpacing(4)
        subLayout1.addWidget(QLabel("Name"))
        subLayout1.addWidget(self.name)
        subLayout1.addWidget(QLabel(" Bind to local variable:"))
        subLayout1.addWidget(self.bindName)
        subLayout1.addWidget(self.updateBindButton)
        layout.addItem(subLayout1)

        layout.addWidget(QLabel("Filename"))
        layout.addWidget(self.filename)
        layout.addWidget(QLabel("Tags"))
        layout.addWidget(self.tags)
        layout.addWidget(QLabel("Description"))
        layout.addWidget(self.description)

        subLayout2= QGridLayout()
        subLayout2.setSpacing(4) 

        subLayout2.addWidget(QLabel("Parameters"),0,0)
        subLayout2.addWidget(QLabel("Child attributes"),0,1)
        subLayout2.addWidget(self.parameters,1,0)
        subLayout2.addWidget(self.attributes,1,1)
        layout.addItem(subLayout2)

        self.connect(self.name,SIGNAL("textEdited(QString)"),self.nameChanged)
        self.connect(self.tags,SIGNAL("textEdited(QString)"),self.tagsChanged)
        self.connect(self.description,SIGNAL("textChanged()"),self.descriptionChanged)
        self.setLayout(layout)
        
    def descriptionChanged(self):
        if self._cube == None:
          return
        if self._cube.description() != self.description.toPlainText():
          self._cube.setDescription(self.description.toPlainText())
    
    def nameChanged(self,text):
        if self._cube == None:
          return
        self._cube.setName(self.name.text())

    def tagsChanged(self,text):
        if self._cube == None:
          return
        self._cube.setTags(self.tags.text())
      
    def setCube(self,cube):
        self.debugPrint("in DatacubeProperties.setCube(cube) with cube = ",cube)
        if self._cube != None:
          self.debugPrint('detaching ',self._cube,' from ',self )
          self._cube.detach(self)
        self._cube = cube
        if not self._cube == None:
          self.debugPrint('attaching',self._cube,'to',self)
          self._cube.attach(self)
        self.updateProperties()
    
    def updateProperties(self):
        self.debugPrint("in DatacubeProperties.updateProperties()")
        filename=name=tags=description=''
        self.parameters.clearContents ()
        self.attributes.clearContents ()
        if self._cube != None:
            filename=str(self._cube.filename());
            name=str(self._cube.name())
            tags=str(self._cube.tags())
            description=str(self._cube.description())
            self.setEnabled(True)
            params=self._cube.parameters()
            i=0
            for key in params:
                self.parameters.setItem(i,0,QTableWidgetItem(str(key)))
                self.parameters.setItem(i,1,QTableWidgetItem(str(params[key])))
                i+=1
            parent=self._cube.parent()
            if parent:
                attribs=parent.attributesOfChild(self._cube)
                self.attributes.setEnabled(True)
                i=0
                if 'row' in attribs:
                    self.attributes.setItem(i,0,QTableWidgetItem('row'))
                    self.attributes.setItem(i,1,QTableWidgetItem(str(attribs['row'])))
                    del attribs['row']
                    i+=1
                for key in attribs:
                    self.attributes.setItem(i,0,QTableWidgetItem(str(key)))
                    self.attributes.setItem(i,1,QTableWidgetItem(str(attribs[key])))
                    i+=1
            else:
                self.attributes.setEnabled(False)
        else: self.setEnabled(False)  
        self.filename.setText(filename)
        self.name.setText(name)
        self.tags.setText(tags)
        self.description.setPlainText(description)

    def updatedGui(self,subject = None,property = None,value = None):
        self.debugPrint("in DatacubeProperties.updatedGui with property ",property,' and value=',value)
        if subject == self._cube and property == "name" or property == "filename":
            self.updateProperties()
      
    
#********************************************
#  DataManager GUI (frontpanel) class
#********************************************
# general rules :
#   - the client interacts with the dataManager only, and not with the dataManager frontpanel
#   - the dataManager or the datacubes then send notifications to the frontpanel or to its elements.
# The general algorithm is the following : 
# 1) possibly add a datacube to the dataManager
# 2) It is set as the current one, but the user can set another one from the front panel
# 3) x and y variables selectors are automatically. An x,y pair is pre-selected but can be changed from the front panel
# 4) The graphics and the list of plots is cleared if requested
# 5) A plot is added to the list of plots if requested, or if autoplot is true, provided it is not already present
# 6) Graphics is updated 

class DataManager(QMainWindow,ObserverWidget,debugger):

    def __init__(self,parent = None,globals = {}):  # creator of the frontpanel
        debugger.__init__(self)
        self.debugPrint("in dataManagerGUI frontpanel creator")
        QMainWindow.__init__(self,parent)
        ObserverWidget.__init__(self)

        self.manager = dm.DataManager()
        self.manager._gui=self

        self.debugPrint('attaching',self.manager,'to',self)
        self.manager.attach(self)
        self._globals = globals
        
        self._workingDirectory = None
        
        self.setStyleSheet("""QTreeWidget:Item {padding:6;} QTreeView:Item {padding:6;}""")

        self.setWindowTitle("Data Manager plugin version "+plugin["version"])
        self.setAttribute(Qt.WA_DeleteOnClose,True)

        splitter = QSplitter(Qt.Horizontal)

        self.cubeList = DataTreeView(parent=self)
        self.cubeViewer = DatacubeTableView()
        self.connect(self.cubeList,SIGNAL("currentItemChanged(QTreeWidgetItem *,QTreeWidgetItem *)"),self.selectCube)
        self.plotters2D=[]
        self.plotters3D=[]    
        self.tabs = QTabWidget()

        self._cube = None   # current cube of the datamanager GUI
        
        leftLayout = QGridLayout()
        
        leftLayout.addWidget(self.cubeList)
        
        leftWidget = QWidget()
        leftWidget.setLayout(leftLayout)
        
        splitter.addWidget(leftWidget)
        splitter.addWidget(self.tabs)
        menubar = self.menuBar()
        filemenu = menubar.addMenu("File")
        
        newCube = filemenu.addAction("New")
        loadCube = filemenu.addAction("Open...")
        renameCube = filemenu.addAction("Rename...")
        filemenu.addSeparator()
        removeCube = filemenu.addAction("Remove")
        removeAll = filemenu.addAction("Remove all")
        filemenu.addSeparator()
        saveCube = filemenu.addAction("Save")
        saveCubeAs = filemenu.addAction("Save as...")
        filemenu.addSeparator()
        markAsGood = filemenu.addAction("Mark as Good")
        markAsBad = filemenu.addAction("Mark as Bad")
        filemenu.addSeparator()
        sendToIgor=filemenu.addAction("Send to IgorPro")

        menubar.addMenu(filemenu)    

        self.connect(loadCube,SIGNAL("triggered()"),self.loadCube)
        self.connect(newCube,SIGNAL("triggered()"),self.newCube)
        self.connect(renameCube,SIGNAL("triggered()"),self.renameCube)
        self.connect(saveCube,SIGNAL("triggered()"),self.saveCube)
        self.connect(saveCubeAs,SIGNAL("triggered()"),self.saveCubeAs)
        self.connect(removeCube,SIGNAL("triggered()"),self.removeCube)
        self.connect(removeAll,SIGNAL("triggered()"),self.removeAll)
        self.connect(markAsGood,SIGNAL("triggered()"),self.markAsGood)
        self.connect(markAsBad,SIGNAL("triggered()"),self.markAsBad)
        self.connect(sendToIgor,SIGNAL("triggered()"),self.sendToIgor)

        plotmenu = menubar.addMenu("Plots")
        new2DPlot = plotmenu.addAction("New 2D plot")
        new3DPlot = plotmenu.addAction("New 3D plot")
        removePlot = plotmenu.addAction("Remove current plot")
        self.connect(new2DPlot,SIGNAL("triggered()"),self.add2DPlotter)
        self.connect(new3DPlot,SIGNAL("triggered()"),self.add3DPlotter)
        self.connect(removePlot,SIGNAL("triggered()"),self.removePlotter)

        def preparePlotMenu():
            removePlot.setEnabled(isinstance(self.tabs.currentWidget(),Plot2DWidget) or isinstance(self.tabs.currentWidget(),Plot3DWidget))
        self.connect(plotmenu,SIGNAL("aboutToShow()"),preparePlotMenu)

        menubar.addMenu(plotmenu)

        self.setCentralWidget(splitter)
        self.controlWidget = DatacubeProperties(globals = globals)
        self.tabs.addTab(self.controlWidget,"Properties")
        self.tabs.addTab(self.cubeViewer,"Table View")
        self.add2DPlotter()
        self.add3DPlotter()
        self.selectCube(self._cube,None)

    def selectCube(self,current,last):
        self.debugPrint('in DataManagerGUI.selectCube with current cube =',current,' and last cube=',last)
        if current == None: self._cube=None
        else:
          self._cube = current._cube() 
          if self._cube == None: self.cubeList.removeItem(current) 
        cube=self._cube
        self.controlWidget.setCube(cube)
        self.cubeViewer.setDatacube(cube)
        for plotter2D in self.plotters2D:   plotter2D.setCube(cube)
        for plotter3D in self.plotters3D:   plotter3D.setCube(cube)    
          
    def updatedGui(self,subject = None,property = None,value = None):
        self.debugPrint('in DataManagerGUI.updatedGui with subject=', subject,', property =',property,', and value=',value)
        if subject == self.manager and property == "plot":
          cube=value[0][0]
          kwargs=value[1]
          threeD=False
          if 'threeD' in kwargs : threeD = kwargs['threeD']
          for i in range(self.tabs.count()):
            if not  threeD and isinstance(self.tabs.widget(i),Plot2DWidget):
                self.tabs.widget(i).addPlot2(**kwargs)
                break
            elif threeD and isinstance(self.tabs.widget(i),Plot3DWidget):
                self.tabs.currentWidget.addPlot(**kwargs)
                break
        else :self.debugPrint("not managed")
        
    def workingDirectory(self):
        if self._workingDirectory == None: 
          return os.getcwd()
        return self._workingDirectory
    
    def setWorkingDirectory(self,filename):
        if filename != None:
          directory = os.path.dirname(str(filename))
          self._workingDirectory = directory
        else:
          self._workingDirectory = None
  
    def loadCube(self):
        self.debugPrint("in DataManagerGUI.loadCube()")
        filename = QFileDialog.getOpenFileName(filter = "Datacubes (*.par)",directory = self.workingDirectory())
        if not filename == '':
          self.setWorkingDirectory(filename)
          cube = Datacube()
          cube.loadtxt(str(filename))
          self.manager.addDatacube(cube)
          self._cube=cube                     # Make the manually loaded datacube the current cube. It will be automatically selected also in the dataTreeview
    
    def newCube(self):
        self.debugPrint("in DataManagerGUI.newCube()")
        manager = dm.DataManager()
        cube = Datacube()
        cube.set(a =0,b = 0,commit=False)
        manager.addDatacube(cube)
        self._cube=cube                     # Make the manually created datacube the current cube. It will be automatically selected also in the dataTreeview

    def renameCube(self):
        self.debugPrint("in DataManagerGUI.renameCube()")
        if self._cube == None:
          return
        oldName = self._cube.name()
        dialog = QInputDialog()
        dialog.setWindowTitle("Rename datacube")
        dialog.setLabelText("Warning: Existing plots will loose any reference to this datacube.\nNew name:")
        
        dialog.setTextValue(oldName)
        newName = None
        dialog.exec_()
        str1=str(dialog.textValue())
        if dialog.result() == QDialog.Accepted and str1!=oldName :
          if str1 != "":
            newName = str1
            self._cube.setName(newName)

    def removeCube(self,deleteCube=True):
        self.debugPrint("in DataManagerGUI.removeCube()")
        if self._cube != None:
            manager = dm.DataManager()
            manager.removeDatacube(self._cube,deleteCube=deleteCube)
            #self._cube = None

    def removeAll(self,deleteCube=True):
        self.debugPrint("in DataManagerGUI.removeAll()")
        reply = QMessageBox.question(self, 'Please confirm','Delete all datacubes from dataManager ?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            manager = dm.DataManager()
            for cube in list(manager.datacubes()):
                manager.removeDatacube(cube,deleteCube=deleteCube)

    def saveCubeAs(self):
        self.saveCube(saveAs = True)
        
    def addChild(self,new=False):
        self.debugPrint("in DataManagerGUI.addChild()")
        if self._cube != None: 
          cube=None
          if new:
            name0=self._cube.name()+'_child_'
            names=[child.name() for child in self._cube.children()]
            i=1
            while True:
              name=name0+str(i)
              i+=1
              if name not in names or i>1000 : break
            if i<= 1000:
              cube = Datacube(name=name)
              cube.set(aa =0,bb = 0,commit=True)
          else:
            filename = QFileDialog.getOpenFileName(filter = "Datacubes (*.par)",directory = self.workingDirectory())
            if not filename == '':
              cube = Datacube()
              self.setWorkingDirectory(filename)
              cube.loadtxt(str(filename))
          if cube:
            self._cube.addChild(cube)
            self._cube.commit()

    def markAsBad(self):
        if userAsk("Are you sure ?",timeOut=5,defaultValue=False):
          if self._cube == None:
            return
          try:
            self._cube.erase()
          except:
            pass
          workingDir = os.getcwd()
          subDir = os.path.normpath(workingDir+"/bad_data")
          if not os.path.exists(subDir):
            os.mkdir(subDir)
          if "badData" in self._cube.parameters() and self._cube.parameters()["badData"] == True:
            messageBox = QMessageBox(QMessageBox.Information,"Already marked, returning...")
            messageBox.exec_()
            return
          self.removeCube()
          self._cube.savetxt(os.path.normpath(subDir+"/"+self._cube.name()))
          self._cube.parameters()["badData"] = True
          messageBox = QMessageBox(QMessageBox.Information,"Data marked as bad","The data has been marked and moved into the subfolder \"bad_data\"")
          messageBox.exec_()
      
    def markAsGood(self):
        if self._cube == None:
          return
        workingDir = os.getcwd()
        subDir = os.path.normpath(workingDir+"/good_data")
        if not os.path.exists(subDir):
          os.mkdir(subDir)
        if "goodData" in self._cube.parameters() and self._cube.parameters()["goodData"] == True:
          messageBox = QMessageBox(QMessageBox.Information,"Already marked, returning...")
          messageBox.exec_()
          return
        self._cube.savetxt(os.path.normpath(subDir+"/"+self._cube.name()))
        self._cube.parameters()["goodData"] = True
        messageBox = QMessageBox(QMessageBox.Information,"Data marked as good","The data has been marked and copied into the subfolder \"good_data\"")
        messageBox.exec_()

    def saveCube(self,saveAs = False):
        self.debugPrint("in DataManagerGUI.saveAs()")
        if self._cube == None:
          return
        if self._cube.filename() == None or saveAs:
          filename = QFileDialog.getSaveFileName(filter = "Datacubes (*.par)",directory = self.workingDirectory())
          if filename != "":
            self.setWorkingDirectory(filename)
            self._cube.savetxt(str(filename))
        else:
          self._cube.savetxt()
  
    def sendToIgor(self):
        """
        Send the selected datacube to igor
        """
        self._cube.sendToIgor()

    def add2DPlotter(self):
        plotter2D = Plot2DWidget(parent=self,name="2D Data plot "+str(len(self.plotters2D)+1))
        self.plotters2D.append(plotter2D)
        self.tabs.addTab(plotter2D,plotter2D.name)
        plotter2D.setCube(self._cube)

    def add3DPlotter(self):
        plotter3D = Plot3DWidget(parent=self,name="3D Data plot "+str(len(self.plotters3D)+1))
        self.plotters3D.append(plotter3D)
        self.tabs.addTab(plotter3D,plotter3D.name)
        plotter3D.setCube(self._cube)

    def removePlotter(self):
        plotter=self.tabs.currentWidget()
        if plotter in  self.plotters2D : 
            self.plotters2D.remove(plotter)
        elif plotter in self.plotters3D : 
            self.plotters3D.remove(plotter)
        plotter.__del__()
        self.tabs.removeTab(self.tabs.currentIndex())

    def propagateAddChild(self,subject,value):  # Trick from Denis to propagate the notification that a child has been added to a datacube to all plotter2Ds.
        for plotter in  self.plotters2D :
            plotter.updatedGui(subject = subject,property = "addChild",value = value) # Subject is the parent, value is the child.

def startDataManager(exitWhenClosed = False):        # 3) Start the dataManger
    self.debugPrint("in startDataManager")
    global dataManager
    dataManager = DataManager()                        # call the creator of the frontpanel here
    dataManager.show()
    app = QApplication.instance()
    app.setQuitOnLastWindowClosed(exitWhenClosed)

def startDataManagerInGui(exitWhenClosed = False):    # 2) start the datamanager in gui
    execInGui(lambda :startDataManager(exitWhenClosed))

if __name__ == '__main__':      # 1) starts here in the module
    startDataManagerInGui(True)
    print "done..."