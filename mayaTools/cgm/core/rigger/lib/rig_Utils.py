"""
cgmLimb
Josh Burton (under the supervision of David Bokser:)
www.cgmonks.com
1/12/2011

Key:
1) Class - Limb
    Creates our rig objects
2)  


"""
# From Python =============================================================
import copy
import re

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
from cgm.core import cgm_Meta as cgmMeta
from cgm.core import cgm_PuppetMeta as cgmPM
from cgm.core.classes import SnapFactory as Snap
from cgm.core.lib import nameTools
from cgm.core.classes import NodeFactory as nFactory
reload(nFactory)
from cgm.lib import (distance,
                     attributes,
                     deformers,
                     lists,
                     rigging,
                     skinning,
                     dictionary,
                     nodes,
                     joints,
                     cgmMath)
#>>> Utilities
#===================================================================
@r9General.Timer
def createCGMSegment(jointList, influenceJoints = None, addSquashStretch = True, addTwist = True,
                     startControl = None, endControl = None,
                     rotateGroupAxis = 'rotateZ',secondaryAxis = None,
                     baseName = None,
                     orientation = 'zyx', moduleInstance = None):
    """
    CGM Joint Segment setup. Inspiriation from Jason Schleifer's work as well as http://faithofthefallen.wordpress.com/2008/10/08/awesome-spine-setup/ on twist methods

    """
    try:
	if startControl is not None:
	    i_startControl = cgmMeta.cgmObject(startControl)
	else:i_startControl=False
	
	if endControl is not None:
	    i_endControl = cgmMeta.cgmObject(endControl)
	else:i_endControl = False
    except StandardError,error:
	log.error("createCGMSegment>>Initial control initialization fail! start: '%s'|end: '%s'"%(startControl,endControl))
	raise StandardError,error 
    
    i_module = False
    if type(jointList) not in [list,tuple]:jointList = [jointList]
    if len(jointList)<3:
	raise StandardError,"createCGMSegment>>> needs at least three joints"
    if moduleInstance is not None:
	if issubclass(type(moduleInstance),cgmPM.cgmModule):
	    i_module = moduleInstance
	    i_rigNull = i_module.rigNull
	    if baseName is None: baseName = i_module.getPartNameBase()#Get part base name	    
	else:
	    log.error("Not a module instance, ignoring: '%s'"%moduleInstance)
    if baseName is None:baseName = 'testSegment'
    
    ml_influenceJoints = False
    if influenceJoints is not None:
	try:ml_influenceJoints = [cgmMeta.cgmObject(jnt,setClass=True) for jnt in influenceJoints]
	except StandardError,error:
	    log.error("createCGMSegment>>influence joint metaclassing failed!")
	    raise StandardError,error 
	if not i_startControl:i_startControl = ml_influenceJoints[0]
	if not i_endControl:i_endControl = ml_influenceJoints[-1]
	
	
    #Good way to verify an instance list? #validate orientation
    #Gather info
    aimVector = dictionary.stringToVectorDict.get("%s+"%orientation[0])
    aimVectorNegative = dictionary.stringToVectorDict.get("%s-"%orientation[0])
    upVector = dictionary.stringToVectorDict.get("%s+"%orientation[1])    
    outChannel = orientation[2]
    upChannel = '%sup'%orientation[1]
    
    try:ml_jointList = [cgmMeta.cgmObject(jnt,setClass=True) for jnt in jointList]
    except StandardError,error:
	log.error("createCGMSegment>>Joint metaclassing failed!")
	raise StandardError,error 
    
    baseDist = distance.returnDistanceBetweenObjects(ml_jointList[0].mNode,ml_jointList[-1].mNode)/2
    
    #=======================================================================================
    try:#Build Transforms
	#Start Anchor
	i_anchorStart = ml_jointList[0].duplicateTransform()
	i_anchorStart.addAttr('cgmType','anchor',attrType='string',lock=True)
	i_anchorStart.doName()
	i_anchorStart.parent = False  
	
	
	#End Anchor
	i_anchorEnd = ml_jointList[-1].duplicateTransform()
	i_anchorEnd.addAttr('cgmType','anchor',attrType='string',lock=True)
	i_anchorEnd.doName()    
	i_anchorEnd.parent = False
	
	if not i_startControl:i_startControl = i_anchorStart
	if not i_startControl:i_endControl = i_anchorEnd

	#Build locs
	#=======================================================================================    
	ml_rigObjects = []
	#>>>Aims
	#Start Aim
	i_aimStartLoc = ml_jointList[0].duplicateTransform()
	i_aimStartLoc.addAttr('cgmType','aim',attrType='string',lock=True)
	i_aimStartLoc.doName()
	i_aimStartLoc.parent = i_anchorStart.mNode     
	ml_rigObjects.append(i_aimStartLoc)
	
	#End Aim
	i_aimEndLoc = ml_jointList[-1].duplicateTransform()
	i_aimEndLoc.addAttr('cgmType','aim',attrType='string',lock=True)
	i_aimEndLoc.doName()
	i_aimEndLoc.parent = i_anchorEnd.mNode 
	ml_rigObjects.append(i_aimEndLoc)
	
	#=====================================
	if addTwist:
	    #>>>Twist loc
	    #Start Aim
	    i_twistStartLoc = ml_jointList[0].duplicateTransform()
	    i_twistStartLoc.addAttr('cgmType','twist',attrType='string',lock=True)
	    i_twistStartLoc.doName()
	    i_twistStartLoc.parent = i_anchorStart.mNode     
	    ml_rigObjects.append(i_twistStartLoc)
	    
	    #End Aim
	    i_twistEndLoc = ml_jointList[-1].duplicateTransform()
	    i_twistEndLoc.addAttr('cgmType','twist',attrType='string',lock=True)
	    i_twistEndLoc.doName()
	    i_twistEndLoc.parent = i_anchorEnd.mNode  
	    ml_rigObjects.append(i_twistEndLoc)
	    
	#=====================================	
	#>>>Attach
	#Start Attach
	i_attachStartLoc = ml_jointList[0].duplicateTransform()
	i_attachStartLoc.addAttr('cgmType','attach',attrType='string',lock=True)
	i_attachStartLoc.doName()
	i_attachStartLoc.parent = i_anchorStart.mNode     
	ml_rigObjects.append(i_attachStartLoc)
	
	#End Attach
	i_attachEndLoc = ml_jointList[-1].duplicateTransform()
	i_attachEndLoc.addAttr('cgmType','attach',attrType='string',lock=True)
	i_attachEndLoc.doName()
	i_attachEndLoc.parent = i_anchorEnd.mNode  
	ml_rigObjects.append(i_attachEndLoc)
	
	#=====================================	
	#>>>Up locs
	i_startUpLoc = ml_jointList[0].duplicateTransform()
	i_startUpLoc.parent = i_anchorStart.mNode  
	i_startUpLoc.addAttr('cgmType','up',attrType='string',lock=True)
	i_startUpLoc.doName()
	ml_rigObjects.append(i_startUpLoc)
	attributes.doSetAttr(i_startUpLoc.mNode,'t%s'%orientation[1],baseDist)
	
	#End
	i_endUpLoc = ml_jointList[-1].duplicateTransform()
	i_endUpLoc.parent = i_anchorEnd.mNode     
	i_endUpLoc.addAttr('cgmType','up',attrType='string',lock=True)
	i_endUpLoc.doName()
	ml_rigObjects.append(i_endUpLoc)
	attributes.doSetAttr(i_endUpLoc.mNode,'t%s'%orientation[1],baseDist)
	
	#Parent the influenceJoints
	ml_influenceJoints[0].parent = i_attachStartLoc.mNode
	ml_influenceJoints[-1].parent = i_attachEndLoc.mNode
	
	
	if i_module:#if we have a module, connect vis
	    for i_obj in ml_rigObjects:
		i_obj.overrideEnabled = 1		
		cgmMeta.cgmAttr(i_module.rigNull.mNode,'visRig',lock=False).doConnectOut("%s.%s"%(i_obj.mNode,'overrideVisibility'))
	    
	    
	    
    except StandardError,error:
	log.error("createCGMSegment>>Joint anchor and loc build fail! | start joint: %s"%ml_jointList[0].getShortName())
	raise StandardError,error 
     
    #======================================================================================= 
    try:#Constrain Locs
	cBuffer = mc.orientConstraint([i_anchorStart.mNode,i_aimStartLoc.mNode],
	                              i_attachStartLoc.mNode,
	                              maintainOffset = False, weight = 1)[0]
	i_startOrientConstraint = cgmMeta.cgmNode(cBuffer,setClass=True)
	
	cBuffer = mc.orientConstraint([i_anchorEnd.mNode,i_aimEndLoc.mNode],
	                              i_attachEndLoc.mNode,
	                              maintainOffset = False, weight = 1)[0]
	i_endOrientConstraint = cgmMeta.cgmNode(cBuffer,setClass=True)
	
	
    except StandardError,error:
	log.error("createCGMSegment>>Constrain locs build fail! | start joint: %s"%ml_jointList[0].getShortName())
	raise StandardError,error 
    
    #======================================================================================= 
    try:#Build constraint blend
	#start blend
	
	d_startFollowBlendReturn = nFactory.createSingleBlendNetwork([i_startControl.mNode,'followRoot'],
	                                                             [i_startControl.mNode,'resultRootFollow'],
	                                                             [i_startControl.mNode,'resultAimFollow'],
	                                                             keyable=True)
	targetWeights = mc.orientConstraint(i_startOrientConstraint.mNode,q=True, weightAliasList=True)
	#Connect                                  
	d_startFollowBlendReturn['d_result1']['mi_plug'].doConnectOut('%s.%s' % (i_startOrientConstraint.mNode,targetWeights[0]))
	d_startFollowBlendReturn['d_result2']['mi_plug'].doConnectOut('%s.%s' % (i_startOrientConstraint.mNode,targetWeights[1]))
	
	#EndBlend
	d_endFollowBlendReturn = nFactory.createSingleBlendNetwork([i_endControl.mNode,'followRoot'],
	                                                             [i_endControl.mNode,'resultRootFollow'],
	                                                             [i_endControl.mNode,'resultAimFollow'],
	                                                             keyable=True)
	targetWeights = mc.orientConstraint(i_endOrientConstraint.mNode,q=True, weightAliasList=True)
	#Connect                                  
	d_endFollowBlendReturn['d_result1']['mi_plug'].doConnectOut('%s.%s' % (i_endOrientConstraint.mNode,targetWeights[0]))
	d_endFollowBlendReturn['d_result2']['mi_plug'].doConnectOut('%s.%s' % (i_endOrientConstraint.mNode,targetWeights[1]))
	
    except StandardError,error:
	log.error("createCGMSegment>>Constrain locs build fail! | start joint: %s"%ml_jointList[0].getShortName())
	raise StandardError,error 
    
    #======================================================================================= 
    try:#Build segment
	d_segmentBuild = createSegmentCurve(jointList,orientation,secondaryAxis,
	                                    baseName, moduleInstance)
    
	mi_splineCurve = d_segmentBuild['mi_segmentCurve']
	ml_splineIKJoints = d_segmentBuild['ml_splineIKJoints']
	mi_scaleBuffer = d_segmentBuild['mi_scaleBuffer']
	
	
	#Add squash
	if addSquashStretch:
	    addSquashAndStretchToControlSurfaceSetup(mi_scaleBuffer.mNode,
		                                     [i_jnt.mNode for i_jnt in ml_jointList],
		                                     moduleInstance=moduleInstance)
	#Twist
	if addTwist:
	    i_twistStartPlug = cgmMeta.cgmAttr(mi_splineCurve.mNode,'twistStart',attrType='float',keyable=True) 
	    i_twistEndPlug = cgmMeta.cgmAttr(mi_splineCurve.mNode,'twistEnd',attrType='float',keyable=True)
	    capAim = orientation[0].capitalize()
	    log.info("capAim: %s"%capAim)
	    d_twistReturn = addRibbonTwistToControlSurfaceSetup([i_jnt.mNode for i_jnt in ml_jointList],
	                                                        [i_twistStartPlug.obj.mNode,i_twistStartPlug.attr],
	                                                        [i_twistEndPlug.obj.mNode,i_twistEndPlug.attr]) 
	    
	    #Connect resulting full sum to our last spline IK joint to get it's twist
	    attributes.doConnectAttr(i_twistEndPlug.p_combinedName,"%s.rotate%s"%(ml_splineIKJoints[-1].mNode,capAim))
	    
	    d_twistReturn['mi_pmaTwistSum'].mNode
	    
	    if i_startControl:
		i_twistStartPlug.doConnectIn("%s.rotate%s"%(i_startControl.mNode,capAim))
	    if i_endControl:
		i_twistEndPlug.doConnectIn("%s.rotate%s"%(i_endControl.mNode,capAim))	
		
    except StandardError,error:
	log.error("createCGMSegment>>Build segment fail! | start joint: %s"%ml_jointList[0].getShortName())
	raise StandardError,error     
    
    #=======================================================================================     
    try:#Skin curve   
	if ml_influenceJoints:#if we have influence joints, we're gonna skin our curve
	    #Surface influence joints cluster#
	    i_controlSurfaceCluster = cgmMeta.cgmNode(mc.skinCluster ([i_jnt.mNode for i_jnt in ml_influenceJoints],
		                                                      mi_splineCurve.mNode,
		                                                      tsb=True,
		                                                      maximumInfluences = 3,
		                                                      normalizeWeights = 1,dropoffRate=2.5)[0])
	    
	    i_controlSurfaceCluster.addAttr('cgmName', baseName, lock=True)
	    i_controlSurfaceCluster.addAttr('cgmTypeModifier','segmentCurve', lock=True)
	    i_controlSurfaceCluster.doName()
	    """
	    if len(ml_influenceJoints) == 2:
		controlCurveSkinningTwoJointBlend(mi_splineCurve.mNode,start = ml_influenceJoints[0].mNode,
		                                  end = ml_influenceJoints[-1].mNode,tightLength=1,
		                                  blendLength = int(len(jointList)/2))"""
	    
    except StandardError,error:
	log.error("createCGMSegment>>Build segment fail! | start joint: %s"%ml_jointList[0].getShortName())
	raise StandardError,error 
    
    #=======================================================================================  
    try:#Aim constraints
	startAimTarget = i_attachEndLoc.mNode
	endAimTarget = i_attachStartLoc.mNode
	
	cBuffer = mc.aimConstraint(startAimTarget,
	                           i_aimStartLoc.mNode,
	                           maintainOffset = True, weight = 1,
	                           aimVector = aimVector,
	                           upVector = upVector,
	                           worldUpObject = i_startUpLoc.mNode,
	                           worldUpType = 'object' ) 
	i_startAimConstraint = cgmMeta.cgmNode(cBuffer[0],setClass=True)
	
	cBuffer = mc.aimConstraint(endAimTarget,
	                           i_aimEndLoc.mNode,
	                           maintainOffset = True, weight = 1,
	                           aimVector = aimVectorNegative,
	                           upVector = upVector,
	                           worldUpObject = i_startUpLoc.mNode,
	                           worldUpType = 'object' ) 
	i_endAimConstraint = cgmMeta.cgmNode(cBuffer[0],setClass=True)  
	
    except StandardError,error:
	log.error("createCGMSegment>>Build aim constraints! | start joint: %s"%ml_jointList[0].getShortName())
	raise StandardError,error   
    
    return {'mi_anchorStart':i_anchorStart,'mi_anchorEnd':i_anchorEnd,
            'mi_constraintStartAim':i_startAimConstraint,'mi_constraintEndAim':i_endAimConstraint}
      
    
