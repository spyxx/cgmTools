# From Python =============================================================
import copy
import re
import time

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# From Maya =============================================================
import maya.cmds as mc

# From Red9 =============================================================
from Red9.core import Red9_Meta as r9Meta
from Red9.core import Red9_General as r9General

# From cgm ==============================================================
from cgm.core import cgm_General as cgmGeneral
from cgm.core.rigger.lib import module_Utils as modUtils

from cgm.core.cgmPy import validateArgs as cgmValid
from cgm.core import cgm_Meta as cgmMeta
from cgm.core import cgm_RigMeta as cgmRigMeta
from cgm.core.classes import GuiFactory as gui
from cgm.core.classes import SnapFactory as Snap
from cgm.core.classes import NodeFactory as NodeF
from cgm.core.lib import rayCaster as RayCast
from cgm.core.rigger import ModuleShapeCaster as mShapeCast
from cgm.core.rigger import ModuleControlFactory as mControlFactory
reload(mControlFactory)
from cgm.core.lib import nameTools
from cgm.core.rigger.lib import joint_Utils as jntUtils
from cgm.core.rigger.lib.Limb import (spine,neckHead,leg,clavicle,arm,finger)
from cgm.core.rigger.lib.Face import (eyeball,eyelids,eyebrow,mouthNose)

from cgm.lib import (cgmMath,
                     attributes,
                     deformers,
                     locators,
                     constraints,
                     modules,
                     nodes,
                     distance,
                     dictionary,
                     joints,
                     skinning,
                     rigging,
                     search,
                     curves,
                     lists,
                     )
reload(rigging)
l_modulesDone  = ['torso','neckhead','leg','clavicle','arm','finger','thumb','eyeball']
__l_faceModules__ = ['eyebrow','eyelids','eyeball','mouthnose']
#l_modulesDone = []
#>>> Register rig functions
#=====================================================================
d_moduleTypeToBuildModule = {'leg':leg,
                             'torso':spine,
                             'neckhead':neckHead,
                             'clavicle':clavicle,
                             'arm':arm,
                             'finger':finger,
                             'thumb':finger,
                             'eyeball':eyeball,
                             'eyebrow':eyebrow,
                             'mouthnose':mouthNose,
                             'eyelids':eyelids,
                            } 
for module in d_moduleTypeToBuildModule.keys():
    reload(d_moduleTypeToBuildModule[module])
    
__l_moduleJointSingleHooks__ = ['scaleJoint']
__l_moduleJointMsgListHooks__ = ['helperJoints']

