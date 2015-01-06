#**********************************************************************************
# This defines  a hirarchical data storage class called datacube.                 *
# A datacube stores a 2-dimensional table of values of the same types:            *
#       array len(self._table[self._index,:])).                                   *
# Each datacube is identified by a name and has other properties.                 *
# A datacube can have one or more "children datacubes" for each row of its table, *
# thus creating a multidimensional data model.                                    *
#**********************************************************************************

___debugDC2___ = False
def debugDC2(*args):
  if ___debugDC2___:
    for arg in args: print arg,
    print

#*******************************************************************************
# Imports and utility classes
#*******************************************************************************

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

from pyview.helpers.datamanager2 import DataManager   # DATAMANAGER2
from pyview.lib.patterns import Subject,Observer,Reloadable
from pyview.lib.classes import *

class ChildItem:
  """
  Class of datacube child with two private properties _datacube and _attributes
  as well as two public methods datacube() and attributes()returning them.
  The _attributes property is a dictionary {name1:value1, name2:value2...}.
  """
  
  def __init__(self,datacube,attributes):
    self._datacube = datacube
    self._attributes = attributes

  def datacube(self):
    return self._datacube
    
  def attributes(self):
    return self._attributes
    
#******************************************************************************
#  Datacube class
#******************************************************************************
    