@r9General.Timer
def controlSurfaceSmoothWeights(controlSurface,start = None, end = None):
    """Weight fixer for surfaces"""
    if issubclass(type(controlSurface),cgmMeta.cgmNode):
	i_surface = controlSurface
    elif mc.objExists(controlSurface):
	i_surface = cgmMeta.cgmNode(controlSurface)
    else:
	raise StandardError,"controlSurfaceSmoothWeights failed. Surface doesn't exist: '%s'"%controlSurface
    
    l_cvs = i_surface.getComponents('cv')
    l_skinClusters = deformers.returnObjectDeformers(i_surface.mNode,deformerTypes = 'skinCluster')
    i_skinCluster = cgmMeta.cgmNode(l_skinClusters[0])
    l_influenceObjects = skinning.queryInfluences(i_skinCluster.mNode) or []
    
    log.info("l_skinClusters: '%s'"%l_skinClusters)
    log.info("i_skinCluster: '%s'"%i_skinCluster)
    log.info("l_influenceObjects: '%s'"%l_influenceObjects)
    
    if not i_skinCluster and l_influenceObjects:
	raise StandardError,"controlSurfaceSmoothWeights failed. Not enough info found"
    
    cvStarts = [int(cv[-5]) for cv in l_cvs]
    cvEnds = [int(cv[-2]) for cv in l_cvs]
    
    cvStarts = lists.returnListNoDuplicates(cvStarts)
    cvEnds = lists.returnListNoDuplicates(cvEnds)
    log.info(cvStarts)
    log.info(cvEnds)  
    
    #if len{cvEnds)<4:
	#raise StandardError,"Must have enough cvEnds. cvEnds: %s"%(cvEnds)
    if len(cvEnds)<(blendLength + 2):
	raise StandardError,"Must have enough cvEnds. blendLength: %s"%(blendLength)	
    
    blendFactor = 1 * ((2+1)*.1)
    log.info("blendFactor: %s"%blendFactor)
    
    #>>>Tie down tart and ends
    for influence in [start,end]:
	if influence == start:
	    cvBlendEnds = cvEnds[:blendLength+2]
	    log.info("%s: %s"%(influence,cvBlendEnds))
	if influence == end:
	    cvBlendEnds = cvEnds[-(blendLength+2):]
	    cvBlendEnds.reverse()
	    log.info("%s: %s"%(influence,cvBlendEnds))
	for i,endInt in enumerate(cvBlendEnds):
	    if i in [0,1]:
		for startInt in cvStarts:
		    mc.skinPercent(i_skinCluster.mNode,("%s.cv[%s][%s]"%(i_surface.mNode,startInt,endInt)), tv = [influence,1])
		
	    for startInt in cvStarts:
		mc.skinPercent(i_skinCluster.mNode,("%s.cv[%s][%s]"%(i_surface.mNode,startInt,endInt)),
		               tv = [influence,1-(i*blendFactor)])
    
@r9General.Timer
def controlCurveSkinningTwoJointBlend(curve,start = None, end = None, tightLength = 1, blendLength = None):
    """Weight fixer for curves"""
    if issubclass(type(curve),cgmMeta.cgmNode):
	i_curve = curve
    elif mc.objExists(curve):
	i_curve = cgmMeta.cgmNode(curve)
    else:
	raise StandardError,"curveSmoothWeights failed. Surface doesn't exist: '%s'"%curve
    
    l_cvs = i_curve.getComponents('cv')
    l_skinClusters = deformers.returnObjectDeformers(i_curve.mNode,deformerTypes = 'skinCluster')
    i_skinCluster = cgmMeta.cgmNode(l_skinClusters[0])
    l_influenceObjects = skinning.queryInfluences(i_skinCluster.mNode) or []
    
    log.info("l_skinClusters: '%s'"%l_skinClusters)
    log.info("i_skinCluster: '%s'"%i_skinCluster)
    log.info("l_influenceObjects: '%s'"%l_influenceObjects)
    
    if not i_skinCluster and l_influenceObjects:
	raise StandardError,"curveSmoothWeights failed. Not enough info found"
    
    l_cvInts = [int(cv[-2]) for cv in l_cvs]
    l_cvInts = lists.returnListNoDuplicates(l_cvInts)
    
    if blendLength is None:
	blendFactor = 1/ float(len(l_cvInts[tightLength:-tightLength])+1)
    else:
	blendFactor = 1/ float(len(l_cvInts[tightLength:-tightLength])+(blendLength+1))
	
    #( len(l_cvInts[tightLength:-tightLength] )*.5)
    
    log.info("blendFactor: %s "%blendFactor)
    
    #>>>Tie down tart and ends
    for influence in [start,end]:
	log.info("Influence: %s"%influence)
	if influence == start:
	    cvBlendRange = l_cvInts[tightLength:-tightLength]
	    log.info("%s: %s"%(influence,cvBlendRange))
	    for cv in l_cvInts[:tightLength]:
		mc.skinPercent(i_skinCluster.mNode,("%s.cv[%s]"%(i_curve.mNode,cv)), tv = [influence,1])
	    
	if influence == end:
	    cvBlendRange = l_cvInts[tightLength:-tightLength]
	    cvBlendRange.reverse()
	    log.info("%s: %s"%(influence,cvBlendRange))
	    for cv in l_cvInts[-tightLength:]:
		mc.skinPercent(i_skinCluster.mNode,("%s.cv[%s]"%(i_curve.mNode,cv)), tv = [influence,1])
	
	if blendLength:	
	    for i,cv in enumerate(cvBlendRange[:blendLength]):
		log.info("cv: %s | blendFactor: %s"%(cv,1 - ((i+1)*blendFactor)))
		mc.skinPercent(i_skinCluster.mNode,("%s.cv[%s]"%(i_curve.mNode,cv)),
		               tv = [influence,1-((i+1)*blendFactor)])	    
	else:
	    for i,cv in enumerate(cvBlendRange):
		log.info("cv: %s | blendFactor: %s"%(cv,1 - ((i+1)*blendFactor)))
		mc.skinPercent(i_skinCluster.mNode,("%s.cv[%s]"%(i_curve.mNode,cv)),
		               tv = [influence,1-((i+1)*blendFactor)])
@r9General.Timer
def controlCurveTightenEndWeights(curve,start = None, end = None, blendLength = 2):
    """Weight fixer for curves"""
    if issubclass(type(curve),cgmMeta.cgmNode):
	i_curve = curve
    elif mc.objExists(curve):
	i_curve = cgmMeta.cgmNode(curve)
    else:
	raise StandardError,"curveSmoothWeights failed. Surface doesn't exist: '%s'"%curve
    
    l_cvs = i_curve.getComponents('cv')
    l_skinClusters = deformers.returnObjectDeformers(i_curve.mNode,deformerTypes = 'skinCluster')
    i_skinCluster = cgmMeta.cgmNode(l_skinClusters[0])
    l_influenceObjects = skinning.queryInfluences(i_skinCluster.mNode) or []
    
    log.info("l_skinClusters: '%s'"%l_skinClusters)
    log.info("i_skinCluster: '%s'"%i_skinCluster)
    log.info("l_influenceObjects: '%s'"%l_influenceObjects)
    
    if not i_skinCluster and l_influenceObjects:
	raise StandardError,"curveSmoothWeights failed. Not enough info found"
    
    l_cvInts = [int(cv[-2]) for cv in l_cvs]
    
    l_cvInts = lists.returnListNoDuplicates(l_cvInts)
    
    #if len{cvEnds)<4:
	#raise StandardError,"Must have enough cvEnds. cvEnds: %s"%(cvEnds)
    if len(l_cvInts)<(blendLength + 2):
	raise StandardError,"Must have enough cvEnds. blendLength: %s"%(blendLength)	
    
    blendFactor = 1 * ((blendLength+1)*.1)
    log.info("blendFactor: %s"%blendFactor)
    
    #>>>Tie down tart and ends
    for influence in [start,end]:
	log.info("Influence: %s"%influence)
	if influence == start:
	    cvBlendRange = l_cvInts[:blendLength+2]
	    log.info("%s: %s"%(influence,cvBlendRange))
	if influence == end:
	    cvBlendRange = l_cvInts[-(blendLength+2):]
	    cvBlendRange.reverse()
	    log.info("%s: %s"%(influence,cvBlendRange))
	for i,cv in enumerate(cvBlendRange):
	    if i in [0,1]:
		mc.skinPercent(i_skinCluster.mNode,("%s.cv[%s]"%(i_curve.mNode,cv)), tv = [influence,1])
		
	    else:
		mc.skinPercent(i_skinCluster.mNode,("%s.cv[%s]"%(i_curve.mNode,cv)),
		               tv = [influence,1-(i*blendFactor)])
    
