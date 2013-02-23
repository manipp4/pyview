import sys
import os
import os.path

import random
import time
import pyview.gui.objectmodel as objectmodel
import projecttree
import yaml
import re

from pyview.lib.patterns import KillableThread

from PyQt4.QtGui import * 
from PyQt4.QtCore import *

from pyview.gui.editor.codeeditor import *
from pyview.gui.threadpanel import *
from pyview.gui.project import Project
from pyview.helpers.coderunner import MultiProcessCodeRunner
from pyview.gui.patterns import ObserverWidget
from pyview.config.parameters import params

def timeOutFunction(t,qt):
  for i in range(0,t*10):
  	time.sleep(0.1)
  try:
  	qt.close()
  	print "userAsk : timeOut --> closing"
  except:
  	raise
  


def userAsk(message,title="None",timeOut=10,defaultValue=False):
  MyMessageBox = QMessageBox()
  if title!="None":
    MyMessageBox.setWindowTitle("Warning!")
  MyMessageBox.setText(str(message))
  yes = MyMessageBox.addButton("Yes",QMessageBox.YesRole)
  no = MyMessageBox.addButton("No",QMessageBox.NoRole)
  cancel=MyMessageBox.addButton("No",QMessageBox.RejectRole)
  print "Action requested : %s"%str(message)

  t=KillableThread(target=timeOutFunction,args=(timeOut,MyMessageBox,))
  t.start()

  MyMessageBox.exec_()
  choice = MyMessageBox.clickedButton()
  t.terminate()
  
  if choice == no:
    return False
  elif choice == yes:
    return True  
  else :
    return defaultValue
  
  
  




