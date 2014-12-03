
from PyQt4.QtGui import * 
from PyQt4.QtCore import *
from PyQt4.uic import *
import sys
import os
import os.path
import tempfile

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt4agg import FigureManagerQTAgg
from matplotlib.figure import Figure
from pyview.gui.editor.codeeditor import CodeEditor
from math import fabs

class FigureManager(FigureManagerQTAgg):
  pass

class CanvasDialogTab(QWidget):

  def __init__(self,parent = None):
    QWidget.__init__(self,parent)
    self.layout = QGridLayout()
    self.setLayout(self.layout)
    self._options=dict()

  def addOption(self,name,enterType,defaultValue=None,row=None,column=None,rowSpan=None,colSpan=None):
    lay=self.layout
    row2,col2,rowSpan2,columnSpan2=0,0,0,0
    validRowAndColumn= isinstance(row,int) and isinstance(column,int)
    validSpans= isinstance(rowSpan,int) and isinstance(colSpan,int)
    if enterType in ["QLineEdit","QDoubleSpinBox"]:
      if enterType== "QLineEdit":
        option= QLineEdit()
        option.setText(str(defaultValue))
      elif enterType== "QDoubleSpinBox":
        option= QDoubleSpinBox()
        if defaultValue: option.setValue(defaultValue)
      label=QLabel(name+": ") 
      if validRowAndColumn:
        if validSpans:
          lay.addWidget(label,row,column,rowSpan,colSpan)
          lay.addWidget(option,row+1,column,rowSpan,colSpan)
        else:
          lay.addWidget(label,row,column)
          lay.addWidget(option,row+1,column)
      else:
        lay.addWidget(label)
        row2,col2=lay.getItemPosition(lay.indexOf(label))[:2]
        lay.addWidget(option,row2+1,col2)
    elif enterType=="QCheckBox":
      option = QCheckBox(name)
      if isinstance(defaultValue,bool): option.setChecked(defaultValue)
      if validRowAndColumn:
        if validSpans:
          lay.addWidget(option,row,column,rowSpan,colSpan)
        else:
          lay.addWidget(option,row,column)
      else:
        lay.addWidget(option)
    else: return None
    self._options[name]=option
    return option