@r9General.Timer
def createSegmentCurve(jointList,orientation = 'zyx',secondaryAxis = None,
                       baseName ='test', moduleInstance = None):
    """
    """
    if type(jointList) not in [list,tuple]:jointList = [jointList]
    
    #Good way to verify an instance list?
    #validate orientation
    outChannel = orientation[2]
    upChannel = '%sup'%orientation[1]
    
    i_module = False
    i_rigNull = False
    if moduleInstance is not None:
	if issubclass(type(moduleInstance),cgmPM.cgmModule):
	    i_module = moduleInstance
	    i_rigNull = i_module.rigNull
	else:
	    log.error("Not a module instance, ignoring: '%s'"%moduleInstance)
	baseName = i_module.getPartNameBase()
    
    #Create our group
    i_grp = cgmMeta.cgmObject(name = 'newgroup')
    i_grp.addAttr('cgmName', str(baseName), lock=True)
    i_grp.addAttr('cgmTypeModifier','surfaceFollow', lock=True)
    i_grp.doName()
    
    ml_jointList = [cgmMeta.cgmObject(j) for j in jointList]#Initialize original joints

    if not moduleInstance:#if it is, we can assume it's right
	if secondaryAxis is None:
	    raise StandardError,"createControlSurfaceSegment>>> Must have secondaryAxis arg if no moduleInstance is passed"
	for i_jnt in ml_jointList:
	    """
	    Cannot iterate how important this step is. Lost a day trying to trouble shoot why one joint chain worked and another didn't.
	    WILL NOT connect right without this.
	    """
    	    joints.orientJoint(i_jnt.mNode,orientation,secondaryAxis)
	    

    #Joints
    #=========================================================================
    #Create spline IK joints
    #>>Surface chain    
    l_splineIKJoints = mc.duplicate(jointList,po=True,ic=True,rc=True)
    ml_splineIKJoints = []
    for i,j in enumerate(l_splineIKJoints):
	i_j = cgmMeta.cgmObject(j,setClass=True)
	i_j.addAttr('cgmName',baseName,lock=True)
	i_j.addAttr('cgmTypeModifier','splineIK',attrType='string')
	i_j.doName()
	l_splineIKJoints[i] = i_j.mNode
	ml_splineIKJoints.append(i_j)

    #Create Curve
    i_splineSolver = cgmMeta.cgmNode(nodeType = 'ikSplineSolver',setClass=True)
    buffer = mc.ikHandle( sj=ml_splineIKJoints[0].mNode, ee=ml_splineIKJoints[-1].mNode,simplifyCurve=False,
                          solver = i_splineSolver.mNode, ns = 4, rootOnCurve=True,forceSolver = True,
                          createCurve = True,snapHandleFlagToggle=True )  
    
    i_segmentCurve = cgmMeta.cgmObject( buffer[2],setClass=True )
    i_segmentCurve.addAttr('cgmName',str(baseName),attrType='string',lock=True)    
    i_segmentCurve.addAttr('cgmType','splineIKCurve',attrType='string',lock=True)
    i_segmentCurve.doName()
    if i_module:#if we have a module, connect vis
	 i_segmentCurve.overrideEnabled = 1		
	 cgmMeta.cgmAttr(i_module.rigNull.mNode,'visSegment',lock=False).doConnectOut("%s.%s"%(i_segmentCurve.mNode,'overrideVisibility'))    

    i_ikHandle = cgmMeta.cgmObject( buffer[0],setClass=True )
    i_ikEffector = cgmMeta.cgmObject( buffer[1],setClass=True )
    
    #Joints
    #=========================================================================
    ml_ = []
    ml_pointOnCurveInfos = []
    ml_upGroups = []
    
    #First thing we're going to do is create our follicles
    shape = mc.listRelatives(i_segmentCurve.mNode,shapes=True)[0]
    for i,i_jnt in enumerate(ml_jointList):   
        l_closestInfo = distance.returnNearestPointOnCurveInfo(i_jnt.mNode,i_segmentCurve.mNode)
        log.debug("%s : %s"%(i_jnt.mNode,l_closestInfo))
        #>>> """Follicle""" =======================================================
	i_closestPointNode = cgmMeta.cgmNode(nodeType = 'pointOnCurveInfo')
        mc.connectAttr ((shape+'.worldSpace'),(i_closestPointNode.mNode+'.inputCurve'))	
	
        #> Name
        i_closestPointNode.doStore('cgmName',i_jnt.mNode)
        i_closestPointNode.doName()
        #>Set follicle value
        i_closestPointNode.parameter = l_closestInfo['parameter']
        
        ml_pointOnCurveInfos.append(i_closestPointNode)
		
	#if i_module:#if we have a module, connect vis
	    #i_follicleTrans.overrideEnabled = 1		
	    #cgmMeta.cgmAttr(i_module.rigNull.mNode,'visRig',lock=False).doConnectOut("%s.%s"%(i_follicleTrans.mNode,'overrideVisibility'))
	
	
	#>>> loc
	#First part of full ribbon wist setup
	if i_jnt != ml_jointList[-1]:
	    i_upLoc = i_jnt.doLoc()#Make up Loc
	    i_locRotateGroup = i_jnt.duplicateTransform(False)#group in place
	    i_locRotateGroup.parent = ml_splineIKJoints[i].mNode
	    i_locRotateGroup.doStore('cgmName',i_jnt.mNode)	    
	    i_locRotateGroup.addAttr('cgmTypeModifier','rotate',lock=True)
	    i_locRotateGroup.doName()
	    
	    #Store the rotate group to the joint
	    i_jnt.connectChildNode(i_locRotateGroup,'rotateUpGroup','drivenJoint')
	    i_zeroGrp = cgmMeta.cgmObject( i_locRotateGroup.doGroup(True),setClass=True )
	    i_zeroGrp.addAttr('cgmTypeModifier','zero',lock=True)
	    i_zeroGrp.doName()
	    #connect some other data
	    i_locRotateGroup.connectChildNode(i_locRotateGroup.parent,'zeroGroup')
	    i_locRotateGroup.connectChildNode(i_upLoc,'upLoc')
	    mc.makeIdentity(i_locRotateGroup.mNode, apply=True,t=1,r=1,s=1,n=0)
	    
	    i_upLoc.parent = i_locRotateGroup.mNode
	    mc.move(0,10,0,i_upLoc.mNode,os=True)	
	    ml_upGroups.append(i_upLoc)
	    
	    if i_module:#if we have a module, connect vis
		i_upLoc.overrideEnabled = 1		
		cgmMeta.cgmAttr(i_module.rigNull.mNode,'visRig',lock=False).doConnectOut("%s.%s"%(i_upLoc.mNode,'overrideVisibility'))
	    
	
    #Orient constrain our last joint to our splineIK Joint
    mc.orientConstraint(ml_splineIKJoints[-1].mNode,ml_jointList[-1].mNode,maintainOffset = True)
    
    #>>>Create scale stuff
    #>>>Create IK effectors,Create distance nodes
    l_iIK_effectors = []
    l_iIK_handles = []  
    l_iDistanceObjects = []
    i_distanceShapes = []  
    for i,i_jnt in enumerate(ml_jointList[:-1]):
        ik_buffer = mc.ikHandle (startJoint=i_jnt.mNode,
                                 endEffector = ml_jointList[i+1].mNode,
                                 setupForRPsolver = True, solver = 'ikRPsolver',
                                 enableHandles=True )
        #Handle
        i_IK_Handle = cgmMeta.cgmObject(ik_buffer[0],setClass=True)
        i_IK_Handle.parent = ml_splineIKJoints[i+1].mNode
        i_IK_Handle.doStore('cgmName',i_jnt.mNode)    
        i_IK_Handle.doName()
        
        #Effector
        i_IK_Effector = cgmMeta.cgmObject(ik_buffer[1])        
        #i_IK_Effector.doStore('cgmName',i_jnt.mNode)    
        i_IK_Effector.doName()
        
        l_iIK_handles.append(i_IK_Handle)
        l_iIK_effectors.append(i_IK_Effector)
        
	if i_module:#if we have a module, connect vis
	    i_IK_Handle.overrideEnabled = 1		
	    cgmMeta.cgmAttr(i_module.rigNull.mNode,'visRig',lock=False).doConnectOut("%s.%s"%(i_IK_Handle.mNode,'overrideVisibility'))
        
        #>> Distance nodes
        i_distanceShape = cgmMeta.cgmNode( mc.createNode ('distanceDimShape') )        
        i_distanceObject = cgmMeta.cgmObject( i_distanceShape.getTransform() )
        i_distanceObject.doStore('cgmName',i_jnt.mNode)
        i_distanceObject.addAttr('cgmType','measureNode',lock=True)
        i_distanceObject.doName(nameShapes = True)
	i_distanceObject.parent = i_grp.mNode#parent it
        i_distanceObject.overrideEnabled = 1
        i_distanceObject.overrideVisibility = 1
	
        #Connect things
        mc.connectAttr ((ml_pointOnCurveInfos[i].mNode+'.position'),(i_distanceShape.mNode+'.startPoint'))
        mc.connectAttr ((ml_pointOnCurveInfos[i+1].mNode+'.position'),(i_distanceShape.mNode+'.endPoint'))
        
        l_iDistanceObjects.append(i_distanceObject)
        i_distanceShapes.append(i_distanceShape)
	
	if i_module:#Connect hides if we have a module instance:
	    cgmMeta.cgmAttr(i_module.rigNull.mNode,'visRig',lock=False).doConnectOut("%s.%s"%(i_distanceObject.mNode,'overrideVisibility'))
	
    #>> Second part for the full twist setup
    aimChannel = orientation[0]  
    fixOptions = [0,90,180,-90,-180]      

    for i,i_jnt in enumerate(ml_jointList[:-1]):
	rotBuffer = mc.xform (i_jnt.mNode, q=True, ws=True, ro=True)
	log.info("rotBuffer: %s"%rotBuffer)
	#Create the poleVector
	poleVector = mc.poleVectorConstraint (ml_upGroups[i].mNode,l_iIK_handles[i].mNode)  	
	optionCnt = 0
	while not cgmMath.isFloatEquivalent((mc.getAttr(i_jnt.mNode+'.r'+aimChannel)),0):
	    log.info("%s.r%s: %s"%(i_jnt.getShortName(),aimChannel,mc.getAttr(i_jnt.mNode+'.r'+aimChannel)))
	    log.info ("Trying the following for '%s':%s" %(l_iIK_handles[i].getShortName(),fixOptions[optionCnt]))
	    attributes.doSetAttr(l_iIK_handles[i].mNode,'twist',fixOptions[optionCnt])
	    optionCnt += 1
	    if optionCnt == 4:
		raise StandardError,"failed to find a good twist value to zero out poleVector: %s"%(i_jnt.getShortName())
	    
	if mc.xform (i_jnt.mNode, q=True, ws=True, ro=True) != rotBuffer:
	    log.info("Found the following on '%s': %s"%(i_jnt.getShortName(),mc.xform (i_jnt.mNode, q=True, ws=True, ro=True)))
    
    #>>>Hook up scales
    #==========================================================================
    #Translate scale
    #Buffer
    i_jntScaleBufferNode = cgmMeta.cgmBufferNode(name = str(baseName),overideMessageCheck=True)
    i_jntScaleBufferNode.addAttr('cgmType','distanceBuffer')
    i_jntScaleBufferNode.addAttr('masterScale',value = 1.0, attrType='float')        
    i_jntScaleBufferNode.doName()
    
    i_jntScaleBufferNode.connectParentNode(i_segmentCurve.mNode,'segmentCurve','scaleBuffer')
    ml_mainMDs = []
    for i,i_jnt in enumerate(ml_jointList[:-1]):
	
	#Store our distance base to our buffer
        try:i_jntScaleBufferNode.store(i_distanceShapes[i].distance)#Store to our buffer
	except StandardError,error:
	    log.error(error)
	    raise StandardError,"Failed to store joint distance: %s"%i_distanceShapes[i].mNode
	
	#Create the mdNode
	i_md = cgmMeta.cgmNode(mc.createNode('multiplyDivide'))
	i_md.operation = 2
	i_md.doStore('cgmName',i_jnt.mNode)
	i_md.addAttr('cgmTypeModifier','masterScale')
	i_md.doName()
	attributes.doConnectAttr('%s.%s'%(i_distanceShapes[i].mNode,'distance'),#>>
	                         '%s.%s'%(i_md.mNode,'input1X'))
	attributes.doConnectAttr('%s.%s'%(i_jntScaleBufferNode.mNode,i_jntScaleBufferNode.d_indexToAttr[i]),#>>
	                         '%s.%s'%(i_md.mNode,'input2X'))
	
	#Connect to the joint
	i_attr = cgmMeta.cgmAttr(i_jntScaleBufferNode.mNode,"distance_%s"%i,attrType = 'float',initialValue=0,lock=True)		
	i_attrResult = cgmMeta.cgmAttr(i_jntScaleBufferNode.mNode,"scaleResult_%s"%i,attrType = 'float',initialValue=0,lock=True)	
	try:
	    i_attr.doConnectIn('%s.%s'%(i_distanceShapes[i].mNode,'distance'))
	    i_attrResult.doConnectIn('%s.%s'%(i_md.mNode,'output.outputX'))
	    i_attrResult.doConnectOut('%s.s%s'%(i_jnt.mNode,orientation[0]))
	    
	    for axis in orientation[1:]:
		attributes.doConnectAttr('%s.%s'%(i_jntScaleBufferNode.mNode,'masterScale'),#>>
		                         '%s.s%s'%(i_jnt.mNode,axis))	    
	except StandardError,error:
	    log.error(error)
	    raise StandardError,"Failed to connect joint attrs: %s"%i_jnt.mNode
		
	ml_mainMDs.append(i_md)#store the md
	for axis in ['scaleX','scaleY','scaleZ']:
	    attributes.doConnectAttr('%s.%s'%(i_jnt.mNode,axis),#>>
		                     '%s.%s'%(ml_splineIKJoints[i].mNode,axis))	 	

	
    #Connect last joint scale to second to last
    for axis in ['scaleX','scaleY','scaleZ']:
	attributes.doConnectAttr('%s.%s'%(ml_jointList[-2].mNode,axis),#>>
                                 '%s.%s'%(ml_jointList[-1].mNode,axis))	 
	
    mc.pointConstraint(ml_splineIKJoints[0].mNode,ml_jointList[0].mNode,maintainOffset = False)
    
    #Store info to the segment curve
    
    #>>> Store em all to our instance
    i_segmentCurve.connectChildNode(i_jntScaleBufferNode,'scaleBuffer','segmentCurve')
    i_segmentCurve.connectChildrenNodes(ml_jointList,'bindJoints','segmentCurve')       
    i_segmentCurve.connectChildrenNodes(ml_splineIKJoints,'splineIKJoints','segmentCurve')   
	
    return {'mi_segmentCurve':i_segmentCurve,'segmentCurve':i_segmentCurve.mNode,
            'l_splineIKJoints':[i_jnt.getShortName() for i_jnt in ml_splineIKJoints],'ml_splineIKJoints':ml_splineIKJoints,
            'scaleBuffer':i_jntScaleBufferNode.mNode,'mi_scaleBuffer':i_jntScaleBufferNode,
            'l_joints':jointList,'ml_joints':ml_jointList}