#>>> Main class function
#=====================================================================
class go(object):
    def __init__(self,moduleInstance,forceNew = True,autoBuild = True, ignoreRigCheck = False, **kws): 
        """
        To do:
        Add rotation order settting
        Add module parent check to make sure parent is templated to be able to move forward, or to constrain
        Add any other piece meal data necessary
        Add a cleaner to force a rebuild
        """
        # Get our base info
        #==============	        
        #>>> module null data
	"""
	try:moduleInstance
	except Exception,error:
	    log.error("RigFactory.go.__init__>>module instance isn't working!")
	    raise StandardError,error    
	"""
	#>>> Intial stuff
	i_module = False
	try:
	    if moduleInstance.isModule():
		i_module = moduleInstance
	except Exception,error:
	    raise StandardError,"RigFactory.go.init. Module call failure. Probably not a module: '%s'"%error	    
	if not i_module:
	    raise StandardError,"RigFactory.go.init Module instance no longer exists: '%s'"%moduleInstance
	
	_str_funcName = "go.__init__(%s)"%i_module.p_nameShort  
	log.info(">>> %s "%(_str_funcName) + "="*100)
	start = time.clock()
	
	#Some basic assertions
        assert moduleInstance.isSkeletonized(),"Module is not skeletonized: '%s'"%moduleInstance.getShortName()
        
        log.debug(">>> forceNew: %s"%forceNew)	
        self._i_module = moduleInstance# Link for shortness
	self._i_module.__verify__()
	self._cgmClass = 'RigFactory.go'
	
	#First we want to see if we have a moduleParent to see if it's rigged yet
	if self._i_module.getMessage('moduleParent'):
	    if not self._i_module.moduleParent.isRigged():
		raise StandardError,"%s >> '%s's module parent is not rigged yet: '%s'"%(_str_funcName,self._i_module.getShortName(),self._i_module.moduleParent.getShortName())
	
	#Then we want to see if we have a moduleParent to see if it's rigged yet
	b_rigged = self._i_module.isRigged()
	if b_rigged and forceNew is not True and ignoreRigCheck is not True:
	    raise StandardError,"%s >>> '%s' already rigged and not forceNew"%(_str_funcName,self._i_module.getShortName())
	
	#Verify we have a puppet and that puppet has a masterControl which we need for or master scale plug
	self._i_puppet = self._i_module.modulePuppet
	if not self._i_puppet.__verify__():
	    raise StandardError,"%s >>> modulePuppet failed to verify"%_str_funcName	
	if not self._i_puppet._verifyMasterControl():
	    raise StandardError,"%s >>> masterControl failed to verify"%_str_funcName
	
	#Verify a dynamic switch
	try:
	    if not self._i_module.rigNull.getMessage('dynSwitch'):
		self._i_dynSwitch = cgmRigMeta.cgmDynamicSwitch(dynOwner=self._i_module.rigNull.mNode)
	    else:
		self._i_dynSwitch = self._i_module.rigNull.dynSwitch
	    log.debug("switch: '%s'"%self._i_dynSwitch.getShortName())
	except Exception,error:
	    raise StandardError,"%s >> Dynamic switch build failed! | %s"%(self._strShortName,error)
				
	try:#>>> Gather info =========================================================================
	    #Master control ---------------------------------------------------------
	    self._i_masterControl = self._i_module.modulePuppet.masterControl
	    self.mPlug_globalScale = cgmMeta.cgmAttr(self._i_masterControl.mNode,'scaleY')	    
	    self._i_masterSettings = self._i_masterControl.controlSettings
	    self._i_masterDeformGroup = self._i_module.modulePuppet.masterNull.deformGroup	    
	    self._l_moduleColors = self._i_module.getModuleColors()
	    self._mi_moduleParent = False
	    if self._i_module.getMessage('moduleParent'):
		self._mi_moduleParent = self._i_module.moduleParent	    
	    #Module stuff ------------------------------------------------------------
	    self._l_coreNames = self._i_module.coreNames.value
	    self._i_templateNull = self._i_module.templateNull#speed link
	    self._i_rigNull = self._i_module.rigNull#speed link
	    self._bodyGeo = self._i_module.modulePuppet.getGeo() or ['Morphy_Body_GEO'] #>>>>>>>>>>>>>>>>>this needs better logic   
	    self._version = self._i_rigNull.version
	    self._direction = self._i_module.getAttr('cgmDirection')
	    
	    #Mirror stuff
	    self._str_mirrorDirection = self._i_module.get_mirrorSideAsString()
	    self._f_skinOffset = self._i_puppet.getAttr('skinDepth') or 1 #Need to get from puppet!<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<		

	    #Joints ------------------------------------------------------------------
	    self._ml_moduleJoints = self._i_rigNull.msgList_get('moduleJoints',asMeta = True,cull = True)
	    if not self._ml_moduleJoints:raise StandardError, "No module joints found!"
	    self._l_moduleJoints = [j.p_nameShort for j in self._ml_moduleJoints]
	    self._ml_skinJoints = get_skinJoints(self._i_module,asMeta=True)
	    if not self._ml_skinJoints:raise StandardError,"No Skin joints found"
	    if not self._ml_moduleJoints:raise StandardError, "No module joints found!"        
	    self._l_skinJoints = [j.p_nameShort for j in self._ml_skinJoints]

	    #>>> part name -----------------------------------------------------------------
	    self._partName = self._i_module.getPartNameBase()
	    self._partType = self._i_module.moduleType.lower() or False
	    self._strShortName = self._i_module.getShortName() or False
	    
	    #>>> Instances and joint stuff ----------------------------------------------------
	    self._mi_orientation = cgmValid.simpleOrientation(str(modules.returnSettingsData('jointOrientation')) or 'zyx')
	    self._jointOrientation = self._mi_orientation.p_string      
	    self._vectorAim = self._mi_orientation.p_aim.p_vector
	    self._vectorUp = self._mi_orientation.p_up.p_vector
	    self._vectorOut = self._mi_orientation.p_out.p_vector
	    self._vectorAimNegative = self._mi_orientation.p_aimNegative.p_vector
	    self._vectorUpNegative = self._mi_orientation.p_upNegative.p_vector
	    self._vectorOutNegative = self._mi_orientation.p_outNegative.p_vector
	    
	except Exception,error:
	    raise StandardError,"%s >> Module data gather fail! | %s"%(_str_funcName,error)
	    
        #>>> See if we have a buildable module -- do we have a builder
	if not isBuildable(self):
	    raise StandardError,"The builder for module type '%s' is not ready"%self._partType
	
	try:#>>>Version Check ========================================================================
	    self._outOfDate = False
	    if self._version != self._buildVersion:
		self._outOfDate = True	    
		log.warning("%s >> '%s'(%s) rig version out of date: %s != %s"%(_str_funcName, self._strShortName,self._partType,self._version,self._buildVersion))	
	    else:
		if forceNew and self._i_module.isRigged():
		    self._i_module.rigDelete()
		log.debug("%s >>> '%s' rig version up to date !"%(_str_funcName,self.buildModule.__name__))	
	except Exception,error:
	    raise StandardError,"%s  >> Version check fail | %s"%(self._strShortName,error)

	#>>>Connect switches
	try: verify_moduleRigToggles(self)
	except Exception,error:
	    raise StandardError,"%s  >> Module data gather fail! | %s"%(self._strShortName,error)
	
	#>>> Object Set
	try: self._i_module.__verifyObjectSet__()
	except Exception,error:
	    raise StandardError,"%s >>> error : %s"%(_str_funcName,error) 
	
	try:#>>> FACE MODULES If face module we need a couple of data points
	    if self._partType.lower() in __l_faceModules__:
		log.info("FACE MODULE")
		self.verify_faceModuleAttachJoint()
		self.verify_faceSkullPlate()
		self.verify_faceDeformNull()#make sure we have a face deform null
		self.verify_faceScaleDriver()#scale driver
	
		try:#>> Constrain  head stuff =======================================================================================
		    mi_parentHeadHandle = self.mi_parentHeadHandle
		    mi_constrainNull =  self._i_faceDeformNull
		    log.info(mi_parentHeadHandle)
		    log.info(mi_constrainNull)		    
		    try:
			if not mi_constrainNull.isConstrainedBy(mi_parentHeadHandle.mNode):
			    mc.parentConstraint(mi_parentHeadHandle.mNode,mi_constrainNull.mNode)
			    #for attr in 'xzy':
				#mi_go.mPlug_multpHeadScale.doConnectOut("%s.s%s"%(mi_constrainNull.mNode,attr))
			    mc.scaleConstraint(mi_parentHeadHandle.mNode,mi_constrainNull.mNode)
		    except Exception,error:raise Exception,"Failed to constrain | %s"%error
		except Exception,error:raise StandardError,"!constrain stuff to the head! | %s"%(error)			
	except Exception,error:
	    raise StandardError,"%s >>> error : %s"%(_str_funcName,error) 	
	
	try:#>>> Deform group for the module =====================================================
	    if not self._i_module.getMessage('deformNull'):
		if self._partType in ['eyebrow', 'mouthnose']:
		    #Make it and link it ------------------------------------------------------
		    buffer = rigging.groupMeObject(self.str_faceAttachJoint,False)
		    i_grp = cgmMeta.cgmObject(buffer,setClass=True)
		    i_grp.addAttr('cgmName',self._partName,lock=True)
		    i_grp.addAttr('cgmTypeModifier','deform',lock=True)	 
		    i_grp.doName()
		    i_grp.parent = self._i_faceDeformNull	
		    self._i_module.connectChildNode(i_grp,'deformNull','module')
		    self._i_module.connectChildNode(i_grp,'constrainNull','module')
		    self._i_deformNull = i_grp#link
		    
		else:
		    #Make it and link it
		    buffer = rigging.groupMeObject(self._ml_skinJoints[0].mNode,False)
		    i_grp = cgmMeta.cgmObject(buffer,setClass=True)
		    i_grp.addAttr('cgmName',self._partName,lock=True)
		    i_grp.addAttr('cgmTypeModifier','deform',lock=True)	 
		    i_grp.doName()
		    i_grp.parent = self._i_masterDeformGroup.mNode
		    self._i_module.connectChildNode(i_grp,'deformNull','module')
		    if self._partType in ['eyeball', 'eyelids']:
			self._i_module.connectChildNode(i_grp,'constrainNull','module')		
	    self._i_deformNull = self._i_module.deformNull
	except Exception,error:
	    raise StandardError,"%s  >> Deform Null fail! | %s"%(self._strShortName,error)	
	
	try:#>>> Constrain Deform group for the module ==========================================
	    if not self._i_module.getMessage('constrainNull'):
		if self._partType not in __l_faceModules__:
		    #Make it and link it
		    buffer = rigging.groupMeObject(self._ml_skinJoints[0].mNode,False)
		    i_grp = cgmMeta.cgmObject(buffer,setClass=True)
		    i_grp.addAttr('cgmName',self._partName,lock=True)
		    i_grp.addAttr('cgmTypeModifier','constrain',lock=True)	 
		    i_grp.doName()
		    i_grp.parent = self._i_deformNull.mNode
		    self._i_module.connectChildNode(i_grp,'constrainNull','module')
		
	    self._i_constrainNull = self._i_module.constrainNull
	except Exception,error:
	    raise StandardError,"%s  >> Constrain Null fail! | %s"%(self._strShortName,error)	
	
        #Make our stuff
	self._md_controlShapes = {}
	if self._partType in l_modulesDone:
	    if self._outOfDate and autoBuild:
		self.doBuild(**kws)
	    else:
		log.debug("'%s' No autobuild."%self._strShortName)
	else:
	    log.warning("'%s' module type not in done list. No auto build"%self.buildModule.__name__)
	    
	log.info("%s >> Complete Time >> %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)     	    
	
    
    
    def doBuild(self,buildTo = '',**kws):
	"""
	Return if a module is shaped or not
	"""
	_str_funcName = "go.doBuild(%s)"%self._i_module.p_nameShort  
	log.debug(">>> %s "%(_str_funcName) + "="*75)
	start = time.clock()
	
	d_build = self.buildModule.__d_buildOrder__
	int_keys = d_build.keys()
	
	#Build our progress Bar
	mayaMainProgressBar = gui.doStartMayaProgressBar(len(int_keys))
	#mc.progressBar(mayaMainProgressBar, edit=True, progress=0) 
	for k in int_keys:
	    try:	
		str_name = d_build[k].get('name') or 'noName'
		func_current = d_build[k].get('function')
		_str_subFunc = str_name
		time_sub = time.clock() 
		log.debug(">>> %s..."%_str_subFunc) 
		
		mc.progressBar(mayaMainProgressBar, edit=True, status = "%s >>Rigging>> step:'%s'..."%(self._strShortName,str_name), progress=k+1)    
		func_current(self)
    
		if buildTo.lower() == str_name:
		    log.debug("%s.doBuild >> Stopped at step : %s"%(self._strShortName,str_name))
		    break
		log.info("%s >> Time >> %s = %0.3f seconds " % (_str_funcName,_str_subFunc,(time.clock()-time_sub)) + "-"*75) 		
	    except Exception,error:
		raise StandardError,"%s.doBuild >> Step %s failed! | %s"%(self._strShortName,str_name,error)
	
	log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)
	gui.doEndMayaProgressBar(mayaMainProgressBar)#Close out this progress bar        
	
	    
    def isShaped(self):
	"""
	Return if a module is shaped or not
	"""
	_str_funcName = "go.isShaped(%s)"%self._i_module.p_nameShort  
	log.debug(">>> %s "%(_str_funcName) + "="*75)
	start = time.clock()	
	b_return = True
	try:
	    if self._partType in d_moduleTypeToBuildModule.keys():
		checkShapes = d_moduleTypeToBuildModule[self._partType].__d_controlShapes__
	    else:
		log.debug("%s.isShaped>>> Don't have a shapeDict, can't check. Passing..."%(self._strShortName))	    
		return True
	    for key in checkShapes.keys():
		for subkey in checkShapes[key]:
		    if not self._i_rigNull.getMessage('%s_%s'%(key,subkey)):
			if not self._i_rigNull.msgList_getMessage('%s_%s'%(key,subkey)):
			    if not self._i_rigNull.msgList_get('%s'%(subkey),False):
				log.warning("%s.isShaped>>> Missing %s '%s' "%(self._strShortName,key,subkey))
				b_return =  False
				break
	    log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)
	    return True
	except Exception,error:
	    raise StandardError,"%s >>  %s"%(_str_funcName,error)  
	
    def isRigSkeletonized(self):
	"""
	Return if a module is rig skeletonized or not
	"""
	_str_funcName = "go.isRigSkeletonized(%s)"%self._i_module.p_nameShort  
	log.debug(">>> %s "%(_str_funcName) + "="*75)
	for key in self._l_jointAttrs:
	    if not self._i_rigNull.getMessage('%s'%(key)) and not self._i_rigNull.msgList_getMessage('%s'%(key)):
		log.error("%s.isRigSkeletonized>>> Missing key '%s'"%(self._strShortName,key))
		return False		
	return True
    
    def verify_faceModuleAttachJoint(self):
	_str_funcName = "go.verify_faceModuleAttachJoint(%s)"%self._i_module.p_nameShort  
	
	#Find our head attach joint ------------------------------------------------------------------------------------------------
	self.str_faceAttachJoint = False
	if not self._i_module.getMessage('moduleParent'):
	    raise StandardError,"%s >> Must have a module parent"%_str_funcName
	try:
	    mi_end = self._i_module.moduleParent.rigNull.msgList_get('moduleJoints')[-1]
	    self.mi_parentHeadHandle = self._i_module.moduleParent.rigNull.handleIK	    
	    buffer =  mi_end.getMessage('scaleJoint')
	    if buffer:
		buffer2 =  mi_end.scaleJoint.getMessage('rigJoint')
		if buffer2:
		    self.str_faceAttachJoint = buffer2[0]
		else:
		    self.str_faceAttachJoint = buffer[0]
	    else:
		self.str_faceAttachJoint = mi_end.mNode
	except Exception,error:
	    log.error("%s failed to find root joint from moduleParent | %s"%(_str_funcName,error))
	
	return self.str_faceAttachJoint
    
    def verify_faceSkullPlate(self,*args,**kws):
	return fnc_verify_faceSkullPlate(self,*args,**kws)

    def verify_faceDeformNull(self):
	"""
	Return if a module is rig skeletonized or not
	"""
	_str_funcName = "go.verify_faceDeformNull(%s)"%self._i_module.p_nameShort  
	log.debug(">>> %s "%(_str_funcName) + "="*75)
	if self._partType not in __l_faceModules__:
	    raise StandardError, "%s >> Not a face module"%_str_funcName
	
	#Try to see if we ahve a face attach joint ==============================
	try:self.str_faceAttachJoint
	except:
	    try:self.verify_faceModuleAttachJoint()
	    except Exception,error:
		raise StandardError, "%s >> error: %s"%(_str_funcName,error)
	
	
	#Check if we have a face deformNull on a parent --------------------------	    
	buffer = self._mi_moduleParent.getMessage('faceDeformNull')
	if buffer:
	    self._i_module.connectChildNode(buffer[0],'faceDeformNull')
	    self._i_faceDeformNull = self._mi_moduleParent.faceDeformNull
	    return True
	
	#Make it and link it ------------------------------------------------------
	buffer = rigging.groupMeObject(self.str_faceAttachJoint,False)
	i_grp = cgmMeta.cgmObject(buffer,setClass=True)
	i_grp.addAttr('cgmName','face',lock=True)
	i_grp.addAttr('cgmTypeModifier','deform',lock=True)	 
	i_grp.doName()
	i_grp.parent = self._i_masterDeformGroup.mNode	
	self._i_module.connectChildNode(i_grp,'faceDeformNull')	
	self._mi_moduleParent.connectChildNode(i_grp,'faceDeformNull','module')
	self._i_faceDeformNull = i_grp#link
	return True
    
    def verify_faceScaleDriver(self):
	try:
	    mi_parentHeadHandle = self._i_module.moduleParent.rigNull.handleIK
	    mi_parentBlendPlug = cgmMeta.cgmAttr(self.mi_parentHeadHandle,'scale')
	    mi_faceDeformNull = self._i_faceDeformNull
	    #connect blend joint scale to the finger blend joints
	    '''
	    for i_jnt in ml_blendJoints:
		mi_parentBlendPlug.doConnectOut("%s.scale"%i_jnt.mNode)
	    '''	
	    
	    #intercept world scale and add in head scale
	    mPlug_multpHeadScale = cgmMeta.cgmAttr(mi_faceDeformNull,'out_multpHeadScale',value = 1.0,defaultValue=1.0,lock = True)
	    
	    mPlug_globalScale = cgmMeta.cgmAttr(self._i_masterControl.mNode,'scaleY')
	    mPlug_globalScale.doConnectOut(mPlug_multpHeadScale)
	    NodeF.argsToNodes("%s = %s * %s.sy"%(mPlug_multpHeadScale.p_combinedShortName,
						 mPlug_globalScale.p_combinedShortName,
						 mi_parentHeadHandle.p_nameShort)).doBuild()
	    self.mPlug_multpHeadScale = mPlug_multpHeadScale
	except Exception,error:raise StandardError,"!verify_faceScaleDriver! | %s"%(error)	
	
    def verify_faceSettings(self):
	"""
	Return if a module is rig skeletonized or not
	"""
	_str_funcName = "go.verify_faceSettings(%s)"%self._i_module.p_nameShort  
	log.debug(">>> %s "%(_str_funcName) + "="*75)
	if self._partType not in __l_faceModules__:
	    raise StandardError, "%s >> Not a face module"%_str_funcName
		
	#>> Constrain Null ==========================================================    
	if self._i_rigNull.getMessage('settings'):
	    return True
	
	#Check if we have a settings control on parent module --------------------------	    
	buffer = self._mi_moduleParent.rigNull.getMessage('settings')
	if buffer:
	    self._i_rigNull.connectChildNode(buffer[0],'settings')		    
	    return True
	
	raise Exception,"No face settings found!"
     
    def verify_mirrorSideArg(self,arg  = None):
	_str_funcName = "return_mirrorSideAsString(%s)"%self._i_module.p_nameShort   
	log.debug(">>> %s "%(_str_funcName) + "="*75)   
	try:
	    if arg is not None and arg.lower() in ['right','left']:
		return arg.capitalize()
	    else:
		return 'Centre'
	except Exception,error:
	    raise StandardError,"%s >> %s"%(_str_funcName,error) 
	
    def cleanTempAttrs(self):
	for key in self._shapesDict.keys():
	    for subkey in self._shapesDict[key]:
		self._i_rigNull.doRemove('%s_%s'%(key,subkey))
	return True
	                         
    def _get_influenceChains(self):
	return get_influenceChains(self._i_module)	
	
    def _get_segmentHandleChains(self):
	return get_segmentHandleChains(self._i_module)
	
    def _get_segmentChains(self):
	return get_segmentChains(self._i_module)
        
    def _get_rigDeformationJoints(self):
	return get_rigDeformationJoints(self._i_module)
	
    def _get_handleJoints(self):
	return get_rigHandleJoints(self._i_module)
    
    def _get_simpleRigJointDriverDict(self):
	return get_simpleRigJointDriverDict(self._i_module)
    def _get_eyeLook(self):
	return get_eyeLook(self._i_module)
    def _verify_eyeLook(self):
	return verify_eyeLook(self._i_module)   
    def get_report(self):
	self._i_module.rig_getReport()
    def _set_versionToCurrent(self):
	self._i_rigNull.version = str(self._buildVersion)	
	
    #>> Connections
    #=====================================================================
    def connect_toRigGutsVis(self, ml_objects, vis = True):
	try:
	    _str_funcName = "go.connect_toRigGutsVis(%s)"%self._i_module.p_nameShort  
	    log.debug(">>> %s "%(_str_funcName) + "="*75)
	    start = time.clock()	
	    
	    if type(ml_objects) not in [list,tuple]:ml_objects = [ml_objects]
	    for i_obj in ml_objects:
		i_obj.overrideEnabled = 1		
		if vis: cgmMeta.cgmAttr(self._i_module.rigNull.mNode,'gutsVis',lock=False).doConnectOut("%s.%s"%(i_obj.mNode,'overrideVisibility'))
		cgmMeta.cgmAttr(self._i_module.rigNull.mNode,'gutsLock',lock=False).doConnectOut("%s.%s"%(i_obj.mNode,'overrideDisplayType'))    
	    
	    log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)
	
	except Exception,error:
	    raise StandardError,"%s >> %s"%(_str_funcName,error)
    
    def connect_restoreJointLists(self):
	raise DeprecationWarning, "Please remove this instance of 'connect_restoreJointLists'"
	try:
	    if self._ml_rigJoints:
		log.debug("%s.connect_restoreJointLists >> Found rig joints to store back"%self._strShortName)
		self._i_rigNull.connectChildrenNodes(self._ml_rigJoints,'rigJoints','rigNull')
	    self._i_rigNull.connectChildrenNodes(self._ml_skinJoints,'skinJoints','rigNull')#Push back
	    self._i_rigNull.connectChildrenNodes(self._ml_moduleJoints,'moduleJoints','rigNull')#Push back
	except Exception,error:
	    raise StandardError,"%s.connect_restoreJointLists >> Failure: %s"%(self._strShortName,error)
    
    #>> Attributes
    #=====================================================================	
    def _verify_moduleMasterScale(self):
	_str_funcName = "go._verify_moduleMasterScale(%s)"%self._i_module.p_nameShort  
	log.debug(">>> %s "%(_str_funcName) + "="*75)
	start = time.clock()	
	try:
	    mPlug_moduleMasterScale = cgmMeta.cgmAttr(self._i_rigNull,'masterScale',value = 1.0,defaultValue=1.0)
	    mPlug_globalScale = cgmMeta.cgmAttr(self._i_masterControl.mNode,'scaleY')
	    mPlug_globalScale.doConnectOut(mPlug_moduleMasterScale)
	    log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)	    
	except Exception,error:
	    raise StandardError,"%s >> %s"%(_str_funcName,error)
	
	
    def _get_masterScalePlug(self):
	_str_funcName = "go._verify_moduleMasterScale(%s)"%self._i_module.p_nameShort  
	log.debug(">>> %s "%(_str_funcName) + "="*75)
	try:
	    if self._i_rigNull.hasAttr('masterScale'):
		return cgmMeta.cgmAttr(self._i_rigNull,'masterScale')
	    return cgmMeta.cgmAttr(self._i_masterControl.mNode,'scaleY')
	except Exception,error:
	    raise StandardError,"%s >> %s"%(_str_funcName,error)   
	
    
    def build_visSub(self):
	_str_funcName = "go.build_visSub(%s)"%self._strShortName
	log.debug(">>> %s "%(_str_funcName) + "="*75)
	start = time.clock()	
	try:
	    mi_settings = self._i_rigNull.settings
	    #Add our attrs
	    mPlug_moduleSubDriver = cgmMeta.cgmAttr(mi_settings,'visSub', value = 1, defaultValue = 1, attrType = 'int', minValue=0,maxValue=1,keyable = False,hidden = False)
	    mPlug_result_moduleSubDriver = cgmMeta.cgmAttr(mi_settings,'visSub_out', defaultValue = 1, attrType = 'int', keyable = False,hidden = True,lock=True)
	    
	    #Get one of the drivers
	    if self._i_module.getAttr('cgmDirection') and self._i_module.cgmDirection.lower() in ['left','right']:
		str_mainSubDriver = "%s.%sSubControls_out"%(self._i_masterControl.controlVis.getShortName(),
		                                            self._i_module.cgmDirection)
	    else:
		str_mainSubDriver = "%s.subControls_out"%(self._i_masterControl.controlVis.getShortName())
	
	    iVis = self._i_masterControl.controlVis
	    visArg = [{'result':[mPlug_result_moduleSubDriver.obj.mNode,mPlug_result_moduleSubDriver.attr],
		       'drivers':[[iVis,"subControls_out"],[mi_settings,mPlug_moduleSubDriver.attr]]}]
	    NodeF.build_mdNetwork(visArg)
	    
	    log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)	    
	    return mPlug_result_moduleSubDriver
	    
	except Exception,error:
	    raise StandardError,"%s >> %s"%(_str_funcName,error)   
    
    def build_visSubFace(self):
	_str_funcName = "go.build_visSubFace(%s)"%self._strShortName
	log.debug(">>> %s "%(_str_funcName) + "="*75)
	start = time.clock()	
	try:
	    mi_settings = self._i_rigNull.settings
	    #Add our attrs
	    mPlug_moduleSubFaceDriver = cgmMeta.cgmAttr(mi_settings,'visSubFace', value = 1, defaultValue = 1, attrType = 'int', minValue=0,maxValue=1,keyable = False,hidden = False)
	    mPlug_result_moduleSubFaceDriver = cgmMeta.cgmAttr(mi_settings,'visSubFace_out', defaultValue = 1, attrType = 'int', keyable = False,hidden = True,lock=True)
	    
	    #Get one of the drivers
	    if self._i_module.getAttr('cgmDirection') and self._i_module.cgmDirection.lower() in ['left','right']:
		str_mainSubDriver = "%s.%sSubControls_out"%(self._i_masterControl.controlVis.getShortName(),
		                                            self._i_module.cgmDirection)
	    else:
		str_mainSubDriver = "%s.subControls_out"%(self._i_masterControl.controlVis.getShortName())
	
	    iVis = self._i_masterControl.controlVis
	    visArg = [{'result':[mPlug_result_moduleSubFaceDriver.obj.mNode,mPlug_result_moduleSubFaceDriver.attr],
		       'drivers':[[iVis,"subControls_out"],[mi_settings,mPlug_moduleSubFaceDriver.attr]]}]
	    NodeF.build_mdNetwork(visArg)
	    
	    log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)	    
	    return mPlug_result_moduleSubFaceDriver
	    
	except Exception,error:
	    raise StandardError,"%s >> %s"%(_str_funcName,error) 
    
    
    #>>> Joint chains
    #=====================================================================
    def mirrorChainOrientation(self,ml_chain):
	_str_funcName = "go.mirrorChainOrientation(%s)"%self._strShortName
	log.debug(">>> %s "%(_str_funcName) + "="*75)
	start = time.clock()	
	try:
	    #Get our segment joints
	    for mJoint in ml_chain:
		mJoint.parent = False
		
	    for mJoint in ml_chain:
		mJoint.__setattr__("r%s"%self._jointOrientation[2],180)
		
	    for i,mJoint in enumerate(ml_chain[1:]):
		mJoint.parent = ml_chain[i]
		
	    jntUtils.metaFreezeJointOrientation(ml_chain)
	    
	    log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)	    
	    return ml_chain
	except Exception,error:
	    raise StandardError,"%s >> %s"%(_str_funcName,error)  
	
    def build_rigChain(self):
	_str_funcName = "go.build_rigChain(%s)"%self._strShortName
	log.debug(">>> %s "%(_str_funcName) + "="*75)
	start = time.clock()	
	try:
	    #Get our segment joints
	    l_rigJointsExist = self._i_rigNull.msgList_get('rigJoints',asMeta = False, cull = True)
	    if l_rigJointsExist:
		log.error("Deleting existing rig chain")
		mc.delete(l_rigJointsExist)
		
	    l_rigJoints = mc.duplicate([i_jnt.mNode for i_jnt in self._ml_skinJoints],po=True,ic=True,rc=True)
	    ml_rigJoints = [cgmMeta.cgmObject(j) for j in l_rigJoints]
	    
	    for i,mJnt in enumerate(ml_rigJoints):
		#log.info(mJnt.p_nameShort)		
		mJnt.addAttr('cgmTypeModifier','rig',attrType='string',lock=True)
		mJnt.doName()
		l_rigJoints[i] = mJnt.mNode
		mJnt.connectChildNode(self._l_skinJoints[i],'skinJoint','rigJoint')#Connect	    
		if mJnt.hasAttr('scaleJoint'):
		    if mJnt.scaleJoint in self._ml_skinJoints:
			int_index = self._ml_skinJoints.index(mJnt.scaleJoint)
			mJnt.connectChildNode(l_rigJoints[int_index],'scaleJoint','sourceJoint')#Connect
		if mJnt.hasAttr('rigJoint'):mJnt.doRemove('rigJoint')
	    
	    self._ml_rigJoints = ml_rigJoints
	    self._l_rigJoints = [i_jnt.p_nameShort for i_jnt in ml_rigJoints]
	    self._i_rigNull.msgList_connect(ml_rigJoints,'rigJoints','rigNull')#connect	
	    log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)	    
	    return ml_rigJoints
	except Exception,error:
	    raise StandardError,"%s >> %s"%(_str_funcName,error)  
	
    
    def build_handleChain(self,typeModifier = 'handle',connectNodesAs = False): 
	_str_funcName = "go.build_handleChain(%s)"%self._strShortName
	log.debug(">>> %s "%(_str_funcName) + "="*75)
	start = time.clock()		
	try:
	    ml_handleJoints = self._i_module.rig_getHandleJoints()
	    ml_handleChain = []
	    
	    for i,i_handle in enumerate(ml_handleJoints):
		i_new = i_handle.doDuplicate()
		if ml_handleChain:i_new.parent = ml_handleChain[-1]#if we have data, parent to last
		else:i_new.parent = False
		i_new.addAttr('cgmTypeModifier',typeModifier,attrType='string',lock=True)
		i_new.doName()
		
		#i_new.rotateOrder = self._jointOrientation#<<<<<<<<<<<<<<<<This would have to change for other orientations
		ml_handleChain.append(i_new)
		
	    #self._i_rigNull.connectChildrenNodes(self._l_skinJoints,'skinJoints','rigNull')#Push back
	    #self._i_rigNull.connectChildrenNodes(self._ml_moduleJoints,'moduleJoints','rigNull')#Push back
	    log.debug("%s.buildHandleChain >> built '%s handle chain: %s"%(self._strShortName,typeModifier,[i_j.getShortName() for i_j in ml_handleChain]))
	    if connectNodesAs not in [None,False] and type(connectNodesAs) in [str,unicode]:
		self._i_rigNull.msgList_connect(ml_handleChain,connectNodesAs,'rigNull')#Push back
	    
	    log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)
	    return ml_handleChain

	except Exception,error:
	    raise StandardError,"%s >> %s"%(_str_funcName,error)  
	
    def duplicate_jointChain(self,ml_jointList = None, typeModifier = 'handle',connectNodesAs = False): 
	_str_funcName = "go.duplicate_jointChain(%s)"%self._strShortName
	log.debug(">>> %s "%(_str_funcName) + "="*75)
	start = time.clock()		
	try:
	    ml_dupChain = []
	    for i,i_handle in enumerate(ml_jointList):
		i_new = i_handle.doDuplicate()
		if ml_dupChain:i_new.parent = ml_dupChain[-1]#if we have data, parent to last
		else:i_new.parent = False
		i_new.addAttr('cgmTypeModifier',typeModifier,attrType='string',lock=True)
		i_new.doName()
		ml_dupChain.append(i_new)
		
	    log.debug("%s.duplicate_jointChain >> built '%s handle chain: %s"%(self._strShortName,typeModifier,[i_j.getShortName() for i_j in ml_dupChain]))
	    if connectNodesAs not in [None,False] and type(connectNodesAs) in [str,unicode]:
		self._i_rigNull.msgList_connect(ml_dupChain,connectNodesAs,'rigNull')#Push back
	    
	    log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)
	    return ml_dupChain

	except Exception,error:
	    raise StandardError,"%s >> %s"%(_str_funcName,error)  
    
    def duplicate_moduleJoint(self, index = None, typeModifier = 'duplicate', connectNodesAs = False):    
	"""
	This is only necessary because message connections are duplicated and make duplicating connected joints problematic
	"""
	_str_funcName = "go.duplicate_moduleJoint(%s)"%self._strShortName
	log.debug(">>> %s "%(_str_funcName) + "="*75)
	start = time.clock()		
	try:
	    if index is None:
		raise StandardError, "%s.duplicate_moduleJoint >> No index specified"%(self._strShortName)
	    if type(index) is not int:
		raise StandardError, "%s.duplicate_moduleJoint >> index not int: %s | %s"%(self._strShortName,index,type(index))
	    if index > len(self._ml_moduleJoints)+1:
		raise StandardError, "%s.duplicate_moduleJoint >> index > len(moduleJoints): %s | %s"%(self._strShortName,index,(len(self._ml_moduleJoints)+1))
	    
	    i_target = self._ml_moduleJoints[index]
	    buffer = mc.duplicate(i_target.mNode,po=True,ic=True)[0]
	    i_new = cgmMeta.validateObjArg(buffer,cgmMeta.cgmObject)
	    i_new.parent = False
	    
	    i_new.addAttr('cgmTypeModifier',typeModifier,attrType='string',lock=True)
	    i_new.doName()
		
	    #Push back our nodes
	    self.connect_restoreJointLists()#Push back
	    log.debug("%s.duplicate_moduleJoint >> created: %s"%(self._strShortName,i_new.p_nameShort))
	    if connectNodesAs not in [None,False] and type(connectNodesAs) in [str,unicode]:
		self._i_rigNull.connectChildNode(i_new,connectNodesAs,'rigNull')#Push back
		
	    log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)
	    return i_new

	except Exception,error:
	    raise StandardError,"%s >> %s"%(_str_funcName,error)  
	
    def build_segmentChains(self, ml_segmentHandleJoints = None, connectNodes = True):
	_str_funcName = "go.build_segmentChains(%s)"%self._strShortName
	log.debug(">>> %s "%(_str_funcName) + "="*75)
	start = time.clock()
	try:
	    ml_segmentChains = []
	    if ml_segmentHandleJoints is None:
		ml_segmentHandleJoints = get_segmentHandleTargets(self._i_module)
		
	    if not ml_segmentHandleJoints:raise StandardError,"%s.build_segmentChains>> failed to get ml_segmentHandleJoints"%self._strShortName
	    
	    l_segPairs = lists.parseListToPairs(ml_segmentHandleJoints)
	    
	    for i,ml_pair in enumerate(l_segPairs):
		index_start = self._ml_moduleJoints.index(ml_pair[0])
		index_end = self._ml_moduleJoints.index(ml_pair[-1]) + 1
		buffer_segmentTargets = self._ml_moduleJoints[index_start:index_end]
		
		log.debug("segment %s: %s"%(i,buffer_segmentTargets))
		
		ml_newChain = []
		for i2,j in enumerate(buffer_segmentTargets):
		    i_j = j.doDuplicate()
		    i_j.addAttr('cgmTypeModifier','seg_%s'%i,attrType='string',lock=True)
		    i_j.doName()
		    if ml_newChain:
			i_j.parent = ml_newChain[-1].mNode
		    ml_newChain.append(i_j)
		    
		ml_newChain[0].parent = False#Parent to deformGroup
		ml_segmentChains.append(ml_newChain)
	    
	    #Sometimes last segement joints have off orientaions, we're gonna fix
	    joints.doCopyJointOrient(ml_segmentChains[-1][-2].mNode,ml_segmentChains[-1][-1].mNode)
	    for segmentChain in ml_segmentChains:
		jntUtils.metaFreezeJointOrientation([i_jnt.mNode for i_jnt in segmentChain])
		
	    #Connect stuff ============================================================================================    
	    #self._i_rigNull.connectChildrenNodes(self._l_skinJoints,'skinJoints','rigNull')#Push back
	    #self._i_rigNull.connectChildrenNodes(self._ml_moduleJoints,'moduleJoints','rigNull')#Push back	
	    if connectNodes:
		for i,ml_chain in enumerate(ml_segmentChains):
		    l_chain = [i_jnt.getShortName() for i_jnt in ml_chain]
		    log.debug("segment chain %s: %s"%(i,l_chain))
		    self._i_rigNull.msgList_connect(ml_chain,'segment%s_Joints'%i,"rigNull")
		    log.debug("segment%s_Joints>> %s"%(i,self._i_rigNull.msgList_getMessage('segment%s_Joints'%i,False)))
	    
	    log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)
	    return ml_segmentChains
	except Exception,error:
	    raise StandardError,"%s >> %s"%(_str_funcName,error)  
	
    
    def build_simpleInfluenceChains(self,addMidInfluence = True):
	"""
	
	"""
	_str_funcName = "go.build_simpleInfluenceChains(%s)"%self._strShortName
	log.debug(">>> %s "%(_str_funcName) + "="*75)
	start = time.clock()
	try:
	    ml_handleJoints = self._i_module.rig_getHandleJoints()
	    ml_segmentHandleJoints = get_segmentHandleTargets(self._i_module)
	    
	    #>> Make influence joints ================================================================================
	    l_influencePairs = lists.parseListToPairs(ml_segmentHandleJoints)
	    ml_influenceJoints = []
	    ml_influenceChains = []
	    
	    for i,m_pair in enumerate(l_influencePairs):#For each pair
		str_nameModifier = 'seg_%s'%i	    
		l_tmpChain = []
		ml_midJoints = []	    
		for ii,i_jnt in enumerate(m_pair):
		    i_new = cgmMeta.cgmObject(mc.duplicate(i_jnt.mNode,po=True,ic=True)[0])
		    i_new.parent = False
		    i_new.addAttr('cgmNameModifier',str_nameModifier,attrType='string',lock=True)
		    i_new.addAttr('cgmTypeModifier','influence',attrType='string',lock=True)		
		    if l_tmpChain:
			i_new.parent = l_tmpChain[-1].mNode
		    i_new.doName()
		    i_new.rotateOrder = self._jointOrientation#<<<<<<<<<<<<<<<<This would have to change for other orientations    
		    l_tmpChain.append(i_new)
		    
		if addMidInfluence:
		    log.debug("%s.build_simpleInfuenceChains>>> Splitting influence segment: 2 |'%s' >> '%s'"%(self._i_module.getShortName(),m_pair[0].getShortName(),m_pair[1].getShortName()))
		    l_new_chain = joints.insertRollJointsSegment(l_tmpChain[0].mNode,l_tmpChain[1].mNode,1)
		    #Let's name our new joints
		    for ii,jnt in enumerate(l_new_chain):
			i_jnt = cgmMeta.cgmObject(jnt,setClass=True)
			i_jnt.doCopyNameTagsFromObject(m_pair[0].mNode)
			i_jnt.addAttr('cgmName','%s_mid_%s'%(m_pair[0].cgmName,ii),lock=True)
			i_jnt.addAttr('cgmNameModifier',str_nameModifier,attrType='string',lock=True)		
			i_jnt.addAttr('cgmTypeModifier','influence',attrType='string',lock=True)		
			i_jnt.doName()
			ml_midJoints.append(i_jnt)
		    
		#Build the chain lists -------------------------------------------------------------------------------------------
		ml_segmentChain = [l_tmpChain[0]]
		if ml_midJoints:
		    ml_segmentChain.extend(ml_midJoints)
		ml_segmentChain.append(l_tmpChain[-1])
		for i_j in ml_segmentChain:ml_influenceJoints.append(i_j)
		ml_influenceChains.append(ml_segmentChain)#append to influence chains
		
		log.debug("%s.buildHandleChain >> built handle chain %s: %s"%(self._strShortName,i,[i_j.getShortName() for i_j in ml_segmentChain]))
		
	    #Copy orientation of the very last joint to the second to last
	    joints.doCopyJointOrient(ml_influenceChains[-1][-2].mNode,ml_influenceChains[-1][-1].mNode)
    
	    #Figure out how we wanna store this, ml_influence joints 
	    for i_jnt in ml_influenceJoints:
		i_jnt.parent = False
		
	    for i_j in ml_influenceJoints:
		jntUtils.metaFreezeJointOrientation(i_j.mNode)#Freeze orientations
	    
	    #Connect stuff ============================================================================================    
	    for i,ml_chain in enumerate(ml_influenceChains):
		l_chain = [i_jnt.getShortName() for i_jnt in ml_chain]
		log.debug("%s.build_simpleInfuenceChains>>> split chain: %s"%(self._i_module.getShortName(),l_chain))
		self._i_rigNull.msgList_connect(ml_chain,'segment%s_InfluenceJoints'%i,"rigNull")
		log.debug("segment%s_InfluenceJoints>> %s"%(i,self._i_rigNull.msgList_getMessage('segment%s_InfluenceJoints'%i,False)))
	    
	    log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)
	    return {'ml_influenceChains':ml_influenceChains,'ml_influenceJoints':ml_influenceJoints,'ml_segmentHandleJoints':ml_segmentHandleJoints}
	except Exception,error:
	    raise StandardError,"%s >> %s"%(_str_funcName,error)  
	
