import maya.cmds as mc
import maya.mel as mel
from cgm.lib.classes import NameFactory

import copy

from cgm.lib import (lists,
                     search,
                     attributes,
                     dictionary,
                     rigging,
                     settings,
                     guiFactory)

#=========================================================================      
# R9 Stuff - We force the update on the Red9 internal registry  
#=========================================================================      
from Red9.core import Red9_Meta as r9Meta
reload(r9Meta)
from Red9.core.Red9_Meta import *

r9Meta.registerMClassInheritanceMapping()    
#=========================================================================

#Mark, any thoughts on where to store important defaults
drawingOverrideAttrsDict = {'overrideEnabled':0,
                            'overrideDisplayType':0,
                            'overrideLevelOfDetail':0,
                            'overrideShading':1,
                            'overrideTexturing':1,
                            'overridePlayback':1,
                            'overrideVisibility':1}

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>   
# cgmMeta - MetaClass factory for figuring out what to do with what's passed to it
#=========================================================================    
class cgmMeta(MetaClass):
    def __new__(cls, node = None, name = None, nodeType = None,*args,**kws):
        '''
        Idea here is if a MayaNode is passed in and has the mClass attr
        we pass that into the super(__new__) such that an object of that class
        is then instantiated and returned.
        '''
        doName = None
        objectFlags = ['cgmObject','object','obj','transform']
            
        if not node and name: 
            node = name
        if not node and nodeType:
            node = True # Yes, make the sucker
        if node and not name:
            doName = node
            
        #If the node doesn't exists, make one 
        #==============           
        if node and not mc.objExists(node):#If we have a node and it exists, we'll initialize. Otherwise, we need to figure out what to make
            if nodeType in objectFlags:
                node = mc.createNode('transform')
                log.info("Created a transform")
            elif nodeType != 'network':
                log.info("Trying to make a node of this type '%s'"%nodeType)
                node = mc.createNode(nodeType)
            else:
                log.info("Make default node")
                
        if name and node != name:
            node = mc.rename(node, name)
        elif doName:
            node = mc.rename(node,doName)
            
        log.debug("In MetaFactory.__new__ Node is '%s'"%node)
        log.debug("In MetaFactory.__new__ Name is '%s'"%name) 
        log.debug("In MetaFactory.__new__ nodeType is '%s'"%nodeType)   
        
        #Process what to do with it
        #==============             
        mClass = attributes.doGetAttr(node,'mClass')
        if mClass:
            log.info("Appears to be a '%s'"%mClass)
            log.error("Specialized processing not implemented, initializing as...")
            
        if mc.ls(node,type='transform'):
            log.info("Appears to be a transform, initializing as cgmObject")
            return cgmObject(name = name, node = node)          
        else:
            log.info("Appears to be a '%s'. Initializing as cgmNode"%search.returnObjectType(node))  
            return cgmNode(name = name, node = node)    
          
        return False
            
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>   
# cgm Node
#=========================================================================    
class cgmNode(MetaClass):#Should we do this?
    def __asdfasdfasdf__(cls, node = None, name = None, *args, **kws):        
        if not node and name: 
            node = name
        if node and not name:
            name = node

        if name and node != name:
            node = mc.rename(node, name)
                
        return super(cls.__class__, cls).__new__(cls)    
    
    def __init__(self,node = None, name = None,*args,**kws):
        """ 
        Utilizing Red 9's MetaClass. Intialized a node in cgm's system.
        """
        log.debug("In cgmNode.__init__ Node is '%s'"%node)
        log.debug("In cgmNode.__init__ Name is '%s'"%name) 
        
        super(cgmNode, self).__init__(node=node, name = name)
        self.update(self.mNode)
        
    def __bindData__(self):
        pass
    
    def __setattr__(self, attr, value):
        #Overloading until the functionality is what we need. For now, just handling locking
        try:
            MetaClass.__setattr__(self,attr,value)
            if attributes.doGetAttr(self.mNode,attr) != value  and self.hasAttr(attr):
                log.info("Setting '%s.%s' with MetaClass failed to set, attempting with cgm"%(self.mNode,attr) )               
                a = cgmAttr(self.mNode,attr,value = value)                
        except:
            if attr not in self.UNMANAGED and not attr=='UNMANAGED': 
                log.info("Setting '%s.%s' with MetaClass failed, attempting with cgm"%(self.mNode,attr) )               
                a = cgmAttr(self.mNode,attr,value = value)

    def addAttr(self, attr,attrType = False,value = None,enum = False,initialValue = None,lock = None,keyable = None, hidden = None,**kws):
        if attr not in self.UNMANAGED and not attr=='UNMANAGED':            
            cgmAttr(self.mNode, attrName = attr, attrType = attrType, value = value, enum = enum, initialValue = initialValue, lock=lock,keyable=keyable,hidden = hidden)
            object.__setattr__(self, attr, value)
            #super(cgmNode, self).__init__(node = self.mNode)         
            return True
        return False
            
    #=========================================================================      
    # Get Info
    #========================================================================= 
    def update(self,obj):
        """ Update the instance with current maya info. For example, if another function outside the class has changed it. """ 
        assert mc.objExists(obj) is True, "'%s' doesn't exist" %obj
        super(cgmNode, self).__init__(node = obj)         
        
        self.getRefState()

    def getRefState(self):
        """
        Get ref state of the object
        """	
        if mc.referenceQuery(self.mNode, isNodeReferenced=True):
            self.refState = True
            self.refPrefix = search.returnReferencePrefix(self.mNode)
            return [self.refState,self.refPrefix]
        self.refState = False
        self.refPrefix = None
        return {'referenced':self.refState,'prefix':self.refPrefix}
    
    def getCGMNameTags(self):
        """
        Get the cgm name tags of an object.
        """
        self.cgm = {}
        for tag in NameFactory.cgmNameTags:
            self.cgm[tag] = search.findRawTagInfo(self.mNode,tag)
        return self.cgm    
        
    def getAttrs(self):
        """ Stores the dictionary of userAttrs of an object."""
        self.userAttrsDict = attributes.returnUserAttrsToDict(self.mNode) or {}
        self.userAttrs = mc.listAttr(self.mNode, userDefined = True) or []
        self.attrs = mc.listAttr(self.mNode) or []
        self.keyableAttrs = mc.listAttr(self.mNode, keyable = True) or []

        self.transformAttrs = []
        for attr in 'translate','translateX','translateY','translateZ','rotate','rotateX','rotateY','rotateZ','scaleX','scale','scaleY','scaleZ','visibility','rotateOrder':
            if mc.objExists(self.mNode+'.'+attr):
                self.transformAttrs.append(attr)

    def getMayaType(self):
        """ get the type of the object """
        return search.returnObjectType(self.mNode)
    
    def doName(self,sceneUnique=False,nameChildren=False):
        """
        Function for naming a maya instanced object using the cgm.NameFactory class.

        Keyword arguments:
        sceneUnique(bool) -- Whether to run a full scene dictionary check or the faster just objExists check (default False)

        """       
        if self.refState:
            log.error("'%s' is referenced. Cannot change name"%self.mNode)
            return

        if nameChildren:
            buffer = NameFactory.doRenameHeir(self.mNode,sceneUnique)
            if buffer:
                self.update(buffer[0])

        else:
            buffer = NameFactory.doNameObject(self.mNode,sceneUnique)
            if buffer:
                self.update(buffer) 
    #=========================================================================                   
    # Attribute Functions
    #=========================================================================                   
    def doStore(self,attr,info,*a,**kw):
        """ Store information to an object in maya via case specific attribute. """
        attributes.storeInfo(self.mNode,attr,info,*a,**kw)

    def doRemove(self,attr):
        """ Removes an attr from the maya object instanced. """
        if self.refState:
            return guiFactory.warning("'%s' is referenced. Cannot delete attrs"%self.mNode)    	
        try:
            attributes.doDeleteAttr(self.mNode,attr)
        except:
            guiFactory.warning("'%s.%s' not found"%(self.mNode,attr))
             
    def copyNameTagsFromObject(self,target,ignore=[False]):
        """
        Get name tags from a target object (connected)
        
        Keywords
        ignore(list) - tags to ignore
        
        Returns
        success(bool)
        """
        assert mc.objExists(target),"Target doesn't exist"
        targetCGM = NameFactory.returnObjectGeneratedNameDict(target,ignore = ignore)
        didSomething = False
        
        for tag in targetCGM.keys():
            if tag not in ignore and targetCGM[tag] is not None or False:
                attributes.doCopyAttr(target,tag,
                                      self.mNode,connectTargetToSource=True)
                didSomething = True
        return didSomething
    
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>   
# cgmObject
#=========================================================================        
class cgmObject(cgmNode):
    def __new__(cls, node = None, name = None, *args, **kws):
        created = False
        
        if not node and name: 
            node = name
        if node and not name:
            name = node

        #If the node doesn't exists, make one 
        #==============           
        if node and not mc.objExists(node):#If we have a node and it exists, we'll initialize. Otherwise, we need to figure out what to make
            node = mc.createNode('transform')
            created = True
        if name and node != name:
            node = mc.rename(node, name)
        if not node:
            raise Exception, 'Logic broken must have an error by here'
        
        if created:log.info("Transform '%s' created!"%node)
        
        return super(cls.__class__, cls).__new__(cls)    
        
                
    def __init__(self,node = None, name = None,*args,**kws):
        """ 
        Utilizing Red 9's MetaClass. Intialized a object in cgm's system. If no object is passed it 
        creates an empty transform

        Keyword arguments:
        obj(string)     
        autoCreate(bool) - whether to create a transforum if need be
        """
        ### input check
        assert node is not None, "Must have node assigned"
        assert mc.objExists(node), "Node must exist"
               
        #log.info("'%s' created as a null." %obj)
            
        super(cgmObject, self).__init__(node=node, name = name)
        
        if len(mc.ls(self.mNode,type = 'transform',long = True)) == 0:
            log.error("'%s' has no transform"%self.mNode)
            raise StandardError, "The class was designed to work with objects with transforms"
        
        self.update(self.mNode)#Get intial info
        
    def __bindData__(self):pass
        #self.addAttr('test',2)
    #=========================================================================      
    # Get Info
    #=========================================================================                   
    def update(self,obj):
        """ Update the instance with current maya info. For example, if another function outside the class has changed it. """ 
        assert mc.objExists(obj) is True, "'%s' doesn't exist" %obj
        cgmNode.update(self,obj=obj)
        
        try:
            self.getFamily()
            self.transformAttrs = []
            for attr in 'translate','translateX','translateY','translateZ','rotate','rotateX','rotateY','rotateZ','scaleX','scale','scaleY','scaleZ','visibility','rotateOrder':
                if mc.objExists(self.mNode+'.'+attr):
                    self.transformAttrs.append(attr)
            return True
        except:
            log.debug("Failed to update '%s'"%self.mNode)
            return False
        
    def getFamily(self):
        """ Get the parent, child and shapes of the object."""
        self.parent = self.getParent()
        self.children = self.getChildren()
        self.shapes = self.getShapes()
        return {'parent':self.parent,'children':self.children,'shapes':self.shapes}
        
    def getParent(self):
        return search.returnParentObject(self.mNode) or False
    
    def getChildren(self):
        return search.returnChildrenObjects(self.mNode) or []
    
    def getShapes(self):
        return mc.listRelatives(self.mNode,shapes=True) or []

    def getMatchObject(self):
        """ Get match object of the object. """
        matchObject = search.returnTagInfo(self.mNode,'cgmMatchObject')
        if mc.objExists(matchObject):
            log.debug("Match object found")
            return matchObject
        return False

    
    #=========================================================================  
    # Rigging Functions
    #=========================================================================  
    def copyRotateOrder(self,targetObject):
        """ 
        Copy the rotate order from a target object to the current instanced maya object.
        """
        try:
            #If we have an Object Factory instance, link it
            targetObject.mNode
            targetObject = targetObject.mNode
            log.debug("Target is an instance")            
        except:	
            log.debug("Target is not an instance")
            assert mc.objExists(targetObject) is True, "'%s' - target object doesn't exist" %targetObject    
        assert self.transform ,"'%s' has no transform"%obj	
        assert mc.ls(targetObject,type = 'transform'),"'%s' has no transform"%targetObject
        buffer = mc.getAttr(targetObject + '.rotateOrder')
        attributes.doSetAttr(self.mNode, 'rotateOrder', buffer) 

    def copyPivot(self,sourceObject):
        """ Copy the pivot from a source object to the current instanced maya object. """
        try:
            #If we have an Object Factory instance, link it
            sourceObject.mNode
            sourceObject = sourceObject.mNode
            log.debug("Source is an instance")                        
        except:
            #If it fails, check that the object name exists and if so, initialize a new Object Factory instance
            assert mc.objExists(sourceObject) is True, "'%s' - source object doesn't exist" %sourceObject

        assert mc.ls(sourceObject,type = 'transform'),"'%s' has no transform"%sourceObject
        rigging.copyPivot(self.mNode,sourceObject)

    def doGroup(self,maintain=False):
        """
        Grouping function for a maya instanced object.

        Keyword arguments:
        maintain(bool) -- whether to parent the maya object in place or not (default False)

        """
        assert mc.ls(self.mNode,type='transform'),"'%s' has no transform"%self.mNode	
        
        rigging.groupMeObject(self.mNode,True,maintain)    

    def doParent(self,parent = False):
        """
        Function for parenting a maya instanced object while maintaining a correct object instance.

        Keyword arguments:
        parent(string) -- Target parent
        """       
        if parent == self.parent:
            return True
        
        if parent: #if we have a target parent
            try:
                #If we have an Object Factory instance, link it
                parent = parent.mNode
                log.debug("Parent is an instance")
            except:
                #If it fails, check that the object name exists and if so, initialize a new Object Factory instance
                assert mc.objExists(parent) is True, "'%s' - parent object doesn't exist" %parent    
            
            log.debug("Parent is '%s'"%parent)
            try:
                mc.parent(self.mNode,parent)
            except:
                log.debug("'%s' already has target as parent"%self.mNode)
                return False
            
        else:#If not, do so to world
            rigging.doParentToWorld(self.mNode)
            log.debug("'%s' parented to world"%self.mNode)                        
            
    def setDrawingOverrideSettings(self, attrs = None, pushToShapes = False):
        """
        Function for changing drawing override settings on on object

        Keyword arguments:
        attrs -- default will set all override attributes to default settings
                 (dict) - pass a dict in and it will attempt to set the key to it's indexed value ('attr':1}
                 (list) - if a name is provided and that attr is an override attr, it'll reset only that one
        """
        # First make sure the drawing override attributes exist on our instanced object
        for a in drawingOverrideAttrsDict:
            assert mc.objExists('%s.%s'%(self.mNode,a)),"'%s.%s' doesn't exist"%(self.mNode,a)

        #Get what to act on
        targets = [self.mNode]
        if pushToShapes:
            shapes = self.getShapes()
            if shapes:
                targets.extend(shapes)
        
        for t in targets:
            #Get to business
            if attrs is None or False:
                for a in drawingOverrideAttrsDict:
                    attributes.doSetAttr(t,a,drawingOverrideAttrsDict[a])
    
            if type(attrs) is dict:
                for a in attrs.keys():
                    if a in drawingOverrideAttrsDict:
                        try:
                            attributes.doSetAttr(t,a,attrs[a])
                        except:
                            raise AttributeError, "There was a problem setting '%s.%s' to %s"%(self.mNode,a,drawingOverrideAttrsDict[a])
                    else:
                        guiFactory.warning("'%s.%s' doesn't exist"%(t,a))
                        
            if type(attrs) is list:
                for a in attrs:
                    if a in drawingOverrideAttrsDict:
                        try:
                            attributes.doSetAttr(self.mNode,a,drawingOverrideAttrsDict[a])
                        except:
                            raise AttributeError, "There was a problem setting '%s.%s' to %s"%(self.mNode,a,drawingOverrideAttrsDict[a])
                    else:
                        guiFactory.warning("'%s.%s' doesn't exist"%(t,a))       
                        

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>   
# cgmAttr
#=========================================================================    
class cgmAttr(object):
    """ 
    Initializes a maya attribute as a class obj
    """
    attrTypesDict = {'message':['message','msg','m'],
                     'double':['float','fl','f','doubleLinear','doubleAngle','double','d'],
                     'string':['string','s','str'],
                     'long':['long','int','i','integer'],
                     'bool':['bool','b','boolean'],
                     'enum':['enum','options','e'],
                     'double3':['vector','vec','v','double3','d3']}    
    
    def __init__(self,objName,attrName,attrType = False,value = None,enum = False,initialValue = None,lock = None,keyable = None, hidden = None, *a, **kw):
        """ 
        Asserts object's existance then initializes. If 
        an existing attribute name on an object is called and the attribute type is different,it converts it. All functions
        ignore locks on attributes and will act when called regardless of target settings
        
        
        Keyword arguments:
        obj(string) -- must exist in scene or an cgmObject instance
        attrName(string) -- name for an attribute to initialize
        attrType(string) -- must be valid attribute type. If AttrFactory is imported, you can type 'print attrTypesDict'
        enum(string) -- default enum list to set on call or recall
        value() -- set value on call
        initialValue() -- only set on creation
        
        *a, **kw
        
        """
        ### input check
        try:
            #If we have an Object Factory instance, link it
            objName.mNode
            self.obj = objName
        except:
            #If it fails, check that the object name exists and if so, initialize a new Object Factory instance
            assert mc.objExists(objName) is True, "'%s' doesn't exist" %objName
            catch = cgmNode(objName)
            self.obj = catch
        
        self.form = attributes.validateRequestedAttrType(attrType)
        self.attr = attrName
        self.children = False
        initialCreate = False
        
        # If it exists we need to check the type. 
        if mc.objExists('%s.%s'%(self.obj.mNode,attrName)):
            log.debug("'%s.%s' exists"%(self.obj.mNode,attrName))
            currentType = mc.getAttr('%s.%s'%(self.obj.mNode,attrName),type=True)
            log.debug("Current type is '%s'"%currentType)
            if not attributes.validateAttrTypeMatch(attrType,currentType) and self.form is not False:
                if self.obj.refState:
                    log.error("'%s' is referenced. cannot convert '%s' to '%s'!"%(self.obj.mNode,attrName,attrType))                   
                self.doConvert(attrType)             
                
            else:
                self.attr = attrName
                self.form = currentType
                
        else:
            try:
                if self.form == False:
                    self.form = 'string'
                    attributes.addStringAttributeToObj(self.obj.mNode,attrName,*a, **kw)
                elif self.form == 'double':
                    attributes.addFloatAttributeToObject(self.obj.mNode,attrName,*a, **kw)
                elif self.form == 'string':
                    attributes.addStringAttributeToObj(self.obj.mNode,attrName,*a, **kw)
                elif self.form == 'long':
                    attributes.addIntegerAttributeToObj(self.obj.mNode,attrName,*a, **kw) 
                elif self.form == 'double3':
                    attributes.addVectorAttributeToObj(self.obj.mNode,attrName,*a, **kw)
                elif self.form == 'enum':
                    attributes.addEnumAttrToObj(self.obj.mNode,attrName,*a, **kw)
                elif self.form == 'bool':
                    attributes.addBoolAttrToObject(self.obj.mNode,attrName,*a, **kw)
                elif self.form == 'message':
                    attributes.addMessageAttributeToObj(self.obj.mNode,attrName,*a, **kw)
                else:
                    log.error("'%s' is an unknown form to this class"%(self.form))
                
                initialCreate = True
                
            except:
                log.error("'%s.%s' failed to add"%(self.obj.mNode,attrName))
         
        self.updateData(*a, **kw)
            
        if enum:
            try:
                self.setEnum(enum)
            except:
                log.error("Failed to set enum value of '%s'"%enum)        

        if initialValue is not None and initialCreate:
            self.set(initialValue)
          
        elif value is not None:
            self.set(value)
        
        if type(keyable) is bool:
            self.doKeyable(keyable)   
            
        if type(hidden) is bool:
            self.doHidden(hidden)
            
        if type(lock) is bool:
            self.doLocked(lock)
                  
    def __call__(self):
        return self.get()
    
    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # Base Functions
    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def updateData(self,*a, **kw):
        """ 
        Get's attr updated data       
        """     
        assert mc.objExists('%s.%s'%(self.obj.mNode,self.attr)) is True, "'%s.%s' doesn't exist" %(self.obj.mNode,self.attr)
        # Default attrs
        self.nameCombined = '%s.%s'%(self.obj.mNode,self.attr)        
        self.minValue = False
        self.maxValue = False
        self.defaultValue = False
        self.nameNice = mc.attributeQuery(self.attr, node = self.obj.mNode, niceName = True)
        self.nameLong = mc.attributeQuery(self.attr, node = self.obj.mNode, longName = True)
        self.nameAlias = False
        if mc.aliasAttr(self.nameCombined,q=True):
            self.nameAlias = mc.aliasAttr(self.nameCombined,q=True)
            
        self.get(*a, **kw)
        
        #>>> Parent Stuff
        pBuffer = mc.attributeQuery(self.attr, node = self.obj.mNode, listParent=True)
        if pBuffer is None:
            self.parent = False
        else:
            self.parent = pBuffer[0]
        self.children = mc.attributeQuery(self.attr, node = self.obj.mNode, listChildren=True)
        if self.children is None:
            self.children = False        
        self.siblings = mc.attributeQuery(self.attr, node = self.obj.mNode, listSiblings=True)
        if self.siblings is None:
            self.siblings = False    
        self.enum = False
        
        self.userAttrs = mc.listAttr(self.obj.mNode, userDefined = True) or []
        
        standardFlagsBuffer = attributes.returnStandardAttrFlags(self.obj.mNode,self.nameLong)
        standardDataBuffer = attributes.returnAttributeDataDict(self.obj.mNode,self.nameLong)
        
        #Check connections
        self.driver = attributes.returnDriverAttribute(self.nameCombined,False)
        self.driven = attributes.returnDrivenAttribute(self.nameCombined,False)
        
        self.numeric = standardFlagsBuffer.get('numeric')
        self.dynamic = standardFlagsBuffer.get('dynamic')
            
        self.locked = standardFlagsBuffer.get('locked')
        self.keyable = standardFlagsBuffer.get('keyable')
        self.hidden = standardFlagsBuffer.get('hidden')
         
        if self.dynamic:
            self.readable = standardFlagsBuffer.get('readable')
            self.writable = standardFlagsBuffer.get('writable')
            self.storable = standardFlagsBuffer.get('storable')
            self.usedAsColor = standardFlagsBuffer.get('usedAsColor')   
            
        #>>> Numeric 
        if self.numeric:
            bufferDict = attributes.returnNumericAttrSettingsDict(self.obj.mNode,self.nameLong)
            if bufferDict:
                self.maxValue = bufferDict.get('max')
                self.minValue = bufferDict.get('min')
                self.defaultValue = bufferDict.get('default')
                self.softMaxValue = bufferDict.get('softMax')
                self.softMinValue = bufferDict.get('softMin')
                self.rangeValue = bufferDict.get('range')
                self.softRangeValue = bufferDict.get('softRange')
            else:
                self.maxValue = False
                self.minValue = False
                self.defaultValue = False
                self.softMaxValue = False
                self.softMinValue = False
                self.rangeValue = False
                self.softRangeValue = False               
                           
        if self.form == 'enum':
            self.enum = standardFlagsBuffer.get('enum')
                
    
    def doConvert(self,attrType):
        """ 
        Converts an attribute type from one to another while preserving as much data as possible.
        
        Keyword arguments:
        attrType(string)        
        """
        self.updateData()
        if self.obj.refState:
            log.error("'%s' is referenced. cannot convert '%s' to '%s'!"%(self.obj.mNode,self.attr,attrType))                           

        if self.children:
            log.error("'%s' has children, can't convert"%self.nameCombined)
        keyable = copy.copy(self.keyable)
        hidden =  copy.copy(self.hidden)
        locked =  copy.copy(self.locked)
        storedNumeric = False
        if self.numeric and not self.children:
            storedNumeric = True
            minimum =  copy.copy(self.minValue)
            maximum =  copy.copy(self.maxValue)
            default =  copy.copy(self.defaultValue)
            softMin =  copy.copy(self.softMinValue)
            softMax =  copy.copy(self.softMaxValue)
        
        attributes.doConvertAttrType(self.nameCombined,attrType)
        self.updateData()
        
        #>>> Reset variables
        self.doHidden(hidden)
        self.doKeyable(keyable)        
        self.doLocked(locked)

        if self.numeric and not self.children and storedNumeric:
            if softMin is not False or int(softMin) !=0 :
                self.doSoftMin(softMin)
            if softMax is not False or int(softMax) !=0 :
                self.doSoftMax(softMax)            
            if minimum is not False:
                self.doMin(minimum)
            if maximum is not False:
                self.doMax(maximum)
            if default is not False:
                self.doDefault(default)
            
        log.info("'%s.%s' converted to '%s'"%(self.obj.mNode,self.attr,attrType))
            
    
    def set(self,value,*a, **kw):
        """ 
        Set attr value based on attr type
        
        Keyword arguments:
        value(varied)   
        *a, **kw
        """
        
        try:
            if self.children:
                log.info("'%s' has children, running set command on '%s'"%(self.nameCombined,"','".join(self.children)))
                
                for i,c in enumerate(self.children):
                    try:
                        cInstance = AttrFactory(self.obj.mNode,c)                        
                        if type(value) is list and len(self.children) == len(value): #if we have the same length of values in our list as we have children, use them
                            attributes.doSetAttr(cInstance.obj.mNode,cInstance.attr, value[i], *a, **kw)
                            cInstance.value = value[i]
                            self.value = value
                        else:    
                            attributes.doSetAttr(cInstance.obj.mNode,cInstance.attr, value, *a, **kw)
                            self.value = value
                    except:
                        log.debug("'%s' failed to set"%c)
                        
            elif self.form == 'message':
                if value != self.value:
                    self.doStore(value)
            elif value != self.value:
                attributes.doSetAttr(self.obj.mNode,self.attr, value, *a, **kw)
                self.value = value
        
        except:
            log.error("'%s.%s' failed to set '%s'"%(self.obj.mNode,self.attr,value))
        
        
    def get(self,*a, **kw):
        """ 
        Get and store attribute value based on attr type
        
        Keyword arguments:
        *a, **kw
        """     
        try:
            if self.form == 'message':
                self.value = attributes.returnMessageObject(self.obj.mNode,self.attr)
            else:
                self.value =  attributes.doGetAttr(self.obj.mNode,self.attr)
            return self.value
        except:
            log.info("'%s.%s' failed to get"%(self.obj.mNode,self.attr))
            
            
    def getMessage(self,*a, **kw):
        """ 
        Get and store attribute value as if they were messages. Used for bufferFactory to use a connected
        attribute as a poor man's attribute message function
        
        Keyword arguments:
        *a, **kw
        """   
        try:
            if self.form == 'message':
                self.value = attributes.returnMessageObject(self.obj.mNode,self.attr)
                if search.returnObjectType(self.value) == 'reference':
                    if attributes.repairMessageToReferencedTarget(self.obj.mNode,self.attr,*a,**kw):
                        self.value = attributes.returnMessageObject(self.obj.mNode,self.attr)                        
            else:
                self.value = attributes.returnDriverAttribute("%s.%s"%(self.obj.mNode,self.attr))

            log.info("'%s.%s' >Message> '%s'"%(self.obj.mNode,self.attr,self.value))
            return self.value
            
        except:
            log.error("'%s.%s' failed to get"%(self.obj.mNode,self.attr))
            
            
            
    def setEnum(self,enumCommand):
        """ 
        Set the options for an enum attribute
        
        Keyword arguments:
        enumCommand(string) -- 'off:on', 'off=0:on=2', etc
        """   
        try:
            if self.form == 'enum':
                if self.enum != enumCommand:
                    mc.addAttr ((self.obj.mNode+'.'+self.attr), e = True, at=  'enum', en = enumCommand)
                    self.enum = enumCommand
                    log.info("'%s.%s' has been updated!"%(self.obj.mNode,self.attr))
                
            else:
                log.warning("'%s.%s' is not an enum. Invalid call"%(self.obj.mNode,self.attr))
        except:
            log.error("'%s.%s' failed to change..."%(self.obj.mNode,self.attr))
            
    def doStore(self,infoToStore,convertIfNecessary = True):
        """ 
        Store information to an object. If the info exits as an object, it stores as a message node. Otherwise there are
        other storing methods.
        
        Keyword arguments:
        infoToStore(string) -- string of information to store
        convertIfNecessary(bool) -- whether to convert the attribute if it needs to to store it. Default (True)
        """   
        assert self.children is False,"This attribute has children. Can't store."

        if self.form == 'message':
            self.obj.doStore(self.attr,infoToStore)
            self.value = infoToStore
        elif convertIfNecessary:
            self.doConvert('message')
            self.updateData()
            self.obj.doStore(self.attr,infoToStore)                
            self.value = infoToStore
            
        #except:
          #  log.error("'%s.%s' failed to store '%s'"%(self.obj.mNode,self.attr,infoToStore))
            
    def doDelete(self):
        """ 
        Deletes an attribute
        """   
        try:
            attributes.doDeleteAttr(self.obj.mNode,self.attr)
            log.warning("'%s.%s' deleted"%(self.obj.mNode,self.attr))
            self.value = None
            return self.value
        
        except:
            log.error("'%s.%s' failed to delete"%(self.obj.mNode,self.attr))  
    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # Set Options
    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>                       
    def doDefault(self,value = None):
        """ 
        Set default settings of an attribute
        
        Keyword arguments:
        value(string) -- value or False to reset
        """   
        if self.numeric: 
            if value is not None:
                if self.children:
                    log.warning("'%s' has children, running set command on '%s'"%(self.nameCombined,"','".join(self.children)))
                    for c in self.children:
                        cInstance = AttrFactory(self.obj.mNode,c)                        
                        try:
                            mc.addAttr((cInstance.obj.mNode+'.'+cInstance.attr),e=True,defaultValue = value)
                            cInstance.defaultValue = value                                                        
                        except:
                            log.warning("'%s' failed to set a default value"%cInstance.nameCombined)                
                    self.defaultValue = value                            
                
                else:     
                    try:
                        mc.addAttr((self.obj.mNode+'.'+self.attr),e=True,defaultValue = value)
                        self.defaultValue = value
                    except:
                        log.warning("'%s.%s' failed to set a default value"%(self.obj.mNode,self.attr))       
                
    def doMax(self,value = None):
        """ 
        Set max value for a numeric attribute
        
        Keyword arguments:
        value(string) -- value or False to reset
        """ 
        if self.numeric and not self.children: 
            if value is False:
                try:
                    mc.addAttr((self.obj.mNode+'.'+self.attr),e=True,hasMaxValue = value)
                    self.maxValue = value
                    log.warning("'%s.%s' had it's max value cleared"%(self.obj.mNode,self.attr))                     
                except:
                    log.error("'%s.%s' failed to clear a max value"%(self.obj.mNode,self.attr))  
            
            elif value is not None:
                try:
                    mc.addAttr((self.obj.mNode+'.'+self.attr),e=True,maxValue = value)
                    self.maxValue = value
                except:
                    log.error("'%s.%s' failed to set a max value"%(self.obj.mNode,self.attr))
                
                
    def doMin(self,value = None):
        """ 
        Set min value for a numeric attribute
        
        Keyword arguments:
        value(string) -- value or False to reset
        """ 
        if self.numeric and not self.children: 
            if value is False:
                try:
                    mc.addAttr((self.obj.mNode+'.'+self.attr),e=True,hasMinValue = value)
                    self.minValue = value
                    log.warning("'%s.%s' had it's min value cleared"%(self.obj.mNode,self.attr))                     
                except:
                    log.error("'%s.%s' failed to clear a min value"%(self.obj.mNode,self.attr))
            
            
            elif value is not None:
                try:
                    mc.addAttr((self.obj.mNode+'.'+self.attr),e=True,minValue = value)
                    self.minValue = value
                except:
                    log.warning("'%s.%s' failed to set a default value"%(self.obj.mNode,self.attr))
                    
    def doSoftMax(self,value = None):
        """ 
        Set soft max value for a numeric attribute
        
        Keyword arguments:
        value(string) -- value or False to reset
        """ 
        if self.numeric and not self.children: 
            if value is False:
                try:
                    mc.addAttr((self.obj.mNode+'.'+self.attr),e=True,hasSoftMaxValue = 0)
                    self.softMaxValue = value
                    log.warning("'%s.%s' had it's soft max value cleared"%(self.obj.mNode,self.attr))                     
                except:
                    log.error("'%s.%s' failed to clear a soft max value"%(self.obj.mNode,self.attr))  
            
            elif value is not None:
                try:
                    mc.addAttr((self.obj.mNode+'.'+self.attr),e=True,softMaxValue = value)
                    self.softMaxValue = value
                except:
                    log.error("'%s.%s' failed to set a soft max value"%(self.obj.mNode,self.attr))
                    
    def doSoftMin(self,value = None):
        """ 
        Set soft min value for a numeric attribute
        
        Keyword arguments:
        value(string) -- value or False to reset
        """ 
        if self.numeric and not self.children: 
            if value is False:
                try:
                    mc.addAttr((self.obj.mNode+'.'+self.attr),e=True,hasSoftMinValue = 0)
                    self.softMinValue = value
                    log.warning("'%s.%s' had it's soft max value cleared"%(self.obj.mNode,self.attr))                     
                except:
                    log.error("'%s.%s' failed to clear a soft max value"%(self.obj.mNode,self.attr))  
            
            elif value is not None:
                try:
                    mc.addAttr((self.obj.mNode+'.'+self.attr),e=True,softMinValue = value)
                    self.softMinValue = value
                except:
                    log.error("'%s.%s' failed to set a soft max value"%(self.obj.mNode,self.attr))
        
    def doLocked(self,arg = True):
        """ 
        Set lock state of an attribute
        
        Keyword arguments:
        arg(bool)
        """ 
        assert type(arg) is bool, "doLocked arg must be a bool!"
        if arg:
            if self.children:
                log.info("'%s' has children, running set command on '%s'"%(self.nameCombined,"','".join(self.children)))
                for c in self.children:
                    cInstance = AttrFactory(self.obj.mNode,c)                                            
                    if not cInstance.locked:
                        mc.setAttr((cInstance.obj.mNode+'.'+cInstance.attr),e=True,lock = True) 
                        log.warning("'%s.%s' locked!"%(cInstance.obj.mNode,cInstance.attr))
                        cInstance.locked = True
                self.updateData()  
                
            elif not self.locked:
                mc.setAttr((self.obj.mNode+'.'+self.attr),e=True,lock = True) 
                log.warning("'%s.%s' locked!"%(self.obj.mNode,self.attr))
                self.locked = True
                
        else:
            if self.children:
                log.warning("'%s' has children, running set command on '%s'"%(self.nameCombined,"','".join(self.children)))
                for c in self.children:
                    cInstance = AttrFactory(self.obj.mNode,c)                                            
                    if cInstance.locked:
                        mc.setAttr((cInstance.obj.mNode+'.'+cInstance.attr),e=True,lock = False) 
                        log.warning("'%s.%s' unlocked!"%(cInstance.obj.mNode,cInstance.attr))
                        cInstance.locked = False
                self.updateData()  
                
            elif self.locked:
                mc.setAttr((self.obj.mNode+'.'+self.attr),e=True,lock = False)           
                log.warning("'%s.%s' unlocked!"%(self.obj.mNode,self.attr))
                self.locked = False
                
    def doHidden(self,arg = True):
        """ 
        Set hidden state of an attribute
        
        Keyword arguments:
        arg(bool)
        """ 
        assert type(arg) is bool, "doLocked arg must be a bool!"        
        if arg:
            if self.children:
                log.warning("'%s' has children, running set command on '%s'"%(self.nameCombined,"','".join(self.children)))
                for c in self.children:
                    cInstance = AttrFactory(self.obj.mNode,c)                                            
                    if not cInstance.hidden:
                        if cInstance.keyable:
                            cInstance.doKeyable(False)
                        mc.setAttr((cInstance.obj.mNode+'.'+cInstance.attr),e=True,channelBox = False) 
                        log.info("'%s.%s' hidden!"%(cInstance.obj.mNode,cInstance.attr))
                        cInstance.hidden = False
                
            elif not self.hidden:
                if self.keyable:
                    self.doKeyable(False)
                mc.setAttr((self.obj.mNode+'.'+self.attr),e=True,channelBox = False) 
                log.info("'%s.%s' hidden!"%(self.obj.mNode,self.attr))
                self.hidden = True

                
        else:
            if self.children:
                log.warning("'%s' has children, running set command on '%s'"%(self.nameCombined,"','".join(self.children)))
                for c in self.children:
                    cInstance = AttrFactory(self.obj.mNode,c)                                            
                    if cInstance.hidden:
                        mc.setAttr((cInstance.obj.mNode+'.'+cInstance.attr),e=True,channelBox = True) 
                        log.info("'%s.%s' unhidden!"%(cInstance.obj.mNode,cInstance.attr))
                        cInstance.hidden = False
                
            elif self.hidden:
                mc.setAttr((self.obj.mNode+'.'+self.attr),e=True,channelBox = True)           
                log.info("'%s.%s' unhidden!"%(self.obj.mNode,self.attr))
                self.hidden = False
                
                
    def doKeyable(self,arg = True):
        """ 
        Set keyable state of an attribute
        
        Keyword arguments:
        arg(bool)
        """         
        assert type(arg) is bool, "doLocked arg must be a bool!"        
        if arg:
            if self.children:
                log.warning("'%s' has children, running set command on '%s'"%(self.nameCombined,"','".join(self.children)))
                for c in self.children:
                    cInstance = AttrFactory(self.obj.mNode,c)                                            
                    if not cInstance.keyable:
                        mc.setAttr(cInstance.nameCombined,e=True,keyable = True) 
                        log.info("'%s.%s' keyable!"%(cInstance.obj.mNode,cInstance.attr))
                        cInstance.keyable = True
                        cInstance.hidden = False

                
            elif not self.keyable:
                mc.setAttr((self.obj.mNode+'.'+self.attr),e=True,keyable = True) 
                log.info("'%s.%s' keyable!"%(self.obj.mNode,self.attr))
                self.keyable = True
                self.hidden = False
                    
                
        else:
            if self.children:
                log.warning("'%s' has children, running set command on '%s'"%(self.nameCombined,"','".join(self.children)))
                for c in self.children:
                    cInstance = AttrFactory(self.obj.mNode,c)                                            
                    if cInstance.keyable:
                        mc.setAttr((cInstance.obj.mNode+'.'+cInstance.attr),e=True,keyable = False) 
                        log.info("'%s.%s' unkeyable!"%(cInstance.obj.mNode,cInstance.attr))
                        cInstance.keyable = False
                        if not mc.getAttr(cInstance.nameCombined,channelBox=True):
                            cInstance.updateData()
                            cInstance.doHidden(False)                
                
            elif self.keyable:
                mc.setAttr((self.obj.mNode+'.'+self.attr),e=True,keyable = False)           
                log.info("'%s.%s' unkeyable!"%(self.obj.mNode,self.attr))
                self.keyable = False
                if not mc.getAttr(self.nameCombined,channelBox=True):
                    self.updateData()
                    self.doHidden(False)
                    
    def doAlias(self,arg):
        """ 
        Set the alias of an attribute
        
        Keyword arguments:
        arg(string) -- name you want to use as an alias
        """     
        assert type(arg) is str or unicode,"Must pass string argument into doAlias"                
        if arg:
            try:
                if arg != self.nameAlias:
                    if mc.aliasAttr(arg,self.nameCombined):
                        self.nameAlias = arg
                else:
                    log.info("'%s.%s' already has that alias!"%(self.obj.mNode,self.attr,arg))
                    
            except:
                log.warning("'%s.%s' failed to set alias of '%s'!"%(self.obj.mNode,self.attr,arg))
                    
        else:
            if self.nameAlias:
                self.attr = self.nameLong                
                mc.aliasAttr(self.nameCombined,remove=True)
                self.nameAlias = False
                self.updateData()
                
                
    def doNiceName(self,arg):
        """ 
        Set the nice name of an attribute
        
        Keyword arguments:
        arg(string) -- name you want to use as a nice name
        """    
        assert type(arg) is str or unicode,"Must pass string argument into doNiceName"        
        if arg:
            try:
                mc.addAttr(self.nameCombined,edit = True, niceName = arg)
                self.nameNice = arg

            except:
                log.warning("'%s.%s' failed to set nice name of '%s'!"%(self.obj.mNode,self.attr,arg))
                    

    def doRename(self,arg):
        """ 
        Rename an attribute as something else
        
        Keyword arguments:
        arg(string) -- name you want to use as a nice name
        """            
        assert type(arg) is str or unicode,"Must pass string argument into doRename"
        if arg:
            try:
                if arg != self.nameLong:
                    attributes.doRenameAttr(self.obj.mNode,self.nameLong,arg)
                    self.attr = arg
                    self.updateData()
                    
                else:
                    log.info("'%s.%s' already has that nice name!"%(self.obj.mNode,self.attr,arg))
                    
            except:
                log.warning("'%s.%s' failed to rename name of '%s'!"%(self.obj.mNode,self.attr,arg))
                
    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # Connections and transfers
    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> 
    def returnCompatibleFromTarget(self,target,*a, **kw):
        """ 
        Attempts to make a connection from instanced attribute to a target
        
        Keyword arguments:
        target(string) - object or attribute to connect to
        *a, **kw
        """ 
        assert mc.objExists(target),"'%s' doesn't exist"%target
        
        return attributes.returnCompatibleAttrs(self.obj.mNode,self.nameLong,target,*a, **kw)
        
            
    
    def doConnectOut(self,target,*a, **kw):
        """ 
        Attempts to make a connection from instanced attribute to a target
        
        Keyword arguments:
        target(string) - object or attribute to connect to
        *a, **kw
        """ 
        assert mc.objExists(target),"'%s' doesn't exist"%target
        
        if '.' in target:           
            try:
                attributes.doConnectAttr(self.nameCombined,target)
            except:
                log.warning("'%s' failed to connect to '%s'!"%(self.nameCombined,target))  
                
        else:
            #If the object has a transform
            matchAttr = attributes.returnMatchNameAttrsDict(self.obj.mNode,target,[self.nameLong]) or []
            if matchAttr:
                #If it has a matching attribute
                try:
                    attributes.doConnectAttr(self.nameCombined,('%s.%s'%(target,matchAttr.get(self.nameLong))))
                except:
                    log.warning("'%s' failed to connect to '%s'!"%(self.nameCombined,target))
            else:
                print "Target object doesn't have this particular attribute"

 
                
    def doConnectIn(self,source,*a, **kw):
        """ 
        Attempts to make a connection from a source to our instanced attribute
        
        Keyword arguments:
        source(string) - object or attribute to connect to
        *a, **kw
        """ 
        assert mc.objExists(source),"'%s' doesn't exist"%source
               
        if '.' in source:           
            try:
                attributes.doConnectAttr(source,self.nameCombined)
            except:
                log.warning("'%s' failed to connect to '%s'!"%(source,self.nameCombined))  
                
        else:
            #If the object has a transform
            matchAttr = attributes.returnMatchNameAttrsDict(self.obj.mNode,source,[self.nameLong]) or []
            if matchAttr:
                #If it has a matching attribute
                try:
                    attributes.doConnectAttr(('%s.%s'%(source,matchAttr.get(self.nameLong))),self.nameCombined)
                except:
                    log.warning("'%s' failed to connect to '%s'!"%(source,self.nameCombined))
            else:
                print "Source object doesn't have this particular attribute"
                
    def doCopyTo(self,target, targetAttrName = None,  debug = True,*a,**kw):
        """                                     
        Replacement for Maya's since maya's can't handle shapes....blrgh...
        Copy attributes from one object to another as well as other options. If the attribute already
        exists, it'll copy the values. If it doesn't, it'll make it. If it needs to convert, it can.
        It will not make toast.
    
        Keywords:
        toObject(string) - obj to copy to
        targetAttrName(string) -- name of the attr to copy to . Default is None which will create an 
                          attribute oft the fromAttr name on the toObject if it doesn't exist
        convertToMatch(bool) -- whether to convert if necessary.default True        
        values(bool) -- copy values. default True
        incomingConnections(bool) -- default False
        outGoingConnections(bool) -- default False
        keepSourceConnections(bool)-- keeps connections on source. default True
        copyAttrSettings(bool) -- copy the attribute state of the fromAttr (keyable,lock,hidden). default True
        connectSourceToTarget(bool) useful for moving attribute controls to another object. default False
        
        RETURNS:
        success(bool)
        """
        assert mc.objExists(target),"'%s' doesn't exist"%target
        assert mc.ls(target,long=True) != [self.obj.mNode], "Can't transfer to self!"
        functionName = 'doCopyTo'
        
        convertToMatch = kw.pop('convertToMatch',True)
        values = kw.pop('values',True)
        incomingConnections = kw.pop('incomingConnections',False)
        outgoingConnections = kw.pop('outgoingConnections',False)
        keepSourceConnections = kw.pop('keepSourceConnections',True)
        copyAttrSettings = kw.pop('copyAttrSettings',True)
        connectSourceToTarget = kw.pop('connectSourceToTarget',False)
        connectTargetToSource = kw.pop('connectTargetToSource',False)  
        
        if debug:
            guiFactory.doPrintReportStart(functionName)
            log.info("AttrFactory instance: '%s'"%self.nameCombined)
            log.info("convertToMatch: '%s'"%convertToMatch)
            log.info("targetAttrName: '%s'"%targetAttrName)
            log.info("incomingConnections: '%s'"%incomingConnections)
            log.info("outgoingConnections: '%s'"%outgoingConnections)
            log.info("keepSourceConnections: '%s'"%keepSourceConnections)
            log.info("copyAttrSettings: '%s'"%copyAttrSettings)
            log.info("connectSourceToTarget: '%s'"%connectSourceToTarget)
            log.info("keepSourceConnections: '%s'"%keepSourceConnections)
            log.info("connectTargetToSource: '%s'"%connectTargetToSource)
            guiFactory.doPrintReportBreak()
            

                
        copyTest = [values,incomingConnections,outgoingConnections,keepSourceConnections,connectSourceToTarget,copyAttrSettings]
        
        if sum(copyTest) < 1:
            log.warning("You must have at least one option for copying selected. Otherwise, you're looking for the 'doDuplicate' function.")            
            return False

        if '.' in list(target):
            targetBuffer = target.split('.')
            if len(targetBuffer) == 2:
                attributes.doCopyAttr(self.obj.mNode,
                                      self.nameLong,
                                      targetBuffer[0],
                                      targetBuffer[1],
                                      convertToMatch = convertToMatch,
                                      values=values, incomingConnections = incomingConnections,
                                      outgoingConnections=outgoingConnections, keepSourceConnections = keepSourceConnections,
                                      copyAttrSettings = copyAttrSettings, connectSourceToTarget = connectSourceToTarget)               

            else:
                log.warning("Yeah, not sure what to do with this. Need an attribute call with only one '.'")
        else:
            attributes.doCopyAttr(self.obj.mNode,
                                  self.nameLong,
                                  target,
                                  targetAttrName,
                                  convertToMatch = convertToMatch,
                                  values=values, incomingConnections = incomingConnections,
                                  outgoingConnections=outgoingConnections, keepSourceConnections = keepSourceConnections,
                                  copyAttrSettings = copyAttrSettings, connectSourceToTarget = connectSourceToTarget)                                                 
        if debug:
            guiFactory.doPrintReportEnd(functionName)        
        #except:
        #    log.warning("'%s' failed to copy to '%s'!"%(target,self.nameCombined))          
            
    def doTransferTo(self,target):
        """ 
        Transfer an instanced attribute to a target with all settings and connections intact
        
        Keyword arguments:
        target(string) -- object to transfer it to
        *a, **kw
        """ 
        assert mc.objExists(target),"'%s' doesn't exist"%target
        assert mc.ls(target,type = 'transform',long = True),"'%s' Doesn't have a transform"%target
        assert self.obj.transform is not False,"'%s' Doesn't have a transform. Transferring this attribute is probably a bad idea. Might we suggest doCopyTo along with a connect to source option"%self.obj.mNode        
        assert mc.ls(target,long=True) != [self.obj.mNode], "Can't transfer to self!"
        assert '.' not in list(target),"'%s' appears to be an attribute. Can't transfer to an attribute."%target
        assert self.dynamic is True,"'%s' is not a dynamic attribute."%self.nameCombined
        
        #mc.copyAttr(self.obj.mNode,self.target.obj.mNode,attribute = [self.target.attr],v = True,ic=True,oc=True,keepSourceConnections=True)
        attributes.doCopyAttr(self.obj.mNode,
                              self.nameLong,
                              target,
                              self.nameLong,
                              convertToMatch = True,
                              values = True, incomingConnections = True,
                              outgoingConnections = True, keepSourceConnections = False,
                              copyAttrSettings = True, connectSourceToTarget = False)
        self.doDelete()

            

        
                                  