class Datacube(Subject,Observer,Reloadable):
  """
  Defines  a hirarchical data storage class called datacube.           
  A datacube stores a 2-dimensional table of values of the same type in a numpy array len(self._table[self._index,:])).                                  
  Each datacube is identified by a name and has other properties as its length, current index,...              
  A datacube can have one or more "child datacubes" for each row of its table, thus creating a multidimensional data model.
  As a member of the Observer and Subject classes, a datacube can send and receive notifications (messages)

  Data are entered in a specific way:
    - Any element at an existing row index starting at 0 and strictly lower than length can be overwritten.
    - An element can be virtually set beyond the length, i.e., at a row index >= length.
      But a row with index >= length is not known as being part of the datacube until this row or another one with greater index
      is validated by the commit() method.
    - An essential role is played by the commit() method :
      commit(rowIndex) means that an existing or a new row at indicated index (or current index if index=None) is validated (probably with new data)
      commit(rowIndex) positions the current index to the indicated index+1 or current index+1.
      commit(rowIndex) send a notification to all datacube listeners of row validation
      As a result filling the table row by row  by succesive calls of set and commit yields the following situation:
        Data are added on a virtual row at current index = length, which does not belong yet to the datacube.
        The commit call makes this line belong to the datacube and preposition the index on the next virtual row.
    For that reason, when opening a datacube, ... 
  """

  # version = "0.2"
  # version = "0.3"
  version = "0.4"   # DV April 2014: Calls to Datamanager modified with named parameters instead of unnamed ones
  
  defaults = dict()

  ######################################
  # creator 
  ######################################
  def __init__(self,*args,**kwargs):  # creator
    Subject.__init__(self)
    Observer.__init__(self)
    Reloadable.__init__(self)
    self.initialize(*args,**kwargs)
  
  def initialize(self,name = "datacube",description = "",filename = None,dtype = float64,defaults = None):    
    """
    Initializes the data cube.
    """    
    debugDC2('Creating datacube ',name,' = ',self)
    self._meta = dict()
    if defaults == None:
      defaults = Datacube.defaults
    self._meta["defaults"] = defaults
    self._meta["filename"] = filename
    self._meta["name"] = name
    self._meta["fieldNames"] = []                 # ordered list of field (column) names
    self._meta["description"] = description
    self._meta["fieldMap"] = dict()               # dictionary of the field names with values equal to their index
                                                  # can appear as redundant but make easier the access by name and provides a memory on column creation or supression.
    self._meta["parameters"] = dict()
    self._meta["index"]= 0
    self._meta["tags"] = ""
    self._meta["length"] = 0
    self._meta["dataType"] = dtype
    self._meta["modificationTime"] = time.asctime()
    self._meta["creationTime"] = time.asctime()
    
    self._children = []
    self._parameters = dict()
    self._table = None
    self._parent = None
    
    self._changed = False
    self._unsaved = True
  
  def __getitem__(self,keys):
    if not hasattr(keys,'__iter__'):
      keys = [keys]
    return self.columns(keys)
    
  ###############################
  # datacube property management
  ###############################

  def name(self):
    """
    Returns the name of the datacube
    """
    return self._meta["name"]
        
  def setName(self,name):
    """
    Sets the name of the datacube
    """
    self._meta["name"] = str(name)    
    self.setModified()
    debugDC2('datacube.setName with datacube ',self.name(),' notifying "name with name=',name)
    self.notify("name",name)  
  
  def parent(self):
    """
    Returns the parent of the data cube.
    """
    if self._parent == None:
      return None
    return self._parent
    
  def setParent(self,parent):
    """
    Sets the parent of the data cube to *parent*.
    """
    self._parent = parent
    
  def dataType(self):
    return self._meta["dataType"] 

  def index(self):
    """
    Returns the current row index.
    """
    return self._meta["index"]
    
  def parameters(self):
    """
    Returns the parameters dictionary of the data cube. The parameter dictionary is saved along with the datacube in a .par file.
    """
    return self._parameters
    
  def setParameters(self,params):
    """
    Sets the parameters of the datacube to *params*
    Then notify the frontpanel of the new params
    """
    self._parameters = params
    self.setModified()
    debugDC2('datacube.setParameters with datacube ',self.name(),' notifying ""parameters"" with parameters=',params)
    self.notify("parameters",params)
 
  def setFilename(self,filename):
    """
    Sets the filename of the datacube to *filename*.
    """
    self._meta["filename"] = os.path.realpath(filename)
    self.setModified()
    debugDC2('datacube.setFilename with datacube=',self,' notifying ""filename"" with filename=',filename)
    self.notify("filename",filename)

  def relfilename(self):
    """
    Returns the relative filename of the datacube.
    """
    return self._meta["filename"]

  def filename(self):
    """
    Returns the filename of the datacube.
    """
    return self._meta["filename"]
      
  def tags(self):
    """
    Returns the tags of the datacube.
    """
    return self._meta["tags"]
    
  def description(self):
    """
    Returns the description of the datacube
    """
    return self._meta["description"]
    
  def setTags(self,tags):
    """
    Sets the tags of the datacube
    """
    self._meta["tags"] = str(tags)
    self.setModified()
    debugDC2('datacube.setTags with datacube ',self.name(),' notifying ""tags"" with tags=',tags)
    self.notify("tags",tags)
    
  def setDescription(self,description):
    """
    Sets the description of the datacube
    """
    self._meta["description"] = str(description)
    self.setModified()
    debugDC2('datacube.setDescription with datacube ',self.name(),' notifying ""description"" with description=',description)
    self.notify("description",description)
  
  def structure(self,tabs = ""):
    """
    Returns a string describing the structure of the datacube
    """
    string = tabs+"cube(%d,%d)" % (self._meta["length"],len(self._meta["fieldNames"]))+"\n"
    for item in self._children:
      child = item.datacube()
      attributes = item.attributes()
      parts = []
      for key in attributes:
        parts.append((" %s = " % str(key))+str(attributes[key]))
      string+=", ".join(parts)+":\n"
      string+=child.structure(tabs+"\t")
    return string
   
  def setModified(self):
    """
    Marks the datacube as unsaved
    """
    self._meta["modificationTime"] = time.asctime()
    self._unsaved = True

  def modified(self):
    """
    Returns True if the datacube has been changed but not saved
    """
    return self._unsaved

  def setChanged(self,changed = False):
    """
    UNUSED: Marks the datacube as changed
    """
    self._changed = changed

  def changed(self):
    """
    UNUSED: Returns True if the datacube has been changed but not saved
    """
    return self._changed
    
            
  def maxDepth(self,initialDepth=0):
    """
    Returns the maximum depth of the datacube's children tree:
    0 for self only, 1 for self and children, 2 for self, children and grand-children, and so on
    """
    if not self.children():
      return initialDepth
    else:
      return max([child.maxDepth(initialDepth=initialDepth+1) for child in self.children()])

  def commonDepth(self):
    """
    Returns the maximum depth common to all datacube's tree branches:
    0 for self only, 1 for self and children, 2 for self, children and grand-children, and so on.
    """
    depth=0
    children=self.children()
    hasChildren=len(children)>0
    while hasChildren:
      depth+=1
      newChildrenList=[]
      for child in children:
        newChildren=child.children()
        hasChildren=len(newChildren)>0
        if not hasChildren:
          return depth
        else:
          newChildrenList+=newChildren
      children=newChildrenList
    return depth

  def tree(self,nameOut=False):
    """
    return the datacube tree in terms of datacube objects or datacube names if name=True
    """
    out=self
    if nameOut: out=self.name()
    tree=[out]
    if self.children():
      out=[child.tree(nameOut=nameOut) for child in self.children()]
      tree.append(out)
    return tree

  def familyMembers(self):
    def flatten(nested, flat=[]):
      for i in nested:
        flatten(i, flat=flat) if isinstance(i, list) else flat.append(i)
      return flat
    return flatten(self.tree())

  def cubesAtLevel(self,level=0,allBranchesOnly=False,nameOut=False):
    """
    return all datacube's children at a level of the datacube's tree, or their names if name=True.
    """
    depth=0
    cubes=[self]
    stop=False
    while depth<level and not stop:            # climb up the datacube's tree up to level level
      cubeList=[]
      for cube in cubes:
        newCubes=cube.children()
        if len(newCubes)==0:
          if allBranchesOnly:     # but return the first time there are no more children if level not reached
            return []
        else:
          cubeList+=newCubes
      if cubeList:
        cubes=cubeList
        depth+=1
      else: stop=True 
    if depth==level:
      if nameOut: cubes=[cube.name() for cube in cubes]
      return cubes
    else: return []

  def names(self,includeChildren=False,upToLevel=-1,flatten=True):
    """
    Returns all column names of the datacube,
    and optionally if includeChildren = True, also all column names of children, grandchildren,
    and so on up to children level upToLevel, starting from level 0 for self.
    Use a negative index for level as usual to specify the level relative to the end.
    Unless flatten is set to True, the hierarchy is respected and the output has the form
    [names,tree_of_children_if_any] with 
    tree_of_children_if_any=[names_of_children_if_any,tree_of_grandchildren_if_any], and so on.
    """
    names=list(self._meta["fieldNames"]) # Very important: clone the list _meta["fieldNames"] to protect it from modification outside
    if not includeChildren:
      return names
    else:
      if upToLevel<0 :
            upToLevel= max(0,self.depth()+1+upToLevel)
      if upToLevel==0 or not self.children():
        new= []
      else:
        upToLevel-=1
        new=[child.names(includeChildren=includeChildren,upToLevel=upToLevel,flatten=flatten) for child in self.children()]
      if flatten:
        new=list(set().union(*map(set,new)))
        return names+new
      else:   
        return [names, new]

  def commonNames(self):
    """
    Returns the  list of lists
    [column names of datacube, names common to all children, names common to all grand-children, ... ]
    Stops at the first level having no common names and do not include the corresponding empty list in the returned list. 
    """
    commonNames=[self.names()]
    children=self.children()
    hasChildren=len(children)>0
    while hasChildren:              # loop while there are still children everywhere at the next level
      newChildrenList=[]
      newCommonNames=set(children[0].names())
      for child in children:
        newNames=child.names()
        newCommonNames.intersection_update(newNames)
        if not newCommonNames:
          return commonNames        # but return the first time there are no common names at the current level
        else:
          newChildren=child.children()
          hasChildren=hasChildren and len(newChildren)>0
          if hasChildren:
            newChildrenList+=newChildren
      if newCommonNames:
        commonNames.append(list(newCommonNames))
        if hasChildren:
          children=newChildrenList
    return commonNames
      
  def clear(self):
    """
    Resets the datacube to its initial state
    """
    self.initialize()
    
  def table(self):
    """
    Returns the validated part of the data table, i.e., from index 0 to length-1
    """
    return self._table[:self._meta["length"],:]

  def updateFieldMap(self):
    debugDC2('In ',self._meta["name"],'.updateFieldMap()')
    self._meta["fieldMap"]=dict()
    for i in range(len(self._meta["fieldNames"])):
      self._meta["fieldMap"][self._meta["fieldNames"][i]] = i

  def __len__(self): # magic method
    """
    Returns the length of the datacube, i.e., the number of rows (up to the last validated one) 
    """
    return self._meta["length"]  


  ############################
  # Table reshaping
  ############################

  def _resize(self,size):
    """
    Resizes the datacube table
    """
    self._table.resize(size,refcheck = False) # size is a tuple (nbrRows,nbrColumns)

  def _adjustTable(self,rowIndex=None,notifyFields=True,reserve=0):
    """
    Resizes the table length at index + 1 + reserve when the reserve reaches 0 (rowIndex = length if set to None).
    Also regenerates the table and fieldMap if columns have changed.
      The table update is done according to:
        - the fieldNames considered as up to date;
        - the fieldMap considered as old but still describing the non updated table.
      Then update the fieldMap
    Finally send notifications of the field names if notifyFields =True
    Does not change the length of the datacube => Use extendTo to change both the table and the datacube length
    """
    debugDC2('In ',self._meta["name"],'._adjustTable(rowIndex=',rowIndex,',reserve=',reserve,')')
    fieldNames,fieldMap,ta=self._meta["fieldNames"],self._meta["fieldMap"],self._table
    nbrCols = len(fieldNames)
    if nbrCols==0:                                      # if all columns deleted
      self._table=None                                  # reset table to Noe and return
    else:
      if rowIndex==None : rowIndex=self._meta["length"]-1
      reserve=int(max(reserve,0))
      nbrRows = rowIndex+2+reserve
      unchangedCols= len(fieldNames)==len(fieldMap) and  all([fieldNames[fieldMap[field]]==field for field in fieldMap ]) # true also for empty fieldNames and fieldMap
      if unchangedCols and ta!=None :                   # if fields (colum names) have'nt changed
        if rowIndex >= len (self._table):               #   => adjust only if room is missing 
          self._resize((nbrRows,nbrCols))               #   => simple resizing without any copy
      else:                                             # else if column have changed
        if ta!=None : nbrRows=max(nbrRows,len(ta))
        newarray = zeros((nbrRows,nbrCols),dtype = self._meta["dataType"]) # create and new array
        if ta!=None:                                    #   and if the table already exist begin to copy the old data in the new array:
          for i in range(nbrCols):                      #     copy column by column the old columns
            if fieldNames[i] in fieldMap:               #     determine if the column i exists in the previous fieldMap
              j=fieldMap[fieldNames[i]]  
              newarray[:len(ta),i]=ta[:,j]                     #     copy from the old to new array
        self._table = newarray                          # update table with new array
      self.updateFieldMap()                             # update the fieldMap. It is now again in agreement with the fieldName list. 
    if notifyFields:
      debugDC2(self.name(),'._adjustTable  notifying "names" with fieldNames=',self._meta["fieldNames"])
      self.notify('names',self._meta['fieldNames'])

  ######################
  # column management
  ######################

  def columnName(self,index):
    """
    Returns a column name from its index
    """
    for key in self._meta['fieldMap'].keys():
      if self._meta['fieldMap'][key] == index:
        return key
    return None

  def columnIndex(self,name):
    """
    Returns a column index from its name or None if the column does not exist
    """
    i=None
    if name in self._meta["fieldMap"]: i=self._meta["fieldMap"][name]
    return i

  def renameColumn(self,oldName,newName):
    """
    Renames a column with current name oldName with new name newName.
    (Combine this function with columnName(index) if necessary)
    """
    #print 'in datacube.renameColumn(',oldName,',',newName,')' 
    fN=self._meta["fieldNames"]
    if newName==None: newName=self.newColumnName()
    if oldName in fN:
      fN[fN.index(oldName)] = newName
      self.updateFieldMap()
    self.notify("names",self._meta["fieldNames"])

  def column(self,name):
    """
    Returns a given column of the datacube (i.e. the table from index 0 to length-1)
    """
    if name in self._meta["fieldMap"]:
      return self._table[:self._meta["length"],self._meta["fieldMap"][name]]
    return None

  def columns(self,names):
    """
    Returns a table containing a set of given columns from their names
    """
    indices = []
    for i in range(0,len(names)):
      indices.append(self._meta["fieldMap"][names[i]])
    if len(indices) == 1:
      return self.table()[:,indices[0]]
    else:
      return self.table()[:,indices]
    
  def removeColumns(self,namesOrIndices,notify=True):
    """
    Removes several columns from the datacube, given their names or/and indices
    """
    debugDC2('In ',self._meta["name"],'.removeColumns(namesOrIndices=',namesOrIndices,',notify=',notify,')')
    names=[]
    for nameOrIndex in namesOrIndices:
      if isinstance(nameOrIndex,basestring):
        if nameOrIndex in self._meta["fieldNames"]:
          names.append(nameOrIndex)
      elif isinstance(nameOrIndex,int) and nameOrIndex< len(self._meta["fieldNames"]):
          names.append(self.columnName(nameOrIndex))
    for name in names:    
      if name in self._meta["fieldNames"]:
        del self._meta["fieldNames"][self._meta["fieldNames"].index(name)]
    self._adjustTable(notifyFields=False) # will also update the fieldMap
    if notify:
      debugDC2('datacube.removeColumn with datacube ',self.name(),' notifying "names" with names=',self._meta["fieldNames"])
      self.notify("names",self._meta["fieldNames"])
      debugDC2('datacube.removeColumn with datacube ',self.name(),' notifying "commit" with rowIndex=',self._meta["index"])
      self.notify("commit",self._meta["index"])

  def removeColumn(self,nameOrIndex,notify=True):
    """
    OBSOLETE: USE removeColumns INSTEAD. Maintained for compatibility issues.
    Removes a given column of the datacube from its name or index depending ifnameOrIndex is a string or a number
    """
    self.removeColumns([nameOrIndex],notify=notify)

  def setColumn(self,*args,**kwargs):
    """
    Alias for createCol.
    """
    return self.createCol(*args,**kwargs)
  
  def newColumnName(self):
    """
    Forms a new name of the form 'New_i' with i a not already used identifier.
    """
    names=self._meta["fieldNames"]
    i=1
    while True:
      name="New_"+str(i)
      i+=1
      if name not in names or i>1000 : break
    if i<= 1000: return name
    else: return None
  
  def _addFields(self,nameIndexDict,adjustTable=True):
    """
    PRIVATE FUNCTION called by createCol.
    Insert a new field name (i.e. column name) in self._meta["fieldNames"] and adjust accordingly the fieldMap and the cube's table.
    """
    debugDC2('In ',self._meta["name"],'_addFields(nameIndexDict=',nameIndexDict,',adjustTable=',adjustTable,')')
    newField=False
    for name in nameIndexDict:
      colIndex=nameIndexDict[name]
      if name==None: name=self.newColumnName()                                  
      existingColIndex=self.columnIndex(name)
      if existingColIndex==None:                                # if field already present don't do anything
        newField=True                                           # name not in fieldNames=> new names to notify soon
        nbrCols=len(self._meta["fieldNames"])
        if colIndex!=None and colIndex<0:                       # an index was indicated
          colIndex=nbrCols+colIndex+1                             # realculate its positive value if negative (relative to the end)
          if colIndex<0: colIndex=0                             # if still negative insert at index 0
        if colIndex == None or colIndex>nbrCols :               # if name and index not given or index too large
          colIndex=nbrCols                                      #   insert at index length (first free index)
        self._meta["fieldNames"].insert(colIndex,name)          # insert the name in fieldNames
      else:
        colIndex=existingColIndex
    if adjustTable: self._adjustTable()                         # New fieldNames now contradicts fieldmap and table => call _adjustTable
    return newField,colIndex

  def createColumn(self,name,values,offset = 0):
    """
    OBSOLETE AND MAINTAINED FOR COMPATIBILITY ISSUES. USE createCol INSTEAD
    Creates a new column
    """
    index = self.index()
    self.goTo(offset)
    for value in values:
      self.set(**{name:value})
      self.commit()
    self.goTo(index)

  def createCol(self,name=None,columnIndex=None,offsetRow=0,values=None,notify=True,**kwargs):
    """
    If it does not already exist, creates a new column and and inserts it at index columnIndex or at the end if index is not specified or invalid;
    If it already exists, overwrites it. 
    Then update the length if the new inserted data exceed the previous length.
    Then sets the passed values (if any) starting from row index = offset.
    Then sends notifications if notify is true.
    """
    debugDC2('In ',self._meta["name"],'createCol(name=',name,',columnIndex=',columnIndex,',offsetRow=',offsetRow,',values=',values,', notify=',notify,')')
    newField,columnIndex = self._addFields({name:columnIndex},adjustTable=False)     # Update fieldNames but wait before adjusting the table that we know adapt the length to the passed rows
    if values!=None:                          
      if offsetRow <0 : offsetRow = self._meta["length"]+offsetRow+1 #offsetRow is the index where to start to write
      if offsetRow <0 : offsetRow=0
      maxRow=offsetRow+len(values)                            # maxRow is the final length
      if maxRow>self._meta["length"]: self._meta["length"]=maxRow
    self._adjustTable(notifyFields=False)                     # adjusts both the table and the fieldMap according to fieldNames
    if values!=None:
      self._table[offsetRow:maxRow,columnIndex]=values
    if notify:
      self.notify("names",self._meta["fieldNames"])
      if values!=None: self.notify("commit")
  
  #################
  # row management
  #################

  def row(self):
    """
    Returns the current row
    """
    return self.rowAt(self._meta["index"])

  def rowAt(self,index):
    """
    Returns a row at a given index
    """
    if index != None and index < len(self):
      return self._table[index,:]

  def setIndex(self,index):
    """
    Synonym for goTo
    """
    self.goTo(self,index)
    
  def goTo(self,row =0):
    """
    Sets the current row index to a given index comprised between 0 (first element) and length (first outside row)
    If row not given, goes to first element (index 0)
    """
    if row <= self._meta["length"]:
      self._meta["index"]= row

  def goToEnd(self):
    """
    Sets the current row index to datacube length (first outside row)
    """
    self._meta["index"]= self._meta["length"]
          
  def clearRow(self):
    """
    Sets all values in the current row to 0
    """
    if self._meta["index"] != None:
      for i in range(0,len(self._table[self._meta["index"],:])):
        self._table[self._meta["index"],i] = 0
    debugDC2('datacube.clearRow with datacube ',self.name(),' notifying "clearRow"')
    self.notify("clearRow")
  
  def removeRow(self,row,notify=False):
    """
    Removes a given row from the datacube.
    """
    if row < self._meta["length"]:
      self._table[row:-1,:] = self._table[row+1:,:] 
      self._meta["length"] -= 1
    if self._meta["index"] >= row:
      self._meta["index"]-=1
    debugDC2('datacube.removeRow with datacube ',self.name(),' notifying ""removeRow"" with row=',row)
    if notify:
      self.notify("commit",row)
    
  def removeRows(self,rows,notify=False):
    """
    Removes a list of rows from the datacube.
    """
    sortedRows = reversed(sorted(rows)) # important to reverse for sequential removing
    for row in sortedRows:
      self.removeRow(row,notify=False)
      if notify: self.notify("commit",row)

  def addRow(self,notify=False):
    debugDC2(self._meta["name"],'.addRow(notify=',notify,')')
    self.commit(rowIndex=len(self),gotoNextRow=False)

  def insertRow(self,rowIndex=None,before=True,notify=False,commit=False,**keys):
    """
    Insert a row before or after a given row index, or at the current index if index=None.
    Then sets the variables.
    Then sends a "commit" notification if notify is true.
    Important: This function does not change the datacube's current row index unless commit is explicitely set to true.
      If commit, the current row index becomes the row after the insertion and not the last row.
      Note: changing the datacube's current row index with commit can be dangerous if several callers update the datacube simultaneously. 
    """
    str1=''
    for key in keys:  str1=str1+key+"="+str(keys[key])+','
    debugDC2(self._meta["name"],'.insertRow(rowIndex=',rowIndex,',before=',before,',notify=',notify,',commit=',commit,str1,')')
    oldIndex=self._meta["index"]
    if rowIndex==None: index=self._meta["index"]
    elif rowIndex<0:index=self._meta["length"]+rowIndex
    else: index=rowIndex
    if not before: index+=1
    if index<self._meta["length"]:
      self.extendTo(rowIndex=self._meta["length"])         # extend datacube table if needed
      self._table[index+1:,:] = self._table[index:-1,:] # copy and paste one row below
    self.set(rowIndex=index,**keys)                     # call set without propagating notify and commit (managed directly below)
    if oldIndex>=index:self._meta["index"]+=1           # by default the data pointed to by index are the same as before 
    if commit: self.commit(rowIndex=index)              # if commit is forced, current row becomas index+1 (dangerous)
    elif notify: self.notify("commit",index)            # notification sent

  def insertAt(self,index,before=True,**keys):
    """
    OBSOLETE: USE insertRow INSTEAD. Maintained for compatibility issue
    """
    self.insertRows(rowIndex=index,before=before,**keys)

  def insertRows(self,rowIndex=None,before=True,notify=False,commit=False,numberOfRows=1,**keys):
    """
    Insert a series of adjacent rows before or after a given row index, or at the current index if index=None.
    """
    str1=''
    for key in keys:  str1=str1+key+"="+str(keys[key])+','
    debugDC2(self._meta["name"],'.insertRows(rowIndex=',rowIndex,',before=',before,',numberOfRows=',numberOfRows,',notify=',notify,',commit=',commit,str1,')')
    for i in range(numberOfRows):
      self.insertRow(rowIndex=rowIndex+i,before=before,notify=False,commit=False,**keys)
    if commit: self.commit()              # if commit is forced, current row becomes index+1 (dangerous)
    elif notify: self.notify("commit")  # notification sent
      
  def extendTo(self,rowIndex=None,reserve=0,extendLength=False):
    """
    Extends the table length to index+1+reserve, and the datacube length to=index+1 if extendLength is true.
    By default extendLength is false and the length of the datacube is not changed.
    (one usually extends the length with commit).
    """
    debugDC2('In ',self._meta["name"],'extendTo(rowIndex=',rowIndex,',reserve=',reserve,',extendLength=',extendLength,')')
    if rowIndex==None: rowIndex=self._meta["index"]
    self._adjustTable(rowIndex=rowIndex,reserve=reserve,notifyFields=False)
    if extendLength and rowIndex>=self._meta["length"]:
      self._meta["length"] = rowIndex+1


  def set(self,rowIndex=None,notify=False,commit=False,columnOrder=None,extendLength=False,**keys):
    """
    Creates new column if needed and sets variables in the row of index rowIndex (or current row if rowIndex=None).
    rowIndex<0 means index=length+1+rowIndex so that -1 corresponds to row after the end.
    Creates new rows and new columns if needed.
    Allows to force the order of column creation using keyword 'columnOrder' with a value equal to a list of column names.
      All forced columns are inserted first in the imposed order while other ones are inserted in random order by python (usually alphabetic order).
      Example: Starting from an empty datacube set(d=0,c=1,b=2,a=3,columnOrder=['b','a']) creates the columns 'b','a','c','d'.
    Sends a "commit" notification if notify is true or do a true commit() if commit is set to True.
    Important: This function does not change the datacube's current row index unless commit is explicitely set to true.
      Note: changing the datacube's current row index is dangerous if several callers edit the datacube simultaneously.
    """ 
    str1=''
    for key in keys:  str1=str1+key+"="+str(keys[key])+','
    debugDC2('In ',self._meta["name"],'.set(rowIndex=',rowIndex,',notify=',notify,',commit=',commit,',columnOrder=',columnOrder,',extendLength=',extendLength,str1,')') 
    specifiedKeys=[]
    if columnOrder:                                        # process first the keys of columnOrder (even if no specified value)
      for key in columnOrder:
        specifiedKeys.append(key)
    if keys:                                               # then append the other keys
      for key in keys:
        if key not in specifiedKeys:
          specifiedKeys.append(key)
    nameIndexDict=dict()
    i=0
    for key in specifiedKeys : 
      nameIndexDict[key]=i
      i++
    newFields,colIndex=self._addFields(nameIndexDict,adjustTable=False) # then call _addFields to add the new fields (column names) but still wait before adjustTabl
    if rowIndex==None : rowIndex = self._meta["index"]     # defines the row index for the set
    elif rowIndex<0 :  rowIndex = self._meta["length"]+rowIndex
    if rowIndex<0 : rowIndex=0
    self.extendTo(rowIndex=rowIndex,reserve=500,extendLength=extendLength) # now adjustTable to correct the fieldmap and increase the table length

    newData=False
    for key in keys:                                        # for each key                           
      newData=True
      columnIndex = self._meta["fieldMap"][key]                 
      self._table[rowIndex,columnIndex] = keys[key]         # add the corresponding value in the table
    if newFields:
      debugDC2('datacube ',self.name(),'notifying "names"=',self._meta["fieldNames"])
      self.notify("names",self._meta["fieldNames"])  # send only one notification if new names have been added
    if newData:
      if commit: self.commit(rowIndex=rowIndex)                  # and commit if requested
      elif notify:
        debugDC2('datacube ',self.name(),'notifying "commit" with index=',rowIndex)
        self.notify("commit",rowIndex)

  def setAt(self,index,**keys):
    """
    OBSOLETE: USE THE MORE POWERFUL METHOD set INSTEAD.
    Sets a set of variables at a given index, keeping the current index unchanged.
    """
    oldIndex = self._meta["index"]
    self._meta["index"] = index
    self.set(**keys)
    self.commit()
    self._meta["index"] = oldIndex

  def commit(self,rowIndex=None,gotoNextRow=True):
    """
    Validates the indicated or current row, i.e. extend the length of the datacube up to this row if necessary.
    Goes to the next row if gotoNextRow is True.
    Then notifies the commit of this row.
    VERY IMPORTANT: When several clients are editing the database at the same time, only one should use commit with the default gotoNextRow=True,
    otherwise they compete for the row index of the next write !!!
    """
    debugDC2('In', self._meta["name"],'.commit (rowIndex=',rowIndex,',gotoNextRow=',gotoNextRow,')')
    if rowIndex==None: rowIndex=self._meta["index"]
    if rowIndex>=self._meta["length"]: self.extendTo(rowIndex=rowIndex,extendLength=True)
    if gotoNextRow : self._meta["index"]=rowIndex+1 # possibly 1st row outside datacube
    self.notify("commit",rowIndex)

  def sortBy(self,column,reverse = False):
    """
    Sorts the datacube by a given variable
    """
    col = list(self.column(column))
    indices = zip(col,range(0,len(col)))
    sortedValues,sortedIndices = zip(*sorted(indices,reverse = reverse))
    self._table = self._table[sortedIndices,:]
    #To do: Add sorting of children!?
    debugDC2('datacube.sortBy with datacube ',self.name(),' notifying "sortBy" with column=',column)
    self.notify("sortBy",column)

  def search(self,**kwargs):
    """
    Searches all rows with a given combination of values.
    Example: datacube.search(a = 4, b = -3,c = 2,start = 0) will return the index of all rows
    where a == 4, b == -3, c == 2,starting at index 0.
    If no row matches the given criteria, search will return [].
    """
    keys = kwargs.keys()
    cols = dict()
    foundRows = []
    dtype = self.table().dtype
    for key in keys:                      # return [] if one of the requested column does not exist
      cols[key] = self.column(key)
      if cols[key] == None:
        return []
    for i in range(0,len(cols[keys[0]])):
      found = True
      for key in keys:
        if not allclose(array(kwargs[key],dtype=dtype), cols[key][i]):
          found = False
          break
      if found:
        foundRows.append(i)
    return foundRows
  