#>>> Functions
#=============================================================================================================
class RigFactoryFunc(cgmGeneral.cgmFuncCls):
    def __init__(self,*args,**kws):
	"""
	"""
	try:
	    goInstance = args[0]			    
	    if not issubclass(type(goInstance),go):
		raise StandardError,"Not a RigFactory.go instance: '%s'"%goInstance
	    assert mc.objExists(goInstance._i_module.mNode),"Module no longer exists"
	except Exception,error:raise StandardError,"RigFactoryFunc fail | %s"%error
	
	super(RigFactoryFunc, self).__init__(*args, **kws)
	self._str_moduleShortName = goInstance._strShortName
	
	self._str_funcName = 'RigFactoryFunc(%s)'%self._str_moduleShortName	
	
	self._l_ARGS_KWS_DEFAULTS = [{'kw':'goInstance',"default":None}]
	#self.__dataBind__(*args,**kws)	
	
	self.mi_go = goInstance
	self.mi_module = goInstance._i_module

	
def testFunc(*args,**kws):
    class fncWrap(RigFactoryFunc):
	def __init__(self,*args,**kws):
	    """
	    """    
	    super(fncWrap, self).__init__(*args, **kws)
	    self._str_funcName = 'testFunc(%s)'%self._str_moduleShortName	
	    
	    #EXTEND our args and defaults
	    self._l_ARGS_KWS_DEFAULTS.extend([{'kw':'cat',"default":None}])
	    self.__dataBind__(*args,**kws)	
	    self.l_funcSteps = [{'step':'Get Data','call':self._getData}]
	    
	    #=================================================================
	    
	def _getData(self):
	    """
	    """
	    self.report()  
    return fncWrap(*args,**kws).go()

