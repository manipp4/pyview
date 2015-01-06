#*******************************************************************************
# DataManager Frontpanel                                  .                    *
#*******************************************************************************

___debugDM2GUI___ = False
def debugDM2GUI(*args):
  if ___debugDM2GUI___:
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
import warnings

from pyview.gui.coderunner import execInGui

from pyview.gui.mpl.canvas import *
reload(sys.modules['pyview.gui.mpl.canvas'])
from pyview.gui.mpl.canvas import *

from matplotlib import colors,cm
from mpl_toolkits.mplot3d import Axes3D


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
  debugDM2GUI("in startPlugin")
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

class cube3DPlot:
    def __init__(self):
        pass

#********************************************
#  PlotWidget classes
#********************************************
__styles2D__=['line','scatter','line+symbol'];__defaultStyle2D__=0
__styles3D__=['Waterfall','Image (reg)','Image (rnd)','Contours','Scatter','Surface','Tri-surface'];__defaultStyle3D__=1
__colors3D__=['binary','gray','jet','hsv','autumn','cool'];__defaultColor3D__=2
__regridize__=['None','skip','interpolate'];__defaultRegridize__=0

class PlotWidget(QWidget,ObserverWidget):

    def __del__(self):
        debugDM2GUI("deleting ",self)

    def __init__(self, parent=None, name=None,threeD=False):  # creator PlotWidget
        debugDM2GUI("in PlotWidget.__init__(parent,name,threeD) with parent=",parent," name=",name," and threeD=",threeD)
        QWidget.__init__(self,parent)
        ObserverWidget.__init__(self)
        self.parent=parent
        self.name=name
        self._threeD=threeD                         # never change this value after instance creation
        self._cube = None
        self._showLegend = False
        self._plots = []
        self._updated = False
        self._currentIndex = None
        self.legends = []
        self.cubes = []
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.connect(self.timer,SIGNAL("timeout()"),self.onTimer)

        self._manager = dm.DataManager()           # attach  dataManager to this Plot2DWidget, i.e. Plot2DWidget receives message from datamanager  
        debugDM2GUI('attaching ',self._manager,' to ',self)
        self._manager.attach(self)
        
        # definition of the Canvas
        self.canvas = MyMplCanvas(dpi = 72,width = 8,height = 8,name=name,threeD=threeD)

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
            self.regularGrid=QRadioButton('regular grid');self.regularGrid.setChecked(False);self.regularGrid.setEnabled(True)
            self.regridize=QComboBox()
            for method in __regridize__: self.regridize.addItem(method)
            self.regridize.setCurrentIndex(__defaultRegridize__)
            comboBoxes=variableNames
            comboBoxes.append(self.regridize)
        for combo in comboBoxes : combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        # then add controls to sublayout,
        if not threeD:
            widgets=[QLabel("Level:"),self.level,QLabel("X:"),self.xNames,QLabel("Y:"),self.yNames]
            #widgets=[QLabel("Level:"),self.level,QLabel("X:"),self.xNames,QLabel("Y:"),self.yNames,self.addButton,self.autoplot,self.autoclear]
        else:
            widgets=[QLabel("X:"),self.xNames,QLabel("Y:"),self.yNames,QLabel("Z:"),self.zNames,self.regularGrid,QLabel("regularize:"),self.regridize]
            #widgets=[QLabel("X:"),self.xNames,QLabel("Y:"),self.yNames,QLabel("Z:"),self.zNames,self.regularGrid,QLabel("regularize:"),self.regridize,self.addButton,self.autoplot,self.autoclear]
        for widget in widgets:    ctrlLayout0.addWidget(widget)
        ctrlLayout0.addStretch()
        # and make connections between signals and slots.
        for variableName in variableNames : self.connect(variableName,SIGNAL("currentIndexChanged (int)"),self.namesChanged)
        selectors=[self.xNames,self.yNames]
        if threeD:
            selectors.append(self.zNames)
        else:
            self.connect(self.level,SIGNAL("valueChanged(int)"),self.levelChanged)
        # Definition of bottom-left layout ctrlLayout1
        ctrlLayout11=QGridLayout()
        # define controls
        if threeD :
            label='Add plot'
        else:
            label= 'Add plot(s)'
        self.addButton = QPushButton(label)
        self.autoplot=QCheckBox("AutoPlot")
        self.styles = QComboBox()
        #self.styles.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Maximum)
        if not threeD:
            styles=__styles2D__
            default=__defaultStyle2D__
        else:
            styles=__styles3D__
            default=__defaultStyle3D__
        for style in styles: self.styles.addItem(style)
        self.styles.setCurrentIndex(default)
        self.colors=QComboBox()
        #self.colors.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Maximum)
        if not threeD:
            color_cycle =self.canvas.axes._get_lines.color_cycle
            colors=[]
            for i, color in enumerate(color_cycle):
                if i==0 or color!=colors[0]:
                    colors.append(color)
                else: break
            default=0
        else:            
            colors=__colors3D__
            default=__defaultColor3D__
        for color in colors: self.colors.addItem(color)
        self.colors.setCurrentIndex(default)
        self.showLegend = QCheckBox("Legend")
        self.showLegend.setCheckState(Qt.Checked)
        self.clearButton = QPushButton("Clear all")
        self.autoclear=QCheckBox("AutoClear")
        # then add controls to sublayout,
        ctrlLayout11.addWidget(self.addButton,0,0)
        ctrlLayout11.addWidget(self.autoplot,0,1)
        ctrlLayout11.addWidget(self.clearButton,1,0)
        ctrlLayout11.addWidget(self.autoclear,1,1)
        ctrlLayout11.addWidget(self.styles,2,0)
        ctrlLayout11.addWidget(self.showLegend,3,1)
        ctrlLayout11.addWidget(self.colors,3,0)

        #widgets=[QLabel('Default style:'),self.styles,QLabel('Default colors:'),self.colors,self.showLegend,self.clearButton]
        #for widget in widgets:    ctrlLayout1.addWidget(widget)
        ctrlLayout1=QBoxLayout(QBoxLayout.TopToBottom)
        ctrlLayout1.addLayout(ctrlLayout11)
        ctrlLayout1.addStretch()
        # and make connections between signals and slots.
        self.connect(self.autoplot,SIGNAL("stateChanged(int)"),self.autoplotChanged)
        addPlot=lambda: self.addPlot(names=[str(name.currentText()) for name in selectors])
        self.connect(self.addButton,SIGNAL("clicked()"),addPlot)
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
            actionRemove.triggered.connect(lambda : self.removeLine(update=True))
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

        self.timer.start()

    def onTimer(self):
        if self._updated == True:
            return
        debugDM2GUI(self.name,'.onTimer() calling updatePlot()') 
        self._updated = True
        self.updatePlot(draw=True)

    def updatedGui(self,**kwargs):                           # subclass in Plot2DWidget and Plot3DWidget
        return

    def addPlot(self):                                       # subclass in Plot2DWidget and Plot3DWidget
        return

    def removeFromCanvas(self,plot):
        debugDM2GUI('in removeFromCanvas with plot =',plot )
        cv=self.canvas
        fig=cv._fig
        if not self._threeD:
            #if isinstance(plot.MPLPlot) in ['line']        # test if it is a line
            cv.axes.lines.remove(plot.MPLplot)              # delete the plot from axes 
            del plot.MPLplot
        else:
            #if isinstance(plot.MPLPlot) in ['line']        # test if it is an image
            cv.axes.images.remove(plot.MPLplot)             # remove from axes images    
            del plot.MPLplot                                # and delete from memory
            if len(self._plots)==0 and len(fig.axes)>=2:    # if no other plots
                fig.delaxes(fig.axes[1])                    # del colorbar axes = axes(1)
                                                            # restore initial size here

    def clearPlots(self): # simplify here by calling removeplot
        """
        Clears all the plots from the graph and from self._plotList.
        """
        debugDM2GUI("in PlotWidget.clearPlots()")
        pl=self.plotList
        while pl.topLevelItemCount()!=0:
            pl.setCurrentItem(pl.topLevelItem(0))
            self.removeLine(update=False)
        self._updated = False
    
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
            filenames.append(plot.cube.filename())
            if not self._threeD : legendPlots.append(plot.MPLplot)
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

    def updatePlot(self,listOfPlots=None,draw=False):
        """
        Rebuilt axis labels, title and legend, then refill the listed plots with their points.
        If no list of plots is given, all plots in self._plots are updated.
        """
        debugDM2GUI('in PlotWidget ',self.name,'.updatePlot() with draw = ',draw)
        self.updatePlotLabels(draw=False)
        if len(self._plots) == 0:                            # clear the graph without using clf, which would loose the fixed scales if any.
            self.canvas.redraw()                                   
            return
        if listOfPlots==None:   listOfPlots=self._plots
        if listOfPlots==None or listOfPlots==[] : return
        for plot in listOfPlots:
            self.updatePlotData(draw=False,plot=plot)  
        if draw: self.canvas.redraw()        

    def updatePlotData(self,**kwargs):                       # subclass in Plot2DWidget and Plot3DWidget
        return

    def setCube(self,cube,names=[None,None,None]):
        """"
        Set the selected datacube as current cube, update variable names in selectors, and call plot if autoplot
        """
        debugDM2GUI('in PlotWidget.setCube(cube,names) with cube =',cube,' names=',names)  
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
          debugDM2GUI('detaching ',self._cube,' from ',self)
          self._cube.detach(self)
        self._cube = cube                                    # defines the new cube as current cube
        if self._cube!=None:
          debugDM2GUI("attaching",self._cube,'to',self)
          self._cube.attach(self)                            # and observes the cube in case it changes names or gets new data
        if not self._threeD:
            kwargs={'level':0,'names':names[0:2]}            # update the 2D variable selectors
        else:
            kwargs={'names':names}                           # date the 3D variable selectors
        self.updateControls(**kwargs)
        if self.autoplot.isChecked():  self.addPlot2()        # and plot if autoplot     

    def preselectVariables(self):                            # subclass in Plot2DWidget and Plot3DWidget
        return

    def updateControls(self,**kwargs):                       # subclass in Plot2DWidget and Plot3DWidget
        return

    def setStyle(self,**kwargs):                             # subclass in Plot2DWidget and Plot3DWidget
        return

    def setColor(self,**kwargs):                             # subclass in Plot2DWidget and Plot3DWidget
        return

    def removePlot(self,plot,update=True):
        """
        Remove a plot from the graph and from self._plots.
        If index is not specified remove the current index.
        If index does not exist does nothing.
        """
        debugDM2GUI("in PlotWidget.removePlot() with plot = ",plot," and update = ",update)
        if plot:
            self._plots.remove(plot)          #... as well as from self._plots
            self.removeFromCanvas(plot)       # delete the plot from the canvas
            cube=plot.cube                    # retrieve the cube of the plot to be deleted
            del plot
            cubes= [plot.cube for plot in self._plots]      # detach the cube if it is not the current cube and if it is not in another plot
            if cube !=self._cube and not cube in cubes: cube.detach(self)
            #self._currentIndex = None
            if update : self._updated = False

    def removeLine(self, update =True):
        debugDM2GUI("in PlotWidget.removeLine with update =",update)
        self._currentIndex = self.plotList.indexOfTopLevelItem(self.plotList.currentItem())
        plot=self._plots[self._currentIndex]
        self.plotList.takeTopLevelItem(self._currentIndex) # remove the item from plotList
        self.removePlot(plot,update=update)

    def lineSelectionChanged(self,selected,previous):
        if selected != None:
          index = self.plotList.indexOfTopLevelItem(selected)
          self._currentIndex = index

    def autoplotChanged(self,CheckState):
        debugDM2GUI("in PlotWidget.autoplotChanged()")
        if CheckState:
          self.updatedGui(subject=self._cube,property = "names",value = None)

    def levelChanged(self):                                  # subclass in Plot2DWidget only
        return

    def namesChanged(self):
        #debugDM2GUI("in PlotWidget.namesChanged()")               # not used yet
        #self.updatedGui(subject=self,property = "redraw",value = None)
        return
    
    def showLegendStateChanged(self,state):
        debugDM2GUI("in PlotWidget.showLegendStateChanged()")
        if state == Qt.Checked:
          self._showLegend = True
        else:
          self._showLegend = False
        self._updated = False

