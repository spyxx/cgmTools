#=================================================================================================================================================
#=================================================================================================================================================
#	objectFactory - a part of cgmTools
#=================================================================================================================================================
#=================================================================================================================================================
#
# DESCRIPTION:
#	Series of tools for finding stuff
#
# Keyword arguments:
# 	Maya
#
# AUTHOR:
# 	Josh Burton (under the supervision of python guru (and good friend) David Bokser) - jjburton@gmail.com
#	http://www.cgmonks.com
# 	Copyright 2011 CG Monks - All Rights Reserved.
#
# CHANGELOG:
#	0.1 - 02/09/2011 - added documenation
#   0.11 - 04/04/2011 - added cvListSimplifier
#
# FUNCTION KEY:
#   1) ????
#   2) ????
#   3) ????
#
#=================================================================================================================================================

import maya.cmds as mc
import maya.mel as mel
from cgm.lib.classes import NameFactory

from cgm.lib import (lists,
                     search,
                     attributes,
                     dictionary,
                     rigging,
                     settings,
                     guiFactory)


class ObjectFactory():
    """ 
    Initialized a maya object as a class obj
    """
    def __init__(self,obj):
        """ 
        Asserts objects existance and that it has a transform. Then initializes. 
        
        Keyword arguments:
        obj(string)        
        
        """
        ### input check
        assert mc.objExists(obj) is True, "'%s' doesn't exist" %obj

        self.parent = False
        self.children = False
        self.cgm = {}
        self.mType = ''

        self.update(obj)

    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # Base Functions
    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def isRef(self):
        if mc.referenceQuery(self.nameLong, isNodeReferenced=True):
            self.refState = True
            self.refPrefix = search.returnReferencePrefix(self.nameShort)
            return
        self.refState = False
        self.refPrefix = None
	
    def getCGMNameTags(self):
        """
        Get the cgm name tags of an object.
        """
	self.cgm['cgmName'] = search.findRawTagInfo(self.nameLong,'cgmName')
	self.cgm['cgmNameModifier'] =  search.findRawTagInfo(self.nameLong,'cgmNameModifier')
	self.cgm['cgmPosition'] =  search.findRawTagInfo(self.nameLong,'cgmPosition')
	self.cgm['cgmDirectionModifier'] =  search.findRawTagInfo(self.nameLong,'cgmDirectionModifier')
	self.cgm['cgmDirection'] =  search.findRawTagInfo(self.nameLong,'cgmDirection')
	self.cgm['cgmIterator'] =  search.findRawTagInfo(self.nameLong,'cgmIterator')
	self.cgm['cgmTypeModifier'] =  search.findRawTagInfo(self.nameLong,'cgmTypeModifier')
	self.cgm['cgmType'] =  search.findRawTagInfo(self.nameLong,'cgmType')
		

    def getAttrs(self):
        """ Stores the dictionary of userAttrs of an object."""
        self.userAttrsDict = attributes.returnUserAttrsToDict(self.nameLong) or {}
	self.userAttrs = mc.listAttr(self.nameLong, userDefined = True) or []
	self.attrs = mc.listAttr(self.nameLong) or []
	self.keyableAttrs = mc.listAttr(self.nameLong, keyable = True) or []
	
	self.transformAttrs = []
	for attr in 'translate','translateX','translateY','translateZ','rotate','rotateX','rotateY','rotateZ','scaleX','scale','scaleY','scaleZ','visibility','rotateOrder':
	    if mc.objExists(self.nameLong+'.'+attr):
		self.transformAttrs.append(attr)

    def getType(self):
        """ get the type of the object """
        self.mType = search.returnObjectType(self.nameLong)

    def getFamily(self):
        """ Get the parent, child and shapes of the object."""
        self.parent = search.returnParentObject(self.nameLong)
        self.children = search.returnChildrenObjects(self.nameLong)
        self.shapes = mc.listRelatives(self.nameLong,shapes=True)

    def getTransforms(self):
        """ Get transform information of the object. """
        self.rotateOrder = mc.getAttr(self.nameLong + '.rotateOrder')
        
    def getMatchObject(self):
        """ Get match object of the object. """
	matchObject = search.returnTagInfo(self.nameLong,'cgmMatchObject')
	
	if mc.objExists(matchObject):
	    return matchObject
	return False

    def storeNameStrings(self,obj):
        """ Store the base, short and long names of an object to instance."""
        buffer = mc.ls(obj,long=True)
        self.nameLong = buffer[0]
        buffer = mc.ls(obj,shortNames=True)        
        self.nameShort = buffer[0]
        if '|' in buffer[0]:
            splitBuffer = buffer[0].split('|')
            self.nameBase = splitBuffer[-1]
            return
        self.nameBase = self.nameShort

    def update(self,obj):
        """ Update the instance with current maya info. For example, if another function outside the class has changed it. """ 
        assert mc.objExists(obj) is True, "'%s' doesn't exist" %obj
        
        try:
	    self.transform = mc.ls(obj,type = 'transform',long = True) or False
	    self.storeNameStrings(obj) 
	    self.getType()
	    self.getFamily()
	    self.getCGMNameTags()
	    #self.getAttrs() 
	    self.isRef()
	    
	    self.transformAttrs = []
	    for attr in 'translate','translateX','translateY','translateZ','rotate','rotateX','rotateY','rotateZ','scaleX','scale','scaleY','scaleZ','visibility','rotateOrder':
		if mc.objExists(self.nameLong+'.'+attr):
		    self.transformAttrs.append(attr)
	    
	    return True
	except:
	    return False

    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # Attribute Functions
    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>        
    def store(self,attr,info,*a,**kw):
        """ Store information to an object in maya via case specific attribute. """
        attributes.storeInfo(self.nameLong,attr,info,*a,**kw)

    def remove(self,attr):
        """ Removes an attr from the maya object instanced. """
        if self.refState:
            return guiFactory.warning("'%s' is referenced. Cannot delete attrs"%self.nameShort)    	
        try:
            attributes.doDeleteAttr(self.nameLong,attr)
        except:
            guiFactory.warning("'%s.%s' not found"%(self.nameLong,attr))

    def copyRotateOrder(self,targetObject):
        """ Copy the rotate order from a target object to the current instanced maya object. """
        assert mc.objExists(targetObject) is True, "'%s' - target object doesn't exist" %targetObject    
        assert self.transform ,"'%s' has no transform"%obj	
        assert mc.ls(targetObject,type = 'transform'),"'%s' has no transform"%targetObject
        buffer = mc.getAttr(targetObject + '.rotateOrder')
        attributes.doSetAttr(self.nameLong, 'rotateOrder',buffer) 

    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    # Rigging Functions
    #>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>  
    def copyPivot(self,sourceObject):
        """ Copy the pivot from a source object to the current instanced maya object. """
        assert mc.objExists(sourceObject) is True, "'%s' - source object doesn't exist" %sourceObject
        assert self.transform ,"'%s' has no transform"%obj		
        assert mc.ls(sourceObject,type = 'transform'),"'%s' has no transform"%sourceObject
        rigging.copyPivot(self.nameLong,sourceObject)

    def doGroup(self,maintain=False):
        """
        Grouping function for a maya instanced object.
        
        Keyword arguments:
        maintain(bool) -- whether to parent the maya object in place or not (default False)
        
        """
        assert mc.ls(self.nameLong,type='transform'),"'%s' has no transform"%obj	
	
        group = rigging.groupMeObject(self.nameLong,True,maintain) 
        groupLong = mc.ls(group,long=True)
        self.update(groupLong[0]+'|'+self.nameBase)  


    def doName(self,sceneUnique=False):
        """
        Function for naming a maya instanced object using the cgm.NameFactory class.
        
        Keyword arguments:
        sceneUnique(bool) -- Whether to run a full scene dictionary check or the faster just objExists check (default False)
        
        """       
        if self.refState:
            return guiFactory.warning("'%s' is referenced. Cannot change name"%self.nameShort)
	
        buffer = NameFactory.doNameObject(self.nameLong,sceneUnique)
        if buffer:
            self.update(buffer)

    def doParent(self,p):
        """
        Function for parenting a maya instanced object while maintaining a correct object instance.
        
        Keyword arguments:
        p(string) -- Whether to run a full scene dictionary check or the faster just objExists check
        
        """  
        assert mc.objExists(p) is True, "'%s' - parent object doesn't exist" %p     
        assert self.transform,"'%s' has no transform"%obj	
	
        buffer = rigging.doParentReturnName(self.nameLong,p)
        self.update(buffer)  