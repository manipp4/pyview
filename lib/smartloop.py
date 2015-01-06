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
## additions by DV on December 2014
##
#################################

class SmartLoop(Subject,Observer,Reloadable):
  def __iter__(self):
    return self
  """
  Class implementing a loop with the following (smart) features:
    loop parameters start, stop, step, and number of steps can be redefined at will along the loop
    loop can jump at any index or output value along the loop
    loop can be paused or be terminated at the next increment
    loop can be reversed at the next increment or autoreversed when crossing start or stop
  """

  def __init__(self,start,step=None,stop=None,linnsteps=None,name='unamed loop'):
    """
    Initializes the smartloop and adds it to the LoopManager
    """ 
    Subject.__init__(self)
    Observer.__init__(self)
    Reloadable.__init__(self)
    
    self._paused=False
    self._toDelete=False
    self._restart=False
    self._autoreverse=False
       
    self._name=name
    self._start=start
    self._stop=stop
    if linnsteps==None:
      self._step=step
      self._nsteps=int((stop-start)/step)+1 # added +1 by DV in december 2014
    else:
      self._nsteps=linnsteps
      self._step=(stop-start)/linnsteps  
    self._index=0
    self._value = None
    self._previousValue = None

    self._nextParams={} # dictionary of new loop parameters at the next increment

    self.lm=LoopManager()
    self.lm.addLoop(self)
   
  def preIncrement(self):
    """
    This function is called just before updateParams in the iterator function next.
    It is left empty here but can be overidden in child classes.
    """
    pass

  def updateParams(self):
    """
    Updates new parameters that have been stored in self._nextParams by other methods
    """
    keys=self._nextParams.keys()                    # go over all parameters to redefine
    for key in keys:
      setattr(self,'_'+key,self._nextParams[key])   # redefine each param
    increment='value' not in keys                       # if value has been modified directly, don't increment at next step
    self._nextParams={}                             # empty the redefinition dict
    return increment                                

  def finished(self):
    """
    Determines whether the loop is finished and implement autoreverse if _autoreverse is true.
    Termination occurs in one of these situations:
    There is no stop, there is a start, there is a previousValue, value crossed start, and autoreverse is OFF;
    There is no start, there is a stop, there is a previousValue, value crossed stop, and autoreverse is OFF;
    There is a start and a stop, value is outside, and autoreverse is OFF or value has not crossed start or stop.
    Loop is reversed if _autoreverse is true and loop's _value has just crossed one of the start or stop boundary.
    """
    end=False
    hasCrossedLimit=False
    stopIsNumber=isinstance(self._stop, (int, long, float))
    startIsNumber=isinstance(self._start, (int, long, float))
    previousValueIsNumber=isinstance(self._previousValue, (int, long, float))
    if (not stopIsNumber) and startIsNumber and previousValueIsNumber:
      end=hasCrossedLimit= (self._value>self._start and self._previousValue<=self._start) or (self._value<self._start and self._previousValue>=self._start)
    elif stopIsNumber and (not startIsNumber) and previousValueIsNumber:
      end=hasCrossedLimit= (self._value>self._stop and self._previousValue<=self._stop) or (self._value<self._stop and self._previousValue>=self._stop)
    elif stopIsNumber and startIsNumber:
      end=self._value > max(self._start,self._stop) or self._value < min(self._start,self._stop)
      if end and previousValueIsNumber:
        hasCrossedLimit= hasCrossedLimit or (self._value>self._start and self._previousValue<=self._start)
        hasCrossedLimit= hasCrossedLimit or (self._value<self._start and self._previousValue>=self._start)
        hasCrossedLimit= hasCrossedLimit or (self._value>self._stop and self._previousValue<=self._stop) 
        hasCrossedLimit= hasCrossedLimit or (self._value<self._stop and self._previousValue>=self._stop)
    if hasCrossedLimit and self._autoreverse:
      self.reverse()
      end=False
    return end

  def next(self):
    """
    Update the loop by:
    1) pausing or deleting the loop if requested
    2) calling a preIncrement function  
    3) calling updateParams() in case loop was redefined
    4) incrementing the index and value if needed,
    5) reversing or terminating the loop according to the finished() method. 
    """
    if self._paused:
      while self._paused:
        time.sleep(0.1)
    if self._toDelete:
      self.delete()
      raise StopIteration
    self.preIncrement()                # possibility to run a function here if needed
    increment=self.updateParams()      # added by DV dec 2014. Update params present in _nextParams and ask if increment is needed.
    self._previousValue=self._value
    if increment:
      if self._index==0 or self._restart:
        self._restart=False
        self._value=self._start
        self._previousValue=self._value
      else:
        if self._step==None:
          raise "No step set."
        else:
          self._value=self._value+self._step
      self._index+=1
    if self.finished():                 # modified by DV dec 2014. Test of termination deported in the dedicated function finished
      self.delete()
      raise StopIteration
    self.lm.updateLoop(self)
    return self._value
    
  def delete(self):
    self.lm.removeLoop(self) 
  
  def __del__(self):
    return True
  
  def pause(self):
    """ set the pause flag to true"""
    self._paused=True
  
  def play(self):
    """ set the pause flag to true"""
    self._paused=False
  
  def stopAtNext(self):
    """ set the toDelete flag to true"""
    self._toDelete=True

  def getParams(self):
    """ returns the dictionary of all loop parameters"""
    return {'name':self._name,'start':self._start,'stop':self._stop,'step':self._step,'nsteps':self._nsteps,'index':self._index,'value':self._value}

  def getName(self):
    """ returns the loop's name"""
    return self._name

  def getStart(self):
    """ returns the loop's starting value"""
    return self._start

  def getStop(self):
    """ returns the loop's stopping value"""
    return self._stop

  def getStep(self):
    """ returns the loop's step value"""
    return self._step

  def getNsteps(self):
    return self._nsteps

  def getIndex(self):
    """ returns the loop's current index value"""
    return self._index

  def getValue(self):
    """ returns the loop's current value"""
    return self._value

  def setName(self,newName):
    """
    Immediately redefines the name of the loop.
    """
    self._name=newName
    return self._name

  def setStart(self,newStart):
    """
    Stores in _nextParams dictionary the new start and corresponding new nsteps and index, leaving other parameters unchanged.
    """
    self._nextParams={'start':newStart}
    if self._stop!=None:
      self._nextParams['nsteps']=int((float(self._stop)-newStart)/self._step+1)
    if self._value!=None:
      self._nextParams['index']=int((float(self._value)-newStart)/self._step+1)

  def setStop(self,newStop):
    """
    Stores in _nextParams dictionary the new stop and corresponding new nsteps, leaving other parameters unchanged.
    """
    self._nextParams={'stop':newStop}
    if self._step!=None:
      self._nextParams['nsteps']=int((float(newStop)-self._start)/self._step)

  def setStep(self,newStep):
    """
    Stores in _nextParams dictionary the new step and corresponding new nsteps and index , leaving other parameters unchanged.
    """
    self._nextParams={'step':newStep}
    if self._stop!=None:
      self._nextParams['nsteps']=int((float(self._stop)-self._start)/newStep+1)
    if self._value!=None:
      self._nextParams['index']=int((float(self._value)-self._start)/newStep+1)

  def reverse(self):
    """ Reverse the ramp direction by reversing the sign of step"""
    self.setStep(-self._step)

  def getAutoreverse(self):
    """ Returns the autoreverse flag"""
    return self._autoreverse

  def setAutoreverse(self,ONorOFF):
    """ Set the autoreverse flag to True or False"""
    self._autoreverse=ONorOFF
    return self._autoreverse

  def setNsteps(self,newNsteps,adaptStep=False):
    """
    Stores in _nextParams dictionary 
      - the new nsteps
      - and the corresponding
        either new step and index if adaptStep is True,
        or new stop if adaptStep is False;
      Leaves other parameters unchanged.
    """
    self._nextParams={'nsteps':newNsteps}
    if adaptStep:
      newStep=(float(self._stop)-self._start)/newNsteps
      if self._stop!=None:  self._nextParams['step']= newStep
      if self._value!=None: self._nextParams['index']=int((float(self._value)-self._start)/newStep+1)
    else:
      if self._step!=None:  self._nextParams['stop']=self._start+newNsteps*self._step

  def setNextIndex(self,nextIndex):
    """ Stores in _nextParams dictionary the new index and value where to jump at next loop update."""
    self._nextParams={'index':nextIndex}
    if self._step!=None:  self._nextParams['value']=self._start+nextIndex*self._step

  def setNextValue(self,nextValue):
    """ Stores in _nextParams dictionary the new index and value where to jump at next loop update."""
    self._nextParams={'value':nextValue}
    if self._step!=None:  self._nextParams['index']=int((float(nextValue)-self._start)/self._step)+1

  