class Plot2DWidget(PlotWidget):

    def __init__(self, parent=None, name=None): # creator Plot2DWidget
        PlotWidget.__init__(self,parent=parent,name=name,threeD=False)
        self.colors.setEnabled(False)

    def updatedGui(self,subject = None,property = None,value = None):     # notification listener of Plot2DWidget
        debugDM2GUI('in ',self.name,'.updatedGui with subject=', subject,', property=',property,', and value=',value)
        if subject==self._manager and property=="addDatacube" :           # 1) A new datacube arrived.
            if self.autoplot.isChecked():
                self.addPlot(cube=value)                                  #     if autoplot, addPlot it (or attach if it's empty for delayed addplotting)
        elif isinstance(subject,Datacube) and property =="names":         # 2) New names of an attached datacube arrived
            cube=subject                                                  #     the datacube cube is the notifed subject
            if  cube== self._cube:  self.updateControls()                 #     if current datacube => update controls
            if self.autoplot.isChecked():
                self.addPlot(cube=cube)                                   #     allows autoplot of a datacube that gets its first columns     
        elif isinstance(subject,Datacube) and property =="addChild":      # 3) a datacube attached to this plotter has a new child
            cube=subject; child=value                                     #     the datacube and the child are the notified property and value, respectively
            if  cube== self._cube:   self.updateControls()                #     if current datacube and levels >0 => update controls
            if self.autoplot.isChecked():
                self.addPlot(cube=child)                                  #     if autoplot, addplot the added child (the value)
        elif subject==self._manager and property=="addChild" :            #  4) a datacube of the datamanger not attached to this plotter (otherwise would be case 3) has new child
            if self.autoplot.isChecked():
                cube=None # retrieve here the child datacube
                self.addPlot(cube=cube)
        elif isinstance(subject,Datacube) and property =="commit":        #  5) New points arrived in an attached datacube:
            cube=subject;
            for plot in self._plots:                                      #     If attached only as current cube for name update do nothing
                if cube == plot.cube :                                    #     Otherwise update plot
                    self._updated = False
                    break
        else:                                                             # note that addPlot set self._updated to False after completion
            debugDM2GUI("not managed")

    def addPlot(self,cube=None,level=None,names=[None,None],clear='auto',style=None,**kwargs):
        """
        Adds plots of a datacube at level level by calling addPlot2 for all children of that level or for the cube itself if level==0.
        """
        debugDM2GUI('in ',self.name,'.addPlot with cube=',cube,',level=',level,', names=',names,', clear=',clear,', style=',style,', and current cube = ',self._cube)          
        if level==None: level=self.level.value()
        if cube==None : cube =self._cube              # if no datacube passed use the current datacube
        if cube==None:  return                        # give-up if no datacube
        if len(cube.names())==0:                      # if datacube has no column,...
            if self.autoplot.isChecked():
                debugDM2GUI('attaching ',cube,' to ',self)  # attach it  if autoplot... 
                cube.attach(self)                     # ... so that on next names notification it is autoplotted;
            return                                    # then give up
        names=self.preselectVariables(cube=cube,level=level,names=names)  # Build valid x and y names
        if any([not bool(name) for name in names]): return                     # give up if no valid names
        cubes=cube.cubesAtLevel(level=level,allBranchesOnly=True)
        if self.autoclear.isChecked() or clear==True: self.clearPlots() 
        for cubei in cubes:
            self.addPlot2(cube=cubei,names=names,clear=False,style=style,**kwargs)
  
    def addPlot2(self,cube=None,names=[None,None],clear='auto',style=None,**kwargs):
        """
        Adds a plot of a datacube in self._plots with specified axes and pre-clearing if requested. In case cube=None, use the current datacube.
        Add the corresponding line in the table below the graph.
        Then calls self.updatePlot() for redrawing.
        Note: in case datacube has no column, no plot is added.
        """
        debugDM2GUI('in ',self.name,'.addPlot2 with cube=',cube,', names=',names,', clear=',clear,', style= ', style, ' and current cube = ', self._cube)
        if cube==None : cube =self._cube              # if no datacube passed use the current datacube
        if cube==None:  return                        # give-up if no datacube
        if len(cube.names())==0:                      # give up if datacube has no column, but attach it if autoplot
          if self.autoplot.isChecked():
            debugDM2GUI('attaching ',cube,' to ',self)
            cube.attach(self)                         # at the next names notification, opportunity to autoplot.
            return
        if (self.autoclear.isChecked() and clear=='auto') or clear==True:       # clear if autoclear
          self.clearPlots() 
        names=self.preselectVariables(cube=cube,names=names) # Build valid x and y names
        if any([not bool(name) for name in names]): return                     # give up if no valid names                                  
        for plot in self._plots:                      # Check if the plot is already present in the list of plots
          if cube == plot.cube :
            if [plot.xname,plot.yname] == names:
              self._updated = False
              return                                  # and update only and stop if the plot is already present
        plot = cube2DPlot()                           # Ohterwise build the new cube2DPlot 
        plot.xname,plot.yname = names 
        plot.cube = cube 
        plot.legend = "%s, %s vs. %s" % (cube.name(),plot.xname,plot.yname)
        # The cube2DPlot has a property line that point to its corresponding axes' plot
        # Plotting with axes.plot returns a plot.
        # The strategy here is to first make an empty plot, get it and set the line property to it; Then the plot will be filled with points and redrawn.
        plot.MPLplot=None                              # initialize to empty matplolib plot
        self.updatePlotData(plot=plot,**kwargs)       # call the plotting function with all parameters stored in the plot object  
        if (not style) or self.styles.findText(style)==-1: style =self.styles.currentText()
        plot.style = style
        if style == 'scatter':
          plot.MPLplot.set_linestyle('')
          plot.MPLplot.set_marker('o')
        elif style == 'line':
          plot.MPLplot.set_linestyle('-')
          plot.MPLplot.set_marker('')
        else:
          plot.MPLplot.set_linestyle('-')
          plot.MPLplot.set_marker('o')
        #self._cnt+=1
        debugDM2GUI('attaching ',plot.cube,' to ',self)
        plot.cube.attach(self)
        #plot.MPLplotStyleLabel = QLabel("line style") # remove by DV
        plot.color=color=plot.MPLplot.get_color()
        plotItem = QTreeWidgetItem([cube.name(),plot.xname,plot.yname,plot.style,color]) # Add the plot as a plotitem in the view plotList below the graph window 
        self.writeInColorInQTreeWidget(plotItem,4,color,color)
        self.plotList.addTopLevelItem(plotItem)
        #self.plotList.setItemWidget(plotItem,4,plot.MPLplotStyleLabel)
        self.plotList.update()                             # update the view plotList of self._plot
        plot.item=plotItem
        self._plots.append(plot)                           # and add the plot to the list self._plots
        self._updated = False                              # update the graph (will fill with points, create all labels, and redraw)
    
    def updatePlotData(self,plot=None,draw=False,**kwargs):
        """
        Refill the listed plots with their points.
        If no list of plots is given, all plots in self._plots are updated.
        """
        debugDM2GUI('in ',self.name,'.updatePlotData() with plot=',plot,' and draw =',draw)
        if plot==None and self._currentIndex:   plot=self._plots[self._currentIndex]
        if plot:
          if plot.MPLplot==None:
            plot.MPLplot, = self.canvas.axes.plot([],[],**kwargs) #this is where the line plot is created
          if plot.xname != "[row]":
            xvalues = plot.cube.column(plot.xname)
          else:
            xvalues = arange(0,len(plot.cube),1)
          if plot.yname != "[row]":
            yvalues = plot.cube.column(plot.yname)
          else:
            yvalues = arange(0,len(plot.cube),1)
          plot.MPLplot.set_xdata(xvalues)
          plot.MPLplot.set_ydata(yvalues)
          plot.MPLplot.recache()       #Bug in matplotlib. Have to call "recache" to make sure the plot is correctly updated.
        if draw: self.canvas.redraw()


    def updateControls(self,level=None,names=[None,None]):
        """
        Updates the level and the x and y names in the x and y selectors. Then makes a pre-selection by calling preselectVariables().
        """
        debugDM2GUI("in Plot2DWidget.updateControls(level,names) with level=",level,", names=",names,', and current datacube=',self._cube)
        cube=self._cube
        names=names[0:2]
        selectors=[self.xNames,self.yNames]
        previousNames=[str(selector.currentText()) for selector in selectors] # memorize current selection to reuse it if necessary
        for selector in selectors : selector.clear()    # clear the selectors
        if cube!=None:
          commonNames=cube.commonNames()        # gets all column names of the datacube and its children that are common to a same level
          self.level.setMaximum(len(commonNames)-1)
          if level!=None : self.level.setValue(level)
          level=self.level.value()
          commonNames=commonNames[level]
          commonNames.insert(0,'[row]')  # Add the 'row number' choice
          for selector in selectors:  selector.addItems(commonNames)      # add all other choices from the current datacube
          names=self.preselectVariables(cube=cube,level=level,names=names,previousNames=previousNames)
          if all([bool(name) for name in names]):                # select the requested x and y names if correct
            indices=map(lambda selector,name: selector.findText(name),selectors,names)
            #print indices
            if all([index!=-1 for index in indices]):
              map(lambda selector,index: selector.setCurrentIndex(index),selectors,indices)
        if selectors[0].count()>0 : self.addButton.setEnabled(True)
        else: self.addButton.setEnabled(False)

    def preselectVariables(self,cube=None,level=0,names=[None,None],previousNames=[None,None]):
        """
        preselect x and y variables in the selectors before plotting a datacube.
        """
        if cube==None : cube=self._cube           # if no datacube passed use the current datacube
        if cube==None :  return [None,None]       # if no datacube give up
        if level==None :level=0 
        commonNames=cube.commonNames()            # gets all column names of the datacube and its children that are common to a same level
        levelMax=len(commonNames)-1
        if level>levelMax :level=levelMax
        commonNames=commonNames[level]            # select first the passed names if valid for both x and y                  
        commonNames.insert(0,'[row]')
        if any([not bool(name) for name in names]) or any([not (name in commonNames) for name in names]):
          cubes=cube.cubesAtLevel(level=level,allBranchesOnly=True)
          for cubei in cubes:
            if 'defaultPlot' in cubei.parameters():  # else select the first valid default plot if defined in one of the datacubes
              for params in cube.parameters()["defaultPlot"]:
                names=params[:2]
                if all([name in commonNames for name in names]):
                  break
                return names
          selectors=[self.xNames,self.yNames]     # else select names of previous plot if possible
          if all([bool(name) and name in commonNames for name in previousNames]): 
            names=previousNames
          elif len(commonNames)>=3:                     # else choose commonNames[0] and commonNames[1] if they exist
            names=commonNames[1:3]  
          elif len (commonNames)==2:                    # else choose "[row]" and commonNames[1] if they exist
            names=commonNames[0:2]
          else:
            print "can't select valid columns for x and y"
            names=[None,None]
        return names

    def setStyle(self,index=None,style=None):
        debugDM2GUI("in Plot2DWidget.setStyle() with index=",index,"and style=",style)
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
          self._plots[self._currentIndex].MPLplot.set_linestyle('')
          self._plots[self._currentIndex].MPLplot.set_marker('o')
        elif style == 'line':
          self._plots[self._currentIndex].MPLplot.set_linestyle('-')
          self._plots[self._currentIndex].MPLplot.set_marker('')
        else:
          self._plots[self._currentIndex].MPLplot.set_linestyle('-')
          self._plots[self._currentIndex].MPLplot.set_marker('o')
        self._plots[self._currentIndex].style = style
        self._plots[self._currentIndex].item.setText(3,style)
        self._updated = False

    def setColor(self,index=None,color=None):                            
        debugDM2GUI("in Plot2DWidget.setColor() with index=",index,"and color=",color)
        if index==None :                                                # if index is not passed choose the current index in plotList
          index=self.plotList.indexOfTopLevelItem(self.plotList.currentItem())
        if self._currentIndex == -1:                                
          return                                                      # return if not valid index
        self._currentIndex = index                                    # set the current index of the Plot2DWidget to index
        if not color:                                                 # if style is not passed choose the current default style
          color = self.colors.itemData(index).toString() 
        if self._plots[self._currentIndex].MPLplot.get_color() == color:            # if style is already correct do nothing and return
          return
        self._plots[self._currentIndex].MPLplot.set_color(color)         # set the color in the plot
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
        debugDM2GUI("in Plot2DWidget.showLegendStateChanged()")
        self.updatedGui(subject=self._cube,property = "names",value = None)
    

