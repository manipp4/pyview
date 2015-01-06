#*******************************************************************************
# DataManager Frontpanel                                  .                    *
#*******************************************************************************

___DEBUG___ = False

def debug(*args):
  if ___DEBUG___:
    for arg in args: print arg,
    print

#**************************************
#Imports

import sys
import getopt
import os
import os.path
import weakref
import gc
import time

from pyview.gui.coderunner import execInGui

from pyview.gui.mpl.canvas import *
reload(sys.modules['pyview.gui.mpl.canvas'])
from pyview.gui.mpl.canvas import *

from matplotlib import colors


import pyview.helpers.datamanager2 as dm            # DATAMANAGER2
from pyview.lib.datacube2 import *                  # DATACUBE2
from pyview.lib.classes import *
from pyview.lib.patterns import *
from pyview.gui.datacubeview2 import *              # DATACUBEVIEW2
reload(sys.modules['pyview.gui.datacubeview2'])     # DATACUBEVIEW2
from pyview.gui.datacubeview2 import *              # DATACUBEVIEW2
from pyview.gui.patterns import ObserverWidget
from pyview.gui.graphicalCommands import *

import numpy

#*******************************************
# Plugin or Helper initialization
 
def startPlugin(ide,*args,**kwargs):
  """
  This function initializes the plugin
  """
  debug("in startPlugin")
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
#  utility classes
#********************************************

class cube2DPlot:
    def __init__(self):
        pass

