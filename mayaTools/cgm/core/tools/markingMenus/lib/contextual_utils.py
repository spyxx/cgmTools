"""
------------------------------------------
contextual_utils: cgm.core.tools.markingMenus.lib.contextual_utils
Author: Josh Burton
email: jjburton@cgmonks.com
Website : http://www.cgmonks.com
------------------------------------------

"""
# From Python =============================================================
import copy
import re

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

# From Maya =============================================================
import maya.cmds as mc


from cgm.core import cgm_Meta as cgmMeta
from cgm.core.lib import name_utils as NAMES
from cgm.core.lib import search_utils as SEARCH

def get_list(context = 'selection', mType = None):
    """
    Get contextual data for updating a transform
    
    :parameters
        context(string): 
            selection
            children
            heirarchy
            scene
            buffer

    :returns
        list(list)
    """ 
    _str_func = "get_list"    
    _l_context = []
    _context = context.lower()
    
    log.debug("|{0}| >> context: {1} | mType: {2}".format(_str_func,_context,mType))  
    
    if _context == 'selection':
        log.debug("|{0}| >> selection mode...".format(_str_func))
        _l_context = mc.ls(sl=True)
    elif _context == 'scene':
        log.debug("|{0}| >> scene mode...".format(_str_func))        
        if mType is not None:
            _l_context = mc.ls(type=mType)
        else:
            raise Exception,"Really shouldn't use this without a specific object type..."
        
    elif _context == 'children':
        log.debug("|{0}| >> children mode...".format(_str_func)) 
        
        _sel = mc.ls(sl=True)
        for o in _sel:
            if mType:
                if mc.ls(o,type=mType):
                    _l_context.append(o)
            else:_l_context.append(o)
            
            if mType:
                try:_buffer = mc.listRelatives (o, allDescendents=True, type = mType) or []
                except:_buffer = []
            else:_buffer = mc.listRelatives (o, allDescendents=True) or []
            for o2 in _buffer:
                if o2 not in _l_context:
                    _l_context.append(o2)
       
    elif _context == 'heirarchy':
        log.debug("|{0}| >> heirarchy mode...".format(_str_func))  
        
        _sel = mc.ls(sl=True)
        for o in _sel:
            if mType:
                if mc.ls(o,type=mType):
                    _l_context.append(o)
            else:_l_context.append(o)
            
            _parents = SEARCH.get_all_parents(o)
            if _parents:
                root = _parents[-1]#...get the top of the tree
                if mType:
                    if mc.ls(root,type=mType):
                        _l_context.append(root)
                else:_l_context.append(root)   
                
                if mType:
                    try:_buffer = mc.listRelatives (root, allDescendents=True, type = mType) or []
                    except:_buffer = []
                    else:_buffer = mc.listRelatives (root, allDescendents=True) or []
                for o2 in _buffer:
                    if o2 not in _l_context:
                        _l_context.append(o2)
            else:
                if mType:
                    try:_buffer = mc.listRelatives (o, allDescendents=True, type = mType) or []
                    except:_buffer = []
                else:_buffer = mc.listRelatives (o, allDescendents=True) or []
                for o2 in _buffer:
                    if o2 not in _l_context:
                        _l_context.append(o2)                
                    
    else:
        log.warning("|{0}| >> context unkown: {1}...".format(_str_func,_context))        
        return False
    
    return _l_context

    
def set_attrs(self, attr = None, value = None, context = 'selection', mType = None):
    """
    Get data for updating a transform
    
    :parameters
        self(instance): cgmMarkingMenu

    :returns
        info(dict)
    """   
    _str_func = "set_attr"
    _context = context.lower()
    _l_context = get_list(_context, mType)
    
    log.debug("|{0}| >> attr: {1} | value: {2} | mType: {3} | context: {4}".format(_str_func,attr,value,mType,_context))             
        
    for o in _l_context:
        try:
            cgmMeta.cgmNode(o).__setattr__(attr,value)
        except Exception,err:
            log.error("|{0}| >> set fail. obj:{1} | attr:{2} | value:{3} | error: {4} | {5}".format(_str_func,NAMES.get_short(o),attr,value,err,Exception))
    
    mc.select(_l_context)
    return True

def select(context = 'selection', mType = None):
    """
    Get data for updating a transform
    
    :parameters
        self(instance): cgmMarkingMenu

    :returns
        info(dict)
    """   
    _str_func = "select"
    _context = context.lower()
    _l_context = get_list(_context, mType)
    log.debug("|{0}| >> List...".format(_str_func))   
    for o in _l_context:
        log.debug("|{0}| >> {1}".format(_str_func,o))   
        
    if not _l_context:
        log.warning("|{0}| >> no objects found. context: {1} | mType: {2}".format(_str_func,context,mType))
        return False
        
    mc.select(_l_context)