@r9General.Timer
def createControlSurfaceSegment(jointList,orientation = 'zyx',secondaryAxis = None,
                                baseName ='test', moduleInstance = None):
    """
    """
    #Good way to verify an instance list?
    #validate orientation
    outChannel = orientation[2]
    upChannel = '%sup'%orientation[1]
    
    i_module = False
    i_rigNull = False
    if moduleInstance is not None:
	if issubclass(type(moduleInstance),cgmPM.cgmModule):
	    i_module = moduleInstance
	    i_rigNull = i_module.rigNull
	else:
	    log.error("Not a module instance, ignoring: '%s'"%moduleInstance)
    
    #Create our group
    i_grp = cgmMeta.cgmObject(name = 'newgroup')
    i_grp.addAttr('cgmName', str(baseName), lock=True)
    i_grp.addAttr('cgmTypeModifier','surfaceFollow', lock=True)
    i_grp.doName()
    
    #Create surface
    l_surfaceReturn = joints.loftSurfaceFromJointList(jointList,outChannel)
    
    i_controlSurface = cgmMeta.cgmObject( l_surfaceReturn[0] )
    i_controlSurface.addAttr('cgmName',str(baseName),attrType='string',lock=True)    
    i_controlSurface.addAttr('cgmType','controlSurface',attrType='string',lock=True)
    i_controlSurface.doName()
    i_controlSurface.addAttr('mClass','cgmObject')
    
    if i_module:#if we have a module, connect vis
	i_controlSurface.overrideEnabled = 1		
	cgmMeta.cgmAttr(i_module.rigNull.mNode,'visSegment',lock=False).doConnectOut("%s.%s"%(i_controlSurface.mNode,'overrideVisibility'))
    
    
    ml_jointList = [cgmMeta.cgmObject(j) for j in jointList]
    if not moduleInstance:#if it is, we can assume it's right
	if secondaryAxis is None:
	    raise StandardError,"createControlSurfaceSegment>>> Must have secondaryAxis arg if no moduleInstance is passed"
	for i_jnt in ml_jointList:
	    """
	    Cannot iterate how important this step is. Lost a day trying to trouble shoot why one joint chain worked and another didn't.
	    WILL NOT connect right without this.
	    """
    	    joints.orientJoint(i_jnt.mNode,orientation,secondaryAxis)
	
    #Create folicles
    ml_follicleTransforms = []
    ml_follicleShapes = []
    ml_upGroups = []
    
    #First thing we're going to do is create our follicles
    for i,i_jnt in enumerate(ml_jointList):       
        l_closestInfo = distance.returnClosestPointOnSurfaceInfo(i_jnt.mNode,i_controlSurface.mNode)
        log.debug("%s : %s"%(i_jnt.mNode,l_closestInfo))
        #>>> Follicle =======================================================
        l_follicleInfo = nodes.createFollicleOnMesh(i_controlSurface.mNode)
        i_follicleTrans = cgmMeta.cgmObject(l_follicleInfo[1],setClass=True)
        i_follicleShape = cgmMeta.cgmNode(l_follicleInfo[0])
        #> Name
        i_follicleTrans.doStore('cgmName',i_jnt.mNode)
        i_follicleTrans.doName()
        #>Set follicle value
        i_follicleShape.parameterU = l_closestInfo['normalizedU']
        i_follicleShape.parameterV = l_closestInfo['normalizedV']
        
        ml_follicleShapes.append(i_follicleShape)
        ml_follicleTransforms.append(i_follicleTrans)
	
	i_follicleTrans.parent = i_grp.mNode	
	
	if i_module:#if we have a module, connect vis
	    i_follicleTrans.overrideEnabled = 1		
	    cgmMeta.cgmAttr(i_module.rigNull.mNode,'visRig',lock=False).doConnectOut("%s.%s"%(i_follicleTrans.mNode,'overrideVisibility'))
	
	
	#>>> loc
	"""
	First part of full ribbon wist setup
	"""
	if i_jnt != ml_jointList[-1]:
	    i_upLoc = i_jnt.doLoc()#Make up Loc
	    i_locRotateGroup = i_jnt.duplicateTransform(False)#group in place
	    i_locRotateGroup.parent = i_follicleTrans.mNode
	    i_locRotateGroup.doStore('cgmName',i_jnt.mNode)	    
	    i_locRotateGroup.addAttr('cgmTypeModifier','rotate',lock=True)
	    i_locRotateGroup.doName()
	    
	    #Store the rotate group to the joint
	    i_jnt.connectChildNode(i_locRotateGroup,'rotateUpGroup','drivenJoint')
	    i_zeroGrp = cgmMeta.cgmObject( i_locRotateGroup.doGroup(True),setClass=True )
	    i_zeroGrp.addAttr('cgmTypeModifier','zero',lock=True)
	    i_zeroGrp.doName()
	    #connect some other data
	    i_locRotateGroup.connectChildNode(i_follicleTrans,'follicle','drivenGroup')
	    i_locRotateGroup.connectChildNode(i_locRotateGroup.parent,'zeroGroup')
	    i_locRotateGroup.connectChildNode(i_upLoc,'upLoc')
	    
	    mc.makeIdentity(i_locRotateGroup.mNode, apply=True,t=1,r=1,s=1,n=0)
	    
	    
	    i_upLoc.parent = i_locRotateGroup.mNode
	    mc.move(0,10,0,i_upLoc.mNode,os=True)	
	    ml_upGroups.append(i_upLoc)
	    
	    if i_module:#if we have a module, connect vis
		i_upLoc.overrideEnabled = 1		
		cgmMeta.cgmAttr(i_module.rigNull.mNode,'visRig',lock=False).doConnectOut("%s.%s"%(i_upLoc.mNode,'overrideVisibility'))
	    
	
        #>> Surface Anchor ===================================================
    #Orient constrain our last joint to our last follicle
    #>>>DON'T Like this method --- mc.orientConstraint(ml_follicleTransforms[-1].mNode,ml_jointList[-1].mNode,maintainOffset = True)
    
    #>>>Create scale stuff
    #>>>Create IK effectors,Create distance nodes
    l_iIK_effectors = []
    l_iIK_handles = []  
    l_iDistanceObjects = []
    i_distanceShapes = []  
    for i,i_jnt in enumerate(ml_jointList[:-1]):
        ik_buffer = mc.ikHandle (startJoint=i_jnt.mNode,
                                 endEffector = ml_jointList[i+1].mNode,
                                 setupForRPsolver = True, solver = 'ikRPsolver',
                                 enableHandles=True )
        #Handle
        i_IK_Handle = cgmMeta.cgmObject(ik_buffer[0])
        i_IK_Handle.parent = ml_follicleTransforms[i+1].mNode
        i_IK_Handle.doStore('cgmName',i_jnt.mNode)    
        i_IK_Handle.doName()
        
        #Effector
        i_IK_Effector = cgmMeta.cgmObject(ik_buffer[1])        
        #i_IK_Effector.doStore('cgmName',i_jnt.mNode)    
        i_IK_Effector.doName()
        
        l_iIK_handles.append(i_IK_Handle)
        l_iIK_effectors.append(i_IK_Effector)
        
	if i_module:#if we have a module, connect vis
	    i_IK_Handle.overrideEnabled = 1		
	    cgmMeta.cgmAttr(i_module.rigNull.mNode,'visRig',lock=False).doConnectOut("%s.%s"%(i_IK_Handle.mNode,'overrideVisibility'))
        
        #>> Distance nodes
        i_distanceShape = cgmMeta.cgmNode( mc.createNode ('distanceDimShape') )        
        i_distanceObject = cgmMeta.cgmObject( i_distanceShape.getTransform() )
        i_distanceObject.doStore('cgmName',i_jnt.mNode)
        i_distanceObject.addAttr('cgmType','measureNode',lock=True)
        i_distanceObject.doName(nameShapes = True)
	i_distanceObject.parent = i_grp.mNode#parent it
        i_distanceObject.overrideEnabled = 1
        i_distanceObject.overrideVisibility = 0
	
        #Connect things
        mc.connectAttr ((ml_follicleTransforms[i].mNode+'.translate'),(i_distanceShape.mNode+'.startPoint'))
        mc.connectAttr ((ml_follicleTransforms[i+1].mNode+'.translate'),(i_distanceShape.mNode+'.endPoint'))
        
        l_iDistanceObjects.append(i_distanceObject)
        i_distanceShapes.append(i_distanceShape)
	
	if i_module:#Connect hides if we have a module instance:
	    cgmMeta.cgmAttr(i_module.rigNull.mNode,'visRig',lock=False).doConnectOut("%s.%s"%(i_distanceObject.mNode,'overrideVisibility'))
	
            
    #Connect the first joint's position since an IK handle isn't controlling it    
    attributes.doConnectAttr('%s.translate'%ml_follicleTransforms[0].mNode,'%s.translate'%ml_jointList[0].mNode)
    #attributes.doConnectAttr('%s.translate'%ml_follicleTransforms[-1].mNode,'%s.translate'%ml_jointList[-1].mNode)
    
    #>> Second part for the full twist setup
    aimChannel = orientation[0]  
    fixOptions = [0,90,180,-90,-180]      

    for i,i_jnt in enumerate(ml_jointList[:-1]):
	rotBuffer = mc.xform (i_jnt.mNode, q=True, ws=True, ro=True)
	log.info("rotBuffer: %s"%rotBuffer)
	#Create the poleVector
	poleVector = mc.poleVectorConstraint (ml_upGroups[i].mNode,l_iIK_handles[i].mNode)  	
	optionCnt = 0
	while not cgmMath.isFloatEquivalent((mc.getAttr(i_jnt.mNode+'.r'+aimChannel)),0):
	    log.info("%s.r%s: %s"%(i_jnt.getShortName(),aimChannel,mc.getAttr(i_jnt.mNode+'.r'+aimChannel)))
	    log.info ("Trying the following for '%s':%s" %(l_iIK_handles[i].getShortName(),fixOptions[optionCnt]))
	    attributes.doSetAttr(l_iIK_handles[i].mNode,'twist',fixOptions[optionCnt])
	    optionCnt += 1
	    if optionCnt == 4:
		raise StandardError,"failed to find a good twist value to zero out poleVector: %s"%(i_jnt.getShortName())
	    
	if mc.xform (i_jnt.mNode, q=True, ws=True, ro=True) != rotBuffer:
	    log.info("Found the following on '%s': %s"%(i_jnt.getShortName(),mc.xform (i_jnt.mNode, q=True, ws=True, ro=True)))

    #>>>Hook up scales
    #==========================================================================
    #Translate scale
    """
    for i,i_jnt in enumerate(ml_jointList[1:]):
	#i is already offset, which we need as we want i to be the partn
	attributes.doConnectAttr('%s.%s'%(i_distanceShapes[i].mNode,'distance'),#>>
                                 '%s.t%s'%(i_jnt.mNode,orientation[0]))	   """ 
    
    #Buffer
    i_jntScaleBufferNode = cgmMeta.cgmBufferNode(name = str(baseName),overideMessageCheck=True)
    i_jntScaleBufferNode.addAttr('cgmType','distanceBuffer')
    i_jntScaleBufferNode.addAttr('masterScale',value = 1.0, attrType='float')        
    i_jntScaleBufferNode.doName()
    
    i_jntScaleBufferNode.connectParentNode(i_controlSurface.mNode,'surface','scaleBuffer')
    ml_mainMDs = []
    for i,i_jnt in enumerate(ml_jointList[:-1]):
	
	#Store our distance base to our buffer
        try:i_jntScaleBufferNode.store(i_distanceShapes[i].distance)#Store to our buffer
	except StandardError,error:
	    log.error(error)
	    raise StandardError,"Failed to store joint distance: %s"%i_distanceShapes[i].mNode
	
	#Create the mdNode
	i_md = cgmMeta.cgmNode(mc.createNode('multiplyDivide'))
	i_md.operation = 2
	i_md.doStore('cgmName',i_jnt.mNode)
	i_md.addAttr('cgmTypeModifier','masterScale')
	i_md.doName()
	attributes.doConnectAttr('%s.%s'%(i_distanceShapes[i].mNode,'distance'),#>>
	                         '%s.%s'%(i_md.mNode,'input1X'))
	attributes.doConnectAttr('%s.%s'%(i_jntScaleBufferNode.mNode,i_jntScaleBufferNode.d_indexToAttr[i]),#>>
	                         '%s.%s'%(i_md.mNode,'input2X'))
	
	#Connect to the joint
	i_attr = cgmMeta.cgmAttr(i_jntScaleBufferNode.mNode,"distance_%s"%i,attrType = 'float',initialValue=0,lock=True)		
	i_attrResult = cgmMeta.cgmAttr(i_jntScaleBufferNode.mNode,"scaleResult_%s"%i,attrType = 'float',initialValue=0,lock=True)	
	try:
	    i_attr.doConnectIn('%s.%s'%(i_distanceShapes[i].mNode,'distance'))
	    i_attrResult.doConnectIn('%s.%s'%(i_md.mNode,'output.outputX'))
	    i_attrResult.doConnectOut('%s.s%s'%(i_jnt.mNode,orientation[0]))
	    
	    for axis in orientation[1:]:
		attributes.doConnectAttr('%s.%s'%(i_jntScaleBufferNode.mNode,'masterScale'),#>>
		                         '%s.s%s'%(i_jnt.mNode,axis))	    
	except StandardError,error:
	    log.error(error)
	    raise StandardError,"Failed to connect joint attrs: %s"%i_jnt.mNode
	
	#mc.pointConstraint(ml_follicleTransforms[i].mNode,i_jnt.mNode,maintainOffset = False)
	ml_mainMDs.append(i_md)#store the md
	

	
    #Connect last joint scale to second to last
    for axis in ['scaleX','scaleY','scaleZ']:
	attributes.doConnectAttr('%s.%s'%(ml_jointList[-2].mNode,axis),#>>
                                 '%s.%s'%(ml_jointList[-1].mNode,axis))	 
	
    return {'i_controlSurface':i_controlSurface,'controlSurface':i_controlSurface.mNode,'surfaceScaleBuffer':i_jntScaleBufferNode.mNode,'i_surfaceScaleBuffer':i_jntScaleBufferNode,'l_joints':jointList,'l_iJoints':ml_jointList}