class CanvasDialog(QDialog): #The canvas dialog does not redraw by itself
  
  def __init__(self,canvas,parent = None):
    try:
      reload(sys.modules["pyview.gui.mpl.canvas"])
      from pyview.gui.mpl.canvas import CanvasDialogTab
    except:
      raise Error("Unable to import CanvasDialogTab")
    QDialog.__init__(self,parent)
    self.setFixedWidth(250)
    layout = QGridLayout()
    self.setLayout(layout)
    self._canvas = canvas
    self.setWindowTitle(self._canvas.title()+" properties")
    self.tabs = QTabWidget()
    layout.addWidget(self.tabs,0,0)
    cancelButton = QPushButton("Cancel")
    applyButton = QPushButton("Apply")
    okButton = QPushButton("OK")
    buttonsLayout = QBoxLayout(QBoxLayout.RightToLeft)
    buttonsLayout.addWidget(okButton)
    buttonsLayout.addWidget(applyButton)
    buttonsLayout.addWidget(cancelButton)
    buttonsLayout.addStretch(0)
    layout.addLayout(buttonsLayout,1,0)

    st=self.scaleTab=CanvasDialogTab(self)
    cva=canvas.axes

    squared=st.addOption("Square XY","QCheckBox",defaultValue=not canvas.squared,row=0,column=0)
    centered=st.addOption("centered","QCheckBox",defaultValue=canvas.centered,row=0,column=1)
    squared.stateChanged.connect(lambda : centered.setEnabled(squared.isChecked()))
    squared.setChecked(canvas.squared)

    def enable(optionList,trueOrFalse):
      for option in optionList: option.setEnabled(trueOrFalse) 

    xMin=st.addOption("X Min","QLineEdit",defaultValue=cva.get_xlim()[0],row=1,column=0)
    xMax=st.addOption("X Max","QLineEdit",defaultValue=cva.get_xlim()[1],row=1,column=1)
    autoX=st.addOption("Auto X","QCheckBox",defaultValue=not canvas.autoX,row=2,column=2)
    autoX.stateChanged.connect(lambda : enable([xMin,xMax],not autoX.isChecked()))
    autoX.setChecked(canvas.autoX)

    yMin=st.addOption("Y Min","QLineEdit",defaultValue=cva.get_ylim()[0],row=3,column=0)
    yMax=st.addOption("Y Max","QLineEdit",defaultValue=cva.get_ylim()[1],row=3,column=1)
    autoY=st.addOption("Auto Y","QCheckBox",defaultValue=not canvas.autoY,row=4,column=2)
    autoY.stateChanged.connect(lambda : enable([yMin,yMax],not autoY.isChecked()))
    autoY.setChecked(canvas.autoY)

    inputBoxes=[xMin,xMax,yMin,yMax]

    if  canvas.threeD:      # find a way to retrieve Z extrema of the scale for any of the plot types
      minZ,maxZ = 0,1       # have something just in case we fail
      fig=canvas._fig
      if len(fig.axes)>0:   # if the figure contains axes
        axe=fig.axes[0]
        if len(axe.get_images())>0: # and the first axe contains images
          im4Z=axe.get_images()[0]  # select the first one as the one for defining the z limits
          minZ,maxZ= im4Z.get_clim()         # and get the info from from clim
      zMin=st.addOption("Z Min","QLineEdit",defaultValue=round(minZ,5),row=5,column=0)
      zMax=st.addOption("Z Max","QLineEdit",defaultValue=round(maxZ,5),row=5,column=1)
      autoZ=st.addOption("Auto Z","QCheckBox",defaultValue=not canvas.autoZ,row=6,column=2)
      autoZ.stateChanged.connect(lambda : enable([zMin,zMax],not autoZ.isChecked()))
      autoZ.setChecked(canvas.autoZ)
      inputBoxes.extend([zMin,zMax])

    objValidator = QDoubleValidator(self)
    for extr in inputBoxes:
      extr.setValidator(objValidator)  
    #xMin.setValidator(objValidator);xMax.setValidator(objValidator);yMin.setValidator(objValidator);yMax.setValidator(objValidator)
    #self.connect(xMin,SIGNAL("textEdited(QString)"),lambda : autoX.setChecked(False))
   
    self.tabs.addTab(self.scaleTab,"Scale")
    self.connect(cancelButton,SIGNAL("clicked()"),self.close)
    self.connect(applyButton,SIGNAL("clicked()"),self.apply)
    self.connect(okButton,SIGNAL("clicked()"),self.ok)

  def ok(self):
    self.apply()
    self.close()

  def apply(self):
    # memorize part of the settings in the canvas...
    cv=self._canvas
    fig=cv._fig
    cva=cv.axes
    sto=self.scaleTab._options
    cv.squared=sto["Square XY"].isChecked(); cv.centered=sto["centered"].isChecked()
    cv.autoX=sto["Auto X"].isChecked(); cv.autoY=sto["Auto Y"].isChecked()
    # ... and the absolute limits in the matpolib figure if necessary.
    if not cv.autoX: cva.set_xlim(float(sto["X Min"].text()),float(sto["X Max"].text()))
    if not cv.autoY: cva.set_ylim(float(sto["Y Min"].text()),float(sto["Y Max"].text()))
    if cv.threeD: #set the z scale of the graph here
      cv.autoZ=sto["Auto Z"].isChecked();
      if len(fig.axes)>0:       # if the figure contains axes
        if not cv.autoZ :     
          for axe in fig.axes:  # set the clim of all images (including colorbar) of all axes  
            for image in axe.get_images(): 
              image.set_clim(float(sto["Z Min"].text()),float(sto["Z Max"].text()))
        else:
          zMinList,zMaxList=[],[]
          for axe in fig.axes[:-1]:           # take the min max of all the clim of all images except the colorbar in the last axe  
            for image in axe.get_images(): 
              image.autoscale()
              zMin,zMax=image.get_clim()
              zMinList.append(zMin)
              zMaxList.append(zMax)
          if len(zMinList)*len(zMaxList)>0:
            zMin,zMax=min(zMinList),max(zMaxList) # take the min max of all the clim of all images except the colorbar in the last axe
            for axe in fig.axes:             
              for image in axe.get_images(): 
                image.set_clim(zMin,zMax)       
    # Don't modify xy autoscale or call draw here in this dialog. Call a redraw routine in the canvas itself
    cv.redraw()

