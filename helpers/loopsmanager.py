import sys
import getopt

import os.path

import traceback

from threading import Thread

import PyQt4.uic as uic

from pyview.lib.patterns import Singleton,Reloadable,ThreadedDispatcher,Subject,Observer

#This is a class that manages datacubes
class LoopManager(Singleton,Reloadable,ThreadedDispatcher,Subject,Observer):
  
  """
  The LoopManager is a Singleton class which can be used to keep track of loops. Just call addLoops() to add a loo to the LoopManager. pyview.gui.loopmanager.LoopManager provides a graphical frontend of the LoopManager class.
  """
  
  def __init__(self):
    if hasattr(self,"_initialized"):
      return
    self._initialized = True
    Singleton.__new__(self)
    Reloadable.__init__(self)
    Observer.__init__(self)
    ThreadedDispatcher.__init__(self)
    Subject.__init__(self)
    self._loops = []

  def updated(self,subject = None,property = None,value = None):
    self.notify("updated",subject)
  
  def removeLoop(self,loop):
    """
    Adds a loop to the loop manager.
    """
    if loop in self._loops:
      del self._loops[self._loops.index(loop)]
      self.notify("removeLoop",loop)
      return True
        
  def addLoop(self,loop):
    """
    Adds a loop to the loop manager.
    """
    if not loop in self._loops:
      self._loops.append(loop)
      self.notify("addLoop",loop)
      return True
        
  def updateLoop(self,loop):
    """
    Update loop manager
    """
    if loop in self._loops:
      self.notify("updateLoop",loop)
      return True