@r9General.Timer
def createConstraintSurfaceSegmentTranslatePosition(jointList,orientation = 'zyx',baseName ='test', moduleInstance = None):
    """
    """
    #Good way to verify an instance list?
    #validate orientation
    outChannel = orientation[2]
    upChannel = '%sup'%orientation[1]
    
    i_module = False
    i_rigNull = False
    if moduleInstance is not None:
	if issubclass(type(moduleInstance),cgmPM.cgmModule):
	    i_module = moduleInstance
	    i_rigNull = i_module.rigNull
	else:
	    log.error("Not a module instance, ignoring: '%s'"%moduleInstance)
    
    #Create our group
    i_grp = cgmMeta.cgmObject(name = 'newgroup')
    i_grp.addAttr('cgmName', str(baseName), lock=True)
    i_grp.addAttr('cgmTypeModifier','surfaceFollow', lock=True)
    i_grp.doName()
    
    #Create surface
    l_surfaceReturn = joints.loftSurfaceFromJointList(jointList,outChannel)
    
    i_controlSurface = cgmMeta.cgmObject( l_surfaceReturn[0] )
    i_controlSurface.addAttr('cgmName',str(baseName),attrType='string',lock=True)    
    i_controlSurface.addAttr('cgmType','controlSurface',attrType='string',lock=True)
    i_controlSurface.doName()
    i_controlSurface.addAttr('mClass','cgmObject')
    
    ml_jointList = [cgmMeta.cgmObject(j) for j in jointList]
    #Create folicles
    ml_follicleTransforms = []
    ml_follicleShapes = []
    l_snapToGroups = []
    il_snapToGroups = []
    il_upLocs = []
    
    #First thing we're going to do is create our follicles
    for i_jnt in ml_jointList:       
        l_closestInfo = distance.returnClosestPointOnSurfaceInfo(i_jnt.mNode,i_controlSurface.mNode)
        log.debug("%s : %s"%(i_jnt.mNode,l_closestInfo))
        #>>> Follicle =======================================================
        l_follicleInfo = nodes.createFollicleOnMesh(i_controlSurface.mNode)
        i_follicleTrans = cgmMeta.cgmObject(l_follicleInfo[1])
        i_follicleShape = cgmMeta.cgmNode(l_follicleInfo[0])
        #> Name
        i_follicleTrans.doStore('cgmName',i_jnt.mNode)
        i_follicleTrans.doName()
        #>Set follicle value
        i_follicleShape.parameterU = l_closestInfo['normalizedU']
        i_follicleShape.parameterV = l_closestInfo['normalizedV']
        
        ml_follicleShapes.append(i_follicleShape)
        ml_follicleTransforms.append(i_follicleTrans)
	
	i_follicleTrans.parent = i_grp.mNode	
	
        #>> Surface Anchor ===================================================
        i_grpPos = cgmMeta.cgmObject( rigging.groupMeObject(i_jnt.mNode,False) )
        i_grpPos.doStore('cgmName',i_jnt.mNode)        
        i_grpOrient = cgmMeta.cgmObject( mc.duplicate(i_grpPos.mNode,returnRootsOnly=True,ic=True)[0] )
        i_grpPos.addAttr('cgmType','surfaceAnchor',attrType='string',lock=True)
        i_grpOrient.addAttr('cgmType','surfaceOrient',attrType='string',lock=True)
        i_grpPos.doName()
        i_grpOrient.doName()
        i_grpOrient.parent = i_grpPos.mNode
	
	i_jnt.connectParentNode(i_grpOrient.mNode,'snapToGroup','snapTarget')	
	
	#Contrain pos group
        constraint = mc.parentConstraint(i_follicleTrans.mNode,i_grpPos.mNode, maintainOffset=False)
	
	i_upLoc = i_jnt.doLoc()#Make up Loc
	i_upLoc.parent = i_grpPos.mNode
	mc.move(0,2,0,i_upLoc.mNode,os=True)
	
	#mc.aimConstraint(ml_jointList[],objGroup,maintainOffset = False, weight = 1, aimVector = aimVector, upVector = upVector, worldUpObject = upLoc, worldUpType = 'object' )        
        l_snapToGroups.append(i_grpOrient.mNode)
	il_snapToGroups.append(i_grpOrient)
	il_upLocs.append(i_upLoc)
	
    for i,i_grp in enumerate(il_snapToGroups[:-1]):
	mc.aimConstraint(il_snapToGroups[i+1].mNode,i_grp.mNode,
	                 maintainOffset = False, weight = 1,
	                 aimVector = [0,0,1], upVector = [0,1,0],
	                 worldUpObject = il_upLocs[i].mNode,
	                 worldUpType = 'object' )        
	
	
    return {'i_controlSurface':i_controlSurface,'controlSurface':i_controlSurface.mNode,
            'il_snapToGroups':il_snapToGroups,'l_snapToGroups':l_snapToGroups}
    
@r9General.Timer
def createControlSurfaceSegment2(jointList,orientation = 'zyx',baseName ='test', moduleInstance = None):
    """
    """
    #Good way to verify an instance list?
    #validate orientation
    outChannel = orientation[2]
    upChannel = '%sup'%orientation[1]
    
    i_module = False
    i_rigNull = False
    if moduleInstance is not None:
	if issubclass(type(moduleInstance),cgmPM.cgmModule):
	    i_module = moduleInstance
	    i_rigNull = i_module.rigNull
	else:
	    log.error("Not a module instance, ignoring: '%s'"%moduleInstance)
    
    #Create our group
    i_grp = cgmMeta.cgmObject(name = 'newgroup')
    i_grp.addAttr('cgmName', str(baseName), lock=True)
    i_grp.addAttr('cgmTypeModifier','surfaceFollow', lock=True)
    i_grp.doName()
    
    #Create surface
    l_surfaceReturn = joints.loftSurfaceFromJointList(jointList,outChannel)
    
    i_controlSurface = cgmMeta.cgmObject( l_surfaceReturn[0] )
    i_controlSurface.addAttr('cgmName',str(baseName),attrType='string',lock=True)    
    i_controlSurface.addAttr('cgmType','controlSurface',attrType='string',lock=True)
    i_controlSurface.doName()
    i_controlSurface.addAttr('mClass','cgmObject')
    
    ml_jointList = [cgmMeta.cgmObject(j) for j in jointList]
    #Create folicles
    ml_follicleTransforms = []
    ml_follicleShapes = []
    ml_upGroups = []
    
    #First thing we're going to do is create our follicles
    for i,i_jnt in enumerate(ml_jointList):       
        l_closestInfo = distance.returnClosestPointOnSurfaceInfo(i_jnt.mNode,i_controlSurface.mNode)
        log.debug("%s : %s"%(i_jnt.mNode,l_closestInfo))
        #>>> Follicle =======================================================
        l_follicleInfo = nodes.createFollicleOnMesh(i_controlSurface.mNode)
        i_follicleTrans = cgmMeta.cgmObject(l_follicleInfo[1],setClass=True)
        i_follicleShape = cgmMeta.cgmNode(l_follicleInfo[0])
        #> Name
        i_follicleTrans.doStore('cgmName',i_jnt.mNode)
        i_follicleTrans.doName()
        #>Set follicle value
        i_follicleShape.parameterU = l_closestInfo['normalizedU']
        i_follicleShape.parameterV = l_closestInfo['normalizedV']
        
        ml_follicleShapes.append(i_follicleShape)
        ml_follicleTransforms.append(i_follicleTrans)
	
	i_follicleTrans.parent = i_grp.mNode	
	
	#>>> loc
	"""
	First part of full ribbon wist setup
	"""
	if i_jnt != ml_jointList[-1]:
	    i_upLoc = i_jnt.doLoc()#Make up Loc
	    i_locRotateGroup = i_jnt.duplicateTransform(False)#group in place
	    i_locRotateGroup.parent = i_follicleTrans.mNode
	    i_locRotateGroup.doStore('cgmName',i_jnt.mNode)	    
	    i_locRotateGroup.addAttr('cgmTypeModifier','rotate',lock=True)
	    i_locRotateGroup.doName()
	    
	    #Store the rotate group to the joint
	    i_jnt.connectChildNode(i_locRotateGroup,'rotateUpGroup','drivenJoint')
	    i_zeroGrp = cgmMeta.cgmObject( i_locRotateGroup.doGroup(True),setClass=True )
	    i_zeroGrp.addAttr('cgmTypeModifier','zero',lock=True)
	    i_zeroGrp.doName()
	    #connect some other data
	    i_locRotateGroup.connectChildNode(i_follicleTrans,'follicle','drivenGroup')
	    i_locRotateGroup.connectChildNode(i_locRotateGroup.parent,'zeroGroup')
	    
	    mc.makeIdentity(i_locRotateGroup.mNode, apply=True,t=1,r=1,s=1,n=0)
	    
	    
	    i_upLoc.parent = i_locRotateGroup.mNode
	    mc.move(0,10,0,i_upLoc.mNode,os=True)	
	    ml_upGroups.append(i_upLoc)
	    
	
        #>> Surface Anchor ===================================================
        """
        i_grpPos = cgmMeta.cgmObject( rigging.groupMeObject(i_jnt.mNode,False) )
        i_grpPos.doStore('cgmName',i_jnt.mNode)        
        i_grpOrient = cgmMeta.cgmObject( mc.duplicate(i_grpPos.mNode,returnRootsOnly=True)[0] )
        i_grpPos.addAttr('cgmType','surfaceAnchor',attrType='string',lock=True)
        i_grpOrient.addAttr('cgmType','surfaceOrient',attrType='string',lock=True)
        i_grpPos.doName()
        i_grpOrient.doName()
        i_grpOrient.parent = i_grpPos.mNode
        
        constraint = mc.pointConstraint(i_transFollicle.mNode,i_grpPos.mNode, maintainOffset=False)
        constraint = mc.orientConstraint(i_transFollicle.mNode,i_grpPos.mNode, maintainOffset=False)
        """

    #Orient constrain our last joint to our last follicle
    #>>>DON'T Like this method --- mc.orientConstraint(ml_follicleTransforms[-1].mNode,ml_jointList[-1].mNode,maintainOffset = True)
    
    #>>>Create scale stuff
    #>>>Create IK effectors,Create distance nodes
    l_iIK_effectors = []
    l_iIK_handles = []  
    l_iDistanceObjects = []
    i_distanceShapes = []  
    for i,i_jnt in enumerate(ml_jointList[:-1]):
        ik_buffer = mc.ikHandle (startJoint=i_jnt.mNode,
                                 endEffector = ml_jointList[i+1].mNode,
                                 setupForRPsolver = True, solver = 'ikRPsolver',
                                 enableHandles=True )
        #Handle
        i_IK_Handle = cgmMeta.cgmObject(ik_buffer[0],setClass=True)
        i_IK_Handle.parent = ml_follicleTransforms[i+1].mNode
        i_IK_Handle.doStore('cgmName',i_jnt.mNode)    
        i_IK_Handle.doName()
        
        #Effector
        i_IK_Effector = cgmMeta.cgmObject(ik_buffer[1],setClass=True)        
        i_IK_Effector.doName()
        
        l_iIK_handles.append(i_IK_Handle)
        l_iIK_effectors.append(i_IK_Effector)	
        
        #>> Distance nodes
        i_distanceShape = cgmMeta.cgmNode( mc.createNode ('distanceDimShape') )        
        i_distanceObject = cgmMeta.cgmObject( i_distanceShape.getTransform() )
        i_distanceObject.doStore('cgmName',i_jnt.mNode)
        i_distanceObject.addAttr('cgmType','measureNode',lock=True)
        i_distanceObject.doName(nameShapes = True)
	i_distanceObject.parent = i_grp.mNode#parent it
        i_distanceObject.overrideEnabled = 1
        i_distanceObject.overrideVisibility = 0
	
        #Connect things
        mc.connectAttr ((ml_follicleTransforms[i].mNode+'.translate'),(i_distanceShape.mNode+'.startPoint'))
        mc.connectAttr ((ml_follicleTransforms[i+1].mNode+'.translate'),(i_distanceShape.mNode+'.endPoint'))
        
        l_iDistanceObjects.append(i_distanceObject)
        i_distanceShapes.append(i_distanceShape)
            
    #Connect the first joint's position since an IK handle isn't controlling it    
    attributes.doConnectAttr('%s.translate'%ml_follicleTransforms[0].mNode,'%s.translate'%ml_jointList[0].mNode)
    #attributes.doConnectAttr('%s.translate'%ml_follicleTransforms[-1].mNode,'%s.translate'%ml_jointList[-1].mNode)
    
    #>> Second part for the full twist setup
    aimChannel = orientation[0]  
    fixOptions = [0,90,180,-90,-180]      

    for i,i_jnt in enumerate(ml_jointList[:-1]):
	rotBuffer = mc.xform (i_jnt.mNode, q=True, ws=True, ro=True)
	log.info("rotBuffer: %s"%rotBuffer)
	#Create the poleVector
	poleVector = mc.poleVectorConstraint (ml_upGroups[i].mNode,l_iIK_handles[i].mNode)  	
	optionCnt = 0
	while not cgmMath.isFloatEquivalent((mc.getAttr(i_jnt.mNode+'.r'+aimChannel)),0):
	    log.info("%s.r%s: %s"%(i_jnt.getShortName(),aimChannel,mc.getAttr(i_jnt.mNode+'.r'+aimChannel)))
	    log.info ("Trying the following for '%s':%s" %(l_iIK_handles[i].getShortName(),fixOptions[optionCnt]))
	    attributes.doSetAttr(l_iIK_handles[i].mNode,'twist',fixOptions[optionCnt])
	    optionCnt += 1
	    if optionCnt == 4:
		raise StandardError,"failed to find a good twist value to zero out poleVector: %s"%(i_jnt.getShortName())
	    
	if mc.xform (i_jnt.mNode, q=True, ws=True, ro=True) != rotBuffer:
	    log.info("Found the following on '%s': %s"%(i_jnt.getShortName(),mc.xform (i_jnt.mNode, q=True, ws=True, ro=True)))

    #>>>Hook up scales
    #===================================================================
    #World scale
    
    #Buffer
    i_jntScaleBufferNode = cgmMeta.cgmBufferNode(name = str(baseName),overideMessageCheck=True)
    i_jntScaleBufferNode.addAttr('cgmType','distanceBuffer')
    i_jntScaleBufferNode.addAttr('masterScale',value = 1.0, attrType='float')        
    i_jntScaleBufferNode.doName()
    
    i_jntScaleBufferNode.connectParentNode(i_controlSurface.mNode,'surface','scaleBuffer')
    ml_mainMDs = []
    for i,i_jnt in enumerate(ml_jointList[:-1]):
	#Store our distance base to our buffer
        try:i_jntScaleBufferNode.store(i_distanceShapes[i].distance)#Store to our buffer
	except StandardError,error:
	    log.error(error)
	    raise StandardError,"Failed to store joint distance: %s"%i_distanceShapes[i].mNode
	
	#Create the mdNode
	i_md = cgmMeta.cgmNode(mc.createNode('multiplyDivide'))
	i_md.operation = 2
	i_md.doStore('cgmName',i_jnt.mNode)
	i_md.addAttr('cgmTypeModifier','masterScale')
	i_md.doName()
	attributes.doConnectAttr('%s.%s'%(i_distanceShapes[i].mNode,'distance'),#>>
	                         '%s.%s'%(i_md.mNode,'input1X'))
	attributes.doConnectAttr('%s.%s'%(i_jntScaleBufferNode.mNode,i_jntScaleBufferNode.d_indexToAttr[i]),#>>
	                         '%s.%s'%(i_md.mNode,'input2X'))
	
	#Connect to the joint
	try:
	    attributes.doConnectAttr('%s.%s'%(i_md.mNode,'output.outputX'),#>>
		                     '%s.s%s'%(i_jnt.mNode,orientation[0]))
	    for axis in orientation[1:]:
		attributes.doConnectAttr('%s.%s'%(i_jntScaleBufferNode.mNode,'masterScale'),#>>
		                         '%s.s%s'%(i_jnt.mNode,axis))	    
	except StandardError,error:
	    log.error(error)
	    raise StandardError,"Failed to connect joint attrs: %s"%i_jnt.mNode
	
	ml_mainMDs.append(i_md)#store the md
	
	#If second to last we need to add an extra md
	
    #Connect last joint scale to second to last
    for axis in ['scaleX','scaleY','scaleZ']:
	attributes.doConnectAttr('%s.%s'%(ml_jointList[-2].mNode,axis),#>>
                                 '%s.%s'%(ml_jointList[-1].mNode,axis))	 
	
    return {'i_controlSurface':i_controlSurface,'controlSurface':i_controlSurface.mNode,'surfaceScaleBuffer':i_jntScaleBufferNode.mNode,'i_surfaceScaleBuffer':i_jntScaleBufferNode,'l_joints':jointList,'l_iJoints':ml_jointList}
    