class AdaptiveLoop(SmartLoop):
  """
  Smartloop with a method for adapting its next update based on a feedback value.
  Typical feedback consists in calling newFeedbackValue(value) once per loop iteration.
  All feedback values are stored in _feedBackValues.
  The adaptive function is an external function adaptiveFunc(adaptiveLoop) with the loop as its single parameter.
  It has consequently access to all methods of a adaptiveLoop including getParams, feedBackValues, and all methods filling _nextParams   
  It is passed to the adaptive loop at its creation or later using the setAdaptFunc(function) method
  
  Example:

    def adaptFunc1(adaptiveLoop):
      adaptiveLoop.setStep(1)
      if adaptiveLoop.feedBackValues[-1] > 2: adaptiveLoop.setStep(2)

    adaptiveLoop1=AdaptiveLoop(0,step=1,stop=10,adaptFunc=adaptFunc1)
    for x in adaptiveLoop1:
      # do something here and generate a feedback value yi
      adaptiveLoop1.newFeedbackValue(yi)
  
  WARNING: Competing with adaptFunc1() by changing in parallel the loop parameters from another piece of code or from a GUI interface
  will very likely lead to wrong results and errors.
  """  
  
  def __init__(self,start,adaptFunc=None,**kwargs):
    SmartLoop.__init__(self,start,**kwargs)
    self._feedBackValues=[]
    self._adaptFunc=adaptFunc
  
  def newFeedbackValue(self,value):
    self._feedBackValues.append(value)

  def feedBackValues(self):
    return self._feedBackValues

  def adaptFunc(self,adaptFunc):
    return self._adaptFunc

  def setAdaptFunc(self,adaptFunc):
    self._adaptFunc=adaptFunc
    return self._adaptFunc

  def preIncrement(self): # overidden method of the SmartLoop parent class
    if self._adaptFunc!=None:
      self._adaptFunc(self) 