#********************************************
#  PlotWidget classes
#********************************************
class PlotWidget(QWidget,ObserverWidget):
  
    def __del__(self):
        debug("deleting ",self)

    def __init__(self, parent=None, name=None,threeD=False):  # creator PlotWidget
        debug("in PlotWidget.__init__(parent,name,threeD) with parent=",parent," name=",name," and threeD=",threeD)
        QWidget.__init__(self,parent)
        ObserverWidget.__init__(self)
        self.parent=parent
        self.name=name
        self._threeD=threeD # never change this value after instance creation
        self._cube = None
        self._showLegend = True
        self._plots = []
        self._updated = False
        self._currentIndex = None
        self.legends = []
        self.cubes = []
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.connect(self.timer,SIGNAL("timeout()"),self.onTimer)
        self.timer.start()

        self._manager = dm.DataManager()           # attach  dataManager to this Plot2DWidget, i.e. Plot2DWidget receives message from datamanager  
        debug('attaching ',self._manager,' to ',self)
        self._manager.attach(self)
        
        # definition of the Canvas
        self.canvas = MyMplCanvas(dpi = 72,width = 8,height = 8,name=name)

        # Definition of top sub-layout ctrlLayout0
        ctrlLayout0 = QBoxLayout(QBoxLayout.LeftToRight)
        # Define controls,
        if not threeD:
            self.level=QSpinBox()
        self.xNames,self.yNames = QComboBox(),QComboBox()
        variableNames=[self.xNames,self.yNames]
        comboBoxes=variableNames
        if threeD:
            self.zNames = QComboBox()
            variableNames.append(self.zNames)
            self.regularGrid=QRadioButton('on regular grid');self.regularGrid.setChecked(False);self.regularGrid.setEnabled(False)
            self.regridize=QComboBox()
            comboBoxes=variableNames
            comboBoxes.append(self.regridize)
        for combo in comboBoxes : combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.addButton = QPushButton("Add plot(s)")
        self.autoplot=QCheckBox("AutoPlot")
        self.autoclear=QCheckBox("AutoClear")
        # then add controls to sublayout,
        if not threeD:
            widgets=[QLabel("Level:"),self.level,QLabel("X:"),self.xNames,QLabel("Y:"),self.yNames,self.addButton,self.autoplot,self.autoclear]
        else:
            widgets=[QLabel("X:"),self.xNames,QLabel("Y:"),self.yNames,QLabel("Z:"),self.zNames,self.regularGrid,QLabel("regularize:"),self.regridize,self.addButton,self.autoplot,self.autoclear]
        for widget in widgets:    ctrlLayout0.addWidget(widget)
        ctrlLayout0.addStretch()
        # and make connections between signals and slots.
        for variableName in variableNames : self.connect(variableName,SIGNAL("currentIndexChanged (int)"),self.namesChanged)
        self.connect(self.autoplot,SIGNAL("stateChanged(int)"),self.autoplotChanged)
        if not threeD:
            self.connect(self.level,SIGNAL("valueChanged(int)"),self.levelChanged)
            addPlot=lambda: self.addPlots(x=self.xNames.currentText(),y=self.yNames.currentText())
        else:
            addPlot=lambda: self.addPlots(x=self.xNames.currentText(),y=self.yNames.currentText(),z=self.zNames.currentText())
        self.connect(self.addButton,SIGNAL("clicked()"),addPlot)

        # Definition of bottom-left layout ctrlLayout1
        ctrlLayout1=QBoxLayout(QBoxLayout.TopToBottom)
        # define controls
        self.styles = QComboBox()
        self.styles.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Maximum)
        if not threeD:
            styles=["line","scatter","line+symbol"]
        else:
            styles=['2D image','Contours','Scatter','Surface','Tri-surface']
        for style in styles: self.styles.addItem(style)
        self.colors=QComboBox()
        self.colors.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Maximum)
        if not threeD:
            color_cycle =self.canvas.axes._get_lines.color_cycle
            colors=[]
            for i, color in enumerate(color_cycle):
                if i==0 or color!=colors[0]:
                    colors.append(color)
                else: break
        else:            
            colors=['binary','gray','jet','hsv(circular)','autumn','cool']
        for color in colors: self.colors.addItem(color)
        self.showLegend = QCheckBox("Legend")
        self.showLegend.setCheckState(Qt.Checked)
        self.clearButton = QPushButton("Clear all")
        # then add controls to sublayout,
        widgets=[QLabel('Default style:'),self.styles,QLabel('Default colors:'),self.colors,self.showLegend,self.clearButton]
        for widget in widgets:    ctrlLayout1.addWidget(widget)
        ctrlLayout1.addStretch()
        # and make connections between signals and slots.
        self.connect(self.showLegend,SIGNAL("stateChanged(int)"),self.showLegendStateChanged)
        self.connect(self.clearButton,SIGNAL("clicked()"),self.clearPlots)

        # Definition of bottom-right plotList QTreeWidget
        self.plotList=pl= QTreeWidget()
        if not threeD:
            headers=("Datacube","X variable","Y variable","style","colors")
        else:
            headers=("Datacube","X variable","Y variable","Z variable","style","colors")
        pl.setColumnCount(len(headers))
        pl.setMinimumHeight(30)
        pl.setHeaderLabels(headers)
        def menuContextPlotlist(point):
          item = self.plotList.itemAt(point) 
          if item:
            name = item.text(0)
            colorModel=None
            styleIndex=3                #2D
            colorIndex=4
            if self._threeD:            #3D
                styleIndex=4
                colorIndex=5           
            styleItem=str(item.text(styleIndex))
            colorItem=str(item.text(colorIndex))
            menu=QMenu(self)
            actionRemove=menu.addAction("Remove")
            menu.addSeparator() 
            actionRemove.triggered.connect(self.removeLine)
            def makeFunc(style):
                return lambda : self.setStyle(style=style)
            for style in styles:
                action=menu.addAction(style)
                if style==styleItem:
                    action.setCheckable(True)
                    action.setChecked(True)
                    action.setEnabled(False)
                action.triggered.connect(makeFunc(style))
            menu.addSeparator()
            def makeFunc2(color):
                return lambda : self.setColor(color=color)
            for color in colors:
                action=menu.addAction(color)
                if color==colorItem:
                    action.setCheckable(True)
                    action.setChecked(True)
                    action.setEnabled(False)
                action.triggered.connect(makeFunc2(color))
            menu.exec_(self.plotList.mapToGlobal(point))
        pl.setContextMenuPolicy(Qt.CustomContextMenu) 
        self.connect(pl, SIGNAL("customContextMenuRequested(const QPoint &)"),menuContextPlotlist)

        #Full Layout
        ctrlLayout = QGridLayout()          # create a layout for 
        ctrlLayout.addLayout(ctrlLayout0,0,0,1,2)   # the controls above
        ctrlLayout.addItem(ctrlLayout1,1,0) # the line properties on the left
        ctrlLayout.addWidget(self.plotList,1,1)      # and the list of plots on the right
        splitter = QSplitter(Qt.Vertical)   # vertica splitter with  
        splitter.addWidget(self.canvas)     # the canvas
        self.ctrlWidget = QWidget()              # the propLayout with the controlWidget, the line properites and the plot list
        self.ctrlWidget.setLayout(ctrlLayout)
        splitter.addWidget(self.ctrlWidget)
        layout = QGridLayout()              # overall layout
        layout.addWidget(splitter)          # takes the vertical splitter
        self.setLayout(layout)

    def onTimer(self):
        if self._updated == True:
            return
        debug(self,'.onTimer() calling updatePlot()') 
        self._updated = True
        self.updatePlot()

    def updatedGui(self,subject = None,property = None,value = None):     # notification listener of Plot2DWidget
        debug("in",self,".updatedGui with subject=", subject,", property=",property,", and value=",value)
        if subject==self._manager and property=="addDatacube" :                     # 1) A new datacube arrived.
            if self.autoplot.isChecked():
                self.addPlots(cube=value)                                           #     if autoplot, addPlot it (or attach if it's empty for delayed addplotting)
        elif isinstance(subject,Datacube) and property =="names":                   # 2) New names of an attached datacube arrived
            cube=subject                                                            #     the datacube cube is the notifed subject
            if  cube== self._cube:  self.updateControls()                           #     if current datacube => update controls
            if self.autoplot.isChecked():
                self.addPlots(cube=cube)                                            #     allows autoplot of a datacube that gets its first columns     
        elif isinstance(subject,Datacube) and property =="addChild":                # 3) a datacube attached to this plotter has a new child
            cube=subject; child=value                                               #     the datacube and the child are the notified property and value, respectively
            if  cube== self._cube and self.level.value()>0:   self.updateControls() #     if current datacube and levels >0 => update controls
            if self.autoplot.isChecked():
                self.addPlots(cube=child)                                           #     if autoplot, addplot the added child (the value)
        elif subject==self._manager and property=="addChild" :                      #  4) a datacube of the datamanger not attached to this plotter (otherwise would be case 3) has new child
            if self.autoplot.isChecked():
                cube=None # retrieve here the child datacube
                self.addPlots(cube=cube)
        elif isinstance(subject,Datacube) and property =="commit":                  #  5) New points arrived in an attached datacube
            self._updated = False
        else:                                                                       # note that addPlots set self._updated to False after completion
            debug("not managed")

    def addPlot(self):                                      # subclass in Plot2DWidget and Plot3DWidget
        return

    def addPlots(self):                                     # subclass in Plot2DWidget and Plot3DWidget
        return
    
    def removePlot(self,index=None):
        """
        Remove a plot from the graph and from self._plots by index.
        If index is not specified remove the current index.
        If index does not exist does nothing.
        """
        debug("in PlotWidget.removePlot()")
        if index ==None : index=self._currentIndex
        if index!= -1 and index < len(self._plots):
            cube=self._plots[index].cube                    # retrieve the cube of the plot to be deleted
            if not self._threeD: 
                self.canvas.axes.lines.pop(index)           # delete the plot from axes...
            else:
                i=None                                      # insert the propoer code here for 3D removing
            self._plots.pop(index)                          #... as well as from self._plots
            cubes= [plot.cube for plot in self._plots]      # detach the cube if it is not the current cube and if it is not in another plot
            if cube !=self._cube and not cube in cubes: cube.detach(self)
            self._currentIndex = None
            self._updated = False

    def clearPlots(self):
        """
        Clears all the plots from the graph and from self._plotList.
        """
        debug("in PlotWidget.clearPlots()")
        for plot in self._plots:
          if plot.cube != self._cube:
            debug("detaching ",plot.cube," from ",self)
            plot.cube.detach(self)
        self._plots = []
        self._currentIndex = None
        self.plotList.clear()
        if not self._threeD:
            self.canvas.axes.lines=[]                       # delete all plots from axes...
        else:
            i=None                                          # insert the propoer code here for 3D clearing
        self._updated = False
    
    def updatePlotLabels(self):                             # subclass in Plot2DWidget and Plot3DWidget
        return

    def updatePlot(self,listOfPlots=None):
        """
        Rebuilt axis labels, title and legend, then refill the listed plots with their points.
        If no list of plots is given, all plots in self._plots are updated.
        """
        debug("in PlotWidget.updatePlot()")
        if len(self._plots) == 0:                            # clear the graph without using clf, which would loose the fixed scales if any.
            if not self._threeD:
                self.canvas.axes.cla()
                self.canvas.redraw()
            else:
                None                                         #insert proper code for 3D
            return
        self.updatePlotLabels(draw=False)
        self.updatePlotLines(draw=True,listOfPlots=listOfPlots)

    def updatePlotLines(self):                               # subclass in Plot2DWidget and Plot3DWidget
        return

    def setCube(self,cube,xName=None,yName=None,zName=None):
        """"
        Set the selected datacube as current cube, update variable names in selectors, and call plot if autoplot
        """
        debug('in PlotWidget.setCube(cube,xName,yName) with cube =',cube,' xName=',xName, ' and yName=',yName)  
        detachPrevious= True
        if self._cube!=None and  self._cube in self.parent.manager.datacubes():
          found = False                 # Detach previous cube if not in a plot or if removed from datamanager
          for plot in self._plots:
            if self._cube == plot.cube :
              found = True
              break
          if found:
            detachPrevious= False
        if self._cube!=None and detachPrevious :
          debug('detaching ',self._cube,' from ',self)
          self._cube.detach(self)
        self._cube = cube                                     # defines the new cube as current cube
        if self._cube!=None:
          debug("attaching",self._cube,'to',self)
          self._cube.attach(self)                             # and observes the cube in case it changes names or gets new data
        if not self._threeD:
            kwargs={'level':0,'xName':xName,'yName':yName}    # update the 2D variable selectors
        else:
            kwargs={'xName':xName,'yName':yName,'zName':zName} # update the 3D variable selectors
        self.updateControls(**kwargs)
        if self.autoplot.isChecked():  self.addPlot()         # and plot if autoplot     

    def preselectVariables(self):                            # subclass in Plot2DWidget and Plot3DWidget
        return

    def updateControls(self,**kwargs):                       # subclass in Plot2DWidget and Plot3DWidget
        return

    def setStyle(self,**kwargs):                             # subclass in Plot2DWidget and Plot3DWidget
        return

    def setColor(self,**kwargs):                             # subclass in Plot2DWidget and Plot3DWidget
        return

    def removeLine(self):
        debug("in Plot2DWidget.removeLine()")
        self._currentIndex = self.plotList.indexOfTopLevelItem(self.plotList.currentItem())
        self.plotList.takeTopLevelItem(self._currentIndex) # remove the item from plotList
        self.removePlot()

    def lineSelectionChanged(self,selected,previous):
        if selected != None:
          index = self.plotList.indexOfTopLevelItem(selected)
          self._currentIndex = index

    def autoplotChanged(self,CheckState):
        debug("in PlotWidget.autoplotChanged()")
        if CheckState:
          self.updatedGui(subject=self._cube,property = "names",value = None)

    def levelChanged(self):                                 # subclass in Plot2DWidget only
        return

    def namesChanged(self):
        debug("in PlotWidget.namesChanged()")                                            # not used yet
        self.updatedGui(subject=self,property = "redraw",value = None)
    
    def showLegendStateChanged(self,state):
        debug("in PlotWidget.showLegendStateChanged()")
        if state == Qt.Checked:
          self._showLegend = True
        else:
          self._showLegend = False
        self._updated = False