def fnc_verify_faceSkullPlate(*args,**kws):
    class fncWrap(RigFactoryFunc):
	def __init__(self,*args,**kws):
	    """
	    """    
	    super(fncWrap, self).__init__(*args, **kws)
	    self._str_funcName = '__verify_faceSkullPlate(%s)'%self._str_moduleShortName	
	    
	    #EXTEND our args and defaults
	    #self._l_ARGS_KWS_DEFAULTS.extend([{'kw':'cat',"default":None}])
	    self.__dataBind__(*args,**kws)
	    self.l_funcSteps = [{'step':'Find skullPlate','call':self._findData}]
		
	def _findData(self):
	    mi_go = self.mi_go
	    #>> validate ============================================================================
	    mModuleParent = self.mi_module.moduleParent
	    mParentRigNull = mModuleParent.rigNull
	    buffer = mParentRigNull.getMessage('skullPlate')
	    if buffer:
		mi_go._mi_skullPlate = cgmMeta.validateObjArg(mParentRigNull.getMessage('skullPlate'),cgmMeta.cgmObject,noneValid=True)
		mi_go._mi_skullPlate.parent = False
		
		return True
	    
	    #See if we have a helper
	    mi_go._mi_rigHelper = cgmMeta.validateObjArg(self.mi_module.getMessage('helper'),noneValid=True)
	    if mi_go._mi_rigHelper:#See if we have a connected skullPlate
		mi_skullPlate = cgmMeta.validateObjArg(mi_go._mi_rigHelper.getMessage('skullPlate'),cgmMeta.cgmObject,noneValid=True)
		if mi_skullPlate:#then we connect it
		    log.info("%s '%s' connected to module parent"%(self._str_reportStart,mi_skullPlate.p_nameShort))
		    mParentRigNull.connectChildNode(mi_skullPlate,'skullPlate','module')
		    mi_go._mi_skullPlate = mi_skullPlate
		    mi_skullPlate.parent = False
		    return True
	    return False
    return fncWrap(*args,**kws).go()