@r9General.Timer
def createControlSurfaceSegmentBAK2(jointList,orientation = 'zyx',baseName ='test', moduleInstance = None):
    """
    """
    #Good way to verify an instance list?
    #validate orientation
    outChannel = orientation[2]
    upChannel = '%sup'%orientation[1]
    
    i_module = False
    i_rigNull = False
    if moduleInstance is not None:
	if issubclass(type(moduleInstance),cgmPM.cgmModule):
	    i_module = moduleInstance
	    i_rigNull = i_module.rigNull
	else:
	    log.error("Not a module instance, ignoring: '%s'"%moduleInstance)
    
    #Create our group
    i_grp = cgmMeta.cgmObject(name = 'newgroup')
    i_grp.addAttr('cgmName', str(baseName), lock=True)
    i_grp.addAttr('cgmTypeModifier','surfaceFollow', lock=True)
    i_grp.doName()
    
    #Create surface
    l_surfaceReturn = joints.loftSurfaceFromJointList(jointList,outChannel)
    
    i_controlSurface = cgmMeta.cgmObject( l_surfaceReturn[0] )
    i_controlSurface.addAttr('cgmName',str(baseName),attrType='string',lock=True)    
    i_controlSurface.addAttr('cgmType','controlSurface',attrType='string',lock=True)
    i_controlSurface.doName()
    i_controlSurface.addAttr('mClass','cgmObject')
    
    ml_jointList = [cgmMeta.cgmObject(j) for j in jointList]
    #Create folicles
    ml_follicleTransforms = []
    ml_follicleShapes = []
    ml_upGroups = []
    
    #First thing we're going to do is create our follicles
    for i,i_jnt in enumerate(ml_jointList):       
        l_closestInfo = distance.returnClosestPointOnSurfaceInfo(i_jnt.mNode,i_controlSurface.mNode)
        log.debug("%s : %s"%(i_jnt.mNode,l_closestInfo))
        #>>> Follicle =======================================================
        l_follicleInfo = nodes.createFollicleOnMesh(i_controlSurface.mNode)
        i_follicleTrans = cgmMeta.cgmObject(l_follicleInfo[1])
        i_follicleShape = cgmMeta.cgmNode(l_follicleInfo[0])
        #> Name
        i_follicleTrans.doStore('cgmName',i_jnt.mNode)
        i_follicleTrans.doName()
        #>Set follicle value
        i_follicleShape.parameterU = l_closestInfo['normalizedU']
        i_follicleShape.parameterV = l_closestInfo['normalizedV']
        
        ml_follicleShapes.append(i_follicleShape)
        ml_follicleTransforms.append(i_follicleTrans)
	
	i_follicleTrans.parent = i_grp.mNode	
	
	#>>> loc
	"""
	i_upLoc = i_jnt.doLoc()#Make up Loc
	i_upLoc.parent = i_follicleTrans.mNode
	mc.move(0,2,0,i_upLoc.mNode,os=True)	
	ml_upGroups.append(i_upLoc)
	"""
	
        #>> Surface Anchor ===================================================
        """
        i_grpPos = cgmMeta.cgmObject( rigging.groupMeObject(i_jnt.mNode,False) )
        i_grpPos.doStore('cgmName',i_jnt.mNode)        
        i_grpOrient = cgmMeta.cgmObject( mc.duplicate(i_grpPos.mNode,returnRootsOnly=True)[0] )
        i_grpPos.addAttr('cgmType','surfaceAnchor',attrType='string',lock=True)
        i_grpOrient.addAttr('cgmType','surfaceOrient',attrType='string',lock=True)
        i_grpPos.doName()
        i_grpOrient.doName()
        i_grpOrient.parent = i_grpPos.mNode
        
        constraint = mc.pointConstraint(i_transFollicle.mNode,i_grpPos.mNode, maintainOffset=False)
        constraint = mc.orientConstraint(i_transFollicle.mNode,i_grpPos.mNode, maintainOffset=False)
        """
        
        #>>>Connect via constraint - no worky
        #constraint = mc.pointConstraint(i_grpOrient.mNode,i_jnt.mNode, maintainOffset=True)
        #constraint = mc.orientConstraint(i_grpOrient.mNode,i_jnt.mNode, maintainOffset=True)
        
        #constraints.doConstraintObjectGroup(i_transFollicle.mNode,transform,['point','orient'])
        #>>> Connect the joint
        #attributes.doConnectAttr('%s.translate'%i_grpPos.mNode,'%s.translate'%i_jnt.mNode)
        
    #>>>Create scale stuff
    #>>>Create IK effectors,Create distance nodes
    l_iIK_effectors = []
    l_iIK_handles = []  
    l_iDistanceObjects = []
    i_distanceShapes = []  
    for i,i_jnt in enumerate(ml_jointList[:-1]):
        ik_buffer = mc.ikHandle (startJoint=i_jnt.mNode,
                                 endEffector = ml_jointList[i+1].mNode,
                                 setupForRPsolver = True, solver = 'ikRPsolver',
                                 enableHandles=True )
        #Handle
        i_IK_Handle = cgmMeta.cgmObject(ik_buffer[0])
        i_IK_Handle.parent = ml_follicleTransforms[i+1].mNode
        i_IK_Handle.doStore('cgmName',i_jnt.mNode)    
        i_IK_Handle.doName()
        
        #Effector
        i_IK_Effector = cgmMeta.cgmObject(ik_buffer[1])        
        #i_IK_Effector.doStore('cgmName',i_jnt.mNode)    
        i_IK_Effector.doName()
        
        l_iIK_handles.append(i_IK_Handle)
        l_iIK_effectors.append(i_IK_Effector)
        
        #>> create up loc
        #i_loc = i_jnt.doLoc()
        #mc.move(0, 10, 0, i_loc.mNode, r=True,os=True,wd=True)
	
        """poleVector = mc.poleVectorConstraint (ml_upGroups[i].mNode,i_IK_Handle.mNode)"""
        
        #>> Distance nodes
        i_distanceShape = cgmMeta.cgmNode( mc.createNode ('distanceDimShape') )        
        i_distanceObject = cgmMeta.cgmObject( i_distanceShape.getTransform() )
        i_distanceObject.doStore('cgmName',i_jnt.mNode)
        i_distanceObject.addAttr('cgmType','measureNode',lock=True)
        i_distanceObject.doName(nameShapes = True)
	i_distanceObject.parent = i_grp.mNode#parent it
        i_distanceObject.overrideEnabled = 1
        i_distanceObject.overrideVisibility = 0
	
        #Connect things
        mc.connectAttr ((ml_follicleTransforms[i].mNode+'.translate'),(i_distanceShape.mNode+'.startPoint'))
        mc.connectAttr ((ml_follicleTransforms[i+1].mNode+'.translate'),(i_distanceShape.mNode+'.endPoint'))
        
        l_iDistanceObjects.append(i_distanceObject)
        i_distanceShapes.append(i_distanceShape)
            
    #Connect the first joint's position since an IK handle isn't controlling it    
    attributes.doConnectAttr('%s.translate'%ml_follicleTransforms[0].mNode,'%s.translate'%ml_jointList[0].mNode)
    
    #>>>Hook up scales
    #World scale
    
    #Buffer
    i_jntScaleBufferNode = cgmMeta.cgmBufferNode(name = str(baseName),overideMessageCheck=True)
    i_jntScaleBufferNode.addAttr('cgmType','distanceBuffer')
    i_jntScaleBufferNode.addAttr('masterScale',value = 1.0, attrType='float')        
    i_jntScaleBufferNode.doName()
    
    i_jntScaleBufferNode.connectParentNode(i_controlSurface.mNode,'surface','scaleBuffer')
    
    for i,i_jnt in enumerate(ml_jointList[:-1]):
	#Store our distance base to our buffer
        try:i_jntScaleBufferNode.store(i_distanceShapes[i].distance)#Store to our buffer
	except StandardError,error:
	    log.error(error)
	    raise StandardError,"Failed to store joint distance: %s"%i_distanceShapes[i].mNode
	
	#Create the mdNode
	i_md = cgmMeta.cgmNode(mc.createNode('multiplyDivide'))
	i_md.operation = 2
	i_md.doStore('cgmName',i_jnt.mNode)
	i_md.addAttr('cgmTypeModifier','masterScale')
	i_md.doName()
	attributes.doConnectAttr('%s.%s'%(i_distanceShapes[i].mNode,'distance'),#>>
	                         '%s.%s'%(i_md.mNode,'input1X'))
	attributes.doConnectAttr('%s.%s'%(i_jntScaleBufferNode.mNode,i_jntScaleBufferNode.d_indexToAttr[i]),#>>
	                         '%s.%s'%(i_md.mNode,'input2X'))
	
	#Connect to the joint
	try:
	    attributes.doConnectAttr('%s.%s'%(i_md.mNode,'output.outputX'),#>>
		                     '%s.s%s'%(i_jnt.mNode,orientation[0]))
	    for axis in orientation[1:]:
		attributes.doConnectAttr('%s.%s'%(i_jntScaleBufferNode.mNode,'masterScale'),#>>
		                         '%s.s%s'%(i_jnt.mNode,axis))	    
	except StandardError,error:
	    log.error(error)
	    raise StandardError,"Failed to connect joint attrs: %s"%i_jnt.mNode
	
	"""
	mdArg = [{'result':[i_jnt.mNode,'sy'],'drivers':[[i_distanceShapes[i].mNode,'distance'],[i_jntScaleBufferNode,i_jntScaleBufferNode.d_indexToAttr[i]]],'driven':[]},
	         {'result':[i_jnt.mNode,'sx'],'drivers':[[i_distanceShapes[i].mNode,'distance'],[i_jntScaleBufferNode,i_jntScaleBufferNode.d_indexToAttr[i]]],'driven':[]}]
	#mdArg = [{'drivers':[[i_jntScaleBufferNode,'masterScale'],[i_jntScaleBufferNode,i_jntScaleBufferNode.d_indexToAttr[i]]],
	          #'driven':[[i_jnt.mNode,'sy'],[i_jnt.mNode,'sx']]}]
        
        try:NodeF.build_mdNetwork(mdArg, defaultAttrType='float',operation=2)
	except StandardError,error:
	    log.error(error)
	    raise StandardError,"Failed to build network: %s"%mdArg 
	"""
	
    #Connect last joint scale to second to last
    for axis in ['scaleX','scaleY','scaleZ']:
	attributes.doConnectAttr('%s.%s'%(ml_jointList[-2].mNode,axis),#>>
                                 '%s.%s'%(ml_jointList[-1].mNode,axis))	 
	
    return {'i_controlSurface':i_controlSurface,'controlSurface':i_controlSurface.mNode,'surfaceScaleBuffer':i_jntScaleBufferNode.mNode,'i_surfaceScaleBuffer':i_jntScaleBufferNode,'l_joints':jointList,'l_iJoints':ml_jointList}
    
        