class MyMplCanvas(FigureCanvas):
  
  """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""
  
  def __init__(self, parent=None, width=5, height=5, dpi=60,name=None, threeD=False):
    
    fig = Figure(figsize=[width, height], dpi=dpi)
    FigureCanvas.__init__(self, fig)
    self._fig = fig
    self._width,self._height,self._dpi = width,height,dpi 
    if name: self.name=name
    else: self.name='Figure'
    self.threeD=threeD
    self.setParent(parent) 
    
    self._dialog = None
    self._pressed = False

    # DV April 2014
    #In order to manage square plots such that xMax-xMin= yMax-yMin, we defines the following 4 variables
    # We don't use the matplotlib axes' properties to store the autorange configuration since they are incompatible with a square autorange
    # but the current x y limit are not stored here and are to be found in the axes.
    self.squared=False
    self.centered=True
    self.axesLines=[]
    self.autoX=True
    self.autoY=True
    if threeD:
      self.autoZ=True
    self.printer=QPrinter()
    #self.setFixedWidth(self._dpi*self._width)
    #self.setFixedHeight(self._dpi*self._height)

    self.createSubplot(threeDAxes=False)  # always start with a normal 2D projection axes object for image plot

    self._isDrawing = False

    self._moveLabel = QLabel("",self)
    self._moveLabel.setText("tes")
    self._moveLabel.hide()
    self._moveLabel.setStyleSheet("font-size:14px; margin:5px; padding:4px; background:#FFFFFF; border:2px solid #000;")
    # connect matplotlib events to functions
    self.mpl_connect('button_press_event', self.onPress)
    self.mpl_connect('button_release_event', self.onRelease)
    self.mpl_connect('motion_notify_event', self.onMove)
    self.mpl_connect('scroll_event', self.scroll)
    self.scrollable=[True,True]

    FigureCanvas.setSizePolicy(self,QSizePolicy.Expanding,QSizePolicy.Expanding)
    FigureCanvas.updateGeometry(self)

  def createSubplot(self,number=1,threeDAxes=False):
    fig=self._fig
    fig.clf() 
    if not threeDAxes:
      for i in range(number): self.axes = fig.add_subplot(111)
    else :
      for i in range(number): self.axes = fig.add_subplot(111, projection='3d')       
    self.axes.set_autoscale_on(True)
    self.axes.hold(True)

  def square(self,xMinxMaxyMinyMaxList, centered=False):
    if centered:
      li=map(abs,xMinxMaxyMinyMaxList)
      m=max(li)
      return[-m,m,-m,m]
    else:
      xMin,xMax,yMin,yMax=xMinxMaxyMinyMaxList
      x=xMax-xMin;y=yMax-yMin;d=y-x
      if d > 0:
        xMin-=d/2;xMax+=d/2
      else:
        yMin+=d/2;yMax-=d/2
    return [xMin,xMax,yMin,yMax]
  
  def redraw(self): # rescale and redraw according to the scaling parameters in the canvas and in the matplolib figure
    ax=self.axes
    # first recalculate the limit with autoscale on the proper axes if any;
    names=['x','y']
    controls=[self.autoX,self.autoY]
    tight=False
    ax.relim()                                                                        # recalculate the xy limits
    if self.threeD:
      names.append('z')
      controls.append(self.autoZ)
      tight=True
    map(lambda name,control: ax.autoscale(enable=control, axis=name, tight=tight),names,controls)

    # Then if squared XY space
    if self.squared:
      xMin,xMax=ax.get_xlim();yMin,yMax=ax.get_ylim()                                 # read the calculated limits
      xMin,xMax,yMin,yMax=self.square([xMin,xMax,yMin,yMax],centered=self.centered)   # calculate the new ones in a squared space
      ax.set_xlim(xMin,xMax);ax.set_ylim(yMin,yMax)                                   # set them in the matplolib axes
      ax.autoscale(enable=False,axis='x')
      ax.autoscale(enable=False,axis='y')
      ax.set_aspect('equal', adjustable='box', anchor='C')
      if self.centered:
        None #self.axesLines=[ax.axhline(y=0,color='k'),ax.axvline(x=0,color='k')]          # draw axes if centered
    else:
      ax.set_aspect('auto', adjustable='box', anchor='C')                         # and disable autoscale
    if not (self.squared and self.centered):                                       # erase the x=0 and y=0 line if not squared and centered
      for line in self.axesLines:
        #self.axesLines.remove(line)
        None#del line 
    self.draw()                                                                       # and redraw in all cases

  def toClipboard(self):
    pixmap = QPixmap.grabWidget(self)
    QApplication.clipboard().setPixmap(pixmap)

  def toPrinter(self):
    (w,h)=self.setScale(4,6)
    dialog = QPrintDialog(self.printer)
    dialog.setModal(True)
    dialog.setWindowTitle("Print Document" )
    dialog.addEnabledOption(QAbstractPrintDialog.PrintSelection)
    if dialog.exec_() == True:
      painter = QPainter(self.printer)
      xscale = self.printer.pageRect().width()/self.width()
      yscale = self.printer.pageRect().height()/self.height()
      scale = min(xscale, yscale)
      painter.translate(self.printer.paperRect().x() + self.printer.pageRect().width()/2,0)#self.printer.paperRect().y() + self.printer.pageRect().height()/2)
      painter.scale(scale, scale)
      painter.translate(-self.width()/2, 0)#-self.height()/2);
        
      self._moveLabel.hide()
      pixmap=QPixmap.grabWidget(self)
      painter.drawPixmap(0,0,pixmap)
      painter.end()
    self.setScale(w,h)

  def scroll(self,event):
    for ax in self._fig.axes:
      cur_xlim = ax.get_xlim()
      cur_ylim = ax.get_ylim()
      cur_xrange = (cur_xlim[1] - cur_xlim[0])*.5
      cur_yrange = (cur_ylim[1] - cur_ylim[0])*.5
      xdata = event.xdata # get event x location
      ydata = event.ydata # get event y location
      if event.button == 'up':
        # deal with zoom in
        scale_factor = 1/1.3
      elif event.button == 'down':
        # deal with zoom out
        scale_factor = 1.3
      else:
        # deal with something that should never happen
        scale_factor = 1
        print "unknown even occured in zooming", event.button
      new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
      new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
      
      relx = (cur_xlim[1] - xdata)/(cur_xlim[1] - cur_xlim[0])
      rely = (cur_ylim[1] - ydata)/(cur_ylim[1] - cur_ylim[0])
      if(self.scrollable[0]): 
        ax.set_xlim([xdata - new_width * (1-relx), xdata + new_width * (relx)])
      if(self.scrollable[1]): 
        ax.set_ylim([ydata - new_height * (1-rely), ydata + new_height * (rely)])
    self.redraw()

  def setScale(self,w,h):
    """
    Set size w,h
    Return previous size
    """
    (wOld,hOld) = self._fig.get_size_inches()
    self._fig.set_size_inches(w, h)
    return wOld, hOld

  def autoScale(self):
    self.autoX=True; self.autoY=True
    if self.threeD:  self.autoZ=True
    self.redraw()

  def zoomTo(self,rect):
    self.axes.set_xlim(rect.left(),rect.right())
    self.axes.set_ylim(rect.bottom(),rect.top())
    self.autoX=False; self.autoY=False 
    self.redraw()

  def title(self):
    return self.name

  def extraCode(self):
    return self._extraCode
      
  def setExtraCode(self,code):
    self._extraCode = code
    
  def execExtraCode(self):
    if self._extraCode == None:
      return
    lv = self.__dict__
    exec(self._extraCode,lv,lv)

  def onPress(self,event):
    if event.button == 1:
      if event.dblclick:  self.showPropertyDialog()
      else:
        self._pressed = True
        self._pressEvent = event
        self._moveEvent = event

  def onRelease(self,event):
    if event.button == 1:
      self._pressed = False
      oldRect = QRectF()
      oldRect.setLeft(self.axes.get_xlim()[0])
      oldRect.setRight(self.axes.get_xlim()[1])
      oldRect.setBottom(self.axes.get_ylim()[0])
      oldRect.setTop(self.axes.get_ylim()[1])
      rect = QRectF()

      (x1,y1) = self.axes.transData.inverted().transform([self._pressEvent.x,self._pressEvent.y])
      (x2,y2) = self.axes.transData.inverted().transform([event.x,event.y])

      rect.setLeft(min(x1,x2))
      rect.setRight(max(x1,x2))
      rect.setBottom(min(y1,y2))
      rect.setTop(max(y1,y2))
      if fabs(rect.width()) >= 0.01*fabs(oldRect.width()) and fabs(rect.height()) >=fabs(0.01*oldRect.height()):
        self.zoomTo(rect)

  def onMove(self,event):
    self._moveLabel.show()
    if self._pressed:
      self._moveEvent = event
      self.update()
    if event.xdata == None:
      self._moveLabel.hide()
      return
    self._moveLabel.setText(QString(r"x = %g, y = %g" % (event.xdata,event.ydata)))
    self._moveLabel.adjustSize()
    offset = 10
    if self.width()-event.x < self._moveLabel.width():
      offset = -10 - self._moveLabel.width()
    self._moveLabel.move(event.x+offset,self.height()-event.y)
      
  def mouseMoveEvent(self,e):
    try:
      FigureCanvas.mouseMoveEvent(self,e)
    except:
      pass
        
  def paintEvent(self,e):
    FigureCanvas.paintEvent(self,e)
    if self._pressed:
      painter = QPainter(self)
      painter.setPen(QPen(Qt.DotLine))
      (x1,y1) = self.figure.transFigure.inverted().transform([self._pressEvent.x,self._pressEvent.y])
      (x2,y2) = self.figure.transFigure.inverted().transform([self._moveEvent.x,self._moveEvent.y])
      painter.drawRect(x1*self.width(),(1-y1)*self.height(),(x2-x1)*self.width(),-(y2-y1)*self.height())

  def onPaint(self,painter):
    print "painting..."

  def leaveEvent(self,e):
    FigureCanvas.leaveEvent(self,e)
    self._pressed = False
    self.update()  
        
  def contextMenuEvent(self, event):    
    menu = QMenu(self)
    fontSizeMenu = menu.addMenu("Graph fontsize")
    autoscaleAction = menu.addAction("Autoscale / Zoom Out")
    propertiesAction = menu.addAction("Graph properties...")
    menu.addSeparator()
    saveAsAction = menu.addAction("Save figure as PNG...")
    pdfAction = menu.addAction("Save and open figure as PDF...")
    menu.addSeparator()
    toClipboardAction = menu.addAction("Copy")
    toPrinterAction = menu.addAction("Print...")
    fontSizes = dict()
    for i in range(6,16,2): fontSizes[i] = fontSizeMenu.addAction("%d px" % i)
    
    action = menu.exec_(self.mapToGlobal(event.pos()))
    if action == saveAsAction:        self.saveAs()  
    elif action == pdfAction:         self.openAndSaveAsPDF() 
    elif action == propertiesAction:  self.showPropertyDialog() 
    elif action == toPrinterAction:   self.toPrinter()
    elif action == toClipboardAction:   self.toClipboard()
    elif action == autoscaleAction:   self.autoScale()
    else:
      for fontSize in fontSizes.keys():
        if action == fontSizes[fontSize]:
          print "Setting font size to %d" % fontSize
          rcParams['font.size'] = str(fontSize)
          self.draw()

  def showPropertyDialog(self):
    try:
      reload(sys.modules["pyview.gui.mpl.canvas"])
      from pyview.gui.mpl.canvas import CanvasDialog
    except ImportError:
      pass
    if not self._dialog == None:
      self._dialog.hide()
    self._dialog = CanvasDialog(self)
    self._dialog.setModal(False)
    self._dialog.show()

  def saveAs(self):
    filename = str(QFileDialog.getSaveFileName(self,"Save figure as", "", "image (*.png, *.svg, *.pdf, *.emf, *.eps, *.pgf, *.ps, *.raw, *.rgba, *.svgz)"))
    if filename != '':
      self._fig.set_size_inches( self._width, self._height )
      self._fig.savefig(str(filename))

  def openAndSaveAsPDF(self):
    filename = str(QFileDialog.getSaveFileName(self,"Save and open figure as PDF", "", "PDF file (*.pdf)"))
    (w,h) = self._fig.get_size_inches()
    try:
      services = QDesktopServices()
      if filename != '':
        self._fig.set_size_inches( self._width, self._height )
        self._fig.savefig(str(filename))
        url = QUrl("file:///%s" % filename)
        services.openUrl(url)
    finally:
        self._fig.set_size_inches( w,h )
        self.draw()

class MatplotlibCanvas(MyMplCanvas):
  pass