class Plot2DWidget(PlotWidget):

    def __init__(self, parent=None, name=None): # creator Plot2DWidget
        PlotWidget.__init__(self,parent=parent,name=name,threeD=False)
        self.colors.setEnabled(False)

    def addPlots(self,cube=None,level=None,x=None,y=None,clear='auto',style=None,**kwargs):
        debug('in Plot2DWidget.addPlots with cube=',cube,',level=',level,', x=',x,', y=',y,', clear=',clear,', style=',style,', and current cube = ',self._cube)          
        if level==None: level=self.level.value()
        if cube==None : cube =self._cube              # if no datacube passed use the current datacube
        if cube==None:  return                        # give-up if no datacube
        if len(cube.names())==0:                      # if datacube has no column,...
            if self.autoplot.isChecked():
                debug('attaching ',cube,' to ',self)  # attach it  if autoplot... 
                cube.attach(self)                     # ... so that on next names notification it is autoplotted;
            return                                    # then give up
        x,y=self.preselectVariables(cube=cube,level=level,xName=x,yName=y)  # Build valid x and y names
        if not x or not y: return                     # give up if no valid names
        cubes=cube.cubesAtLevel(level=level,allBranchesOnly=True)
        if self.autoclear.isChecked() or clear==True: self.clearPlots() 
        for cubei in cubes:
            self.addPlot(cube=cubei,x=x,y=y,clear=False,style=style,**kwargs)
  
    def addPlot(self,cube=None,x=None,y=None,clear='auto',style=None,**kwargs):
        """
        Adds a plot of a datacube in self._plots with specified axes and pre-clearing if requested. In case cube=None, use the current datacube.
        Add the corresponding line in the table below the graph.
        Then calls self.updatePlot() for redrawing.
        Note: in case datacube has no column, no plot is added.
        """
        debug('in Plot2DWidget.addPlot with cube=',cube,', x=',x,', y=',y,', clear=',clear,', style= ', style, ' and current cube = ', self._cube)
        if cube==None : cube =self._cube              # if no datacube passed use the current datacube
        if cube==None:  return                        # give-up if no datacube
        if len(cube.names())==0:                      # give up if datacube has no column, but attach it if autoplot
          if self.autoplot.isChecked():
            debug('attaching ',cube,' to ',self)
            cube.attach(self)                         # at the next names notification, opportunity to autoplot.
            return
        if (self.autoclear.isChecked() and clear=='auto') or clear==True:       # clear if autoclear
          self.clearPlots() 
        x,y=self.preselectVariables(cube=cube,xName=x,yName=y) # Build valid x and y names
        if not x or not y: return                     # give up if no valid names                                  
        for plot in self._plots:                      # Check if the plot is already present in the list of plots
          if cube == plot.cube :
            if plot.xname == x and plot.yname == y:
              self._updated = False
              return                                  # and update only and stop if the plot is already present
        plot = cube2DPlot()                           # Ohterwise build the new cube2DPlot 
        plot.xname = x
        plot.yname = y   
        plot.cube = cube 
        plot.legend = "%s, %s vs. %s" % (cube.name(),plot.xname,plot.yname)
        # The cube2DPlot has a property line that point to its corresponding axes' plot
        # Plotting with axes.plot returns a plot.
        # The strategy here is to first make an empty plot, get it and set the line property to it; Then the plot will be filled with points and redrawn.
        xvalues,yvalues=[[],[]]
        plot.line, = self.canvas.axes.plot(xvalues,yvalues,**kwargs) 
        if (not style) or self.styles.findText(style)==-1: style =self.styles.currentText()
        plot.style = style
        if style == 'scatter':
          plot.line.set_linestyle('')
          plot.line.set_marker('o')
        elif style == 'line':
          plot.line.set_linestyle('-')
          plot.line.set_marker('')
        else:
          plot.line.set_linestyle('-')
          plot.line.set_marker('o')
        #self._cnt+=1
        debug('attaching ',plot.cube,' to ',self)
        plot.cube.attach(self)
        #plot.lineStyleLabel = QLabel("line style") # remove by DV
        color=plot.line.get_color()
        plotItem = QTreeWidgetItem([cube.name(),plot.xname,plot.yname,plot.style,color]) # Add the plot as a plotitem in the view plotList below the graph window 
        self.writeInColorInQTreeWidget(plotItem,4,color,color)
        self.plotList.addTopLevelItem(plotItem)
        #self.plotList.setItemWidget(plotItem,4,plot.lineStyleLabel)
        self.plotList.update()                             # update the view plotList of self._plot
        plot.item=plotItem
        self._plots.append(plot)                           # and add the plot to the list self._plots
        self._updated = False                                  # update the graph (will fill with points, create all labels, and redraw)
    
    def updatePlotLabels(self,draw=False):
        """
        Rebuilt axis labels, title and legend.
        """
        xnames = []
        ynames = []
        legend = []
        legendPlots = []
        filenames = []   
        names=[]
        for plot in self._plots:
          if not plot.xname in xnames:
            xnames.append(plot.xname)
          if not plot.yname in ynames:
            ynames.append(plot.yname)
          if not plot.cube.name() in names:
            names.append(plot.cube.name())
          if plot.cube.filename() != None and not plot.cube.filename() in filenames:
            legend.append(plot.yname+":"+plot.cube.filename()[:-4])
            legendPlots.append(plot.line)
            filenames.append(plot.cube.filename())
        xLabel=", ".join(xnames)
        if len(xLabel) > 30:    xLabel=xLabel[:27] + '...' 
        yLabel=", ".join(ynames)
        if len(yLabel) > 20:    xLabel=yLabel[:27] + '...' 
        title=", ".join(names)
        if len(title) > 63: title=title[:60] + '...'
        self.canvas.axes.set_xlabel(xLabel)
        self.canvas.axes.set_ylabel(yLabel)
        self.canvas.axes.set_title(title)
        if self._showLegend and len(legend) > 0:
          from matplotlib.font_manager import FontProperties
          self.canvas.axes.legend(legendPlots,legend,prop = FontProperties(size = 6))
        else:
          self.canvas.axes.legend_ = None 
        if draw: self.canvas.redraw()

    def updatePlotLine(self,draw=False,plot=None):
        """
        Refill the listed plots with their points.
        If no list of plots is given, all plots in self._plots are updated.
        """
        debug("in Plot2DWidget.updatePlotLine() with plot=",plot)
        if plot==None and self._currentIndex:   plot=self._plots[self._currentIndex]
        if plot:
          if plot.xname != "[row number]":
            xvalues = plot.cube.column(plot.xname)
          else:
            xvalues = arange(0,len(plot.cube),1)
          if plot.yname != "[row number]":
            yvalues = plot.cube.column(plot.yname)
          else:
            yvalues = arange(0,len(plot.cube),1)
          plot.line.set_xdata(xvalues)
          plot.line.set_ydata(yvalues)
          plot.line.recache()       #Bug in matplotlib. Have to call "recache" to make sure the plot is correctly updated.
        if draw: self.canvas.redraw()
  
    def updatePlotLines(self,draw=False,listOfPlots=None):
        """
        Refill the listed plots with their points.
        If no list of plots is given, all plots in self._plots are updated.
        """
        debug("in Plot2DWidget.updatePlotLines() with listOfPlots=",listOfPlots)
        if listOfPlots==None:   listOfPlots=self._plots
        if listOfPlots==None or listOfPlots==[] : return
        for plot in listOfPlots:
            self.updatePlotLine(draw=False,plot=plot)  
        if draw: self.canvas.redraw()
      
    def preselectVariables(self,cube=None,level=0,xName=None,yName=None,previousXName=None,previousYName=None):
        """
        preselect x and y names before plotting a datacube.
        """
        if cube==None : cube=self._cube           # if no datacube passed use the current datacube
        if cube==None :  return                   # if no datacube give up
        if level==None :level=0 
        commonNames=cube.commonNames()            # gets all column names of the datacube and its children that are common to a same level
        levelMax=len(commonNames)-1
        if level>levelMax :level=levelMax
        names=commonNames[level]                  # select first the passed names if valid for both x and y                  
        if (not xName) or (not yName) or not (xName in names or xName=="[row number]") or not (yName in names or yName=="[row number]"):
          cubes=cube.cubesAtLevel(level=level,allBranchesOnly=True)
          for cubei in cubes:
            if 'defaultPlot' in cubei.parameters():  # else select the first valid default plot if defined in one of the datacubes
              for params in cube.parameters()["defaultPlot"]:
                xName,yName=params[:2]
                if xName in names and yName in names:
                  break
                return xName,yName
                                                  # else select names of previous plot if possible
          if not previousXName: previousXName= self.xNames.currentText()
          if not previousYName: previousYName= self.yNames.currentText()
          if previousXName in names and previousYName in names: 
            xName,yName=previousXName,previousYName
          elif len(names)>=2:                     # else choose names[0] and names[1] if they exist
            xName,yName=names[0:2]  
          elif len (names)==1:                    # else choose "[row number]" and names[1] if they exist
              xName="[row number]"
              yName=names[0]
          else:
            xName,yName=None,None
            print "can't select valid columns for x and y"
        return str(xName),str(yName)

    def updateControls(self,level=None,xName=None,yName=None):
        """
        Updates the level and the x and y names in the x and y selectors. Then makes a pre-selection by calling preselectVariables().
        """
        cube=self._cube
        debug("in Plot2DWidget.updateControls(xName,yName) with level=",level,", xName=",xName, ', yName=',yName, ', and current datacube=',self._cube)
        currentX = self.xNames.currentText()  # memorize current selection to reuse it if necessary
        currentY = self.yNames.currentText()
        self.xNames.clear()                   # clear the selector
        self.yNames.clear()
        if cube!=None:
          commonNames=cube.commonNames()        # gets all column names of the datacube and its children that are common to a same level
          self.level.setMaximum(len(commonNames)-1)
          if level!=None : self.level.setValue(level)
          level=self.level.value()
          names=commonNames[level]
          self.xNames.addItem("[row number]") # Add the 'row number' choice
          self.yNames.addItem("[row number]")              
          for name in names:                  # add all other choices from the current datacube
            self.xNames.addItem(name,name)    
            self.yNames.addItem(name,name)   
          xName,yName=self.preselectVariables(cube=cube,level=level,xName=xName,yName=yName,previousXName=currentX,previousYName=currentY)
          if xName and yName:                 # select the requested x and y names if correct
            ix = self.xNames.findText(xName)
            iy = self.yNames.findText(yName)
            if ix != -1 and iy != -1:
              self.xNames.setCurrentIndex(ix)
              self.yNames.setCurrentIndex(iy)
        if self.xNames.count()*self.xNames.count()>0  : self.addButton.setEnabled(True)
        else: self.addButton.setEnabled(False)

    def setStyle(self,index=None,style=None):
        debug("in Plot2DWidget.setStyle() with index=",index,"and style=",style)
        if index==None :                                                # if index is not passed choose the current index in plotList
          index=self.plotList.indexOfTopLevelItem(self.plotList.currentItem())
        if self._currentIndex == -1:                                
          return                                                      # return if not valid index
        self._currentIndex = index                                    # set the current index of the Plot2DWidget to index
        if not style:                                                 # if style is not passed choose the current default style
          style = self.styles.itemData(index).toString() 
        if self._plots[self._currentIndex].style == style:            # if style is already correct do nothing and return
          return
        if style == 'scatter':                                        # set the style in the plot
          self._plots[self._currentIndex].line.set_linestyle('')
          self._plots[self._currentIndex].line.set_marker('o')
        elif style == 'line':
          self._plots[self._currentIndex].line.set_linestyle('-')
          self._plots[self._currentIndex].line.set_marker('')
        else:
          self._plots[self._currentIndex].line.set_linestyle('-')
          self._plots[self._currentIndex].line.set_marker('o')
        self._plots[self._currentIndex].style = style
        self._plots[self._currentIndex].item.setText(3,style)
        self._updated = False

    def setColor(self,index=None,color=None):                            
        debug("in Plot2DWidget.setColor() with index=",index,"and color=",color)
        if index==None :                                                # if index is not passed choose the current index in plotList
          index=self.plotList.indexOfTopLevelItem(self.plotList.currentItem())
        if self._currentIndex == -1:                                
          return                                                      # return if not valid index
        self._currentIndex = index                                    # set the current index of the Plot2DWidget to index
        if not color:                                                 # if style is not passed choose the current default style
          color = self.colors.itemData(index).toString() 
        if self._plots[self._currentIndex].line.get_color() == color:            # if style is already correct do nothing and return
          return
        self._plots[self._currentIndex].line.set_color(color)         # set the color in the plot
        item=self._plots[self._currentIndex].item
        self.writeInColorInQTreeWidget(item,4,color,color)
        self._updated = False
        return

    def writeInColorInQTreeWidget(self,item,index,text,matPlotLibColor):
        colorb = QColor(colors.ColorConverter.colors[matPlotLibColor])
        brush = QBrush()
        brush.setColor(colorb)
        item.setForeground(index,brush)
        item.setText(index,text) 

    def levelChanged(self):
        debug("in Plot2DWidget.showLegendStateChanged()")
        self.updatedGui(subject=self._cube,property = "names",value = None)
    

