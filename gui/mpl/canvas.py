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

  def addOption(self,name,enterType,defaultValue=None):
    if enterType=="QLineEdit":
      self._options[name] = QLineEdit()
      self._options[name].setText(str(defaultValue))
      self.layout.addWidget(QLabel(name+": "))
      self.layout.addWidget(self._options[name])
    elif enterType=="QCheckBox":
      self._options[name] = QCheckBox(name)
      self.layout.addWidget(self._options[name])


class CanvasDialog(QDialog):
  
  def __init__(self,canvas,parent = None):

    try:
      reload(sys.modules["pyview.gui.mpl.canvas"])
      from pyview.gui.mpl.canvas import CanvasDialogTab
    except:
      raise Error("Unable to import CanvasDialogTab")

    QDialog.__init__(self,parent)
    self.setFixedWidth(200)
    layout = QGridLayout()
    self.setLayout(layout)
    self._canvas = canvas
    self.setWindowTitle(self._canvas.title()+" properties")
    self.tabs = QTabWidget()
    layout.addWidget(self.tabs,0,0)
    self.cancelButton = QPushButton("Cancel")
    self.applyButton = QPushButton("Apply")
    buttonsLayout = QBoxLayout(QBoxLayout.RightToLeft)
    buttonsLayout.addWidget(self.applyButton)
    buttonsLayout.addWidget(self.cancelButton)
    buttonsLayout.addStretch(0)
    layout.addLayout(buttonsLayout,1,0)

    self.scaleTab=CanvasDialogTab(self)

    self.scaleTab.addOption("Autorange","QCheckBox")
    self.scaleTab.addOption("X Min","QLineEdit",self._canvas.axes.get_xlim()[0])
    self.scaleTab.addOption("X Max","QLineEdit",self._canvas.axes.get_xlim()[1])
    self.scaleTab.addOption("Y Min","QLineEdit",self._canvas.axes.get_ylim()[0])
    self.scaleTab.addOption("Y Max","QLineEdit",self._canvas.axes.get_ylim()[1])


    self.tabs.addTab(self.scaleTab,"Scale")
    self.connect(self.cancelButton,SIGNAL("clicked()"),self.close)
    self.connect(self.applyButton,SIGNAL("clicked()"),self.apply)

  def apply(self):
    if self.scaleTab._options["Autorange"].isChecked():
      self._canvas.autoScale()
    else:
      self._canvas.axes.set_xlim(float(self.scaleTab._options["X Min"].text()),float(self.scaleTab._options["X Max"].text()))
      self._canvas.axes.set_ylim(float(self.scaleTab._options["Y Min"].text()),float(self.scaleTab._options["Y Max"].text()))
      self._canvas.axes.set_autoscale_on(False) 
      self._canvas.draw()
    self.close()

class MyMplCanvas(FigureCanvas):

    def onPress(self,event):
      if event.button == 1:
        self._pressed = True
        self._pressEvent = event
        self._moveEvent = event
    
    def extraCode(self):
      return self._extraCode
      
    def setExtraCode(self,code):
      self._extraCode = code
    
    def execExtraCode(self):
      if self._extraCode == None:
        return
      lv = self.__dict__
      exec(self._extraCode,lv,lv)
      
    def leaveEvent(self,e):
      FigureCanvas.leaveEvent(self,e)
      self._pressed = False
      self.update()
      
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
                
    def zoomTo(self,rect):
        self.axes.set_xlim(rect.left(),rect.right())
        self.axes.set_ylim(rect.bottom(),rect.top())
        self.axes.set_autoscale_on(False) 
        self.draw()

    def title(self):
      return "Figure"
        
    def contextMenuEvent(self, event):    
      menu = QMenu(self)
      autoscaleAction = menu.addAction("Autoscale / Zoom Out")
      saveAsAction = menu.addAction("Save figure as...")
      fastDisplayAction = menu.addAction("Open as PDF")
      toPrinterAction = menu.addAction("Print")
      propertiesAction = menu.addAction("Properties")
      fontSizeMenu = menu.addMenu("Font size")
      fontSizes = dict()
      for i in range(6,16,2):
        fontSizes[i] = fontSizeMenu.addAction("%d px" % i)
      action = menu.exec_(self.mapToGlobal(event.pos()))
      if action == saveAsAction:
        filename = QFileDialog.getSaveFileName()
        if not filename == '':
          self._fig.set_size_inches( self._width, self._height )
          self._fig.savefig(str(filename))
      elif action == fastDisplayAction:

        dialog = QInputDialog()
        dialog.setWindowTitle("Save and open as *.pdf")
        dialog.setLabelText("Filename")
        dialog.setTextValue("")
        
        dialog.exec_()
        
        if dialog.result() == QDialog.Accepted:
          filename = dialog.textValue()
        else:
          return
        if filename == "":
          filename = "no name"
        baseName = ""+filename
        filename += ".pdf"
        cnt = 1
        while os.path.exists(filename):
          filename = baseName+ "_%d.pdf" % cnt
          cnt+=1
        (w,h) = self._fig.get_size_inches()
        try:
          services = QDesktopServices()
          if not filename == '':
            self._fig.set_size_inches( self._width, self._height )
            self._fig.savefig(str(filename))
            url = QUrl("file:///%s" % filename)
            services.openUrl(url)
        finally:
            self._fig.set_size_inches( w,h )
            self.draw()
      elif action == propertiesAction:
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
      elif action == toPrinterAction:
        self.toPrinter()
      elif action == autoscaleAction:
        self.autoScale()
      for fontSize in fontSizes.keys():
        if action == fontSizes[fontSize]:
          print "Setting font size to %d" % fontSize
          rcParams['font.size'] = str(fontSize)
          self.draw()

    def setScale(self,w,h):
      """
      Set size w,h
      Return previous size
      """
      (wOld,hOld) = self._fig.get_size_inches()
      self._fig.set_size_inches(w, h)
      return wOld, hOld

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

    def autoScale(self):
      self.axes.set_autoscale_on(True)
      self.axes.relim() 
      self.axes.autoscale_view()
      self.draw()

    def onPaint(self,painter):
      print "painting..."
    
                          
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
    
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""
    def __init__(self, parent=None, width=5, height=5, dpi=60):

        fig = Figure(figsize=[width, height], dpi=dpi)
        self._fig = fig
        self._dialog = None
        self._width = width
        self._height = height
        self._dpi = dpi
        self._pressed = False

        self.printer=QPrinter()

        FigureCanvas.__init__(self, fig)
        
#        self.setFixedWidth(self._dpi*self._width)
#        self.setFixedHeight(self._dpi*self._height)

        self._isDrawing = False
        self.axes = fig.add_subplot(111)
        self.axes.set_autoscale_on(True) 
        self.axes.hold(True)


        self.setParent(parent)

        self._moveLabel = QLabel("",self)
        self._moveLabel.setText("tes")
        self._moveLabel.hide()
        self._moveLabel.setStyleSheet("font-size:14px; margin:5px; padding:4px; background:#FFFFFF; border:2px solid #000;")
        
        self.mpl_connect('button_press_event', self.onPress)
        self.mpl_connect('button_release_event', self.onRelease)
        self.mpl_connect('motion_notify_event', self.onMove)

        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

class MatplotlibCanvas(MyMplCanvas):
  pass