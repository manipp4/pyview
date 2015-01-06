#*******************************************************************************
# 2D and 3D Plotter                                                            *
#*******************************************************************************

___debugP2___ = False
def debugP2(*args):
  if ___debugP2___:
    for arg in args: print arg,
    print

def flatten(li):
    result = []
    for el in li:
        if hasattr(el, "__iter__"):
            result.extend(flatten(el))
        else:
            result.append(el)
    return result

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
import numpy


from pyview.gui.mpl.canvas import *
reload(sys.modules['pyview.gui.mpl.canvas'])
from pyview.gui.mpl.canvas import *

from matplotlib import colors,cm
from mpl_toolkits.mplot3d import Axes3D


import pyview.helpers.datamanager2 as dm            # DATAMANAGER2
from pyview.lib.datacube2 import *                  # DATACUBE2
#from pyview.lib.classes import *
#from pyview.lib.patterns import *
from pyview.gui.patterns import ObserverWidget
from pyview.gui.graphicalCommands import *

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
        debugP2("deleting ",self)

    def __init__(self, parent=None, name=None,threeD=False):  # creator PlotWidget
        debugP2("in PlotWidget.__init__(parent,name,threeD) with parent=",parent," name=",name," and threeD=",threeD)
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
        debugP2('attaching ',self._manager,' to ',self)
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
        debugP2(self.name,'.onTimer() calling updatePlot()') 
        self._updated = True
        self.updatePlot(draw=True)

    def updatedGui(self,**kwargs):                           # subclass in Plot2DWidget and Plot3DWidget
        return

    def addPlot(self):                                       # subclass in Plot2DWidget and Plot3DWidget
        return

    def removeFromCanvas(self,plot):
        debugP2('in removeFromCanvas with plot =',plot )
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
                fig.axes[0].set_position(fig.axes[0].initialPosition)              # restore initial size here

    def clearPlots(self): # simplify here by calling removeplot
        """
        Clears all the plots from the graph and from self._plotList.
        """
        debugP2("in PlotWidget.clearPlots()")
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
        debugP2('in PlotWidget ',self.name,'.updatePlot() with draw = ',draw)
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
        debugP2('in PlotWidget.setCube(cube,names) with cube =',cube,' names=',names)  
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
          debugP2('detaching ',self._cube,' from ',self)
          self._cube.detach(self)
        self._cube = cube                                    # defines the new cube as current cube
        if self._cube!=None:
          debugP2("attaching",self._cube,'to',self)
          self._cube.attach(self)                            # and observes the cube in case it changes names or gets new data
        if not self._threeD:
            kwargs={'level':0,'names':names[0:2]}            # update the 2D variable selectors
        else:
            kwargs={'names':names}                           # or the 3D variable selectors
        self.updateControls(**kwargs)
        if self.autoplot.isChecked():  self.addPlot()       # and plot if autoplot     

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
        debugP2("in PlotWidget.removePlot() with plot = ",plot," and update = ",update)
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
        debugP2("in PlotWidget.removeLine with update =",update)
        self._currentIndex = self.plotList.indexOfTopLevelItem(self.plotList.currentItem())
        plot=self._plots[self._currentIndex]
        self.plotList.takeTopLevelItem(self._currentIndex) # remove the item from plotList
        self.removePlot(plot,update=update)

    def lineSelectionChanged(self,selected,previous):
        if selected != None:
          index = self.plotList.indexOfTopLevelItem(selected)
          self._currentIndex = index

    def autoplotChanged(self,CheckState):
        debugP2("in PlotWidget.autoplotChanged()")
        if CheckState:
          self.updatedGui(subject=self._cube,property = "names",value = None)

    def levelChanged(self):                                  # subclass in Plot2DWidget only
        return

    def namesChanged(self):
        #debugP2("in PlotWidget.namesChanged()")               # not used yet
        #self.updatedGui(subject=self,property = "redraw",value = None)
        return
    
    def showLegendStateChanged(self,state):
        debugP2("in PlotWidget.showLegendStateChanged()")
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
        debugP2('in ',self.name,'.updatedGui with subject=', subject,', property=',property,', and value=',value)
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
            debugP2("not managed")

    def addPlot(self,cube=None,level=None,names=[None,None],clear='auto',style=None,**kwargs):
        """
        Adds plots of a datacube at level level by calling addPlot2 for all children of that level or for the cube itself if level==0.
        """
        debugP2('in ',self.name,'.addPlot with cube=',cube,',level=',level,', names=',names,', clear=',clear,', style=',style,', and current cube = ',self._cube)          
        if level==None: level=self.level.value()
        if cube==None : cube =self._cube              # if no datacube passed use the current datacube
        if cube==None:  return                        # give-up if no datacube
        if len(cube.names())==0:                      # if datacube has no column,...
            if self.autoplot.isChecked():
                debugP2('attaching ',cube,' to ',self)  # attach it  if autoplot... 
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
        debugP2('in ',self.name,'.addPlot2 with cube=',cube,', names=',names,', clear=',clear,', style= ', style, ' and current cube = ', self._cube)
        if cube==None : cube =self._cube              # if no datacube passed use the current datacube
        if cube==None:  return                        # give-up if no datacube
        if len(cube.names())==0:                      # give up if datacube has no column, but attach it if autoplot
          if self.autoplot.isChecked():
            debugP2('attaching ',cube,' to ',self)
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
        debugP2('attaching ',plot.cube,' to ',self)
        plot.cube.attach(self)
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
        debugP2('in ',self.name,'.updatePlotData() with plot=',plot,' and draw =',draw)
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
        debugP2("in Plot2DWidget.updateControls(level,names) with level=",level,", names=",names,', and current datacube=',self._cube)
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
        Preselects x and y variables before plotting a datacube.
        """
        debugP2('in Plot2DWidget.preselectVariables(cube,level,names,previousNames) with cube = ',cube,' level = ',level,', names = ',names,', and previousNames = ',previousNames)
        if cube==None : cube=self._cube           # if no datacube passed use the current datacube
        if cube==None :  return [None,None]       # if no datacube give up
        if level==None :level=0                   # prepare a plot at level 0 if no level speciifed
        commonNames=cube.commonNames()            # gets all column names of the datacube and its children that are common to a same level
        levelMax=len(commonNames)-1
        if level>levelMax :level=levelMax
        commonNames=commonNames[level]                              
        if len(commonNames)!=0: commonNames.insert(0,'[row]')
        # select first the passed names if valid for both x and y
        if any([not bool(name) for name in names]) or any([not (name in commonNames) for name in names]): # else
          cubes=cube.cubesAtLevel(level=level,allBranchesOnly=True)
          for cubei in cubes:
            if cubei.parameters().has_key("defaultPlot"):   # select the first valid default plot if defined in one of the datacubes    
              for defaultPlot in cube.parameters()['defaultPlot']:
                if len(defaultPlot) >=2 :names=defaultPlot[:2]
                if all([name in commonNames for name in names]):
                  return names
          selectors=[self.xNames,self.yNames]           # else select names of previous plot if possible (except if one of the names is row)
          if all([bool(name) and name != '[row]' and name in commonNames for name in previousNames]): 
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
        debugP2("in Plot2DWidget.setStyle() with index=",index,"and style=",style)
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
        debugP2("in Plot2DWidget.setColor() with index=",index,"and color=",color)
        if index==None :                                                 # if index is not passed choose the current index in plotList
          index=self.plotList.indexOfTopLevelItem(self.plotList.currentItem())
        if self._currentIndex == -1:                                
          return                                                         # return if not valid index
        self._currentIndex = index                                       # set the current index of the Plot2DWidget to index
        if not color:                                                    # if style is not passed choose the current default style
          color = self.colors.itemData(index).toString() 
        if self._plots[self._currentIndex].MPLplot.get_color() == color: # if style is already correct do nothing and return
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
        debugP2("in Plot2DWidget.showLegendStateChanged()")
        self.updatedGui(subject=self._cube,property = "names",value = None)
    

class Plot3DWidget(PlotWidget):
    
    def __init__(self, parent=None, name=None): # creator Plot3DWidget
        PlotWidget.__init__(self,parent=parent,name=name,threeD=True)

    def updatedGui(self,subject = None,property = None,value = None):     # notification listener of Plot3DWidget
        # Difficult programing especially for autoplotting of a datacube with not enough information.
        """
        Manage all possible GUI updates depending on
            - received messages from attached objects (datacubes and datamanager)
            - the status of the plotter and the attached cubes
        This method is supposed to allow autoplot of new datacubes as soon as they are ready for that (when the have enough children and/or data)
        """
        debugP2('in ',self.name,'.updatedGui with subject=', subject,', property=',property,', and value=',value)
        if subject==self._manager and property=="addDatacube" :           # 1) A new datacube arrived in the datamanager.
            if self.autoplot.isChecked():                                 #     if autoplot
                self.addPlot(cube=value)                                  #         addPlot it (attach the cube to the plotter and plot it if possible)
        elif isinstance(subject,Datacube) and property =="names":         # 2) New names of an attached datacube arrived
            cube=subject                                                  #     cube is the subject
            if  self._cube!=None and (cube == self._cube or cube in self._cube.children()):       #     if cube = current datacube or is child of current datacube
                self.updateControls()                                     #         => update controls
            if self.autoplot.isChecked() :                                #     if autoplot
                parent =cube.parent()                                     #         test if the cube is the child of an attached datacube not already plotted 
                test=parent!=None and self in parent.observers() and parent not in [plot.cube for plot in self._plots]  #         if yes                                                                                 
                if test:
                    self.addPlot(cube=parent)                             #             addPlot the cube's parent cube in case it is now ready for plot creation
                else:                                                     #         if no
                    self.addPlot(cube=cube)                               #             addPlot the cube itself in case it is ready for plot creation
        elif isinstance(subject,Datacube) and property =="addChild":      # 3) a datacube attached to this plotter has a new child
            cube,child = subject,value                                    #     the datacube and the child are the notified property and value, respectively
            if  cube == self._cube:   self.updateControls()               #     if current datacube => update controls
            plot,needChild=None,False                                     #     if cube is plotted ...
            for ploti in self._plots:
                if ploti.cube==cube:
                    plot=ploti
                    break
            if plot:
                names=plot.xname,plot.yname,plot.zname                    #     ... with children variables
                needChild= any(['child:' in name for name in names])
                if needChild:                                             #     
                    debugP2('attaching ',child,' to ',self)               #     => attach child to plot3DWidget
                    child.attach(self)
                    self._updated = False                                 #         and request an update
            elif self.autoplot.isChecked() : self.addPlot(cube=cube)      #     if autoplot and not already plotted => try addPlot
        elif subject==self._manager and property=="addChild" :            # 4) a datacube of the datamanger not attached to this plotter (otherwise would be case 3) has new child
            None                                                          #     do nothing
        elif isinstance(subject,Datacube) and property =="commit":        # 5) New points arrived in an attached datacube or attached child:
            cube=subject;                                                 #     If attached only as current cube for name update do nothing
            for plot in self._plots:                                      #     
                if cube == plot.cube or cube in plot.cube.children():     #     Otherwise update plot
                    self._updated = False
                    break
        else:                                                             # note that addPlot sets self._updated to False after completion
            debugP2("not managed")

    def addPlot(self,cube=None,names=[None,None,None],clear='auto',style=None,color=None,**kwargs): # subclass in Plot2DWidget and Plot3DWidget
        """
        Adds a plot of a datacube in self._plots with specified variables. In case cube=None, use the current datacube.
        Add the corresponding row in the table below the graph.
        Then calls self.updatePlot() for redrawing.
        Note 1: In case datacube has no valid columns, no plot is added but the datacube is attached to plotter for future update.
        Note 2: datacube is attached to the plotter for future notifications, as well as its children 
                                                                                if they are used in the 3D plot,
                                                                                or if autoplot for future notification
        """
        debugP2('in ',self.name,'.addPlot with cube=',cube,', names=',names,', clear=',clear,', style= ', style, ' and current cube = ', self._cube)
        if cube==None : cube =self._cube              # if no datacube passed use the current datacube
        if cube==None:  return                        # give-up if no datacube
        if (self.autoclear.isChecked() and clear=='auto') or clear==True:       # clear if autoclear
          self.clearPlots() 
        names=self.preselectVariables(cube=cube,names=names) # Build valid x and y names
        for plot in self._plots:                      # If the plot is already present in the list of plots...
            if cube == plot.cube :
                if [plot.xname,plot.yname,plot.zname] == names:
                    self._updated = False
                    return                            # ... request update only and stops.
        ready= all([ bool(name) for name in names]) and names[0]!=names[1] and names[0]!= names[2] and names[1]!=names[2]
        if not ready:                                 # if datacube is not ready, dont plot it but 
          if self.autoplot.isChecked():               # if autoplot
            debugP2('attaching ',cube,' to ',self)
            cube.attach(self)                         # attach it   
            for child in cube.children():               
                debugP2('attaching ',child,' to ',self)
                child.attach(self)
            return                                    # so that it has a chance to be autoplotted at the next notifications from the cube or its children
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
        debugP2('attaching ',plot.cube,' to ',self)         # attach cube to plot3DWidget...
        plot.cube.attach(self)
        needChildren=any([('child:' in name) for name in names ])
        if needChildren:
            for child in cube.children():                                      
                debugP2('attaching ',child,' to ',self)     # ... and its relevant children for the plot 
                child.attach(self)
        plotItem = QTreeWidgetItem([cube.name(),xname,yname,zname,style,color]) # Add the plot as a plotitem in the view plotList below the graph window 
        plot.item=plotItem
        self.plotList.addTopLevelItem(plotItem)
        self.plotList.update()                              # update the view plotList of self._plot
        self._plots.append(plot)                            # and add the plot to the list self._plots
        self._updated = False                               # let ontimer() call all functions updating the graph with points, create all labels, and redraw)

    def updatePlotData(self,draw=False,plot=None,regularize=None,**kwargs):
        """
        Creates a new empty plot or update an existing one.
        """
        debugP2('in ',self.name,'.updatePlotData() with plot=',plot)
        if plot==None:
            if self._currentIndex:
                plot=self._plots[self._currentIndex]
            else: return
        fig=self.canvas._fig
        ax=self.canvas.axes
        cmap=cm.get_cmap(plot.color)
        if plot.MPLplot==None:                                                   # this is where any new 3D plot is created (as an empty plot)
            debugP2('create empty plot ',plot)
            if plot.style=="Waterfall":
                plot.MPLplot= ax.plot([0],[0],0,'x')
            elif plot.style=="Image (reg)":
                plot.data={'x':array([0.]),'y':array([0.]),'z':array([[0.]]),'mask':True}             # note that z is always of type a array
                # catch warning here to avoid seeing the error caused by an imshow with all data masked.
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", message="Warning: converting a masked element to nan.")
                    im= ax.imshow(ma.array(plot.data['z'],mask=plot.data['mask']),interpolation='nearest',cmap=cmap,origin='lower',**kwargs) # create 2D image
                    if len(fig.get_axes())==1:
                        ax0=fig.get_axes()[0]
                        if not hasattr(ax0, 'initialPosition'):
                            ax0.initialPosition = ax0.get_position() 
                        cb=fig.colorbar(im,ax=ax0)                  # and its colorbar
                        if hasattr(ax0, 'colorbarPosition'):
                            cb.ax.set_position(ax0.colorbarPosition)
                            ax0.set_position(ax0.position)
                        else:
                            ax0.colorbarPosition=cb.ax.get_position()
                            ax0.position=ax0.get_position()
                        cb.set_label(plot.zname, rotation=90)
                        
                plot.MPLplot=im
            elif plot.style=="Image (rnd)": 
                plot.MPLplot= ax.imshow([[0]],interpolation="nearest",cmap=cmap,**kwargs)
            elif plot.style=="Contours":
                plot.data={'x':array([0.]),'y':array([0.]),'z':array([[0.]]),'mask':True}             # note that z is always of type a array
                plot.MPLplot= ax.contour(ma.array(plot.data['z'],mask=plot.data['mask']),cmap=cmap,**kwargs)
            elif plot.style=="Scatter":
                plot.MPLplot= ax.scatter([0],[0],[0],cmap=cmap,**kwargs)
            elif plot.style=="Surface":
                plot.MPLplot= ax.plot_surface([[0]],[[0]],[[0]],cmap=cmap,**kwargs)
            elif plot.style=="Tri-surface":
                plot.MPLplot= ax.plot_trisurf([0],[0],[0],cmap=cmap,**kwargs)
        else:                                                                     # this is where an existing 3D plot is updated
            debugP2('update existing plot ',plot)
            if plot.style=="Waterfall":
                print 'Waterfall not implemented yet'
            elif plot.style=="Image (reg)" or plot.style=="Contours":
                dat=plot.data
                pl=plot.MPLplot
                self.data2Plot(plot,regularize=regularize)
                if dat['regular']:
                    dims=dat['xyzDims']
                    # Remember that if z is bidimentionel, its first dimension corresponds either to x if x is 1d and y is 2d or to y if x is 2d and y is 1d
                    if dims[0]==1:                                               
                        dat['z']=dat['z'].T
                        dat['mask']=dat['mask'].T
                    pl.set_array(ma.array(dat['z'],mask=dat['mask']))             # this is where the maskedArray is rebuilt
                    xMin,xMax,yMin,yMax,dx,dy=dat['xMin'],dat['xMax'],dat['yMin'],dat['yMax'],dat['dx'],dat['dy']
                    if not isinstance(dx,(int,float)): dx=1.
                    if not isinstance(dy,(int,float)): dy=1.
                    limits=[xMin-dx/2.,xMax+dx/2.,yMin-dy/2.,yMax+dy/2.]
                    pl.set_extent(limits)
                    pl.autoscale()
            elif plot.style=="Image (rnd)":
                print 'Image (rnd) not implemented yet'
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
        - xMin,xMax,yMin,yMax, and dx,dy if regular is True
        """
        debugP2('in ',self.name,'.data2Plot() with plot=',plot," and regularize =",regularize )
        names=xname,yname,zname=plot.xname,plot.yname,plot.zname
        cube=plot.cube
        rowxyz=[]                                                                           # rowxyz is the [x,y,z] structure containing the row data
        dims=[]
        dat=plot.data                                                                             # dim stores the corresponding dimensions [dim[x],dim[y],dim[z]]
        for i in range(3):
            name=names[i]
            if name.startswith('childAttr:'):                                               # If the variable is a child attribute
                shortName=name[len('childAttr:'):]
                var=array([cube.attributesOfChild(childCube)[shortName] for childCube in cube.children()]) #   var is the 1D array of attribute values of all children
                dim=1                                                                       #   save the variable dimension as 1
            elif name.startswith('child:'):                                                 # If the variable is a children's column
                shortName=name[len('child:'):] 
                if shortName=='[row]':
                    var=array([arange(0,len(childCube),1) for childCube in cube.children()])
                else:                                                         
                    var=array([childCube.column(shortName) for childCube in cube.children()])      #   var is the '2D array' (or 1 d array of 1d array) of these children's column    
                dim=2                                                                       #   save the variable dimension as 2
            else:
                if name=='[row]':                                                           # If the variable is one of the column of the parent cube
                    var=arange(0,len(cube),1)
                else:
                    var=cube.column(name)                                                   #   set var to it
                dim=1                                                                       #   save the variable dimension as 1
            rowxyz.append(var)                                                              # Save a first version of the data non necessarily regular,
            dims.append(dim)                                                                #   as well as the corresponding dimensions.
            # NOTE 1: 'bidimentional arrays' in rowxyz can be 1d arrays of 1d arrays instead of numpy 2d arrays if the array is not full
            # NOTE 2: if z is bidimentionel, its first dimension corresponds either to x if x is 1d and y is 2d or to y if x is 2d and y is 1d
        dat['xyzDims']= dims                                                   
        dat['x'], dat['y'],dat['z']=rowxyz
        if plot.style in ["Image (reg)","Image (rnd)","Contours","Surface"]:                # In case the type of matplotlib plot requires regular data
            # The goal is now to build a valid rectangular and regular 2d array dat['z'] and its mask dat[mask'] for building later a masked array
            self.checkRectRegAndComplete(plot)                                                             # checks regularity and stores 'missing','dx','dy','xMin','xMax','yMin','yMax' in the plot.data dictionary.                                                                                                                                                          # fill the mask with False at the unvalid data locations 
            if (not dat['rectangular'] or not dat['regular']) and regularize:                             # if not regular and regularize requested
                self.regularize(plot)                                                       #   try to regularize and overwrite plot.data
              
    def checkRectRegAndComplete(self,plot):
        """
        1) Checks if the data are on
            - a RECTANGULAR XY grid (same y's for all x except missing x in the last row or missing y in the last column),
            - a FULL grid  (i.e. with no data missing) or with missing X in the last row or missing Y in the last column,
            - a REGULAR grid (constant spacing in x, constant in y).
        2) Stores in the plot.data dictionary:
            - 3 booleans 'rectangular','regular',and 'full',
            - 8 numbers (or None if irrelevant) 'missingXOnLastRow','missingYOnLastColumn','dx','dy','xMin','xMax','yMin','yMax'.
            - A new mask of boolean values rectangular and full or rectangular and completed (see below)
        IMPORTANT:  If the grid is rectangular but not full, it is made artificially full by completing it with the last value,
                    and the mask plot.data['mask'] is set accordingly to indicate invalid added data.
        """
        dat=plot.data
        rectangular,regular,full=[False]*3
        missingXOnLastRow,missingYOnLastColumn,dx,dy=[None]*4
        xList,yList=map(lambda varName: list(set(flatten(dat[varName]))),['x','y'])
        xMin,xMax,yMin,yMax=min(xList),max(xList),min(yList),max(yList)
        dims=dat['xyzDims']
        if all([dim==1 for dim in dims]):                # simple columx, column y and column z
            None# sort in x, y, z, and check increments are constant for each => regular => a masked array can be formed
        elif dims[0]+dims[1]==3 and dims[2]==2: # (1d x and 2d y) or (2d x and 1d y) and 2d z values 
            var1d,var2d=dat['x'],dat['y']
            if dims[0]==2:  var1d,var2d=dat['y'],dat['x']
            # First check that the 1d and 2d XY structures match the 2d Z structure
            XYMatchZ=len(var1d)>= len(var2d) and len(var2d)==len(dat['z']) and all([len(var2d[i])==len(dat['z'][i]) for i in range(len(var2d))])
            # Second check for the  XY structure itself           
            if XYMatchZ:
                rectangular = len(var2d) in [len(var1d),len(var1d)-1]
                rectangular = rectangular and all([var==var2d[0] for var in var2d[1:-1]]) and all(var2d[-1]==var2d[0][:len(var2d[-1])])           
                if rectangular:
                    missingX,missingY=0,0
                    maxLe,le=len(var2d[0]),len(var2d[-1])
                    missing=maxLe-le
                    full=missing==0
                    if not full:
                        if dims[0]==2 :
                            missingXOnLastRow=missing
                        else:
                            missingYOnLastColumn=missing
                    if len(var2d[0])==0:    regular2D=False
                    elif len(var2d[0])==1:  regular2D=True
                    else:
                        dys= map (lambda a,b: a-b,var2d[0][1:],var2d[0][:-1])
                        regular2D=all([dyi==dys[0] for dyi in dys])
                        if regular2D:   dy=dys[0]
                    if len(var1d)==0:       regular1D=False
                    elif len(var1d)==1:     regular1D=True
                    else:
                        dxs= map (lambda a,b: a-b,var1d[1:],var1d[:-1])
                        regular1D=all([abs(dxi/dxs[0]-1)<1e-6 for dxi in dxs])
                        if regular1D:   dx=dxs[0]
                    regular=regular2D and regular1D
                    if dims[0]==2:  dx,dy=dy,dx
                    if not full:                          # although missing will be saved in plot.data['missing'],  
                        var2d[-1]=var2d[0]                # the missing x or y values are added 
                        last=array([0]*maxLe)
                        last[:le]=plot.data['z'][-1]
                        last[le:]=plot.data['z'][-1][-1]  # as well as the missing z values set to the last z (will be masked later)
                        plot.data['z'][-1]=last
                        plot.data['z']=array(list(plot.data['z'])) # conversion to a 2d array instead of a 1d array of 1d arrays
                    mask=ma.make_mask_none(dat['z'].shape)
                    if not full:    mask[-1,le:]=True
                    dat['mask'] = mask
        if plot.cube==self._cube:
            self.regularGrid.setChecked(rectangular)
        dat['rectangular'],dat['regular'],dat['full']=rectangular,regular,full
        dat['missingXOnLastRow'],dat['missingYOnLastColumn']=missingXOnLastRow,missingYOnLastColumn
        dat['dx'],dat['dy'],dat['xMin'],dat['xMax'],dat['yMin'],dat['yMax']=dx,dy,xMin,xMax,yMin,yMax 

    def regularize(self,rowxyz):
        return

    def updateControls(self,names=[None,None,None]):        # subclass in Plot2DWidget and Plot3DWidget
        """
        Updates the x, y and z variable names in the x, y, and z selectors. Then makes a pre-selection by calling preselectVariables().
        """
        debugP2('in Plot3DWidget.updateControls(names) with names=',names,', and current datacube=',self._cube)
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
                names1=cube.commonNames()                  # gets all column names common to all direct children
                if len(names1)>=2:
                    names1=names1[1]
                else:
                    names1=[]
            # Then create the lists of choices to add the [row] choices and let the user know if a choice correspond to a parent name,or child name or attribute 
                names1.insert(0,'[row]')
                names1=['child:'+ name for name in names1]
                attributes=cube.attributesOfChildren(common=True)     # gets all attribute names common to all direct children
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
                #print 'names=',names,
                indices=map(lambda selector,name:selector.findText(name),selectors,names)
                #print 'indices=',indices
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
        if len(names0)!=0 : names0.insert(0,'[row]')    # add the row number choice     
        allNames=names0                    
        children=cube.children()                  # Get its children
        hasChildren=len(children)>0               
        if hasChildren:                           # if the cube has children
            names1=[]
            if len(cube.commonNames())>=2:  names1=cube.commonNames()[1]   # gets all column names common to all direct children
            if len(names1)!=0 : names1.insert(0,'[row]')
            names1=['child:'+ name for name in names1]
            allNames.extend(names1)
            attribs=cube.attributesOfChildren(common=True)     # gets all attribute names common to all direct children
            attributes=['childAttr:'+attr for attr in attribs]
            allNames.extend(names1)
        # Then defines how to preselect
        if all([(name and name in allNames) for name in names]): # if all passed names exist select them
            return names
        elif all([(bool(name) and name !='[row]' and name in allNames) for name in previousNames]): # if all previous names exist and are different from 'row'select them
            return previousNames
        elif (not hasChildren or (hasChildren and len(names1)<=1)): # if no children or children with less than 2 variables (including row)
            if len(names0)<3: return [None,None,None]   # and less than 3 columns => no preselection and return
            elif len(names0)==3:                  # and 3 columns including row numbers => preselect them
                names=names0                      # insert code here for proper preselection
            else:                                 # 3 columns or more after row numbers  => preselect them
                names = names0[1:4]               # 
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

    def setStyle(self,style):                          # subclass in Plot2DWidget and Plot3DWidget
        return

    def setColor(self,index=None,color=None):          # subclass in Plot3DWidget
        debugP2("in Plot3DWidget.setColor() with index=",index,"and color=",color)
        if index==None :                                                # if index is not passed choose the current index in plotList
          index=self.plotList.indexOfTopLevelItem(self.plotList.currentItem())
        if self._currentIndex == -1:                                
          return                                                        # return if not valid index
        self._currentIndex = index                                      # set the current index of the Plot2DWidget to index
        if not color:                                                   # if style is not passed choose the current default style
          color = self.colors.itemData(index).toString() 
        if self._plots[self._currentIndex].MPLplot.get_cmap() ==cm.get_cmap(color): # if style is already correct do nothing and return
          return
        self._plots[self._currentIndex].MPLplot.set_cmap(color)         # set the color in the plot
        item=self._plots[self._currentIndex].item
        item.setText(5,color) 
        self._updated = False
        return