#**************************************************************************
# Methods for children management    
#**************************************************************************
    
  def removeChildren(self,cubes):
    """
    Removes a list of children from the datacube.
    """
    for cube in cubes:
      self.removeChild(cube)
  
  def removeChild(self,childCube,deleteChildCube = False):
    """
    Removes a given child (defined by its cube) from the datacube and delete it from memory if deleteChildCube =True.
    Deletion propagates to all descendants.
    """
    for child in self._children:
      if child.datacube() == childCube:
        child.datacube().setParent(None)
        self._children.remove(child)                 # remove from the list of children in the parent
        del child                                    # remove child from memory (does not delete the datacube itself)                              
        self.notify("removeChild",childCube)         # notify of the deletion
        if deleteChildCube:                          # if child cube and its descendents to be deleted
          for child2 in childCube._children:         # call recursively the function to delete descendents
            childCube.removeChild(child2._datacube,deleteChildCube = deleteChildCube)
          del deleteChildCube                        # and delete the child cube   
    return        

  def addChild(self,cube,**kwargs):
    """
    Adds a child (defined by its cube) to the datacube.
    If its raw attribute is not passed in kwargs, adds it to the child with value equal to the current row index of the datacube
    """
    if cube == self:
      raise Exception("Cannot add myself as child!")
    if cube in self.children():
      raise Exception("Datacube is already a child!")
    attributes = kwargs
    if not "row" in attributes:
      attributes["row"] = self.index()    # a datacube added as a child always have a 'row' attribute, which is set to the current row index on adding
    item = ChildItem(cube,attributes)
    if cube.parent() != None:             # a datacube can be the child of only one parent
      cube.parent().removeChild(cube)
    cube.setParent(self)
    self._children.append(item)
    debugDC2('datacube.addChild with datacube ',self.name(),' notifying "addChild" with cube=',cube)
    self.notify("addChild",cube)
    self.setModified()

  def attributesOfChildren(self,common=False):
    """
    Returns attribute keys of all children if common=False, or common to all children if common = True.
    """
    attributeKeys=[]
    childrenCubes=self.children()    #actually children cubes and not children
    if len(childrenCubes)>0:
      attributeKeys=set(self.attributesOfChild(childrenCubes[0]).keys()) # initialize
      for child in childrenCubes[1:-1]:
        keys=set(self.attributesOfChild(child).keys())
        if not common:
          attributeKeys |= keys      # Union and update
        else:
          attributeKeys &= keys      # Intersection and update
    return list(attributeKeys)

  def attributesOfChild(self,childCube):
    """
    Returns the attributes of a child defined by its cube
    """
    childrenCubes=self.children()         #actually children cubes and not children
    if childCube in childrenCubes:
      i=childrenCubes.index(childCube)
      return dict(self._children[i].attributes())  # return a copy (dict) to protect the attributes 
    raise AttributeError("Child not found!")
    
  def setChildAttributes(self,child,**kwargs):
    """
    Set a child attribute
    """
    attributes = self.attributesOfChild(child)
    for key in kwargs:
      attributes[key] = kwargs[key]

  def children(self,**kwargs):
    """
    Returns the list of all children datacubes verifying all the attributes passed in kwargs.
    Returns all children cubes if no kwargs are passed.
    """
    if kwargs == {}:
      return map(lambda x:x.datacube(),self._children)
    else:
      children = []
      for item in self._children:
        deviate = False
        for key in kwargs:
          if (not key in item.attributes()) or item.attributes()[key] != kwargs[key]:
            deviate = True
            continue
        if not deviate:
          children.append(item.datacube())
      return children             
  
  #*******************************************************************************
  # Methods to load from and save to files
  #*******************************************************************************

  def loadTable(self,filename,delimiter = "\t",guessStructure = False):
    """
    Loads the table of the datacube from a text file
    """
    file = open(filename,"r")
    contents = file.read()
    file.close()
    lines = contents.split("\n")
    lines=[line for line in lines if len(line.translate(None, ' \t\n'))!=0]
    if guessStructure:
      self._meta["fieldNames"] = lines[0].split(delimiter)
      self._meta["length"] = len(lines)-1
      if lines[1].find("j") == -1:
        self._meta["dataType"] = float64
      else:
        self._meta["dataType"] = complex128
    self._table = zeros((len(lines[1:]),len(self._meta["fieldNames"])),dtype = self._meta["dataType"])
    self._meta["length"] = 0
    i = 0
    for line in lines[1:]:
      entries = line.split(delimiter)
      j = 0
      if line == "":
        continue
      for entry in entries:
        if entry != "":
          if self._meta["dataType"] == complex128:
            value = complex(entry)
          elif self._meta["dataType"] == bool:
            if entry == "False":
              value = 0
            else:
              value = 1
          else:
            value = float(entry)
          if j < len(self._meta["fieldNames"]) and i < self._table.shape[0]:
            self._table[i,j] = value
          j+=1
      self._meta["length"]+=1
      i+=1
          
  def loadFromHdf5(self,path,verbose = False):
    """
    Loads the datacube from a HDF5 file.
    """
    import h5py
    dataFile = h5py.File(path,"r")
    self.loadFromHdf5Object(dataFile,verbose = verbose)
    dataFile.close()
    
  
  def saveToHdf5(self,path = None,saveChildren = True,overwrite = False,forceSave = False,verbose = False):
    """
    Saves the datacube to a HDF5 file 
    """
    import h5py
    if path == None and self.filename() != None:
      path = self.filename()
      overwrite = True

    elif path == None and self.name() != None:
      path = self.name()+".hdf"
      
    if path == None:
      raise Exception("You must supply a filename!")
    
    if verbose:
      print "Creating HDF5 file at %s" % path
      
    dataFile = h5py.File(path,"w")
    
    self.saveToHdf5Object(dataFile,saveChildren,overwrite,forceSave,verbose = verbose)
    self._meta["modificationTime"] = os.path.getmtime(path)
    self.setFilename(path)

    dataFile.flush()
    dataFile.close()
  
    
  def loadFromHdf5Object(self,dataFile,verbose = False):
    """
    Loads the datacube from a HDF5 group
    """
    version = dataFile.attrs["version"]
    
    if version in ["0.1","0.2"]:
      self._meta = yaml.load(dataFile.attrs["meta"])
      self._parameters = yaml.load(dataFile.attrs["parameters"])
    
    if len(self)>0:   
      ds = dataFile["table"]
      self._table = empty(shape=ds.shape, dtype=ds.dtype)
      self._table[:] = ds[:]
    
    self._adjustTable(reserve=0,notifyFields=False)
    self._children = []
    
    for key in sorted(map(lambda x:int(x),dataFile['children'].keys())):
      child = dataFile['children'][str(key)]
      cube = Datacube()
      cube.loadFromHdf5Object(child)
      attributes = yaml.load(child.attrs["attributes"])
      self.addChild(cube,**attributes)
      
    return True

  def saveToHdf5Object(self,dataFile,saveChildren = True,overwrite = False,forceSave = False,verbose = False):
    """
    Saves the datacube to a HDF5 group
    """
    dataFile.attrs["version"] = Datacube.version
    dataFile.attrs["meta"] = yaml.dump(self._meta)
    dataFile.attrs["parameters"] = yaml.dump(self._parameters)
    
    if len(self)>0:
      dataFile.create_dataset('table',data = self.table())   

    childrenFile = dataFile.create_group("children")

    #We save the child cubes
    if saveChildren:
      cnt = 0
      for item in self._children:
        childFile = childrenFile.create_group(str(cnt))
        childFile.attrs["attributes"] = yaml.dump(item.attributes())
        child = item.datacube()
        child.saveToHdf5Object(childFile,verbose = verbose)
        cnt+=1
        
    self._unsaved = False
    return True

  def saveTable(self,filename,delimiter = "\t",header = None):
    """
    Saves the data table to a given file
    """
    file = open(filename,"w")
    headers = ""
    for name in self.names():
      headers+=name+"\t"
    headers = string.rstrip(headers)+"\n"
    if header != None:
      file.write(header)
    file.write(headers)
    s = self._table.shape
    for i in range(0,min(s[0],self._meta["length"])):
      line = ""
      for j in range(0,len(self._meta["fieldNames"])):
        numberstr = str(self._table[i,j])
        if numberstr[0] == '(':
          numberstr = numberstr[1:-1]
        line+=numberstr
        if j != len(self._meta["fieldNames"])-1:
          line+=delimiter
      line+="\n"
      file.write(line)
    file.close()
  
  def savetxt(self,path = None, absPath=None, saveChildren = True,overwrite = False,forceSave = False,allInOneFile = False, forceFolders=False):
    """
    Saves the datacube to a text file
    """
    if path == None and self.filename() != None:
      path = self.filename()
      overwrite = True
    elif path == None and self.name() != None:
      path = self.name()
    if path == None:
      raise Exception("You must supply a filename!")
    
    path = re.sub(r"\.[\w]{3}$","",path)
    directory = os.path.abspath(os.path.dirname(path))
    filename = os.path.split(path)[1]
    filename = self._sanitizeFilename(filename)
    #We determine the basename of the file to which we want to save the datacube.
    basename = filename
    
    cnt = 1

    if overwrite == False:
      while os.path.exists(directory+"/"+basename+".txt"):
        basename = filename+"-"+str(cnt)
        cnt+=1

    savename = basename+".txt"
    savepath = directory+"/"+savename
    parpath = directory+"/"+basename+".par"

    children=[]
    if float(Datacube.version)>="0.3" or forceFolders:
      print "saving in new version"
      if saveChildren:
        
        for i in range(0,len(self._children)):
          item = self._children[i]
          child = item.datacube()
          if child.name() != None:
            childfilename = basename+"-"+child.name()+("-%d" % (i))
          else:
            childfilename = basename+("-%d" % (i))
          if absPath==None:
            pathChild=os.path.abspath(os.path.dirname(savepath))+"/"+path+"/"+self.name()
          else:
            pathChild=absPath
          print pathChild
          if not os.path.exists(pathChild):
            os.mkdir(pathChild)
                
                
          childPath = child.savetxt(absPath=pathChild,saveChildren = saveChildren,overwrite = True,forceSave = forceSave,forceFolders=forceFolders)
          
          children.append({'attributes':item.attributes(),'path':childPath})
  
      if os.path.exists(savepath) and os.path.getmtime(savepath) <= self._meta["modificationTime"] and os.path.exists(parpath) and os.path.getmtime(parpath) <= self._meta["modificationTime"]:
        if self._unsaved == False and forceSave == False:
          return basename

    else:
      #We save the child cubes
      #print 'saving in old version'
      if saveChildren:
        for i in range(0,len(self._children)):
          item = self._children[i]
          child = item.datacube()
          if child.name() != None:
            childfilename = basename+"-"+child.name()+("-%d" % (i))
          else:
            childfilename = basename+("-%d" % (i))
          childPath = child.savetxt(directory+"/"+childfilename,saveChildren = saveChildren,overwrite = True,forceSave = forceSave)
          children.append({'attributes':item.attributes(),'path':childPath})
  
      if os.path.exists(savepath) and os.path.getmtime(savepath) <= self._meta["modificationTime"] and os.path.exists(parpath) and os.path.getmtime(parpath) <= self._meta["modificationTime"]:
        if self._unsaved == False and forceSave == False:
          return basename

    #We save the datacube itself

    self.setFilename(parpath)
    
    paramsDict = dict()
    paramsDict['version'] = Datacube.version
    paramsDict['meta'] = copy.copy(self._meta)
    paramsDict['parameters'] = self.parameters()
    paramsDict['children'] = children
    paramsDict['tablefilename'] = savename

    paramstxt = yaml.dump(paramsDict)

    if not allInOneFile:
      params = open(parpath,"w")
      params.write(paramstxt)
      params.close()
      self.saveTable(savepath)
    else:
      lines = paramstxt.split("\n")
      paramstxt = "#"+"\n#".join(lines)
      self.saveTable(savepath,header = paramstxt)

    self._unsaved = False
    self._meta["modificationTime"] = os.path.getmtime(savepath)

    return basename
  
  def erase(self):
    """
    Erase a datacube from HardDrive
    """
    filename=self.filename()
    
    for i in range(len(self._children)-1,-1,-1):
      self._children[i].datacube().erase()
    try:
      os.remove(filename)
      os.remove(filename[:-3]+'txt')
    except:
      raise
  
  def childrenAt(self,row):
    """
    Returns all child cubes at row [row]
    """
    return self.children(row = row)
      
  def _sanitizeFilename(self,filename):
    """
    Used to clean up the filename and remove all unwanted characters
    """
    filename = re.sub(r'\.','p',filename)    
    filename = re.sub(r'[^\=\_\-\+\w\d\[\]\(\)\s\\\/]','-',filename)
    return filename
    
  def save(self,filename,format = 'pickle'):
    """
    Dumps the datacube to a pickled string
    """
    self._resize((self._meta["length"],len(self._meta["fieldNames"])))
    f = open(filename,"wb")
    return pickle.dump(self,f)

  def load(self,filename):
    """
    Loads the datacube from a pickled file
    """
    f = open(filename,"rb")
    loaded = pickle.load(f)
    self.__dict__ = loaded.__dict__

  def loadstr(self,string):
    """
    loadstr(string)
    Load the datacube from a pickled string
    """
    loaded = pickle.loads(string)
    self.__dict__ = loaded.__dict__

  def loadtxt(self,path,format = 'yaml',loadChildren = True):
    """
    Loads the datacube from a text file
    """
  
    path = re.sub(r"\.[\w]{3}$","",path)
    params = open(path+".par","r")
    filename = os.path.split(path)[1]
    directory = os.path.abspath(os.path.dirname(path))
    data = yaml.load(params.read())          
    params.close()
    
    if "version" in data:
      version = data["version"]
    else:
      version = "undefined"
    
    guessStructure = False
    
    if version in ["0.1","0.2","0.3","0.4"]:
      self._meta = data["meta"]
      self._parameters = data["parameters"]
    elif version == "undefined":
      print "Undefined version, trying my best to load the datacube..."
      mapping = {"len":"length","index":"index","names":"fieldNames","name":"name","description":"description","tags":"tags","dtype":"dataType"}
      for key in mapping.keys():
        if key in data:
          self._meta[mapping[key]] = data[key]
      
    if "parameters" in data:
      self._parameters = data["parameters"]
    
    self._children = []

    if loadChildren:
      if version == "undefined" or version == "0.1":
        for key in data["children"]:
          try:
            for path in data["children"][key]:
              if not os.path.isabs(path):
                path = directory + "/" + path
              datacube = Datacube()
              datacube.loadtxt(path)
              attributes = {"row" : key}
              item = ChildItem(datacube,attributes)
            self._children.append(item)
          except:
            self.removeChild(datacube)
            print "cannot load 1 datacube"
      elif float(Datacube.version)>=0.2:                   
        for child in data['children']:
          try:
            datacube = Datacube()
            path = child["path"]
            if not os.path.isabs(path):
              path = directory + "/" + path
            datacube.loadtxt(path)
            self.addChild(datacube,**child["attributes"])
          except:
            self.removeChild(datacube)
            print "cannot load 1 datacube"

    tableFilename = directory+"/"+data['tablefilename']

    self.loadTable(tableFilename,guessStructure = guessStructure)
    self._meta["modificationTime"] = os.path.getmtime(directory+"/"+data['tablefilename'])

    self.setFilename(directory+"/"+filename+".par")

  #*******************************************************************************
  # Methods to plot in a Matplotlib figure
  #*******************************************************************************

  def plot(self,fig=None,x=None,y=None,ls='-',marker='o',color='b',**kwargs):
    # Implement a plot in a matplotlib figure
    """
    Plot a numeric datacube in a matplotlib figure.
    In case of complex numbers: Re[y] and Im[y] are plotted as a function of Re[x].
    - fig is an existing matplotlib figure or None (new figure);
    - x: the x column name, a list of x column names, None, or an empty list.
        If None, x=first column if more than two columns in the datacube or x=row index if only one column.
        If empty list [], x is the row index for all y columns
    - y: the y column name, a list of y column names, or None.
        If None, y=second column if more than two columns in the datacube or y=first column if only one column.
    - ls:the linestyle expressed as specified in Matplotlib.
    - marker: the marker style expressed as specified in Matplotlib
    - color: the color of the first curve (automatically incremented if several curves in a single call)
    - kwargs: unused named arguments
    """
    try:
      from matplotlib import pyplot as plt
    except:
      print 'Error Cannot load pyplot from Matplolib module'
      return
    numberTypes=(int_,intc,intp,int8,int16,int32,int64,uint8,uint16,uint32,uint64,float_,float16,float32,float64)
    complexTypes=(complex_,complex64,complex128)
    colors=['b','g','r','c','m','k']
    if not color in colors: colors.insert(0,color)

    length=self._meta["length"]
    names=self._meta["fieldNames"]
    type=self._meta["dataType"]
    
    # give up if no possible plot
    giveup= type not in numberTypes and type not in complexTypes or length==0
    if giveup:
      print "Warning from Datacube.plot(): datacube is empty or not numeric"
      return
    # filter the x and y names
    def filter(t):
      if t and isinstance(t, basestring):
        if t in names: t=[t]                  # replace a string that is not an existing name by None
        else:
          t=None
          print "Warning from Datacube.plot():',t,' is not a valid column name"
      elif t and isinstance(t, list):         # remove all non existing names from a list
        for ti in t: 
          if ti not in names: t.remove(ti)
        if len(t)==0:
          t=None                              # None if empty list
          print "Warning from Datacube.plot():',t,' is not a list with valid column names" 
      else:
        t=None                                # None in all other cases and warning message 
        print "Warning from Datacube.plot(): x or y is neither None, nor a string nor a list" 
      return t
    x=filter(x); y=filter(y)
    # replace None by a single default column
    if y==None:
      if x==None:                             # None,None more than 2 columns => x y first and second columns
        if length>=2 :
          x=[self.columnName(0)]  
          y=[self.columnName(1)]
        else:                                 # None,None only 1 column => x y row index and first column
          x=['row index']
          y=[self.columnName(0)]
      else:
        for name in names:                    # x,None => y = first non x column or row index
          if name not in x:
            y=[name]
            break;
          if y==None: y=['row index']
    elif x==None:                             # None, y=> x first column if non y or row index
      if self.columnName(0) not in y: x=[self.columnName(0)]
      else: x=['row index']
    # builds x-y name pairs
    plots=[]
    lx=len(x);ly=len(y)
    for i in range(max(lx,ly)): plots.append([x[i % lx],y[i % ly]])
    #% function to build columns
    def colFunc(name,l):
      if name=='row index': return range(l)
      else : return self.column(name)
    def colsFunc(namesB):
      name1,name2=namesB
      l=0
      if name1=='row index':  l=len(self.column(name1))
      elif name2=='row index':  l=len(self.column(name2))
      return [colFunc(name1,l),colFunc(name2,l)]
    debugDC2('plots = ',plots)
    # build figure
    if not fig: fig=plt.figure(); leg=False
    else : leg=True
    pl1 = fig.add_subplot(111)
    pl1.set_title(self.name())
    xLabel=pl1.get_xlabel();yLabel=pl1.get_ylabel();
    colorIndex=colors.index(color)
    for i in range(len(plots)):
      colori=colors[colorIndex]
      xCol,yCol=colsFunc(plots[i])
      xName,yName=plots[i]
      if len(xLabel)!=0:  xLabel+=', ';yLabel+=', ';
      if not type in complexTypes:
        plt.plot(xCol,yCol,linestyle=ls, marker=marker,color=colori,label=yName+'('+xName+')')
        xLabel+=xName;yLabel+=yName;
      else:
        xCol=xCol.real()
        plt.plot(xCol,yCol.real(),linestyle='-', marker=marker,color=colori,label=yName+'('+xName+')')
        plt.plot(xCol,yCol.imag(),linestyle='--', marker=marker,color=colori)
        xLabel+='Re('+xName+')';yLabel+='Re('+ yName + '),Im(' + yName + ')'
      colorIndex=(colorIndex+1) % len(colors)
    pl1.set_xlabel(xLabel)
    pl1.set_ylabel(yLabel)
    if not leg : leg =len(plots)>1
    if leg:pl1.legend()
    plt.show()
    return fig

  #*******************************************************************************
  # Methods to interact with a dataManager
  # (and not directly with the dataManager frontpanel)
  #*******************************************************************************

  def dataManager(self):
    """
    Gets the singleton dataManager loaded in the python environment
    """
    return DataManager()

  def toDataManager(self):
    """
    Adds the datacube to the dataManager
    """
    self.dataManager().addDatacube(self)

  def plotInDataManager(self,*args,**kwargs):
    """
    Call dataManager.plot() with the present datacube as first parameter and any other params.
    """
    self.dataManager().plot(self,*args,**kwargs)  # optional named parameters in version 0.4
  
  def addDefaultPlot(self,listOfVariableNames,replace=False):
    """
    Adds a default plot description to the list of default plot descriptions of the datacube.
    If replace=True, all previous default plot description are erased. 
    The list of descriptions of default plots is stored in datacube._parameters["defaultPlot"].
    It can be accessed through datacube.parameters()["defaultPlot"]
    A default plot description is a list ['xName','yName'] or ['xName','yName','zName'] for a 2d and 3d plot respectiely. 
    Default plot descriptions are used by the the datamanager plotters for plot requests that do not specify x,y (and z) variables
    """
    if self._parameters.has_key("defaultPlot") and  not replace:
      if listOfVariableNames not in self._parameters["defaultPlot"]:
        self._parameters["defaultPlot"].append(listOfVariableNames)
    else:
      self._parameters["defaultPlot"]= [listOfVariableNames]
    self.notify('names',self._meta['fieldNames'])

  #*******************************************************************************
  # Methods to interact with Igor software 
  #*******************************************************************************
  
  def sendToIgor(self,path="root:"):
    igorCom=IgorCommunicator()
    igorCom._app.visible=1
    root=igorCom._app.DataFolder("root")
    folderName=self.name()#path+self.name()
    while igorCom.dataFolderExists(path+folderName):
      print "'"+path+folderName +"' already exists"
      i+=1
      folderName=self.name()+"-"+str(i)

    igorCom.createDataFolder(path+"'"+folderName+"'")

    for column in self._meta["fieldNames"]:
      igorCom("Make /N=%i/D/O %s'%s':'%s'"%(len(self[column]),path,folderName,column))
      wave=root.Wave("%s'%s':%s"%(path,folderName,column))
      for i in range(0,len(self[column])):
        wave.SetNumericWavePointValue(i,self[column][i])
    filenameVariable="%s'%s':%s"%(path,folderName,"filename")
    igorCom(["String %s"%filenameVariable])
    igorCom([filenameVariable+"=\"%s\""%string.replace(self.filename(),"\\",":")])

    for c in self.children():
      c.sendToIgor(path=path+"'"+self.name()+"':")

    #cmd="Display %s vs %s"%("root:'"+folderName+"':'"+y+"'","root:'"+folderName+"':'"+x+"'")
    #print cmd     
    #igorCom(cmd)