@r9General.Timer
def addRibbonTwistToControlSurfaceSetup(jointList,
                                        startControlDriver = None, endControlDriver = None,
                                        rotateGroupAxis = 'rotateZ',
                                        orientation = 'zyx', moduleInstance = None):
    """
    Implementing this ribbon method to or control surface setup:
    http://faithofthefallen.wordpress.com/2008/10/08/awesome-spine-setup/
    """
    def createAverageNode(driver1,driver2,driven = None):
	#Create the mdNode
	log.info("driver1: %s"%driver1)
	log.info("driver2: %s"%driver2)
	assert type(driver1) is list and len(driver1) == 2,"Driver1 wrong: %s"%driver1
	assert type(driver2) is list and len(driver1) == 2,"Driver2 wrong: %s"%driver2
	driver1Combined = "%s.%s"%(driver1[0],driver1[1])
	driver2Combined = "%s.%s"%(driver2[0],driver2[1])
	assert mc.objExists(driver1Combined)	
	assert mc.objExists(driver2Combined)
	
	if driven is not None:
	    assert type(driven) is list and len(driver1) == 2,"Driven wrong: %s"%driven	    
	    drivenCombined = "%s.%s"%(driven[0],driven[1])
	    assert mc.objExists(drivenCombined)	    
	    log.info("drivenCombined: %s"%drivenCombined)
	    
	log.info("driver1Combined: %s"%driver1Combined)
	log.info("driver2Combined: %s"%driver2Combined)
	
	#Create the node
	i_pma = cgmMeta.cgmNode(mc.createNode('plusMinusAverage'))
	i_pma.operation = 3
	nameBuffer = "%s_to_%s"%(mc.ls(driver1[0],sn = True)[0],mc.ls(driver2[0],sn = True)[0])
	i_pma.addAttr('cgmName',nameBuffer,lock=True)	
	#i_pma.doStore('cgmName',i_jnt.mNode)
	i_pma.addAttr('cgmTypeModifier','twist')
	i_pma.doName()
	
	#Make our connections
	attributes.doConnectAttr(driver1Combined,'%s.input1D[0]'%i_pma.mNode)
	attributes.doConnectAttr(driver2Combined,'%s.input1D[1]'%i_pma.mNode)
	
	if driven is not None:
	    attributes.doConnectAttr('%s.output1D'%i_pma.mNode,drivenCombined)
	    
	return i_pma

    def averageNetwork_three(indices):
	""" """
	log.info("averageNetwork_three: %s"%indices)
	assert len(indices) == 3,"averageNetwork_three requires 3 indices"
	for i in indices:
	    if i not in d_drivenPlugs.keys():
		raise StandardError,"Index doesn't exist in d_drivenPlugs: %s"%i
	d1 = d_driverPlugs[indices[0]]
	d2 = d_driverPlugs[indices[-1]]
	driven = d_drivenPlugs[indices[1]]
	
	i_buffer = createAverageNode(d1,d2,driven)
	#Register network
	d_driverPlugs[indices[1]] = [i_buffer.mNode,"output1D"]
	
    def averageNetwork_four(indices):
	""" 
	If we don't have an actual middle object we still need to average
	ex[0,1,2,3]
	[0,3]
	[0,3],1 | [0,3],2
	"""
	log.info("averageNetwork_four: %s"%indices)
	assert len(indices) == 4,"averageNetwork_four requires 4 indices"
	for i in indices:
	    if i not in d_drivenPlugs.keys():
		raise StandardError,"Index doesn't exist in d_drivenPlugs: %s"%i
	assert indices[0] in d_drivenPlugs.keys(),"four mode indice not in d_drivenPlugs: %s"%indices[0]
	assert indices[-1] in d_drivenPlugs.keys(),"four mode indice not in d_drivenPlugs: %s"%indices[-1]
	
	#Get the middle driven
	driven1 = d_drivenPlugs[indices[1]]	
	driven2 = d_drivenPlugs[indices[2]]	
	driver1 = d_driverPlugs[indices[0]]
	driver2 = d_driverPlugs[indices[-1]]
	
	#Blend average
	blendDriverIndex = (indices[0],indices[-1])	
	try:
	    if blendDriverIndex not in d_drivenPlugs.keys():
		#If our blend driver isn't in the keys, we need to make it. first check the drivers exist
		i_blendPMA = createAverageNode(driver1,driver2)
		blendConnection = [i_blendPMA.mNode,"output1D"]
	    else:
		blendConnection = d_drivenPlugs[blendDriverIndex]
	except StandardError,error:
	    log.error(error)
	    raise StandardError,"averageNetwork_four>failed to find or build blendDriver: %s"%blendDriverIndex
	
	
	#Hook up first
	createAverageNode(blendConnection,
                          driver1,
                          d_drivenPlugs[1])	
	#Hook up second
	createAverageNode(blendConnection,
                          driver2,
                          d_drivenPlugs[2])	
	
    #Good way to verify an instance list?
    #validate orientation
    outChannel = orientation[2].capitalize()
    upChannel = orientation[1].capitalize()
    aimChannel = orientation[0].capitalize()
    if len(jointList) <3:
	raise StandardError,"addRibbonTwistToControlSurfaceSetup requires 3 joints to work" 
    
    #moduleInstance
    i_module = False
    i_rigNull = False
    if moduleInstance is not None:
	if issubclass(type(moduleInstance),cgmPM.cgmModule):
	    i_module = moduleInstance
	    i_rigNull = i_module.rigNull
	else:
	    log.error("Not a module instance, ignoring: '%s'"%moduleInstance)
	    
    #Initialize joint list
    ml_jointList = [cgmMeta.cgmObject(j) for j in jointList]
    #Gather info:
    #d_driverPlugs = {index:['obj','ry']....}
    #d_drivenPlugs = {index:['rotateGroup','.r']...}
    #twistStartPlug,twistEndPlug
    #For each joint to be connected, we need a connection plug and a rotate group
    #We need a driver start and end plug    
    d_drivenPlugs = {}
    d_driverPlugs = {}
    d_mi_jointToIndex = {}
    #Make sure all but the last have rotate groups,grab those plugs
    for i,i_jnt in enumerate(ml_jointList):
	d_mi_jointToIndex[i_jnt]=i
	if i_jnt == ml_jointList[-1]:#If it's the last
	    d_drivenPlugs[i] = [i_jnt.getShortName(),"rotate%s"%aimChannel]
	else:   
	    rotateGroupBuffer = i_jnt.getMessage('rotateUpGroup',False)[0]
	    if not rotateGroupBuffer:
		raise StandardError,"'%s' lacks a connected rotateUpGroup!"%i_jnt.getShortName()
	    if mc.objExists('%s.%s'%(rotateGroupBuffer,rotateGroupAxis)):
		d_drivenPlugs[i] = [rotateGroupBuffer,rotateGroupAxis]
		#We need to reparent and point constrain our rotate zero groups
		if i_jnt.rotateUpGroup.getMessage('zeroGroup') and i_jnt.rotateUpGroup.getMessage('follicle'):
		    i_zeroGroup = i_jnt.rotateUpGroup.zeroGroup#Get zero
		    i_follicle = i_jnt.rotateUpGroup.follicle#get follicle
		    i_zeroGroup.parent = i_follicle.parent#parent zerogroup to follicle
		    """mc.pointConstraint(i_follicle.mNode,i_zeroGroup.mNode,
				       maintainOffset=False)"""	
		    mc.parentConstraint(i_follicle.mNode,i_zeroGroup.mNode,
			                maintainOffset=True)
		
		
	    else:
		raise StandardError,"Rotate group has no axis: %s!"%rotateGroupAxis
	
    #replace our start and end with our drivers
    d_driverPlugs[0] = startControlDriver
    d_driverPlugs[len(ml_jointList)-1] = endControlDriver

    log.info("drivenPlugs: %s"%d_drivenPlugs)
    log.info("driverPlugs: %s"%d_driverPlugs)
    
    #>>>Setup
    #Connect first and last
    #mc.pointConstraint(i_transFollicle.mNode,i_grpPos.mNode, maintainOffset=False)
    attributes.doConnectAttr('%s.%s'%(startControlDriver[0],startControlDriver[1]),
                             '%s.%s'%(d_drivenPlugs[0][0],d_drivenPlugs[0][1]))
    index = ml_jointList.index(ml_jointList[-1]) 
    #Direct connect no worky
    #attributes.doConnectAttr('%s.%s'%(endControlDriver[0],endControlDriver[1]),
                             #'%s.%s'%(d_drivenPlugs[index][0],d_drivenPlugs[index][1]))
    
    #Connect rest
    if len(ml_jointList) == 3:
	#Grab two control drivers, blend between them, drive mid
	index = ml_jointList.index(ml_jointList[1])
	createAverageNode(startControlDriver,endControlDriver,d_drivenPlugs[index])
    elif len(ml_jointList) == 4:
	#Grab two control drivers, blend
	i_blendPMA = createAverageNode(startControlDriver,endControlDriver)
	
	#Hook up first
	createAverageNode([i_blendPMA.mNode,"output1D"],
                          startControlDriver,
                          d_drivenPlugs[1])	
	#Hook up second
	createAverageNode([i_blendPMA.mNode,"output1D"],
                          endControlDriver,
                          d_drivenPlugs[2])		
	"""
	for i in [1,2]:
	    index = ml_jointList.index(ml_jointList[i])
	    createAverageNode("%s.output1D"%i_blendPMA.mNode,
	                      endControlDriver,
	                      d_drivenPlugs[index])"""	    
	
	#averageNetwork_four()
	
    else:#factor and run
	#Make a factored list
	l_factored = lists.returnFactoredConstraintList(range(len(jointList)),3)
	log.info(l_factored)
	try:
	    for chunk in l_factored:
		log.info("On chunk: %s"%chunk)	    
		if len(chunk) == 3:
		    averageNetwork_three(chunk)
		elif len(chunk) == 4:
		    averageNetwork_four(chunk)
		else:
		    raise StandardError,"Chunk too long: %s"%chunk
	except StandardError,error:
	    log.error(error)
	    raise StandardError,"Chunk failed to network: %s"%chunk
    
    #Finally build full sum
    i_pma = cgmMeta.cgmNode(mc.createNode('plusMinusAverage'))
    i_pma.operation = 1#Sum
    if moduleInstance:
	i_pma.addAttr('cgmName',moduleInstance.cgmName,lock=True)	
    i_pma.addAttr('cgmTypeModifier','twistSum')
    i_pma.doName()
        
    #Make our connections
    for i,driver in enumerate([startControlDriver,endControlDriver]):
	log.info(i)
	log.info(driver)
	attributes.doConnectAttr('%s.%s'%(driver[0],driver[1]),'%s.input1D[%s]'%(i_pma.mNode,i))
	
    #attributes.doConnectAttr('%s.output1D'%(i_pma.mNode),'%s.r%s'%(jointList[-1],orientation[0]))
    return {'mi_pmaTwistSum':i_pma}
    
    """
    for key in d_drivenPlugs.keys():
	log.info(d_drivenPlugs[key])
	log.info('%s.%s'%(d_drivenPlugs[key][0],d_drivenPlugs[key][1]))
	log.info('%s.input1D[%s]'%(i_pma.mNode,i))
	attributes.doConnectAttr('%s.%s'%(d_drivenPlugs[key][0],d_drivenPlugs[key][1]),'%s.input1D[%s]'%(i_pma.mNode,i))
	"""