class Plot3DWidget(PlotWidget):
    
    def __init__(self, parent=None, name=None): # creator Plot3DWidget
        PlotWidget.__init__(self,parent=parent,name=name,threeD=True)

    def addPlot(self,**kwargs):                             # subclass in Plot2DWidget and Plot3DWidget
        return

    def addPlots(self,**kwargs):                            # subclass in Plot2DWidget and Plot3DWidget
        return
    
    def updatePlotLabels(self,**kwargs):                    # subclass in Plot2DWidget and Plot3DWidget
        return

    def updatePlotLines(self,**kwargs):                     # subclass in Plot2DWidget and Plot3DWidget
        return

    def preselectVariables(self,**kwargs):                  # subclass in Plot2DWidget and Plot3DWidget
        return

    def updateControls(self,**kwargs):                      # subclass in Plot2DWidget and Plot3DWidget
        return

    def setStyle(self,style):                               # subclass in Plot2DWidget and Plot3DWidget
        return

    def setColorModel(self,**kwargs):                        # subclass in Plot3DWidget only
        return
 
class Plot2DWidgetOld(QWidget,ObserverWidget):
  
    def __init__(self, parent=None, name=None):  # creator Plot2DWidget
        QWidget.__init__(self,parent)
        ObserverWidget.__init__(self)
        self.parent=parent
        self.name=name
        self._cube = None
        self._showLegend = True
        self._plots = []
        #self._cnt = 0
        self._lineColors = [(0,0,0),(0.8,0,0),(0.0,0,0.8),(0.0,0.5,0),(0.5,0.5,0.5),(0.8,0.5,0.0),(0.9,0,0.9)]
        self._lineStyles = ['-','--','-.',':']
        self._updated = False
        self.xnames = []
        self._currentIndex = None
        self.ynames = []
        self.legends = []
        self.cubes = []
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.connect(self.timer,SIGNAL("timeout()"),self.onTimer)
        self.timer.start()

        self._manager = dm.DataManager()           # attach  dataManager to this Plot2DWidget, i.e. Plot2DWidget receives message from datamanager  
        debug('attaching ',self._manager,' to ',self)
        self._manager.attach(self)
        
        # the canvas
        self.canvas = MyMplCanvas(dpi = 72,width = 8,height = 8,name=name)

        # Layout for controls = playout
        self.level=QSpinBox()
        self.xNames = QComboBox()
        self.xNames.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.yNames = QComboBox()
        self.yNames.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.addButton = QPushButton("Add plot(s)")
        self.autoplot=QCheckBox("AutoPlot")
        self.autoclear=QCheckBox("AutoClear")
        self.showLegend = QCheckBox("Legend")
        self.showLegend.setCheckState(Qt.Checked)
        playout = QBoxLayout(QBoxLayout.LeftToRight)
        playout.addWidget(QLabel("Level:"))
        playout.addWidget(self.level)
        playout.addWidget(QLabel("X:"))
        playout.addWidget(self.xNames)
        playout.addWidget(QLabel("Y:"))
        playout.addWidget(self.yNames)
        playout.addWidget(self.addButton)
        playout.addWidget(self.autoplot)
        playout.addWidget(self.autoclear)
        playout.addWidget(self.showLegend)
        playout.addStretch()
        self.connect(self.level,SIGNAL("valueChanged(int)"),self.levelChanged)
        self.connect(self.xNames,SIGNAL("currentIndexChanged (int)"),self.namesChanged)
        self.connect(self.yNames,SIGNAL("currentIndexChanged (int)"),self.namesChanged)
        self.connect(self.showLegend,SIGNAL("stateChanged(int)"),self.showLegendStateChanged)
        self.connect(self.autoplot,SIGNAL("stateChanged(int)"),self.autoplotChanged)
        self.connect(self.addButton,SIGNAL("clicked()"),lambda: self.addPlots(x=self.xNames.currentText(),y=self.yNames.currentText()))
        
        # Layout for lines
        self.lineStyles = QComboBox()
        self.lineStyles.addItem("line","line")
        self.lineStyles.addItem("scatter","scatter")
        self.lineStyles.addItem("line+symbol","line+symbol")
        self.lineStyles.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Maximum)
        
        self.plotList = QTreeWidget()
        self.plotList.setColumnCount(4)
        self.plotList.setMinimumHeight(30)
        self.plotList.setHeaderLabels(("Datacube","X variable","Y variable","style"))
        #removeButton = QPushButton("Remove line")
        #removeButton.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Maximum)
        self.clearButton = QPushButton("Clear all")
        styleLabel = QLabel("Default style:")
        styleLabel.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Maximum)
        linePropertiesLayout = QBoxLayout(QBoxLayout.TopToBottom)
        linePropertiesLayout.addWidget(styleLabel)
        linePropertiesLayout.addWidget(self.lineStyles)
        #linePropertiesLayout.addWidget(removeButton)
        linePropertiesLayout.addWidget(self.clearButton)
        linePropertiesLayout.insertStretch(-1)
        self.connect(self.clearButton,SIGNAL("clicked()"),self.clearPlots)
        def menuContextPlotlist(point):
          item = self.plotList.itemAt(point) 
          if item:
            name = item.text(0)
            menu=QMenu(self)
            actionLine=menu.addAction("Line")
            actionScatter=menu.addAction("Scatter")
            actionScatterLine=menu.addAction("Line-scatter")
            menu.addSeparator()
            actionRemove=menu.addAction("Remove")
            actionLine.triggered.connect(lambda : self.setLineStyle(style='line'))
            actionScatter.triggered.connect(lambda : self.setLineStyle(style='scatter'))
            actionScatterLine.triggered.connect(lambda : self.setLineStyle(style='scatter-line'))
            actionRemove.triggered.connect(self.removeLine)
            menu.exec_(self.plotList.mapToGlobal(point))
        self.plotList.setContextMenuPolicy(Qt.CustomContextMenu) 
        self.connect(self.plotList, SIGNAL("customContextMenuRequested(const QPoint &)"),menuContextPlotlist)

        #Full Layout
        propLayout = QGridLayout()          # create a layout for 
        propLayout.addLayout(playout,0,0,1,2)   # the controls above
        propLayout.addItem(linePropertiesLayout,1,0) # the line properties on the left
        propLayout.addWidget(self.plotList,1,1)      # and the list of plots on the right
        splitter = QSplitter(Qt.Vertical)   # vertica splitter with  
        splitter.addWidget(self.canvas)     # the canvas
        self.controlWidget = QWidget()              # the propLayout with the controlWidget, the line properites and the plot list
        self.controlWidget.setLayout(propLayout)
        splitter.addWidget(self.controlWidget)
        layout = QGridLayout()              # overall layout
        layout.addWidget(splitter)          # takes the vertical splitter
        self.setLayout(layout)

    def updatedGui(self,subject = None,property = None,value = None):     # notification listener of Plot2DWidget
        debug("in Plot2DWidget.updatedGui with subject=", subject," property=",property," and value=",value)
        self._updated = False
        if subject==self._manager and property=='addDatacube':
          if self.autoplot.isChecked(): self.addPlots(cube=value)
        elif isinstance(subject,Datacube) and (property == "names" or property =="addChild"):
          if subject == self._cube:
            if property =="names":
              self.updateControls()
              if self.autoplot.isChecked():   self.addPlots(cube=subject) # allows autoplot of a datacube that gets its first columns

    def addPlots(self,cube=None,level=None,x=None,y=None,clear='auto',style=None,**kwargs):
        debug('in Plot2DWidget.addPlots with cube=',cube,',level=',level,', x=',x,', y=',y,', clear=',clear,', style=',style,', and current cube = ',self._cube)          
        if level==None: level=self.level.value()
        if cube==None : cube =self._cube              # if no datacube passed use the current datacube
        if cube==None:  return                        # give-up if no datacube
        if len(cube.names())==0:                      # give up if datacube has no column, but attach it if autoplot...
          if self.autoplot.isChecked():
            debug('attaching ',cube,' to ',self)
            cube.attach(self)                         # ... so that on next names notification==> opportunity to autoplot.
        x,y=self.preselectXY(cube=cube,level=level,xName=x,yName=y)  # Build valid x and y names
        if not x or not y: return                     # give up if no valid names
        cubes=cube.cubesAtLevel(level=level,allBranchesOnly=True)
        if self.autoclear.isChecked() or clear==True: self.clearPlots() 
        for cubei in cubes:
          self.addPlot(cube=cubei,x=x,y=y,clear=False,style=style,**kwargs)
  
    def addPlot(self,cube=None,x=None,y=None,clear='auto',style=None,**kwargs):
        """
        Adds a plot of a datacube in self._plots with specified axes and pre-clearing if requested. In case cube=None, use the current datacube.
        Add the corresponding line in the table below the graph.
        Then calls self.updatePlot() for redrawing.
        Note: in case datacube has no column, no plot is added.
        """
        debug('in Plot2DWidget.addPlot with cube=',cube,', x=',x,', y=',y,', clear=',clear,', style= ', style, ' and current cube = ', self._cube)
        if cube==None : cube =self._cube              # if no datacube passed use the current datacube
        if cube==None:  return                        # give-up if no datacube
        if len(cube.names())==0:                      # give up if datacube has no column, but attach it if autoplot
          if self.autoplot.isChecked():
            debug('attaching ',cube,' to ',self)
            cube.attach(self)                         # at the next names notification, opportunity to autoplot.
            return
        if (self.autoclear.isChecked() and clear=='auto') or clear==True:       # clear if autoclear
          self.clearPlots() 
        x,y=self.preselectXY(cube=cube,xName=x,yName=y) # Build valid x and y names
        if not x or not y: return                     # give up if no valid names                                  
        for plot in self._plots:                      # Check if the plot is already present in the list of plots
          if cube == plot.cube :
            if plot.xname == x and plot.yname == y:
              self.updatePlot()
              return                                  # and update only and stop if the plot is  already present
        plot = cube2DPlot()                           # Ohterwise build the new cube2DPlot 
        plot.xname = x
        plot.yname = y   
        plot.cube = cube 
        plot.legend = "%s, %s vs. %s" % (cube.name(),plot.xname,plot.yname)
        # The cube2DPlot has a property line that point to its corresponding axes' plot
        # Plotting with axes.plot returns the list of all plots, the first of which is the last added one.
        # The strategy here is to first make an empty plot, get it and set the line property to it; Then the plot will be filled with points and redrawn.
        xvalues,yvalues=[[],[]]
        plot.line, = self.canvas.axes.plot(xvalues,yvalues,**kwargs) 
        if (not style) or self.lineStyles.findText(style)==-1: style =self.lineStyles.currentText()
        plot.style = style
        if style == 'scatter':
          plot.line.set_linestyle('')
          plot.line.set_marker('o')
        elif style == 'line':
          plot.line.set_linestyle('-')
          plot.line.set_marker('')
        else:
          plot.line.set_linestyle('-')
          plot.line.set_marker('o')
        #self._cnt+=1
        debug('attaching ',plot.cube,' to ',self)
        plot.cube.attach(self)
        #plot.lineStyleLabel = QLabel("line style") # remove by DV
        plotItem = QTreeWidgetItem([cube.name(),plot.xname,plot.yname,plot.style]) # Add the plot as a plotitem in the view plotList below the graph window 
        self.plotList.addTopLevelItem(plotItem)
        #self.plotList.setItemWidget(plotItem,4,plot.lineStyleLabel)
        self.plotList.update()                             # update the view plotList of self._plot
        plot.item=plotItem
        self._plots.append(plot)                           # and add the plot to the list self._plots
        self.updatePlot()                                  # update the graph (will fill with points, create all labels, and redraw)
   
    def removePlot(self,index=None):
        """
        Remove a plot from the graph and from self._plots by index.
        If index is not specified remove the current index.
        If index does not exist does nothing.
        """
        if index ==None : index=self._currentIndex
        if index!= -1 and index < len(self._plots):
            cube=self._plots[index].cube                    # retrieve the cube of the plot to be deleted
            self.canvas.axes.lines.pop(index)               # delete the plot from axes...
            self._plots.pop(index)                          #... as well as from self._plots
            cubes= [plot.cube for plot in self._plots]      # detach the cube if it is not the current cube and if it is not in another plot
            if cube !=self._cube and not cube in cubes: cube.detach(self)
            self._currentIndex = None
            self.updatePlot()

    def clearPlots(self):
        """
        Clears all the plots from the graph and from self._plotList.
        """
        for plot in self._plots:
          if plot.cube != self._cube:
            plot.cube.detach(self)
        self._plots = []
        self._currentIndex = None
        self.plotList.clear()
        self.canvas.axes.lines=[]
        #self._cnt = 0
        self.updatePlot()
    
    def updatePlotLabels(self,draw=False):
        """
        Rebuilt axis labels, title and legend.
        """
        xnames = []
        ynames = []
        legend = []
        legendPlots = []
        filenames = []   
        names=[]
        for plot in self._plots:
          if not plot.xname in xnames:
            xnames.append(plot.xname)
          if not plot.yname in ynames:
            ynames.append(plot.yname)
          if not plot.cube.name() in names:
            names.append(plot.cube.name())
          if plot.cube.filename() != None and not plot.cube.filename() in filenames:
            legend.append(plot.yname+":"+plot.cube.filename()[:-4])
            legendPlots.append(plot.line)
            filenames.append(plot.cube.filename())
        xLabel=", ".join(xnames)
        if len(xLabel) > 30:    xLabel=xLabel[:27] + '...' 
        yLabel=", ".join(ynames)
        if len(yLabel) > 20:    xLabel=yLabel[:27] + '...' 
        title=", ".join(names)
        if len(title) > 63: title=title[:60] + '...'
        self.canvas.axes.set_xlabel(xLabel)
        self.canvas.axes.set_ylabel(yLabel)
        self.canvas.axes.set_title(title)
        if self._showLegend and len(legend) > 0:
          from matplotlib.font_manager import FontProperties
          self.canvas.axes.legend(legendPlots,legend,prop = FontProperties(size = 6))
        else:
          self.canvas.axes.legend_ = None 
        if draw: self.canvas.redraw()

    def updatePlotLine(self,draw=False,plot=None):
        """
        Refill the listed plots with their points.
        If no list of plots is given, all plots in self._plots are updated.
        """
        debug("in Plot2DWidget.updatePlotLine() with plot=",plot)
        if plot==None and self._currentIndex:   plot=self._plots[self._currentIndex]
        if plot:
          if plot.xname != "[row number]":
            xvalues = plot.cube.column(plot.xname)
          else:
            xvalues = arange(0,len(plot.cube),1)
          if plot.yname != "[row number]":
            yvalues = plot.cube.column(plot.yname)
          else:
            yvalues = arange(0,len(plot.cube),1)
          plot.line.set_xdata(xvalues)
          plot.line.set_ydata(yvalues)
          plot.line.recache()       #Bug in matplotlib. Have to call "recache" to make sure the plot is correctly updated.
        if draw: self.canvas.redraw()
  
    def updatePlotLines(self,draw=False,listOfPlots=None):
        """
        Refill the listed plots with their points.
        If no list of plots is given, all plots in self._plots are updated.
        """
        debug("in Plot2DWidget.updatePlotLines() with listOfPlots=",listOfPlots)
        if listOfPlots==None:   listOfPlots=self._plots
        if listOfPlots==None or listOfPlots==[] : return
        for plot in listOfPlots:
            self.updatePlotLine(draw=False,plot=plot)  
        if draw: self.canvas.redraw()

    def updatePlot(self,listOfPlots=None):
        """
        Rebuilt axis labels, title and legend, then refill the listed plots with their points.
        If no list of plots is given, all plots in self._plots are updated.
        """
        debug("in Plot2DWidget.updatePlot()")
        if len(self._plots) == 0:           # clear the graph without using clf, which would loose the fixed scales if any.
            self.canvas.axes.cla()
            self.canvas.redraw()
            return
        self.updatePlotLabels(draw=False)
        self.updatePlotLines(draw=True,listOfPlots=listOfPlots)

    def setCube(self,cube,xName=None,yName=None):
        """"
        Set the selected datacube as current cube, update x and y names in selectors, and call plot if autoplot
        """
        debug('in Plot2DWidget.setCube(cube,xName,yName) with cube =',cube,' xName=',xName, ' and yName=',yName)  
        detachPrevious= True
        if self._cube!=None and  self._cube in self.parent.manager.datacubes():
          found = False                 # Detach previous cube if not in a plot or if removed from datamanager
          for plot in self._plots:
            if self._cube == plot.cube :
              found = True
              break
          if found:
            detachPrevious= False
        if self._cube!=None and detachPrevious :
          debug('detaching ',self._cube,' from ',self)
          self._cube.detach(self)
        self._cube = cube                                     # defines the new cube as current cube
        if self._cube!=None:
          debug("attaching",self._cube,'to',self)
          self._cube.attach(self)                             # and observes the cube in case it changes names or gets new data
        self.updateControls(level=0,xName=xName,yName=yName)  # update the variable selectors
        if self.autoplot.isChecked():  self.addPlot()         # and plot if autoplot      
      
    def preselectXY(self,cube=None,level=0,xName=None,yName=None,previousXName=None,previousYName=None):
        """
        preselect x and y names before plotting a datacube.
        """
        if cube==None : cube=self._cube           # if no datacube passed use the current datacube
        if cube==None :  return                   # if no datacube give up
        if level==None :level=0 
        commonNames=cube.commonNames()            # gets all column names of the datacube and its children that are common to a same level
        levelMax=len(commonNames)-1
        if level>levelMax :level=levelMax
        names=commonNames[level]                  # select first the passed names if valid for both x and y                  
        if (not xName) or (not yName) or not (xName in names or xName=="[row number]") or not (yName in names or yName=="[row number]"):
          cubes=cube.cubesAtLevel(level=level,allBranchesOnly=True)
          for cubei in cubes:
            if 'defaultPlot' in cubei.parameters():  # else select the first valid default plot if defined in one of the datacubes
              for params in cube.parameters()["defaultPlot"]:
                xName,yName=params[:2]
                if xName in names and yName in names:
                  break
                return xName,yName
                                                  # else select names of previous plot if possible
          if not previousXName: previousXName= self.xNames.currentText()
          if not previousYName: previousYName= self.yNames.currentText()
          if previousXName in names and previousYName in names: 
            xName,yName=previousXName,previousYName
          elif len(names)>=2:                     # else choose names[0] and names[1] if they exist
            xName,yName=names[0:2]  
          elif len (names)==1:                    # else choose "[row number]" and names[1] if they exist
              xName="[row number]"
              yName=names[0]
          else:
            xName,yName=None,None
            print "can't select valid columns for x and y"
        return str(xName),str(yName)

    def updateControls(self,level=None,xName=None,yName=None):
        """
        Updates the level and the x and y names in the x and y selectors. Then makes a pre-selection by calling preselectXY().
        """
        cube=self._cube
        debug("in Plot2DWidget.updateControls(xName,yName) with level=",level,", xName=",xName, ', yName=',yName, ', and current datacube=',self._cube)
        currentX = self.xNames.currentText()  # memorize current selection to reuse it if necessary
        currentY = self.yNames.currentText()
        self.xNames.clear()                   # clear the selector
        self.yNames.clear()
        if cube!=None:
          commonNames=cube.commonNames()        # gets all column names of the datacube and its children that are common to a same level
          self.level.setMaximum(len(commonNames)-1)
          if level!=None : self.level.setValue(level)
          level=self.level.value()
          names=commonNames[level]
          self.xNames.addItem("[row number]") # Add the 'row number' choice
          self.yNames.addItem("[row number]")              
          for name in names:                  # add all other choices from the current datacube
            self.xNames.addItem(name,name)    
            self.yNames.addItem(name,name)   
          xName,yName=self.preselectXY(cube=cube,level=level,xName=xName,yName=yName,previousXName=currentX,previousYName=currentY)
          if xName and yName:                 # select the requested x and y names if correct
            ix = self.xNames.findText(xName)
            iy = self.yNames.findText(yName)
            if ix != -1 and iy != -1:
              self.xNames.setCurrentIndex(ix)
              self.yNames.setCurrentIndex(iy)
        if self.xNames.count()*self.xNames.count()>0  : self.addButton.setEnabled(True)
        else: self.addButton.setEnabled(False)
    
    def autoplotChanged(self,CheckState):
        if CheckState:
          self.updatedGui(subject=self._cube,property = "names",value = None)

    def levelChanged(self):
        self.updatedGui(subject=self._cube,property = "names",value = None)

    def namesChanged(self):                                             # not used yet
        self.updatedGui(subject=self,property = "redraw",value = None)
          
    def onTimer(self):
        if self._updated == True:
          return
        self._updated = True
        self.updatePlot()
    
    def showLegendStateChanged(self,state):
        if state == Qt.Checked:
          self._showLegend = True
        else:
          self._showLegend = False
        self.updatePlot()

    def removeLine(self):
        debug("in Plot2DWidget.removeLine()")
        self._currentIndex = self.plotList.indexOfTopLevelItem(self.plotList.currentItem())
        self.plotList.takeTopLevelItem(self._currentIndex) # remove the item from plotList
        self.removePlot()

    def setLineStyle(self,index=None,style=None):
        debug("in Plot2DWidget.setLineStyle() with index=",index,"and style=",style)
        if index==None :                                                # if index is not passed choose the current index in plotList
          index=self.plotList.indexOfTopLevelItem(self.plotList.currentItem())
        if self._currentIndex == -1:                                
          return                                                      # return if not valid index
        self._currentIndex = index                                    # set the current index of the Plot2DWidget to index
        if not style:                                                 # if style is not passed choose the current default style
          style = str(self.styles.itemData(index).toString()) 
        if self._plots[self._currentIndex].style == style:            # if style is already correct do nothing and return
          return
        if style == 'scatter':                                        # set the style in the plot
          self._plots[self._currentIndex].line.set_linestyle('')
          self._plots[self._currentIndex].line.set_marker('o')
        elif style == 'line':
          self._plots[self._currentIndex].line.set_linestyle('-')
          self._plots[self._currentIndex].line.set_marker('')
        else:
          self._plots[self._currentIndex].line.set_linestyle('-')
          self._plots[self._currentIndex].line.set_marker('o')
        self._plots[self._currentIndex].style = style
        self.updatePlot()
        self._plots[self._currentIndex].item.setText(3,style)
  
    def lineSelectionChanged(self,selected,previous):
        if selected != None:
          index = self.plotList.indexOfTopLevelItem(selected)
          self._currentIndex = index
          # do nothing

    def nameSelector(self):
        box = QComboBox()
        box.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        names = self._cube.names()
        return box
    