class Plot3DWidget(PlotWidget):
    
    def __init__(self, parent=None, name=None): # creator Plot3DWidget
        PlotWidget.__init__(self,parent=parent,name=name,threeD=True)

    def updatedGui(self,subject = None,property = None,value = None):
        return

    def addPlot(self,cube=None,names=[None,None,None],clear='auto',style=None,color=None,**kwargs): # subclass in Plot2DWidget and Plot3DWidget
        """
        Adds a plot of a datacube in self._plots with specified variables. In case cube=None, use the current datacube.
        Add the corresponding row in the table below the graph.
        Then calls self.updatePlot() for redrawing.
        Note: in case datacube has no valid columns, no plot is added.
        """
        debugDM2GUI('in ',self.name,'.addPlot with cube=',cube,', names=',names,', clear=',clear,', style= ', style, ' and current cube = ', self._cube)
        if cube==None : cube =self._cube              # if no datacube passed use the current datacube
        if cube==None:  return                        # give-up if no datacube
        ready=self.cubeReadyFor3D(cube=cube,names=names)
        if not ready:                      # give up if datacube is not ready, but attach it if autoplot
          if self.autoplot.isChecked():
            debugDM2GUI('attaching ',cube,' to ',self)
            cube.attach(self)                         # at the next notification, opportunity to autoplot.
            return
        if (self.autoclear.isChecked() and clear=='auto') or clear==True:       # clear if autoclear
          self.clearPlots() 
        names=self.preselectVariables(cube=cube,names=names) # Build valid x and y names
        if any([not bool(name) for name in names]): return                     # give up if no valid names                                  
        for plot in self._plots:                      # Check if the plot is already present in the list of plots
          if cube == plot.cube :
            if [plot.xname,plot.yname,plot.zname] == names:
              self._updated = False
              return                                  # and update only and stop if the plot is already present
        plot = cube3DPlot()                           # Ohterwise build the new cube3DPlot 
        plot.cube = cube
        plot.xname,plot.yname,plot.zname=xname,yname,zname = names  
        plot.legend = "%s, %s vs %s and %s" % (cube.name(),plot.xname,plot.yname,plot.zname)
        if (not style) or self.styles.findText(style)==-1: style =str(self.styles.currentText())
        if (not color) or self.colors.findText(color)==-1: color =str(self.colors.currentText())
        plot.style = style
        plot.color = color
        # Depending on its style property, the cube3DPlot has a data property being a tuple (x,y,2D masked array), a tuple (x,y,z), etc
        # The strategy here is to first make an empty plot
        # Then the data will be filled with new lines of points or new points, the plot's data will be set to data, and the plot will be redrawn.
        plot.MPLplot=None                                   # initialize to empty plot3D
        self.updatePlotData(plot=plot,**kwargs)             # call the updatePlotData function a first time to create an empty plot in the graph 
        debugDM2GUI('attaching ',plot.cube,' to ',self)           # attach cube to plot3DWidget
        plot.cube.attach(self)
        plotItem = QTreeWidgetItem([cube.name(),xname,yname,zname,style,color]) # Add the plot as a plotitem in the view plotList below the graph window 
        self.plotList.addTopLevelItem(plotItem)
        self.plotList.update()                              # update the view plotList of self._plot
        self._plots.append(plot)                            # and add the plot to the list self._plots
        self._updated = False                               # let ontimer() call all functions updating the graph with points, create all labels, and redraw)

    def cubeReadyFor3D(self,cube=None,names=None):
        return True

    def updatePlotData(self,draw=False,plot=None,regularize=None,**kwargs):
        """
        Create a new empty plot or update an existing one.
        """
        debugDM2GUI('in ',self.name,'.updatePlotData() with plot=',plot)
        if plot==None:
            if self._currentIndex:
                plot=self._plots[self._currentIndex]
            else: return
        fig=self.canvas._fig
        ax=self.canvas.axes
        cmap=cm.get_cmap(plot.color)
        if plot.MPLplot==None:                                                   # this is where any new 3D plot is created (as an empty plot)
            debugDM2GUI('create empty plot ',plot)
            if plot.style=="Waterfall":
                plot.MPLplot= ax.plot([0],[0],0,'x')
            elif plot.style=="Image (reg)":
                plot.data={'x':[0.],'y':[0.],'z':[[0.]]}                         # note that z is always of type a masked array
                # catch warning here to avoid seeing the error caused by an imshow with all data masked.
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", message="Warning: converting a masked element to nan.")
                    plot.MPLplot=im= ax.imshow(ma.array(plot.data['z'],mask=True),interpolation='nearest',cmap=cmap,origin='lower',**kwargs) # create 2D image
                    if len(fig.get_axes())==1:
                        cb=fig.colorbar(im,ax=fig.get_axes()[0])                     # and its colorbar
                        cb.set_label(plot.zname, rotation=90)
            elif plot.style=="Image (rnd)": 
                plot.MPLplot= ax.imshow([[0]],interpolation="nearest",cmap=cmap,**kwargs)
            elif plot.style=="Contours":
                plot.MPLplot= ax.contour([[0]],cmap=cmap,**kwargs)
            elif plot.style=="Scatter":
                plot.MPLplot= ax.scatter([0],[0],[0],cmap=cmap,**kwargs)
            elif plot.style=="Surface":
                plot.MPLplot= ax.plot_surface([[0]],[[0]],[[0]],cmap=cmap,**kwargs)
            elif plot.style=="Tri-surface":
                plot.MPLplot= ax.plot_trisurf([0],[0],[0],cmap=cmap,**kwargs)
        else:                                                                     # this is where an existing 3D plot is updated
            debugDM2GUI('update existing plot ',plot)
            if plot.style=="Waterfall":
                print 'Waterfall not implemented yet'
            elif plot.style=="Image (reg)":
                im=plot.MPLplot
                self.data2Plot(plot,regularize=regularize)
                dat=plot.data
                im.set_array(ma.array(dat['z']).T)
                im.autoscale()
                xMin,xMax,yMin,yMax,dx,dy=dat['xMin'],dat['xMax'],dat['yMin'],dat['yMax'],dat['dx'],dat['dy']
                limits=[xMin-dx/2,xMax+dx/2,yMin-dy/2,yMax+dy/2]
                im.set_extent(limits)
            elif plot.style=="Image (rnd)":
                print 'Image (rnd) not implemented yet'
            elif plot.style=="Contours":
                print 'Contours not implemented yet'
            elif plot.style=="Scatter":
                print 'Scatter not implemented yet'
            elif plot.style=="Surface":
                print 'Surface not implemented yet'
            elif plot.style=="Tri-surface":
                print 'Tri-surface not implemented yet'

    def data2Plot(self,plot,regularize=None):
        """
        Build the data dictionary plot.data used for analyzing and plotting the data.
        (This dictionary contains:
        - x (ndarray), y (ndarray), z(ndarray), mask (ndarray), dims(list),
        - rectangular(bool), regular(bool), full(bool),
        - xMin,xMax,yMin,yMax,dx,dy 
        """
        debugDM2GUI('in ',self.name,'.data2Plot() with plot=',plot," and regularize =",regularize )
        names=xname,yname,zname=plot.xname,plot.yname,plot.zname
        cube=plot.cube
        rowxyz=[]                                                                           # rowxyz is the [x,y,z] structure containing the row data
        dims=[]
        dat=plot.data                                                                             # dim stores the corresponding dimensions [dim[x],dim[y],dim[z]]
        for name in names:
            if name.startswith('childAttr:'):                                               # If the variable is a child attribute
                shortName=name[len('childAttr:'):]
                var=[cube.attributesOfChild(childCube)[shortName] for childCube in cube.children()] #   var is the 1D list of attribute values of all children
                dim=1                                                                       #   save the variable dimension as 1
            elif name.startswith('child:'):                                                 # If the variable is a children's column
                shortName=name[len('child:'):] 
                if shortName=='[row]':
                    var=[arange(0,len(childCube),1) for childCube in cube.children()]
                else:                                                         
                    var=[childCube.column(shortName) for childCube in cube.children()]      #   var is the 2D array of these children's column    
                dim=2                                                                       #   save the variable dimension as 2
            else:
                if name=='[row]':                                                           # If the variable is one of the column of the parent cube
                    var=arange(0,len(cube),1)
                else:
                    var=cube.column(name)                                                   #   set var to it
                dim=1                                                                       #   save the variable dimension as 1
            rowxyz.append(array(var))
            dims.append(dim)
        dat['x'],dat['y'],dat['z']=rowxyz                                                   # Save a first version of the data non necessarily regular,                       
        dat['xyzDims']=dims                                                                 #   as well as the corresponding dimensions.
        if plot.style in ["Image (reg)","Image (rnd)","Contours","Surface"]:                # In case the type of matplotlib plot requires regular data
            dat['rectangular'],dat['regular'],dat['full'],dat['xMin'],dat['xMax'],dat['yMin'],dat['yMax'],dat['dx'],dat['dy']=self.checkRegAndComplete(plot,complete=True) # check regularity                                                                 
            if not plot.data['regular'] and regularize:                                     # if not regular and regularize requested
                self.regularize(plot)                                                       #   try to regularize and overwrite plot.data
              
    def checkRegAndComplete(self,plot,complete=False):
        """
        Check if the data are on a rectangular XY grid (same y's for all x),
        a full grid (i.e. with no data missing at the end),
        and a regular grid (constant spacing in x, constant in y).
        Returns 3 booleans rectangular, regular and full and 6 reals xMin,xMax,yMin,yMax,dx,dy (dx,dy=None if not regular).
        """
        rectangular,full,regular=[False]*3
        dx,dy=[None]*2
        xList,yList=plot.data['x'].flatten(),plot.data['y'].flatten()
        xMin,xMax,yMin,yMax=min(xList),max(xList),min(yList),max(yList)
        dims=plot.data['xyzDims']
        if all([dim==1 for dim in dims]):                # simple columx, column y and column z
            None# sort in x, y, z, and check increments are constant for each => regular => a masked array can be formed
        elif dims[0]+dims[1]==3 and dims[2]==2: # (1d x and 2d y) or (2d x and 1d y) and 2d z values 
            var1d,var2d=plot.data['x'],plot.data['y']
            if dims[0]==2:  var1d,var2d=plot.data['y'],plot.data['x']
            # First check that the 1d and 2d XY structures match the 2d Z structure
            XYMatchZ=len(var1d)>= len(var2d) and len(var2d)==len(plot.data['z']) and all([len(var2d[i])==len(plot.data['z'][i]) for i in range(len(var2d))])
            # Second check for the  XY structure itself           
            if XYMatchZ:
                rectangular = len(var2d) in [len(var1d),len(var1d)-1]
                rectangular = rectangular and all([var==var2d[0] for var in var2d[:-1]]) and all(var2d[-1]==var2d[0][:len(var2d[-1])])
                maxLe,le=len(var2d[0]),len(var2d[-1])
                full=(le==maxLe)
                if rectangular:
                    dxs= map (lambda a,b: a-b,var2d[0][1:],var2d[0][:-1]) 
                    if all([dxi==dxs[0] for dxi in dxs]):
                        dx=dxs[0]
                        dys= map (lambda a,b: a-b,var1d[1:],var1d[:-1]) 
                        regular=all([dyi==dys[0] for dyi in dys])
                        if regular: dy=dys[0]
                    if (not full) and complete:
                        var2d[-1]=var2d[0]
                        plot.data['z'][-1].extend([ma.masked]*(maxLe-le))
        if plot.cube==self._cube:
            self.regularGrid.setChecked(rectangular)
        return rectangular,regular,full,xMin,xMax,yMin,yMax,dx,dy 

    def regularize(self,rowxyz):
        return

    def updateControls(self,names=[None,None,None]):        # subclass in Plot2DWidget and Plot3DWidget
        """
        Updates the x, y and z variable names in the x, y, and z selectors. Then makes a pre-selection by calling preselectVariables().
        """
        debugDM2GUI('in Plot3DWidget.updateControls(names) with names=',names,', and current datacube=',self._cube)
        selectors=[self.xNames,self.yNames,self.zNames]
        cube=self._cube
        currentNames=[str(selector.currentText()) for selector in selectors]   # memorize current selection to reuse it if necessary
        # First find the column name of datacube (possibly parent) and the attributes and column names common to all children if any 
        for selector in selectors : selector.clear()       # clear the selector
        self.regularGrid.setChecked(False)
        if cube!=None:                                     # if current cube exists
            names0=cube.names()                            # get its column names
            names0.insert(0,'[row]')                               
            children=cube.children()
            hasChildren=len(children)>0
            if hasChildren:
                names1=cube.commonNames()[1]               # gets all column names common to all direct children
                attributes=cube.attributesOfChildren(common=True)     # gets all attribute names common to all direct children
            # Then create the lists of choices to add the [row] choices and let the user know if a choice correspond to a parent name,or child name or attribute 
                names1.insert(0,'[row]')
                names1=['child:'+ name for name in names1]
                attributes=['childAttr:'+attr for attr in attributes]
            # then fill the selectors
            for selector in selectors:           
                if names0 and len(names0)>0:
                    selector.addItems(names0)
                    selector.insertSeparator(selector.count())
                if hasChildren:
                    if len(names1)>0:                   
                        selector.addItems(names1)
                        selector.insertSeparator(selector.count())
                    if len(attributes)>0:
                        selector.addItems(attributes)
            # Preselect variables
            names=self.preselectVariables(cube=cube,names=names,previousNames=currentNames)
            if  names and all([bool(name) for name in names]):     # select the requested x and y names if correct
                indices=map(lambda selector,name:selector.findText(name),selectors,names)
                if all(index!=-1 for index in indices):
                    map(lambda selector,index:selector.setCurrentIndex(index),selectors,indices)
        if selectors[0].count()>=3: self.addButton.setEnabled(True)
        else: self.addButton.setEnabled(False)

    def preselectVariables(self,cube=None,names=[None,None,None],previousNames=[None,None,None]):   # subclass in Plot2DWidget and Plot3DWidget
        """
        preselect x, y and z variables in the selectors before plotting a datacube.
        """
        if cube==None : cube=self._cube           # if no datacube passed use the current datacube
        if cube==None :  return [None,None]                   # if no datacube give up
        # gets all possible variables
        names0=cube.names()                       # otherwise gets its column names
        names0.insert(0,'[row]')                  # add the row number choice
        allNames=names0                    
        children=cube.children()                  # Get its children
        hasChildren=len(children)>0               
        if hasChildren:                           # if the cube has children
            names1=cube.commonNames()[1]          # gets all column names common to all direct children
            names1.insert(0,'[row]')
            names1=['child:'+ name for name in names1]
            allNames.extend(names1)
            attribs=cube.attributesOfChildren(common=True)     # gets all attribute names common to all direct children
            attributes=['childAttr:'+attr for attr in attribs]
            allNames.extend(names1)
        # Then defines how to preselect
        if all([(name and name in allNames) for name in names]): # if all passed names exist select them
            return names
        elif all([(bool(name) and name in allNames) for name in previousNames]): # if all passed names exist select them
            return previousNames
        elif (not hasChildren or (hasChildren and len(names1)<=1)): # if no children or children with less than 2 variables (including row)
            if len(names0)<3: return [None,None,None]   # and less than 3 columns => no preselection and return
            elif len(names0)==3:                  # and 3 columns including row numbers => preselect them
                names=names0                      # insert code here for proper preselection
            else:                                 # 3 columns or more after row numbers  => preselect them
                names = names[1:4]                # insert code here for proper preselection
        else:                                     # children and more than 2 children variables (including row)
            if len(names0)>=2 and len(cube.column(cube.columnName(0)))==len(children): # if at least one column after row in parent
                names[0]=names0[1]                # x is the first column after row of the parent cube
            else:
                attributes2=list(attributes)      # 
                attributes2.remove('childAttr:row')
                if len(attributes2)!=0:
                    names[0]=attributes2[0]
                else:
                    names[0]='childAttr:row'      # x is the row attribute column
            if len(names1)>=3:
                names[1:3]=names1[1:3]            # yz are is the children first two columns
            else:
                names[1:3]=names1[0:2]            
        return names

    def setStyle(self,style):                               # subclass in Plot2DWidget and Plot3DWidget
        return

    def setColorModel(self,**kwargs):                       # subclass in Plot3DWidget only
        return
 
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
        debugDM2GUI('attaching ',self._manager,' to ',self)
        self._manager.attach(self)
        self.setHeaderLabels(["Name"])
        for cube in self._manager.datacubes():
          self.addDatacube(cube,None)
        self.itemDoubleClicked.connect(self.renameCube)
   
    def renameCube(self):
        if self._parent!=None: self._parent.renameCube()

    def ref(self,cube):
        #debugDM2GUI("in DataTreeView.ref(cube) with cube =",cube,' ref(cube) =',weakref.ref(cube))
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
        debugDM2GUI("in DataTreeView.selectCube(datacube) with datacube =",cube)
        if self.ref(cube) in self._items:
          item = self._items[self.ref(cube)]
          self.setCurrentItem(item)

    def addCube(self,cube,parent):
        debugDM2GUI("in DataTreeView.addCube(cube) with cube =",cube, "and cube's parent =",parent)
        if self.ref(cube) in self._items:     # does not add a cube reference already present
          return
        item = QTreeWidgetItem()
        item.setText(0,str(cube.name()))
        item._cube = self.ref(cube)
        debugDM2GUI('attaching ',cube,' to ',self)
        cube.attach(self)
        self._items[self.ref(cube)]= item
        if parent == None:
          self.insertTopLevelItem(0,item)
        else:
          self._items[self.ref(parent)].addChild(item)
        for child in cube.children():
          self.addCube(child,cube)
      
    def removeItem(self,item):
        debugDM2GUI("in DataTreeView.removeItem(item) with item =",item)
        if item.parent() == None:
          self.takeTopLevelItem(self.indexOfTopLevelItem(item))
        else:
          item.parent().removeChild(item)  
  
    def removeCube(self,cube,parent):
        debugDM2GUI("in DataTreeView.removecube(datacube) with datacube =",cube)
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
        debugDM2GUI("in DataTreeView.updatecube(cube) with cube =",cube)
        item = self._items[self.ref(cube)]
        item.setText(0,cube.name())          
      
    def initTreeView(self):
        debugDM2GUI("in DataTreeView.initTreeView()")
        self.clear()
        dataManager = dm.DataManager()
        for cube in dataManager.datacubes():
          self.addCube(cube,None)
    
    def updatedGui(self,subject,property = None,value = None):
        debugDM2GUI("in DataTreeView.updatedGui with subject=",subject," property=", property,' and value =',value)
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
          debugDM2GUI("not managed")

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
        debugDM2GUI("in DatacubeProperties.setCube(cube) with cube = ",cube)
        if self._cube != None:
          debugDM2GUI('detaching ',self._cube,' from ',self )
          self._cube.detach(self)
        self._cube = cube
        if not self._cube == None:
          debugDM2GUI('attaching',self._cube,'to',self)
          self._cube.attach(self)
        self.updateProperties()
    
    def updateProperties(self):
        debugDM2GUI("in DatacubeProperties.updateProperties()")
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
                self.parameters.setItem(0,i,QTableWidgetItem(str(key)))
                self.parameters.setItem(1,i,QTableWidgetItem(str(params[key])))
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
        debugDM2GUI("in DatacubeProperties.updatedGui with property ",property,' and value=',value)
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
        debugDM2GUI("in dataManagerGUI frontpanel creator")
        QMainWindow.__init__(self,parent)
        ObserverWidget.__init__(self)

        self.manager = dm.DataManager()
        debugDM2GUI('attaching',self.manager,'to',self)
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
        debugDM2GUI('in DataManagerGUI.selectCube with current cube =',current,' and last cube=',last)
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
        debugDM2GUI('in DataManagerGUI.updatedGui with subject=', subject,', property =',property,', and value=',value)
        if subject == self.manager and property == "plot":
          cube=value[0][0]
          kwargs=value[1]
          if isinstance(self.tabs.currentWidget,Plot2DWidget):
            self.tabs.currentWidget.addPlot2(**kwargs)
        else :debugDM2GUI("not managed")
        
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
        debugDM2GUI("in DataManagerGUI.loadCube()")
        filename = QFileDialog.getOpenFileName(filter = "Datacubes (*.par)",directory = self.workingDirectory())
        if not filename == '':
          self.setWorkingDirectory(filename)
          cube = Datacube()
          cube.loadtxt(str(filename))
          self.manager.addDatacube(cube)
          self._cube=cube                     # Make the manually loaded datacube the current cube. It will be automatically selected also in the dataTreeview
    
    def newCube(self):
        debugDM2GUI("in DataManagerGUI.newCube()")
        manager = dm.DataManager()
        cube = Datacube()
        cube.set(a =0,b = 0,commit=False)
        manager.addDatacube(cube)
        self._cube=cube                     # Make the manually created datacube the current cube. It will be automatically selected also in the dataTreeview

    def renameCube(self):
        debugDM2GUI("in DataManagerGUI.renameCube()")
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
        debugDM2GUI("in DataManagerGUI.removeCube()")
        if self._cube != None:
            manager = dm.DataManager()
            manager.removeDatacube(self._cube,deleteCube=deleteCube)
            #self._cube = None

    def saveCubeAs(self):
        self.saveCube(saveAs = True)
        
    def addChild(self,new=False):
        debugDM2GUI("in DataManagerGUI.addChild()")
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
        debugDM2GUI("in DataManagerGUI.saveAs()")
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
    debugDM2GUI("in startDataManager")
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