def isBuildable(goInstance):
    self = goInstance
    _str_funcName = "%s.isBuildable"%self._strShortName
    log.debug(">>> %s "%(_str_funcName) + "="*75)    
    try:
	if not issubclass(type(goInstance),go):
	    log.error("Not a RigFactory.go instance: '%s'"%goInstance)
	    raise StandardError
	self = goInstance#Link
	
	if self._partType not in d_moduleTypeToBuildModule.keys():
	    log.error("%s.isBuildable>>> Not in d_moduleTypeToBuildModule"%(self._strShortName))	
	    return False
	
	try:#Version
	    self._buildVersion = d_moduleTypeToBuildModule[self._partType].__version__    
	except:
	    log.error("%s.isBuildable>>> Missing version"%(self._strShortName))	
	    return False	
	try:#Shapes dict
	    self._shapesDict = d_moduleTypeToBuildModule[self._partType].__d_controlShapes__    
	except:
	    log.error("%s.isBuildable>>> Missing shape dict in module"%(self._strShortName))	
	    return False	
	try:#Joints list
	    self._l_jointAttrs = d_moduleTypeToBuildModule[self._partType].__l_jointAttrs__    
	except:
	    log.error("%s.isBuildable>>> Missing joint attr list in module"%(self._strShortName))	
	    return False
	try:#Build Module
	    #self.build = d_moduleTypeToBuildModule[self._partType].__build__
	    self.buildModule = d_moduleTypeToBuildModule[self._partType]
	except:
	    log.error("%s.isBuildable>>> Missing Build Module"%(self._strShortName))	
	    return False	    
	try:#Build Dict
	    d_moduleTypeToBuildModule[self._partType].__d_buildOrder__
	except:
	    log.error("%s.isBuildable>>> Missing Build Function Dictionary"%(self._strShortName))	
	    return False	    
    
	
	return True
    except Exception,error:
	raise StandardError,"%s >> %s"%(_str_funcName,error)
    

def verify_moduleRigToggles(goInstance):
    """
    Rotate orders
    hips = 3
    """    
    if not issubclass(type(goInstance),go):
	log.error("Not a RigFactory.go instance: '%s'"%goInstance)
	raise StandardError
    
    self = goInstance
    _str_funcName = "%s.verify_moduleRigToggles"%self._strShortName
    log.debug(">>> %s "%(_str_funcName) + "="*75)   
    start = time.clock()    
    try:
	str_settings = str(self._i_masterSettings.getShortName())
	str_partBase = str(self._partName + '_rig')
	str_moduleRigNull = str(self._i_rigNull.getShortName())
	
	self._i_masterSettings.addAttr(str_partBase,enumName = 'off:lock:on', defaultValue = 0, attrType = 'enum',keyable = False,hidden = False)
	try:NodeF.argsToNodes("%s.gutsVis = if %s.%s > 0"%(str_moduleRigNull,str_settings,str_partBase)).doBuild()
	except Exception,error:
	    raise StandardError,"verify_moduleRigToggles>> vis arg fail: %s"%error
	try:NodeF.argsToNodes("%s.gutsLock = if %s.%s == 2:0 else 2"%(str_moduleRigNull,str_settings,str_partBase)).doBuild()
	except Exception,error:
	    raise StandardError,"verify_moduleRigToggles>> lock arg fail: %s"%error
    
	self._i_rigNull.overrideEnabled = 1		
	cgmMeta.cgmAttr(self._i_rigNull.mNode,'gutsVis',lock=False).doConnectOut("%s.%s"%(self._i_rigNull.mNode,'overrideVisibility'))
	cgmMeta.cgmAttr(self._i_rigNull.mNode,'gutsLock',lock=False).doConnectOut("%s.%s"%(self._i_rigNull.mNode,'overrideDisplayType'))    
	
	log.debug("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)
	return True
    except Exception,error:
	raise StandardError,"%s >> %s"%(_str_funcName,error)
    

def bindJoints_connect(goInstance):   
    if not issubclass(type(goInstance),go):
	log.error("Not a RigFactory.go instance: '%s'"%goInstance)
	raise StandardError
    self = goInstance
    start = time.clock()    
    try:
	_str_funcName = "%s.bindJoints_connect"%self._strShortName  
	log.debug(">>> %s "%(_str_funcName) + "="*75)      
	
	l_rigJoints = self._i_rigNull.msgList_get('rigJoints',False) or False
	l_skinJoints = self._i_rigNull.msgList_get('skinJoints',False) or False
	log.debug("%s.connect_ToBind>> skinJoints:  len: %s | joints: %s"%(self._i_module.getShortName(),len(l_skinJoints),l_skinJoints))
	if not l_rigJoints:
	    raise StandardError,"connect_ToBind>> No Rig Joints: %s "%(self._i_module.getShortName())
	if len(l_skinJoints)!=len(l_rigJoints):
	    raise StandardError,"connect_ToBind>> Rig/Skin joint chain lengths don't match: %s | len(skinJoints): %s | len(rigJoints): %s"%(self._i_module.getShortName(),len(l_skinJoints),len(l_rigJoints))
	
	for i,i_jnt in enumerate(self._i_rigNull.skinJoints):
	    log.debug("'%s'>>drives>>'%s'"%(self._i_rigNull.rigJoints[i].getShortName(),i_jnt.getShortName()))
	    pntConstBuffer = mc.parentConstraint(self._i_rigNull.rigJoints[i].mNode,i_jnt.mNode,maintainOffset=True,weight=1)        
	    #pntConstBuffer = mc.pointConstraint(self._i_rigNull.rigJoints[i].mNode,i_jnt.mNode,maintainOffset=False,weight=1)
	    #orConstBuffer = mc.orientConstraint(self._i_rigNull.rigJoints[i].mNode,i_jnt.mNode,maintainOffset=False,weight=1)        
	    
	    attributes.doConnectAttr((self._i_rigNull.rigJoints[i].mNode+'.s'),(i_jnt.mNode+'.s'))
	    #scConstBuffer = mc.scaleConstraint(self._i_rigNull.rigJoints[i].mNode,i_jnt.mNode,maintainOffset=True,weight=1)                
	    #Scale constraint connect doesn't work
	log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)
	
	return True
    except Exception,error:
	raise StandardError,"%s >> %s"%(_str_funcName,error)
    