#********************************************
#  DataTreeView class
#********************************************

class DataTreeView(QTreeWidget,ObserverWidget):
    
    def __init__(self,parent = None):
        QTreeWidget.__init__(self,parent)
        ObserverWidget.__init__(self)
        self._parent=parent
        self._items = dict()
        self._manager = dm.DataManager()           # attach  dataManager to this dataTreeview, i.e. dataTreeView receives message from datamanager  
        debug('attaching ',self._manager,' to ',self)
        self._manager.attach(self)
        self.setHeaderLabels(["Name"])
        for cube in self._manager.datacubes():
          self.addDatacube(cube,None)
        self.itemDoubleClicked.connect(self.renameCube)
   
    def renameCube(self):
        if self._parent!=None: self._parent.renameCube()

    def ref(self,cube):
        #debug("in DataTreeView.ref(cube) with cube =",cube,' ref(cube) =',weakref.ref(cube))
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
        debug("in DataTreeView.selectCube(datacube) with datacube =",cube)
        if self.ref(cube) in self._items:
          item = self._items[self.ref(cube)]
          self.setCurrentItem(item)

    def addCube(self,cube,parent):
        debug("in DataTreeView.addCube(cube) with cube =",cube, "and cube's parent =",parent)
        if self.ref(cube) in self._items:     # does not add a cube reference already present
          return
        item = QTreeWidgetItem()
        item.setText(0,str(cube.name()))
        item._cube = self.ref(cube)
        debug('attaching ',cube,' to ',self)
        cube.attach(self)
        self._items[self.ref(cube)]= item
        if parent == None:
          self.insertTopLevelItem(0,item)
        else:
          self._items[self.ref(parent)].addChild(item)
        for child in cube.children():
          self.addCube(child,cube)
      
    def removeItem(self,item):
        debug("in DataTreeView.removeItem(item) with item =",item)
        if item.parent() == None:
          self.takeTopLevelItem(self.indexOfTopLevelItem(item))
        else:
          item.parent().removeChild(item)  
  
    def removeCube(self,cube,parent):
        debug("in DataTreeView.removecube(datacube) with datacube =",cube)
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
        debug("in DataTreeView.updatecube(cube) with cube =",cube)
        item = self._items[self.ref(cube)]
        item.setText(0,cube.name())          
      
    def initTreeView(self):
        debug("in DataTreeView.initTreeView()")
        self.clear()
        dataManager = dm.DataManager()
        for cube in dataManager.datacubes():
          self.addCube(cube,None)
    
    def updatedGui(self,subject,property = None,value = None):
        debug("in DataTreeView.updatedGui with subject=",subject," property=", property,' and value =',value)
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
          debug("not managed")