@r9General.Timer
def addSquashAndStretchToControlSurfaceSetupSCALETRANSLATE(attributeHolder,jointList,orientation = 'zyx', moduleInstance = None):
    """
    """
    #Good way to verify an instance list?
    #validate orientation
    outChannel = orientation[2].capitalize()
    upChannel = orientation[1].capitalize()
    aimChannel = orientation[0].capitalize()
    
    #moduleInstance
    i_module = False
    i_rigNull = False
    if moduleInstance is not None:
	if issubclass(type(moduleInstance),cgmPM.cgmModule):
	    i_module = moduleInstance
	    i_rigNull = i_module.rigNull
	else:
	    log.error("Not a module instance, ignoring: '%s'"%moduleInstance)
    #attributeHolder
    i_holder = cgmMeta.cgmNode(attributeHolder)
    
    #Initialize joint list
    ml_jointList = [cgmMeta.cgmObject(j) for j in jointList]
    
    ml_scaleNodes = []
    ml_sqrtNodes = []
    ml_attrs = []
    for i,i_jnt in enumerate(ml_jointList[:-1]):
	#make sure attr exists
	i_attr = cgmMeta.cgmAttr(i_holder,"scaleMult_%s"%i,attrType = 'float',initialValue=1)
	outScalePlug = attributes.doBreakConnection(i_jnt.mNode,"scale%s"%outChannel)
	upScalePlug = attributes.doBreakConnection(i_jnt.mNode,"scale%s"%upChannel)
	
	#Create the multScale
	i_mdScale = cgmMeta.cgmNode(mc.createNode('multiplyDivide'))
	i_mdScale.operation = 2
	i_mdScale.doStore('cgmName',i_jnt.mNode)
	i_mdScale.addAttr('cgmTypeModifier','multScale')
	i_mdScale.doName()
	for channel in [aimChannel,outChannel,upChannel]:
	    attributes.doConnectAttr('%s.scaleResult_%s'%(i_holder.mNode,i),#>>
	                             '%s.input1%s'%(i_mdScale.mNode,channel))	    
	    """attributes.doConnectAttr('%s.scale%s'%(i_jnt.mNode,aimChannel),#>>
	                             '%s.input1%s'%(i_mdScale.mNode,channel))"""
	    attributes.doConnectAttr('%s'%(outScalePlug),#>>
	                             '%s.input2%s'%(i_mdScale.mNode,channel))
	    
	#Create the sqrtNode
	i_sqrtScale = cgmMeta.cgmNode(mc.createNode('multiplyDivide'))
	i_sqrtScale.operation = 3#set to power
	i_sqrtScale.doStore('cgmName',i_jnt.mNode)
	i_sqrtScale.addAttr('cgmTypeModifier','sqrtScale')
	i_sqrtScale.doName()
	for channel in [aimChannel,outChannel,upChannel]:
	    attributes.doConnectAttr('%s.output%s'%(i_mdScale.mNode,channel),#>>
	                             '%s.input1%s'%(i_sqrtScale.mNode,channel))
	    mc.setAttr("%s.input2"%(i_sqrtScale.mNode)+channel,.5)
	    
	#Create the invScale
	i_invScale = cgmMeta.cgmNode(mc.createNode('multiplyDivide'))
	i_invScale.operation = 2
	i_invScale.doStore('cgmName',i_jnt.mNode)
	i_invScale.addAttr('cgmTypeModifier','invScale')
	i_invScale.doName()
	for channel in [aimChannel,outChannel,upChannel]:
	    mc.setAttr("%s.input1"%(i_invScale.mNode)+channel,1)	    
	    attributes.doConnectAttr('%s.output%s'%(i_sqrtScale.mNode,channel),#>>
	                             '%s.input2%s'%(i_invScale.mNode,channel))
	
	#Create the powScale
	i_powScale = cgmMeta.cgmNode(mc.createNode('multiplyDivide'))
	i_powScale.operation = 3
	i_powScale.doStore('cgmName',i_jnt.mNode)
	i_powScale.addAttr('cgmTypeModifier','powScale')
	i_powScale.doName()
	for channel in [aimChannel,outChannel,upChannel]:
	    attributes.doConnectAttr('%s.output%s'%(i_invScale.mNode,channel),#>>
	                             '%s.input1%s'%(i_powScale.mNode,channel))
	    attributes.doConnectAttr('%s'%(i_attr.p_combinedName),#>>
	                             '%s.input2%s'%(i_powScale.mNode,channel))
	
	#Create the worldScale multiplier node
	i_worldScale = cgmMeta.cgmNode(mc.createNode('multiplyDivide'))
	i_worldScale.operation = 1
	i_worldScale.doStore('cgmName',i_jnt.mNode)
	i_worldScale.addAttr('cgmTypeModifier','worldScale')
	i_worldScale.doName()
	
	for channel in [aimChannel,outChannel,upChannel]:
	    mc.setAttr("%s.input1"%(i_worldScale.mNode)+channel,1)
	    #Connect powScale to the worldScale
	    attributes.doConnectAttr('%s.output%s'%(i_powScale.mNode,channel),#>>
	                             '%s.input1%s'%(i_worldScale.mNode,channel))
	#Connect original plugs
	attributes.doConnectAttr('%s'%(outScalePlug),#>>
                                 '%s.input2%s'%(i_worldScale.mNode,outChannel))  
	attributes.doConnectAttr('%s'%(upScalePlug),#>>
                                 '%s.input2%s'%(i_worldScale.mNode,upChannel)) 
	
	#Connect to joint
	attributes.doConnectAttr('%s.output%s'%(i_worldScale.mNode,outChannel),#>>
                                 '%s.scale%s'%(i_jnt.mNode,outChannel))  
	attributes.doConnectAttr('%s.output%s'%(i_worldScale.mNode,upChannel),#>>
                                 '%s.scale%s'%(i_jnt.mNode,upChannel))
	
	'''attributes.doConnectAttr('%s.output%s'%(i_worldScale.mNode,aimChannel),#>>
                                 '%s.scale%s'%(i_jnt.mNode,aimChannel))	'''
	
	#>>>Fix the translate aim scale
	'''if i>0:
	    aimTransScalePlug = attributes.doBreakConnection(i_jnt.mNode,"translate%s"%aimChannel)
	    log.info(aimTransScalePlug)
	    i_aimScale = cgmMeta.cgmNode(mc.createNode('multiplyDivide'))
	    i_aimScale.operation = 2
	    i_aimScale.doStore('cgmName',i_jnt.mNode)
	    i_aimScale.addAttr('cgmTypeModifier','aimScale')
	    i_aimScale.doName()
	    """attributes.doConnectAttr('%s.scaleResult_%s'%(i_holder.mNode,i-1),#>>
		                     '%s.input1%s'%(i_aimScale.mNode,aimChannel))"""
	    attributes.doConnectAttr('%s.scale%s'%(ml_jointList[i-1].mNode,aimChannel),#>>
		                     '%s.input1%s'%(i_aimScale.mNode,aimChannel))	    
	    attributes.doConnectAttr('%s'%aimTransScalePlug,#>>
		                     '%s.input2%s'%(i_aimScale.mNode,aimChannel))	
	    attributes.doConnectAttr('%s.output%s'%(i_aimScale.mNode,aimChannel),#>>
		                     '%s.translate%s'%(i_jnt.mNode,aimChannel))	
	    '''
	ml_attrs.append(i_attr)

@r9General.Timer
def addSquashAndStretchToControlSurfaceSetup(attributeHolder,jointList,orientation = 'zyx', moduleInstance = None):
    """
    """
    #Good way to verify an instance list?
    #validate orientation
    outChannel = orientation[2].capitalize()
    upChannel = orientation[1].capitalize()
    aimChannel = orientation[0].capitalize()
    
    #moduleInstance
    i_module = False
    i_rigNull = False
    if moduleInstance is not None:
	if issubclass(type(moduleInstance),cgmPM.cgmModule):
	    i_module = moduleInstance
	    i_rigNull = i_module.rigNull
	else:
	    log.error("Not a module instance, ignoring: '%s'"%moduleInstance)
    #attributeHolder
    i_holder = cgmMeta.cgmNode(attributeHolder)
    
    #Initialize joint list
    ml_jointList = [cgmMeta.cgmObject(j) for j in jointList]
    
    ml_scaleNodes = []
    ml_sqrtNodes = []
    ml_attrs = []
    for i,i_jnt in enumerate(ml_jointList[:-1]):
	#make sure attr exists
	i_attr = cgmMeta.cgmAttr(i_holder,"scaleMult_%s"%i,attrType = 'float',initialValue=1)
	outScalePlug = attributes.doBreakConnection(i_jnt.mNode,"scale%s"%outChannel)
	upScalePlug = attributes.doBreakConnection(i_jnt.mNode,"scale%s"%upChannel)
	
	#Create the multScale
	i_mdScale = cgmMeta.cgmNode(mc.createNode('multiplyDivide'))
	i_mdScale.operation = 2
	i_mdScale.doStore('cgmName',i_jnt.mNode)
	i_mdScale.addAttr('cgmTypeModifier','multScale')
	i_mdScale.doName()
	for channel in [outChannel,upChannel]:
	    attributes.doConnectAttr('%s.scale%s'%(i_jnt.mNode,aimChannel),#>>
		                     '%s.input1%s'%(i_mdScale.mNode,channel))
	    attributes.doConnectAttr('%s'%(outScalePlug),#>>
		                     '%s.input2%s'%(i_mdScale.mNode,channel))
	    
	#Create the sqrtNode
	i_sqrtScale = cgmMeta.cgmNode(mc.createNode('multiplyDivide'))
	i_sqrtScale.operation = 3#set to power
	i_sqrtScale.doStore('cgmName',i_jnt.mNode)
	i_sqrtScale.addAttr('cgmTypeModifier','sqrtScale')
	i_sqrtScale.doName()
	for channel in [outChannel,upChannel]:
	    attributes.doConnectAttr('%s.output%s'%(i_mdScale.mNode,channel),#>>
	                             '%s.input1%s'%(i_sqrtScale.mNode,channel))
	    mc.setAttr("%s.input2"%(i_sqrtScale.mNode)+channel,.5)
	    
	#Create the invScale
	i_invScale = cgmMeta.cgmNode(mc.createNode('multiplyDivide'))
	i_invScale.operation = 2
	i_invScale.doStore('cgmName',i_jnt.mNode)
	i_invScale.addAttr('cgmTypeModifier','invScale')
	i_invScale.doName()
	for channel in [outChannel,upChannel]:
	    mc.setAttr("%s.input1"%(i_invScale.mNode)+channel,1)	    
	    attributes.doConnectAttr('%s.output%s'%(i_sqrtScale.mNode,channel),#>>
	                             '%s.input2%s'%(i_invScale.mNode,channel))
	
	#Create the powScale
	i_powScale = cgmMeta.cgmNode(mc.createNode('multiplyDivide'))
	i_powScale.operation = 3
	i_powScale.doStore('cgmName',i_jnt.mNode)
	i_powScale.addAttr('cgmTypeModifier','powScale')
	i_powScale.doName()
	for channel in [outChannel,upChannel]:
	    attributes.doConnectAttr('%s.output%s'%(i_invScale.mNode,channel),#>>
		                     '%s.input1%s'%(i_powScale.mNode,channel))
	    attributes.doConnectAttr('%s'%(i_attr.p_combinedName),#>>
		                     '%s.input2%s'%(i_powScale.mNode,channel))
	
	#Create the worldScale multiplier node
	i_worldScale = cgmMeta.cgmNode(mc.createNode('multiplyDivide'))
	i_worldScale.operation = 1
	i_worldScale.doStore('cgmName',i_jnt.mNode)
	i_worldScale.addAttr('cgmTypeModifier','worldScale')
	i_worldScale.doName()
	for channel in [outChannel,upChannel]:
	    mc.setAttr("%s.input1"%(i_worldScale.mNode)+channel,1)
	    #Connect powScale to the worldScale
	    attributes.doConnectAttr('%s.output%s'%(i_powScale.mNode,channel),#>>
	                             '%s.input1%s'%(i_worldScale.mNode,channel))
	#Connect original plugs
	attributes.doConnectAttr('%s'%(outScalePlug),#>>
                                 '%s.input2%s'%(i_worldScale.mNode,outChannel))  
	attributes.doConnectAttr('%s'%(upScalePlug),#>>
                                 '%s.input2%s'%(i_worldScale.mNode,upChannel)) 
	
	#Connect to joint
	attributes.doConnectAttr('%s.output%s'%(i_worldScale.mNode,outChannel),#>>
                                 '%s.scale%s'%(i_jnt.mNode,outChannel))  
	attributes.doConnectAttr('%s.output%s'%(i_worldScale.mNode,upChannel),#>>
                                 '%s.scale%s'%(i_jnt.mNode,upChannel)) 	
	
	ml_attrs.append(i_attr)

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Module and Puppet axis settings
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>      
def doSetAimAxis(self,i):
    """
    Set the aim axis. if up or out have that axis. They will be changed. Aim is the priority.
    Then Up, and Out is last.
    
    """
    assert i < 6,"%i isn't a viable aim axis integer"%i
    
    self.optionAimAxis.set(i)
    if self.optionUpAxis.get() == self.optionAimAxis.get():
        doSetUpAxis(self,i)
    if self.optionOutAxis.get() == self.optionAimAxis.get():
        doSetOutAxis(self,i)
        
    return True
    
def doSetUpAxis(self,i):
    """
    Set the aim axis. if up or out have that axis. They will be changed. Aim is the priority.
    Then Up, and Out is last.
    
    """        
    assert i < 6,"%i isn't a viable up axis integer"%i
    axisBuffer = range(6)
    axisBuffer.remove(self.optionAimAxis.get())
    
    if i != self.optionAimAxis.get():
        self.optionUpAxis.set(i)  
    else:
        self.optionUpAxis.set(axisBuffer[0]) 
        guiFactory.warning("Aim axis has '%s'. Changed up axis to '%s'. Change aim setting if you want this seeting"%(dictionary.axisDirectionsByString[self.optionAimAxis.get()],dictionary.axisDirectionsByString[self.optionUpAxis.get()]))                  
        axisBuffer.remove(axisBuffer[0])
        
    if self.optionOutAxis.get() in [self.optionAimAxis.get(),self.optionUpAxis.get()]:
        for i in axisBuffer:
            if i not in [self.optionAimAxis.get(),self.optionUpAxis.get()]:
                doSetOutAxis(self,i)
                guiFactory.warning("Setting conflict. Changed out axis to '%s'"%dictionary.axisDirectionsByString[i])                    
                break
    return True        
    
    
def doSetOutAxis(self,i):
    assert i < 6,"%i isn't a viable aim axis integer"%i
    
    if i not in [self.optionAimAxis.get(),self.optionUpAxis.get()]:
        self.optionOutAxis.set(i)
    else:
        axisBuffer = range(6)
        axisBuffer.remove(self.optionAimAxis.get())
        axisBuffer.remove(self.optionUpAxis.get())
        self.optionOutAxis.set(axisBuffer[0]) 
        guiFactory.warning("Setting conflict. Changed out axis to '%s'"%dictionary.axisDirectionsByString[ axisBuffer[0] ])                    



def copyAxisOptions(self,target):
    target.optionAimAxis
    target.optionUpAxis
    target.optionOutAxis
    self.optionAimAxis
    self.optionUpAxis
    self.optionOutAxis 
    
    doSetAimAxis(self,target.optionAimAxis.get())
    doSetUpAxis(self,target.optionUpAxis.get())
    doSetOutAxis(self,target.optionOutAxis.get())
    
    
    