def bindJoints_connectToBlend(goInstance):
    if not issubclass(type(goInstance),go):
	log.error("Not a RigFactory.go instance: '%s'"%goInstance)
	raise StandardError
    self = goInstance
    _str_funcName = "%s.verify_moduleRigToggles"%self._strShortName
    log.debug(">>> %s "%(_str_funcName) + "="*75)   
    start = time.clock()        
    try:
	l_rigJoints = self._i_rigNull.msgList_get('blendJoints',False) or False
	l_skinJoints = self._i_rigNull.msgList_get('skinJoints',False) or False
	if len(l_skinJoints)!=len(l_rigJoints):
	    raise StandardError,"bindJoints_connectToBlend>> Blend/Skin joint chain lengths don't match: %s"%self._i_module.getShortName()
	
	for i,i_jnt in enumerate(self._i_rigNull.skinJoints):
	    log.debug("'%s'>>drives>>'%s'"%(self._i_rigNull.blendJoints[i].getShortName(),i_jnt.getShortName()))
	    pntConstBuffer = mc.parentConstraint(self._i_rigNull.blendJoints[i].mNode,i_jnt.mNode,maintainOffset=True,weight=1)        
	    #pntConstBuffer = mc.pointConstraint(self._i_rigNull.rigJoints[i].mNode,i_jnt.mNode,maintainOffset=False,weight=1)
	    #orConstBuffer = mc.orientConstraint(self._i_rigNull.rigJoints[i].mNode,i_jnt.mNode,maintainOffset=False,weight=1)        
	    
	    attributes.doConnectAttr((self._i_rigNull.blendJoints[i].mNode+'.s'),(i_jnt.mNode+'.s'))
	    #scConstBuffer = mc.scaleConstraint(self._i_rigNull.rigJoints[i].mNode,i_jnt.mNode,maintainOffset=True,weight=1)                
	    #Scale constraint connect doesn't work
	    log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)	
	return True
    except Exception,error:
	raise StandardError,"%s >> %s"%(_str_funcName,error)

#>>> Module rig functions
"""
You should only pass modules into these 
"""

def get_skinJoints(self, asMeta = True):
    try:
	_str_funcName = "%s.get_skinJoints"%self.p_nameShort  
	log.debug(">>> %s "%(_str_funcName) + "="*75) 
	start = time.clock()        	
	"""
	if not self.isSkeletonized():
	    raise StandardError,"%s.get_skinJoints >> not skeletonized."%(self.p_nameShort)"""
	ml_skinJoints = []
	ml_moduleJoints = self.rigNull.msgList_get('moduleJoints',asMeta = True, cull = True)
	for i,i_j in enumerate(ml_moduleJoints):
	    ml_skinJoints.append(i_j)
	    for attr in __l_moduleJointSingleHooks__:
		str_attrBuffer = i_j.getMessage(attr)
		if str_attrBuffer:ml_skinJoints.append( cgmMeta.validateObjArg(str_attrBuffer) )
	    for attr in __l_moduleJointMsgListHooks__:
		l_buffer = i_j.msgList_get(attr,asMeta = asMeta,cull = True)
		
	log.debug("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)	
	if asMeta:return ml_skinJoints
	if ml_skinJoints:
	    return [obj.p_nameShort for obj in ml_skinJoints]
    except Exception,error:
	raise StandardError, "%s >> %s"(_str_funcName,error)	
    
    
def get_rigHandleJoints(self, asMeta = True):
    #Get our rig handle joints
    try:
	_str_funcName = "%s.get_rigHandleJoints"%self.p_nameShort  
	log.debug(">>> %s "%(_str_funcName) + "="*75) 
	start = time.clock()        		
	"""
	if not self.isSkeletonized():
	    raise StandardError,"%s.get_rigHandleJoints >> not skeletonized."%(self.p_nameShort)"""	
	#ml_rigJoints = self.rigNull.msgList_get('rigJoints')
	#if not ml_rigJoints:
	    #log.error("%s.get_rigHandleJoints >> no rig joints found"%self.getShortName())
	    #return []	
	l_rigHandleJoints = []
	for i_j in self.rigNull.msgList_get('handleJoints'):
	    str_attrBuffer = i_j.getMessage('rigJoint')
	    if str_attrBuffer:
		l_rigHandleJoints.append(str_attrBuffer)
	log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)	
	if asMeta:return cgmMeta.validateObjListArg(l_rigHandleJoints,noneValid=True)	    
	return l_rigHandleJoints
    except Exception,error:
	raise StandardError,"%s >> Probably isn't skeletonized | error: %s"%(_str_funcName,error)
    
    
def get_rigDeformationJoints(self,asMeta = True):
    #Get our joints that segment joints will connect to
    try:
	_str_funcName = "%s.get_rigHandleJoints"%self.p_nameShort  
	log.debug(">>> %s "%(_str_funcName) + "="*75) 	
	start = time.clock()        		
	
	ml_rigJoints = self.rigNull.msgList_get('rigJoints')
	if not ml_rigJoints:
	    log.error("%s.get_rigDeformationJoints >> no rig joints found"%self.getShortName())
	    return []	    
	ml_defJoints = []
	for i_jnt in ml_rigJoints:
	    if not i_jnt.getMessage('scaleJoint'):
		ml_defJoints.append(i_jnt)
		
	log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)	
	    
	if asMeta:return ml_defJoints
	elif ml_defJoints:return [j.p_nameShort for j in ml_defJoints]
	return []
    
    except Exception,error:
	raise StandardError,"get_rigDeformationJoints >> self: %s | error: %s"%(self,error)
    
    
def get_handleJoints(self,asMeta = True):
    #Get our segment joints
    try:
	_str_funcName = "%s.get_handleJoints"%self.p_nameShort  
	log.debug(">>> %s "%(_str_funcName) + "="*75) 
	return self.rigNull.msgList_get('handleJoints',asMeta = asMeta, cull = True)
	"""
	ml_handleJoints = []
	for i_obj in self.templateNull.controlObjects:
	    buffer = i_obj.handleJoint
	    if not buffer:
		log.error("%s.get_handleJoints >> '%s' missing handle joint"%(self.p_nameShort,i_obj.p_nameShort))
		return False
	    ml_handleJoints.append( buffer )
	return ml_handleJoints"""
    except Exception,error:
	raise StandardError,"get_handleJoints >> self: %s | error: %s"%(self,error)
    

def get_segmentHandleTargets(self):
    """
    Figure out which segment handle target joints
    """
    try:
	_str_funcName = "%s.get_segmentHandleTargets"%self.p_nameShort  
	log.debug(">>> %s "%(_str_funcName) + "="*75) 
	start = time.clock()        		
	
	ml_handleJoints = self.rig_getHandleJoints()
	log.debug(ml_handleJoints)
	if not ml_handleJoints:
	    log.error("%s.get_segmentHandleTargets >> failed to find any handle joints at all"%(self.p_nameShort))
	    raise StandardError
	ml_segmentHandleJoints = []#To use later as well
	
	#>> Find our segment handle joints ======================================================================
	#Get our count of roll joints
	l_segmentRollCounts = self.get_rollJointCountList()
	log.debug(l_segmentRollCounts)
	for i,int_i in enumerate(l_segmentRollCounts):
	    if int_i > 0:
		ml_segmentHandleJoints.extend([ml_handleJoints[i],ml_handleJoints[i+1]])
		
	ml_segmentHandleJoints = lists.returnListNoDuplicates(ml_segmentHandleJoints)
	l_segmentHandleJoints = [i_jnt.getShortName() for i_jnt in ml_segmentHandleJoints]
	log.debug("%s.get_segmentHandleTargets >> segmentHandleJoints : %s"%(self.getShortName(),l_segmentHandleJoints))
	
	log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)	
	
	return ml_segmentHandleJoints    
    
    except Exception,error:
	log.error("get_segmentHandleTargets >> self: %s | error: %s"%(self,error))
	return False
    

def get_influenceChains(self):
    try:
	#>>>Influence Joints
	_str_funcName = "%s.get_influenceChains"%self.p_nameShort  
	log.debug(">>> %s "%(_str_funcName) + "="*75) 	
	start = time.clock()        		
	
	l_influenceChains = []
	ml_influenceChains = []
	for i in range(100):
	    str_check = 'segment%s_InfluenceJoints'%i
	    buffer = self.rigNull.msgList_getMessage(str_check)
	    log.debug("Checking %s: %s"%(str_check,buffer))
	    if buffer:
		l_influenceChains.append(buffer)
		ml_influenceChains.append(cgmMeta.validateObjListArg(buffer,cgmMeta.cgmObject))
	    else:
		break 
	log.debug("%s._get_influenceChains>>> Segment Influence Chains -- cnt: %s | lists: %s"%(self.getShortName(),len(l_influenceChains),l_influenceChains)) 		
	log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)	
	return ml_influenceChains
    except Exception,error:
	raise StandardError,"_get_influenceChains >> self: %s | error: %s"%(self,error)
    