#********************************************
#  DatacubeProperties class

class DatacubeProperties(QWidget,ObserverWidget):
  
    def updateBind(self):
        name = str(self.bindName.text())
        self._globals[name] = self._cube
  
    def __init__(self,parent = None,globals = {}):
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
        for widget in [self.parameters,self.attributes]:
            widget.setHorizontalHeaderLabels(('Key','Value'))
            widget.setColumnWidth (0, 100)
            widget.setColumnWidth (1, 200)
            widget.setEditTriggers(QAbstractItemView.AllEditTriggers)

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
        debug("in DatacubeProperties.setCube(cube) with cube = ",cube)
        if self._cube != None:
          debug('detaching ',self._cube,' from ',self )
          self._cube.detach(self)
        self._cube = cube
        if not self._cube == None:
          debug('attaching',self._cube,'to',self)
          self._cube.attach(self)
        self.updateProperties()
    
    def updateProperties(self):
        debug("in DatacubeProperties.updateProperties()")
        filename=name=tags=description=''
        self.parameters.clear()
        self.attributes.clear()
        if self._cube != None:
            filename=str(self._cube.filename());
            name=str(self._cube.name())
            tags=str(self._cube.tags())
            description=str(self._cube.description())
            self.setEnabled(True)
            params=self._cube.parameters()
            i=0
            for key in params:
                self.parameters.setItem(0,i,QTableWidgetItem(str(key)))
                self.parameters.setItem(1,i,QTableWidgetItem(str(params[key])))
                i+=1
            parent=self._cube.parent()
            if parent:
                attribs=parent.attributesOfChild(self._cube)
                self.attributes.setEnabled(True)
                i=0
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
        debug("in DatacubeProperties.updatedGui with property ",property,' and value=',value)
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

