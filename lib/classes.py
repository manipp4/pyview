"""
Some convenience classes for managing instruments and frontpanels.
"""

import traceback
import socket

try:
  import win32com.client
  import pythoncom
except:
  print "Cannot import win32com.client or pythoncom"

try:
  import visa
  from visa import VI_ERROR_CONN_LOST,VI_ERROR_INV_OBJECT
  from visa import VisaIOError
  from visa import Error
  from pyvisa import vpp43
except:
  print "Cannot import Visa!"

from pyview.lib.patterns import *

class Debugger:
  """
  Class Debugger.
  Allows to set a derived class in debugging mode so that it prints messages using debugPrint()
  """
  def __init__(self):
    self._debugging = False

  def debugOn(self):
    self._debugging = True

  def debugOff(self):
    self._debugging = False
    
  def isDebugOn(self):
    return self._debugging

  def debugPrint(self,*args):
    if self._debugging:
      for arg in args: print arg,
      print

class Instrument(Debugger,ThreadedDispatcher,Reloadable,object):
  """
  The generic insrument class (parent of ThreadedDispatcher).
  Has a name and a list of state dictionary
  Public properties: daemon
  Public methods: name,parameters,saveState,pushState,popState,restoreState
  """
  def __init__(self,name = ""):
    Subject.__init__(self)
    Debugger.__init__(self)
    ThreadedDispatcher.__init__(self)
    self._name = name
    self._states = []
    self._stateCount = 0
    self.daemon = True
    
  def initialize(self,*args,**kwargs):
    pass
    
  def __str__(self):
    return "Instrument \"%s\"" % self.name()
    
  def name(self):
    return self._name

  def parameters(self):
    """
    Overide this function to return all relevant instrument parameters in a dictionary.
    """
    return dict()

  def saveState(self,name):
    """
    Saves the state of the instrument.
    Empty method to be overridden.
    """
    return None
    
  def pushState(self):
    self._states.append(self.saveState("state_"+str(self._stateCount)))
    self._stateCount+=1
    
  def popState(self):
    if len(self._states) > 0:
      state = self._states.pop()
      self.restoreState(state)
    
  def restoreState(self,state):
    """
    Restores the state of the instrument given by "state".
    
    "state" can be of any type. For instruments that can store configuration data on a hard disk, "state" could be the name of the file on the disk.
    For other instruments, "state" could contain all relevant instrument parameters in a dictionary.
    """
    pass
                
class VisaInstrument(Instrument):

    """
    A class representing an instrument that can be interfaced via NI VISA protocol.
    """

    def __init__(self,name = "",visaAddress = None):
      """
      Initialization
      """
      Instrument.__init__(self,name)
      self._handle = None
      self._visaAddress = visaAddress

    def getHandle(self,forceReload = False):
      """
      Return the VISA handle for this instrument.
      """
      if forceReload or self._handle == None:
        try:
          if self._handle != None:
            try:
              self._handle.close()
            except:
              pass
            self._handle = None
        except:
          pass
        self._handle = visa.instrument(self._visaAddress)
      return self._handle
      
    def executeVisaCommand(self,method,*args,**kwargs):
      """
      This function executes a VISA command.
      If the VISA connection was lost, it reopens the VISA handle.
      """
      try:
        returnValue = method(*args,**kwargs)
        return returnValue
      except Error as error:
        print "Invalidating Visa handle..."
        self._handle = None
        raise

    def __getattr__(self,name):
      """
      Forward all unknown method calls to the VISA handle.
      """
      handle = self.getHandle()
      if hasattr(handle,name):
        attr = getattr(handle,name)
        if hasattr(attr,"__call__"):
          return lambda *args,**kwargs: self.executeVisaCommand(attr,*args,**kwargs)
        else:
          return attr
      raise AttributeError("No such attribute: %s" % name)

import pickle  # implements an algorithm for turning an arbitrary Python object into a series of bytes (or chars) or vice and versa.
import cPickle
from struct import pack,unpack


_DEBUG=True