def get_segmentHandleChains(self):
    try:
	_str_funcName = "%s.get_segmentHandleChains"%self.p_nameShort  
	log.debug(">>> %s "%(_str_funcName) + "="*75) 	
	start = time.clock()        		
	
	l_segmentHandleChains = []
	ml_segmentHandleChains = []
	for i in range(50):
	    buffer = self.rigNull.msgList_getMessage('segmentHandles_%s'%i,False)
	    if buffer:
		l_segmentHandleChains.append(buffer)
		ml_segmentHandleChains.append(cgmMeta.validateObjListArg(buffer,cgmMeta.cgmObject))
	    else:
		break
	log.debug("%s._get_segmentHandleChains>>> Segment Handle Chains -- cnt: %s | lists: %s"%(self.getShortName(),len(l_segmentHandleChains),l_segmentHandleChains)) 	
	log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)		
	return ml_segmentHandleChains
    except Exception,error:
	raise StandardError,"_get_segmentHandleChains >> self: %s | error: %s"%(self,error)
    
def get_segmentChains(self):
    try:
	#Get our segment joints
	_str_funcName = "%s.get_segmentChains"%self.p_nameShort  
	log.debug(">>> %s "%(_str_funcName) + "="*75) 
	start = time.clock()        		
	
	l_segmentChains = []
	ml_segmentChains = []
	for i in range(50):
	    buffer = self.rigNull.msgList_getMessage('segment%s_Joints'%i,False)
	    if buffer:
		l_segmentChains.append(buffer)
		ml_segmentChains.append(cgmMeta.validateObjListArg(buffer,cgmMeta.cgmObject))
	    else:
		break
	log.debug("%s.get_segmentChains>>> Segment Chains -- cnt: %s | lists: %s"%(self.getShortName(),len(l_segmentChains),l_segmentChains)) 
	log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)			
	return ml_segmentChains
    except Exception,error:
	raise StandardError,"get_segmentChains >> self: %s | error: %s"%(self,error)
    
    
def get_rigJointDriversDict(self,printReport = True):
    """
    Figure out what drives skin joints. BLend joints should have the priority, then segment joints
    """
    _str_funcName = "%s.get_rigJointDriversDict"%self.p_nameShort  
    log.debug(">>> %s "%(_str_funcName) + "="*75)   
    start = time.clock()        		
    
    def __findDefJointFromRigJoint(i_jnt):	    
	if i_jnt.getMessage('rigJoint'):
	    i_rigJoint = cgmMeta.validateObjArg(i_jnt.rigJoint,cgmMeta.cgmObject)
	    if i_rigJoint.hasAttr('scaleJoint'):
		i_scaleJnt = cgmMeta.validateObjArg(i_jnt.scaleJoint,cgmMeta.cgmObject)
		if i_scaleJnt.getShortName() in l_cullRigJoints:
		    #log.debug("Checking: %s | %s"%(i_jnt,i_rigJnt))
		    d_rigIndexToDriverInstance[ml_rigJoints.index(i_scaleJnt)] = i_jnt	
		    return
		else:log.warning("%s no in cull list"%i_rigJnt.getShortName())	    	    
		
	    
	    if i_rigJoint.getShortName() in l_cullRigJoints:
		d_rigIndexToDriverInstance[ml_rigJoints.index(i_scaleJnt)] = i_jnt			
		return
	    else:log.warning("%s no in cull list"%i_rigJnt.getShortName())	    	    
	return False
	    
    #>>>Initial checks
    ml_blendJoints = []
    mll_segmentChains = []
    
    try:
	ml_rigJoints = self.rigNull.msgList_get('rigJoints')
    except:
	log.error("%s.get_deformationRigDriversDict >> no rig joints found"%self.getShortName())
	return {}
    
    try:ml_blendJoints = self.rigNull.msgList_get('rigJoints')
    except:log.warning("%s.get_deformationRigDriversDict >> no blend joints found"%self.getShortName())
	 
    try:mll_segmentChains = get_segmentChains(self)
    except Exception,error:
	log.error("%s.get_deformationRigDriversDict >> mll_segmentChains failure: %s"%(self.getShortName(),error))
    
    if not ml_blendJoints:log.warning("%s.get_deformationRigDriversDict >> no blend joints found"%self.getShortName())
    if not mll_segmentChains:log.warning("%s.get_deformationRigDriversDict >> no segment found"%self.getShortName())
    
    #>>>Declare
    l_cullRigJoints = [i_jnt.getShortName() for i_jnt in ml_rigJoints]	
    d_rigIndexToDriverInstance = {}
    ml_matchTargets = []
    if mll_segmentChains:
	l_matchTargets = []
	for i,ml_chain in enumerate(mll_segmentChains):
	    if i == len(mll_segmentChains)-1:
		ml_matchTargets.extend([i_jnt for i_jnt in ml_chain])
	    else:
		ml_matchTargets.extend([i_jnt for i_jnt in ml_chain[:-1]])		
		
    
    #First let's get our blend joints taken care of:
    if ml_blendJoints:
	for i,i_jnt in enumerate(ml_blendJoints):
	    if i_jnt.getMessage('rigJoint'):
		i_rigJnt = cgmMeta.validateObjArg(i_jnt.rigJoint,cgmMeta.cgmObject)
		if i_rigJnt.getShortName() in l_cullRigJoints:
		    #log.debug("Checking: %s | %s"%(i_jnt,i_rigJnt))
		    d_rigIndexToDriverInstance[ml_rigJoints.index(i_rigJnt)] = i_jnt
		    try:l_cullRigJoints.remove(i_rigJnt.getShortName())
		    except:log.error("%s failed to remove from cull list: %s"%(i_rigJnt.getShortName(),l_cullRigJoints))
		else:
		    log.warning("%s no in cull list"%i_rigJnt.getShortName())
	
		        
    #If we have matchTargets, we're going to match them	
    if ml_matchTargets:
	for i,i_jnt in enumerate(ml_matchTargets):
	    if i_jnt.getMessage('rigJoint'):
		i_rigJnt = cgmMeta.validateObjArg(i_jnt.rigJoint,cgmMeta.cgmObject)
		if i_rigJnt.getMessage('scaleJoint'):
		    log.debug("Scale joint found!")
		    i_scaleJnt = cgmMeta.validateObjArg(i_rigJnt.scaleJoint,cgmMeta.cgmObject)
		    if i_scaleJnt.getShortName() in l_cullRigJoints:
			#log.debug("Checking: %s | %s"%(i_jnt,i_rigJnt))
			d_rigIndexToDriverInstance[ml_rigJoints.index(i_scaleJnt)] = i_jnt	
			try:l_cullRigJoints.remove(i_scaleJnt.getShortName())
			except:log.error("%s failed to remove from cull list: %s"%(i_scaleJnt.getShortName(),l_cullRigJoints))			
		    else:log.warning("scale joint %s not in cull list"%i_rigJnt.getShortName())	   		    
    
		elif i_rigJnt.getShortName() in l_cullRigJoints:
		    #log.debug("Checking: %s | %s"%(i_jnt,i_rigJnt))
		    d_rigIndexToDriverInstance[ml_rigJoints.index(i_rigJnt)] = i_jnt
		    try:l_cullRigJoints.remove(i_rigJnt.getShortName())
		    except:log.error("%s failed to remove from cull list: %s"%(i_rigJnt.getShortName(),l_cullRigJoints))	
		else:
		    log.warning("%s no in cull list"%i_rigJnt.getShortName())
		    
    #If we have any left, do a distance check
    l_matchTargets = [i_jnt.mNode for i_jnt in ml_matchTargets]
    for i,jnt in enumerate(l_cullRigJoints):
	i_jnt = cgmMeta.cgmObject(jnt)
	attachJoint = distance.returnClosestObject(jnt,l_matchTargets)
	int_match = l_matchTargets.index(attachJoint)
	d_rigIndexToDriverInstance[ml_rigJoints.index(i_jnt)] = ml_matchTargets[int_match]    
	l_cullRigJoints.remove(jnt)

    if printReport or l_cullRigJoints:
	log.debug("%s.get_rigJointDriversDict >> "%self.getShortName() + "="*50)
	for i,i_jnt in enumerate(ml_rigJoints):
	    if d_rigIndexToDriverInstance.has_key(i):
		log.debug("'%s'  << driven by << '%s'"%(i_jnt.getShortName(),d_rigIndexToDriverInstance[i].getShortName()))		    
	    else:
		log.debug("%s  << HAS NO KEY STORED"%(i_jnt.getShortName()))	
		
	log.debug("No matches found for %s | %s "%(len(l_cullRigJoints),l_cullRigJoints))	    
	log.debug("="*75)
	    
    if l_cullRigJoints:
	raise StandardError,"%s to find matches for all rig joints: %s"%(i_scaleJnt.getShortName())
    
    log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)		    
    return d_rigIndexToDriverInstance
    
    #except Exception,error:
	#raise StandardError,"get_rigJointDriversDict >> self: %s | error: %s"%(self,error)
	
    