class DataManager(QMainWindow,ObserverWidget):
  
    def __init__(self,parent = None,globals = {}):  # creator of the frontpanel
        debug("in dataManager frontpanel creator")
        QMainWindow.__init__(self,parent)
        ObserverWidget.__init__(self)

        self.manager = dm.DataManager()
        debug('attaching',self.manager,'to',self)
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
            debug("self.tabs.currentWidget=",self.tabs.currentWidget())
            debug("self.plotters2D=",self.plotters2D)
            debug("self.plotters3D=",self.plotters3D)
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
        debug('in DataManager.selectCube with current cube =',current,' and last cube=',last)
        if current == None: self._cube=None
        else:
          self._cube = current._cube() 
          if self._cube == None: self.cubeList.removeItem(current) 
        cube=self._cube
        self.controlWidget.setCube(cube)
        self.cubeViewer.setDatacube(cube)
        for plotter2D in self.plotters2D:
          plotter2D.setCube(cube)
        #for plotter3D in self.plotters3D: plotter3D.setCube(cube)    
          
    def updatedGui(self,subject = None,property = None,value = None):
        debug('in DataManager.updatedGui with subject=', subject,', property =',property,', and value=',value)
        if subject == self.manager and property == "plot":
          cube=value[0][0]
          kwargs=value[1]
          if isinstance(self.tabs.currentWidget,Plot2DWidget):
            self.tabs.currentWidget.addPlot(**kwargs)
        else :debug("not managed")
        
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
        debug("in DataManager.loadCube()")
        filename = QFileDialog.getOpenFileName(filter = "Datacubes (*.par)",directory = self.workingDirectory())
        if not filename == '':
          self.setWorkingDirectory(filename)
          cube = Datacube()
          cube.loadtxt(str(filename))
          self.manager.addDatacube(cube)
          self._cube=cube                     # Make the manually loaded datacube the current cube. It will be automatically selected also in the dataTreeview
    
    def newCube(self):
        debug("in DataManager.newCube()")
        manager = dm.DataManager()
        cube = Datacube()
        cube.set(a =0,b = 0,commit=True)
        manager.addDatacube(cube)
        self._cube=cube                     # Make the manually created datacube the current cube. It will be automatically selected also in the dataTreeview

    def renameCube(self):
        debug("in DataManager.renameCube()")
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

    def removeCube(self):
        debug("in DataManager.removeCube()")
        if self._cube == None:
          return
        manager = dm.DataManager()
        if self._cube in manager.datacubes():
          print "Removing from data manager..."
          manager.removeDatacube(self._cube)
        elif self._cube.parent() != None:
          self._cube.parent().removeChild(self._cube)
        self._cube = None

    def saveCubeAs(self):
        self.saveCube(saveAs = True)
        
    def addChild(self,new=False):
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
          if cube:  self._cube.addChild(cube)

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
    debug("in startDataManager")
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