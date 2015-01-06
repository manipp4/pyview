#*******************************************************************************
# DataManager Singleton class which can be used to keep track of datacubes.    *
# Just call addDatacube() to add a datacube to the DataManager.                *
# pyview.gui.datamanager.DataManager                                           *
#   provides a graphical frontend of the DataManager class.                    *
#*******************************************************************************
___debugDM2___ = False
def debugDM2(*args):
  if ___debugDM2___:
    for arg in args: print arg,
    print

#Imports

import sys
import getopt
import os.path
import traceback
from threading import Thread
import PyQt4.uic as uic

from pyview.lib.patterns import Singleton,Reloadable,ThreadedDispatcher,Subject,Observer

#This is a class that manages datacubes
class DataManager(Singleton,Reloadable,ThreadedDispatcher,Subject,Observer):  
  """
  The DataManager is a Singleton class which can be used to keep track of datacubes.
  Just call addDatacube() to add a datacube to the DataManager.
  pyview.gui.datamanager.DataManager provides a graphical frontend of the DataManager class.
  """
  
  def __init__(self,globals = {}):
    if hasattr(self,"_initialized"):
      return
    self._initialized = True
    Singleton.__init__(self)
    Reloadable.__init__(self)
    Observer.__init__(self)
    ThreadedDispatcher.__init__(self)
    Subject.__init__(self)
    self._datacubes = []
    self._globals = globals

  def datacubes(self):
    """
    Returns the datacubes.
    """
    return self._datacubes
  
  def addDatacube(self,datacube, checkTopLevelOnly=False):
    """
    Adds a datacube to the data manager if not already present in the datamanager if topLevelOnly is true,
    or at any child level of the datacubes present otherwise.
    """
    cubes=self._datacubes
    if not checkTopLevelOnly:
      family=[]
      for cube in cubes:
        family.extend(cube.familyMembers())
    cubes.extend(family)
    if not datacube in cubes:
      cubes.append(datacube)
      debugDM2('DataManager notifying "addDatacube" for datacube',datacube)
      # datacube.attach(self)
      self.notify("addDatacube",datacube)
      return True
  
  def removeDatacube(self,datacube,deleteCube=False):
    """
    Removes a datacube from the data manager and delete it from memory if deleteCube=True.
    The deletion will be propagated to all descendants by the removeChild function of the datacube
    """
    cubes=self._datacubes
    if datacube in cubes:                             # the cube is at the top level of the hyerarchy
      del cubes[cubes.index(datacube)]
      debugDM2('DataManager notifying "removeDatacube" for datacube',datacube)
      self.notify("removeDatacube",datacube)
      if deleteCube: del datacube
    else:                                             # the cube is not at the top level of the hyerarchy
      parent =datacube.parent()                                                       
      while parent!=None and not parent in cubes :    # check that it has a parent or ascendent in the datamanager
        parent=parent.parent()
      if parent in cubes:                             # give up if the datacube is not managed by the dataManager
        datacube.parent().removeChild(datacube,deleteChildCube=deleteCube)
  
  def clear(self):
    """
    Removes all datacubes from the data manager.
    """
    self._datacubes = []
    debugDM2('DataManager notifying "cleared" ')
    self.notify("cleared")
  
  ##


  #*******************************************************************************  
  ## Below are functions to notify the dataManager frontpanel to make a plot.
  ## Note that a datacube has methods to call these functions. 
    
  def plot(self,datacube,*args,**kwargs):
    """
    1) If datacube not already present, adds it to dataManager;
    2) Notify the dataManager frontpanel to plot the datacube in a way possibly defined by additional parameters.
    See the listener response documentation or code to know the enumerated (*args) or named (**kwargs) parameters that can be passed
    """
    self.addDatacube(datacube,checkTopLevelOnly=False)  # will add it to the dataManager only if not already present
    debugDM2('DataManager notifying ""plot"" for datacube ',datacube)
    self.notify("plot",((datacube,)+args,kwargs)) # then sends a plot notification with value ((datacube,arg1,arg2,...),{kwarg1:val1,kwarg2:val2,...})

    
  
        
  
  
    
  