def get_simpleRigJointDriverDict(self,printReport = True):
    log.debug(">>> %s.get_simpleRigJointDriverDict() >> "%(self.p_nameShort) + "="*75) 				    
    """
    Figure out what drives skin joints. BLend joints should have the priority, then segment joints
    """
    _str_funcName = "%s.get_simpleRigJointDriverDict"%self.p_nameShort  
    log.debug(">>> %s "%(_str_funcName) + "="*75)    
    start = time.clock()        		    
    #>>>Initial checks
    ml_blendJoints = []
    mll_segmentChains = []
    try:
	ml_moduleJoints = self.rigNull.msgList_get('moduleJoints')
	#ml_moduleJoints = cgmMeta.validateObjListArg(self.rigNull.moduleJoints,cgmMeta.cgmObject,noneValid=False)
    except:
	log.error("%s.get_simpleRigJointDriverDict >> no rig joints found"%self.getShortName())
	return {}
    try:
	ml_rigJoints = self.rigNull.msgList_get('rigJoints')
    except:
	log.error("%s.get_simpleRigJointDriverDict >> no rig joints found"%self.getShortName())
	return {}
    
    try:
	ml_blendJoints = self.rigNull.msgList_get('blendJoints')
    except:log.warning("%s.get_simpleRigJointDriverDict >> no blend joints found"%self.getShortName())
	 
    try:mll_segmentChains = get_segmentChains(self)
    except Exception,error:
	log.error("%s.get_simpleRigJointDriverDict >> mll_segmentChains failure: %s"%(self.getShortName(),error))
    
    if not ml_blendJoints:log.error("%s.get_simpleRigJointDriverDict >> no blend joints found"%self.getShortName())
    if not mll_segmentChains:log.error("%s.get_simpleRigJointDriverDict >> no segment found"%self.getShortName())
    if not ml_blendJoints or not mll_segmentChains:
	return False
    
    #>>>Declare
    d_rigJointDrivers = {}
    
    ml_moduleRigJoints = []#Build a list of our module rig joints
    for i,i_j in enumerate(ml_moduleJoints):
	ml_moduleRigJoints.append(i_j.rigJoint)
	
    l_cullRigJoints = [i_jnt.getShortName() for i_jnt in ml_moduleRigJoints]	
    
    ml_matchTargets = []
    if mll_segmentChains:
	l_matchTargets = []
	for i,ml_chain in enumerate(mll_segmentChains):
	    ml_matchTargets.extend([i_jnt for i_jnt in ml_chain[:-1]])	
    
    #First time we just check segment chains
    l_matchTargets = [i_jnt.getShortName() for i_jnt in ml_matchTargets]
    for i,i_jnt in enumerate(ml_moduleRigJoints):
	attachJoint = distance.returnClosestObject(i_jnt.mNode,l_matchTargets)
	i_match = cgmMeta.cgmObject(attachJoint)
	if cgmMath.isVectorEquivalent(i_match.getPosition(),i_jnt.getPosition()):
	    d_rigJointDrivers[i_jnt.mNode] = i_match
	    l_cullRigJoints.remove(i_jnt.getShortName())
	    if i_match in ml_matchTargets:
		ml_matchTargets.remove(i_match)
	else:
	    log.debug("'%s' is not in same place as '%s'. Going to second match"%(i_match.getShortName(),i_jnt.getShortName()))
    
    #Now we add blend joints to search list and check again
    ml_matchTargets.extend(ml_blendJoints)    
    l_matchTargets = [i_jnt.getShortName() for i_jnt in ml_matchTargets]
    ml_cullList = cgmMeta.validateObjListArg(l_cullRigJoints,cgmMeta.cgmObject)
    for i,i_jnt in enumerate(ml_cullList):
	attachJoint = distance.returnClosestObject(i_jnt.mNode,l_matchTargets)
	i_match = cgmMeta.cgmObject(attachJoint)
	log.debug("Second match: '%s':'%s'"%(i_jnt.getShortName(),i_match.getShortName()))	
	d_rigJointDrivers[i_jnt.mNode] = i_match
	l_cullRigJoints.remove(i_jnt.getShortName())
	ml_matchTargets.remove(i_match)

    if printReport or l_cullRigJoints:
	log.debug("%s.get_simpleRigJointDriverDict >> "%self.getShortName() + "="*50)
	for i,i_jnt in enumerate(ml_moduleRigJoints):
	    if d_rigJointDrivers.has_key(i_jnt.mNode):
		log.debug("'%s'  << driven by << '%s'"%(i_jnt.getShortName(),d_rigJointDrivers[i_jnt.mNode].getShortName()))		    
	    else:
		log.debug("%s  << HAS NO KEY STORED"%(i_jnt.getShortName()))	
		
	log.debug("No matches found for %s | %s "%(len(l_cullRigJoints),l_cullRigJoints))	    
	log.debug("="*75)
	    
    if l_cullRigJoints:
	raise StandardError,"%s.get_simpleRigJointDriverDict >> failed to find matches for all rig joints: %s"%(self.getShortName(),l_cullRigJoints)
    
    d_returnBuffer = {}
    for str_mNode in d_rigJointDrivers.keys():
	d_returnBuffer[cgmMeta.cgmObject(str_mNode)] = d_rigJointDrivers[str_mNode]
	
    log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)		
    return d_returnBuffer
    
    #except Exception,error:
	#raise StandardError,"get_rigJointDriversDict >> self: %s | error: %s"%(self,error)

def get_report(self):
    #try:
    _str_funcName = "%s.get_report"%self.p_nameShort  
    log.debug(">>> %s "%(_str_funcName) + "="*75)  
    start = time.clock()        		    
    if not self.isSkeletonized():
	log.error("%s.get_report >> Not skeletonized. Wrong report."%(self.p_nameShort))
	return False
    l_moduleJoints = self.rigNull.msgList_get('moduleJoints',False) or []
    l_skinJoints = get_skinJoints(self,False)
    ml_handleJoints = get_handleJoints(self) or []
    l_rigJoints = self.rigNull.msgList_get('rigJoints',False) or []
    ml_rigHandleJoints = get_rigHandleJoints(self) or []
    ml_rigDefJoints = get_rigDeformationJoints(self) or []
    ml_segmentHandleTargets = get_segmentHandleTargets(self) or []
    
    log.info("%s.get_report >> "%self.getShortName() + "="*50)
    log.info("moduleJoints: len - %s | %s"%(len(l_moduleJoints),l_moduleJoints))	
    log.info("skinJoints: len - %s | %s"%(len(l_skinJoints),l_skinJoints))	
    log.info("handleJoints: len - %s | %s"%(len(ml_handleJoints),[i_jnt.getShortName() for i_jnt in ml_handleJoints]))	
    log.info("rigJoints: len - %s | %s"%(len(l_rigJoints),l_rigJoints))	
    log.info("rigHandleJoints: len - %s | %s"%(len(ml_rigHandleJoints),[i_jnt.getShortName() for i_jnt in ml_rigHandleJoints]))	
    log.info("rigDeformationJoints: len - %s | %s"%(len(ml_rigDefJoints),[i_jnt.getShortName() for i_jnt in ml_rigDefJoints]))	
    log.info("segmentHandleTargets: len - %s | %s"%(len(ml_segmentHandleTargets),[i_jnt.getShortName() for i_jnt in ml_segmentHandleTargets]))	
    
    log.info("="*75)
    log.info("%s >> Time >> = %0.3f seconds " % (_str_funcName,(time.clock()-start)) + "-"*75)		
    #except Exception,error:
	#raise StandardError,"get_report >> self: %s | error: %s"%(self,error)	

def get_eyeLook(self):
    try:
	self.isModule()
    except Exception,error:
	raise StandardError,"get_eyeLook >> self: %s | error: %s"%(self,error)
    
    try:#Get our segment joints
	_str_funcName = "%s.verify_eyeLook"%self.p_nameShort  
	log.debug(">>> %s "%(_str_funcName) + "="*75) 	
	#We need a module type, find a head etc
	if self.moduleType != 'eyeball':
	    raise StandardError, "Don't know how to build from non eyeball type yet"
	else:
	    mi_module = self
	    mi_rigNull = self.rigNull
	    mi_puppet = self.modulePuppet
	    
	    try:
		buffer = mi_module.eyeLook
		if buffer:return buffer
	    except:pass
	    
	    ml_puppetEyelooks = mi_puppet.msgList_get('eyeLook')
	    if ml_puppetEyelooks:
		if len(ml_puppetEyelooks) == 1 and ml_puppetEyelooks[0]:
		    return ml_puppetEyelooks[0]
		else:
		    raise StandardError,"More than one puppet eye look"
	    raise StandardError,"The end."
    except Exception,error:
	raise StandardError,"%s >>> Failed to find eyeLook! | error: %s"%(_str_funcName,error)
    
#Module Rig Functions ===================================================================================================    
#!! Duplicated from ModuleFactory due to importing loop 
class ModuleFunc(cgmGeneral.cgmFuncCls):
    def __init__(self,*args,**kws):
	"""
	"""	
	try:
	    try:moduleInstance = kws['moduleInstance']
	    except:moduleInstance = args[0]
	    try:
		assert moduleInstance.isModule()
	    except Exception,error:raise StandardError,"Not a module instance : %s"%error	
	except Exception,error:raise StandardError,"ModuleFunc failed to initialize | %s"%error
	self._str_funcName= "testFModuleFuncunc"		
	super(ModuleFunc, self).__init__(*args, **kws)

	self.mi_module = moduleInstance	
	self._l_ARGS_KWS_DEFAULTS = [{'kw':'moduleInstance',"default":None}]	
	#=================================================================
	
def verify_eyeLook(*args,**kws):
    class fncWrap(ModuleFunc):
	def __init__(self,*args,**kws):
	    """
	    """
	    super(fncWrap, self).__init__(*args, **kws)
	    self._str_funcName= "verify_eyeLook(%s)"%self.mi_module.p_nameShort	
	    self._b_reportTimes = True
	    self.__dataBind__(*args,**kws)	
	    self.l_funcSteps = [{'step':'Get Data','call':self._gatherInfo_},
	                        {'step':'Build','call':self._build_}]
	    
	    #=================================================================
	def _gatherInfo_(self):
	    #We need a module type, find a head etc
	    if self.mi_module.moduleType != 'eyeball':
		raise StandardError, "Don't know how to build from non eyeball type yet"

	def _build_(self):
	    mi_buildModule = self.mi_module
	    mi_rigNull = self.mi_module.rigNull
	    mi_puppet = self.mi_module.modulePuppet
	    
	    try:mShapeCast.go(mi_buildModule,['eyeLook'])
	    except Exception,error:raise StandardError,"shapeCast | %s"%(error)	    
	    try:mi_eyeLookShape = mi_rigNull.shape_eyeLook
	    except Exception,error:raise StandardError,"grabShape | %s"%(error)	    
	    mi_rigNull.doRemove('shape_eyeLook')
	    try:d_buffer = mControlFactory.registerControl(mi_eyeLookShape.mNode,addDynParentGroup=True,
	                                                   addSpacePivots=2)
	    except Exception,error:raise StandardError,"register Control | %s"%(error)
	    mi_eyeLookShape = d_buffer['instance']
	    mi_eyeLookShape.masterGroup.parent = mi_puppet.masterControl
	    
	    try:#Setup dynamic parent -------------------------------------------
		ml_dynParentsToAdd = []
		ml_dynParentsToAdd.append(mi_puppet.masterControl)
		if mi_eyeLookShape.msgList_getMessage('spacePivots'):
		    ml_dynParentsToAdd.extend(mi_eyeLookShape.msgList_get('spacePivots',asMeta = True))	
		
		self.log_info(">>> Dynamic parents to add: %s"%([i_obj.getShortName() for i_obj in ml_dynParentsToAdd]))
		#Add our parents
		mi_dynGroup = mi_eyeLookShape.dynParentGroup
		mi_dynGroup.dynMode = 0
		
		for o in ml_dynParentsToAdd:
		    mi_dynGroup.addDynParent(o)
		mi_dynGroup.rebuild()	    
	    except Exception,error:raise StandardError,"dynParent setup | %s"%(error)	
	    
	    try:#Setup dynamic parent -------------------------------------------
		mi_puppet.msgList_append(mi_eyeLookShape,'eyeLook','puppet')
		mi_buildModule.connectChildNode(mi_eyeLookShape,'eyeLook')
		#need to add connection to face or whatever
	    except Exception,error:raise StandardError,"connect | %s"%(error)	
	    
	    try:#DynSwitch ------------------------------------------------------
		mi_dynSwitch = cgmRigMeta.cgmDynamicSwitch(dynOwner=mi_eyeLookShape.mNode)
	    except Exception,error:raise StandardError,"dynSwitch | %s"%(error)	
		
	    mi_eyeLookShape._setControlGroupLocks(True)
    return fncWrap(*args,**kws).go()