class Command:

  def __init__(self,name = None,args = [],kwargs = {}):
    self._name = name
    self._args = args
    self._kwargs = kwargs

  def __str__(self):
    return str([self._name,self._args,self._kwargs])
    
  def name(self):
    return self._name
    
  def args(self):
    return self._args
    
  def kwargs(self):
    return self._kwargs

  def toString(self):
    pickled = cPickle.dumps(self,cPickle.HIGHEST_PROTOCOL)  # encode the Python object into a string of bytes (or equivalently chars)
    s = pack("l",len(pickled))
    return s+pickled

  @classmethod # decorator. Why using this here? It is not reused by other methods. Not clear...
  def fromString(self,string):
    m = cPickle.loads(string) # decode the string as a Python object
    return m                  

class ServerConnection:

  def __init__(self,ip,port):
    if _DEBUG:  print 'in client serverConnection.__init__  with ip=',ip,'and port=',port
    self._ip = ip
    self._port = port
    self._socket = self.openConnection()
    
  def openConnection(self):
    if _DEBUG:  print 'in client serverConnection.openConnection() with ip=',self._ip,'and port=',self._port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt( socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.connect((self._ip, self._port))
    return sock
    
  def ip(self):
    return self._ip
    
  def port(self):
    return self._port

  def _send(self,commandName,args = [],kwargs = {}):
    """
    Method that both sends a command to an instrument server through a network socket, and receives a response from the server.
    """
    #We set some socket options that help to avoid errors like 10048 (socket already in use...)
    if _DEBUG:  print 'in client serverConnection._send() with commandName=',commandName,' args=',args, 'and kwargs=',kwargs
    command = Command(name = commandName,args = args,kwargs = kwargs)
    sock = self._socket
    try:
      sock.send(command.toString())           # sends the command as a serialized string
      lendata = sock.recv(4)                  # reads 4 bytes to get a string containing the number of available following bytes
      if len(lendata) == 0:                   # if no bytes areceived => connection lost
        raise Exception("Connection to server %s port %d failed." % (self._ip,self._port))
      length = unpack("l",lendata)[0]         # unpack this 4 bytes using format 'l' and keep the length to be read.
      received = sock.recv(length)            # read length bytes 
      binary = received
      while len(received)>0 and len(binary) < length: # if you get the beginning of the data, waits for all bytes
        received = sock.recv(length-len(binary))
        binary+=received
      if len(binary) == 0:                    # if you don't get anything, return
        return None
      response = Command().fromString(binary) # Now deserialize the data received to rebuild the python object
      if response == None:                    # No response => no connection to server
        raise Exception("Connection to server %s port %d failed." % (self._ip,self._port))
      if response.name() == "exception" and len(response.args()) > 0: 
        raise response.args()[0]              # we receive an error from the server and raise it here on the client side
      if _DEBUG:  print 'in client serverConnection._send() and getting response=',response
      return response.args()[0]               # we return the valid response
    except:
      self._socket = self.openConnection()    # if an error occured anywhere we reopen the connection (it is strange because if an error occured on the distant instrument, why reopening the connection)
      raise

  # Any attributes other than the ServerConnection's methods above will be 'routed' to ServerConnection._send with its arguments.
  def __getattr__(self,attr):
    if _DEBUG: print 'in client serverConnection.__getattr__() with attr=',attr
    return lambda *args,**kwargs:self._send(attr,args,kwargs)

class RemoteInstrument(Debugger,ThreadedDispatcher,Reloadable,object):
  """
  Class that represents locally a distant remote instrument, and that is able to communicate with it through a ServerConnection.
  """

  def __init__(self,name,server,baseclass = None, args = [],kwargs = {},forceReload = False):
    
    Debugger.__init__(self)
    ThreadedDispatcher.__init__(self)
    Reloadable.__init__(self)
    server.initInstrument(name,baseclass,args,kwargs,forceReload)
    self._server = server
    self._name = name
    self._baseclass = baseclass
    self._args = args
    self._kwargs = kwargs
    
  def remoteDispatch(self,command,args = [],kwargs = {}): # sends a command to a server
    self.debugPrint('in remoteInstrument.remoteDispatch() with command = ',command,' args=',args,' and kwargs=',kwargs)
    result =  self._server.dispatch(self._name,command,args,kwargs)
    self.notify(command,result)
    return result
    
  def __str__(self):  # Standard method called when printing
    return "Remote Instrument \"%s\" on server %s:%d" % (self.name(),self._server.ip(),self._server.port())
    
  def name(self):
    """
    We redefine name, since it is already defined as an attribute in Thread
    """ 
    return self.remoteDispatch("name")

  def __getitem__(self,key):
    return self.remoteDispatch("__getitem__",[str(key)])

  def __setitem__(self,key,value):
    print "Setting %s" % key
    return self.remoteDispatch("__setitem__",[key,value])

  def __delitem__(self,key):
    return self.remoteDispatch("__delitem__",[key])
    
  def getAttribute(self,attr):
    return self.remoteDispatch("__getattribute__",[attr])
    
  def setAttribute(self,attr,value):
    return self.remoteDispatch("__setattr__",[attr,value])

  # any call remoteInstrument.method(args,kwargs) with method different from the methods above will be treated by __getattr__ below and be transformed into remoteDispatch('method',args,kwargs)
  # but a call remoteInstrument.property is transformed into the meaningless function lambda *args,**kwargs:remoteDispatch(property,args,kwargs)
  # one should treat differently methods and properties
  def __getattr__(self,attr):
    self.debugPrint('in remoteInstrument.__getattr__() with attr = ',attr)
    return lambda *args,**kwargs:self.remoteDispatch(attr,args,kwargs)
  
  def __call__(self,request):
    """
    redefinig instr(requestString) to instr.ask(requestString) for remote instruments that don't work well when using instr.request
    Example: Replace instr.methodLeve1().methodLevel2() by instr('methodLeve1().methodLevel2()')
    """
    return self.ask(request)
        
class IgorCommunicator:
  """
  A class used to communicate with IgorPro using ActiveX
  """
  def __init__(self,new=False):
    """
    Initialization
    """
    try:
      pythoncom.CoInitialize()
      self._app=win32com.client.Dispatch("IgorPro.Application") 
      self._app.Visible=1
    except:
      raise Exception("Unable to load IgorPro ActiveX Object, ensure that IGOR Pro and pythoncom are installed ")
    
  def execute(self, command):
    """
    Execution of single-line command (str)
    Return results (str or None)
    """
    flag_nolog = 0
    code_page = 0
    err_code = 0
    result_tuple = self._app.Execute2(flag_nolog, code_page, command,err_code)
    err_code, err_msg, history, results = result_tuple
    if len(err_msg)>1:
      raise Exception("Active X IgorApp exception: \n  Command : \"" + command +"\"\n  Returns : \""+ err_msg+"\"")
    history=str(history)
    history=history.split("\r")
    return str(results),history
    
  def run(self,commands):
    """
    Execute multi-lines commands, ie list of strings
    return list or results for each single-line
    """
    if len(commands)<1:
      return ''
    results=[]
    for command in commands:
      result=self.execute(command)
      if result!='':
        results.append(result)
    return results

  def __call__(self,commands):
    """
    'smart' alias of run ie. encapsulate commands in [] if commands is a string
    """
    if type(commands)==type("string"):
      return self.run([commands])
    elif type(commands)==type([]):
      return self.run(commands)
    else: raise Exception("IgorApp badly called")

  def dataFolderExists(self,path):
    if path[-1]!=":":
        path+=":"
    history=self.execute("print DataFolderExists(\""+path+"\")")[1]
    return int(history[1][-1])==1

  def createDataFolder(self,fullPath):
    path=""
    if fullPath=="root:": return
    for subFolderName in fullPath.split(":"):
      path+=subFolderName
      if not(self.dataFolderExists(path+":")):
        self("NewDataFolder "+path)
      path+=":"
    return True
