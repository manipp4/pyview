from ctypes import *
from numpy import *
from scipy import *
import yaml
import StringIO
import os
import os.path
import pickle
import sys
import copy
import time
import weakref
import re
import string

from pyview.helpers.loopsmanager import LoopManager
from pyview.lib.patterns import Subject,Observer,Reloadable

##############################
## To Do:
##    - lock while next or modifying
##    - add temporary point
## 
##
##
##
##
#################################

class SmartLoop(Subject,Observer,Reloadable):
  def __iter__(self):
    return self
  
  def next(self):
    if self._paused:
      while self._paused:
        time.sleep(0.1)
    if self._toDelete:
      self.delete()
      raise StopIteration
    self._previousValue=self._value
    if self._index==0 or self._restart:
      self._restart=False
      self._value=self._start
      self._previousValue=self._value
    else:
      if self._step==None:
        raise "No step setted"
      else:
        self._value=self._value+self._step
    self._index+=1
    if self._stop!=None:
      if (self._value>self._stop and self._previousValue<=self._stop) or (self._value<self._stop and self._previousValue>=self._stop) :
        self.delete()
        raise StopIteration
    
    self.lm.updateLoop(self)
    
    return self._value
    
  
  def delete(self):
    self.lm.removeLoop(self)

  
  def __init__(self,start,step=None,stop=None,linnsteps=None,name='unamed loop'):
    
    Subject.__init__(self)
    Observer.__init__(self)
    Reloadable.__init__(self)
    
    
    self._paused=False
    self._toDelete=False
    self._value = None
    self._restart=False
    self._index=0
    
    if linnsteps==None:
      self._step=step
    else:
      self._step=(stop-start)/linnsteps  
    
    self._start=start
    self._stop=stop
    
    self._name=name
  
    self.lm=LoopManager()
    self.lm.addLoop(self)
    
  
  
  def __del__(self):
    return True

  
  def pause(self):
    self._paused=True
  
  def play(self):
    self._paused=False
  
  def stopAtNext(self):
    self._toDelete=True




