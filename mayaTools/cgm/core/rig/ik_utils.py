"""
------------------------------------------
ik_utils: cgm.core.rig
Author: Josh Burton
email: jjburton@cgmonks.com
Website : http://www.cgmonks.com
------------------------------------------


================================================================
"""
# From Python =============================================================
import copy
import re
import time
import pprint

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

# From Maya =============================================================
import maya.cmds as mc

# From cgm ==============================================================
from cgm.core import cgm_Meta as cgmMeta
from cgm.core import cgm_General as cgmGEN
import cgm.core.lib.snap_utils as SNAP
from cgm.core.lib import curve_Utils as CURVES
from cgm.core.cgmPy import validateArgs as VALID
#from cgm.core.classes import SnapFactory as Snap
from cgm.core.lib import nameTools
from cgm.core.rigger.lib import rig_Utils
from cgm.core.classes import NodeFactory as NodeF
import cgm.core.rig.joint_utils as JOINTS
import cgm.core.lib.attribute_utils as ATTR
import cgm.core.lib.distance_utils as DIST
import cgm.core.rig.constraint_utils as RIGCONSTRAINTS
import cgm.core.rig.create_utils as RIGCREATE
import cgm.core.rig.general_utils as RIGGEN
import cgm.core.lib.list_utils as LISTS
import cgm.core.lib.rigging_utils as CORERIG
import cgm.core.lib.locator_utils as LOC
import cgm.core.lib.node_utils as NODES
import cgm.core.lib.math_utils as MATH
import cgm.core.rig.skin_utils as RIGSKIN

for m in CURVES,RIGCREATE,RIGGEN,LISTS,RIGCONSTRAINTS,MATH,NODES:
    reload(m)

def spline(jointList = None,
           useCurve = None,
           orientation = 'zyx',
           secondaryAxis = 'y+',
           baseName = None,
           stretchBy = 'translate',
           advancedTwistSetup = False,
           extendTwistToEnd = False,
           reorient = False,
           moduleInstance = None,
           parentGutsTo = None):
    """
    Root of the segment setup.
    Inspiriation from Jason Schleifer's work as well as

    http://faithofthefallen.wordpress.com/2008/10/08/awesome-spine-setup/
    on twist methods.

    Latest rewrite - July 2017

    :parameters:
        jointList(joints - None) | List or metalist of joints
        useCurve(nurbsCurve - None) | Which curve to use. If None. One Created
        orientation(string - zyx) | What is the joints orientation
        secondaryAxis(maya axis arg(y+) | Only necessary when no module provide for orientating
        baseName(string - None) | baseName string
        stretchBy(string - trans/scale/None) | How the joint will scale
        advancedTwistSetup(bool - False) | Whether to do the cgm advnaced twist setup
        addMidTwist(bool - True) | Whether to setup a mid twist on the segment
        moduleInstance(cgmModule - None) | cgmModule to use for connecting on build
        extendTwistToEnd(bool - False) | Whether to extned the twist to the end by default

    :returns:
        mIKHandle, mIKEffector, mIKSolver, mi_splineCurve
        

    :raises:
        Exception | if reached

    """ 
    _str_func = 'splineIK'
    #try:
    #>>> Verify =============================================================================================
    ml_joints = cgmMeta.validateObjListArg(jointList,mType = 'cgmObject', mayaType=['joint'], noneValid = False)
    l_joints = [mJnt.p_nameShort for mJnt in ml_joints]
    int_lenJoints = len(ml_joints)#because it's called repeatedly
    mi_useCurve = cgmMeta.validateObjArg(useCurve,mayaType=['nurbsCurve'],noneValid = True)

    mi_mayaOrientation = VALID.simpleOrientation(orientation)
    str_orientation = mi_mayaOrientation.p_string
    str_secondaryAxis = VALID.stringArg(secondaryAxis,noneValid=True)
    str_baseName = VALID.stringArg(baseName,noneValid=True)
    
    
    #module -----------------------------------------------------------------------------------------------
    mModule = cgmMeta.validateObjArg(moduleInstance,noneValid = True)
    try:mModule.isModule()
    except:mModule = False

    mi_rigNull = False	
    if mModule:
        log.debug("|{0}| >> Module found. mModule: {1}...".format(_str_func,mModule))                                    
        mi_rigNull = mModule.rigNull	
        if str_baseName is None:
            str_baseName = mModule.getPartNameBase()#Get part base name	    
    if not str_baseName:str_baseName = 'testSplineIK' 
    #...
    
    str_stretchBy = VALID.stringArg(stretchBy,noneValid=True)		
    b_advancedTwistSetup = VALID.boolArg(advancedTwistSetup)
    b_extendTwistToEnd= VALID.boolArg(extendTwistToEnd)

    if int_lenJoints<3:
        pprint.pprint(vars())
        raise ValueError,"needs at least three joints"
    
    if parentGutsTo is None:
        mGroup = cgmMeta.cgmObject(name = 'newgroup')
        mGroup.addAttr('cgmName', str(str_baseName), lock=True)
        mGroup.addAttr('cgmTypeModifier','segmentStuff', lock=True)
        mGroup.doName()
    else:
        mGroup = cgmMeta.validateObjArg(parentGutsTo,'cgmObject',False)

    #Good way to verify an instance list? #validate orientation             
    #> axis -------------------------------------------------------------
    axis_aim = VALID.simpleAxis("{0}+".format(str_orientation[0]))
    axis_aimNeg = axis_aim.inverse
    axis_up = VALID.simpleAxis("{0}+".format(str_orientation [1]))

    v_aim = axis_aim.p_vector#aimVector
    v_aimNeg = axis_aimNeg.p_vector#aimVectorNegative
    v_up = axis_up.p_vector   #upVector

    outChannel = str_orientation[2]#outChannel
    upChannel = '{0}up'.format(str_orientation[1])#upChannel
    l_param = []  
    
    #>>> SplineIK ===========================================================================================
    if mi_useCurve:
        log.debug("|{0}| >> useCurve. SplineIk...".format(_str_func))    
        f_MatchPosOffset = CURVES.getUParamOnCurve(ml_joints[0].mNode, mi_useCurve.mNode)
        log.debug("|{0}| >> Use curve mode. uPos: {1}...".format(_str_func,f_MatchPosOffset))                            
        
        
        for mJnt in ml_joints:
            param = CURVES.getUParamOnCurveFromObj(mJnt.mNode, mi_useCurve.mNode) 
            log.debug("|{0}| >> {1}...".format(_str_func,param))                
            l_param.append(param)
        
        #Because maya is stupid, when doing an existing curve splineIK setup in 2011, you need to select the objects
        #Rather than use the flags
        mc.select(cl=1)
        mc.select([ml_joints[0].mNode,ml_joints[-1].mNode,mi_useCurve.mNode])
        buffer = mc.ikHandle( simplifyCurve=False, eh = 1,curve = mi_useCurve.mNode,
                              rootOnCurve=True, forceSolver = True, snapHandleFlagToggle=True,
                              parentCurve = False, solver = 'ikSplineSolver',createCurve = False,)  
        log.info(buffer)
        mSegmentCurve = mi_useCurve#Link
        mSegmentCurve.addAttr('cgmType','splineIKCurve',attrType='string',lock=True)
        mSegmentCurve.doName()		
             
    else:
        log.debug("|{0}| >> createCurve. SplineIk...".format(_str_func))                                    

        buffer = mc.ikHandle( sj=ml_joints[0].mNode, ee=ml_joints[-1].mNode,simplifyCurve=False,
                              solver = 'ikSplineSolver', ns = 4, rootOnCurve=True,forceSolver = True,
                              createCurve = True,snapHandleFlagToggle=True )  

        mSegmentCurve = cgmMeta.asMeta( buffer[2],'cgmObject',setClass=True )
        mSegmentCurve.addAttr('cgmName',str_baseName,attrType='string',lock=True)    
        mSegmentCurve.addAttr('cgmType','splineIKCurve',attrType='string',lock=True)
        mSegmentCurve.doName()

    #if mModule:#if we have a module, connect vis
        #mSegmentCurve.overrideEnabled = 1		
        #cgmMeta.cgmAttr(mi_rigNull.mNode,'gutsVis',lock=False).doConnectOut("%s.%s"%(mSegmentCurve.mNode,'overrideVisibility'))    
        #cgmMeta.cgmAttr(mi_rigNull.mNode,'gutsLock',lock=False).doConnectOut("%s.%s"%(mSegmentCurve.mNode,'overrideDisplayType'))    

    mIKSolver = cgmMeta.cgmNode(name = 'ikSplineSolver')
    
    #>> Handle/Effector --------------------------------------------------------------------------------------
    mIKHandle = cgmMeta.validateObjArg( buffer[0],'cgmObject',setClass=True )
    mIKHandle.addAttr('cgmName',str_baseName,attrType='string',lock=True)    		
    mIKHandle.doName()
    mIKHandle = mIKHandle

    mIKEffector = cgmMeta.validateObjArg( buffer[1],'cgmObject',setClass=True )
    mIKEffector.addAttr('cgmName',str_baseName,attrType='string',lock=True)  
    mIKEffector.doName()
    mIKHandle.parent = mGroup
    
    mSegmentCurve.connectChildNode(mGroup,'segmentGroup','owner')
    
    if mi_useCurve:
        log.debug("|{0}| >> useCurve fix. setIk handle offset to: {1}".format(_str_func,f_MatchPosOffset))                                            
        mIKHandle.offset = f_MatchPosOffset           
        
    _res = {'mIKHandle':mIKHandle, 
            'mIKEffector':mIKEffector,
            'mIKSolver':mIKSolver,
            'mSplineCurve':mSegmentCurve}
    
    #>>> Stretch ============================================================================================
    if str_stretchBy:
        log.debug("|{0}| >> Stretchy. by: {1}...".format(_str_func,str_stretchBy))
        ml_pointOnCurveInfos = []
        
        #First thing we're going to do is create our 'follicles'
        str_shape = mSegmentCurve.getShapes(asMeta=False)[0]
    
        for i,mJnt in enumerate(ml_joints):   
            #import cgm.lib.distance as distance
            #l_closestInfo = distance.returnNearestPointOnCurveInfo(mJnt.mNode,mSegmentCurve.mNode)
            #param = CURVES.getUParamOnCurve(mJnt.mNode, mSegmentCurve.mNode)
            if not l_param:
                param = CURVES.getUParamOnCurveFromObj(mJnt.mNode, mSegmentCurve.mNode)  
            else:
                param = l_param[i]
            #param = DIST.get_closest_point(mJnt.mNode,mSegmentCurve.mNode)[1]
            log.debug("|{0}| >> {1} param: {2}...".format(_str_func,mJnt.p_nameShort,param))
            
            #>>> POCI ----------------------------------------------------------------
            mi_closestPointNode = cgmMeta.cgmNode(nodeType = 'pointOnCurveInfo')
            ATTR.connect(str_shape+'.worldSpace',mi_closestPointNode.mNode+'.inputCurve')	
    
            #> Name
            mi_closestPointNode.doStore('cgmName',mJnt.mNode)
            mi_closestPointNode.doName()
            #>Set follicle value
            mi_closestPointNode.parameter = param
            ml_pointOnCurveInfos.append(mi_closestPointNode)
            
        ml_distanceObjects = []
        ml_distanceShapes = []  
        mSegmentCurve.addAttr('masterScale',value = 1.0, minValue = 0.0001, attrType='float')
        
        for i,mJnt in enumerate(ml_joints[:-1]):
            #>> Distance nodes
            mDistanceShape = cgmMeta.cgmNode( mc.createNode ('distanceDimShape') )        
            mDistanceDag = mDistanceShape.getTransform(asMeta=True) 
            mDistanceDag.doStore('cgmName',mJnt.mNode)
            mDistanceDag.addAttr('cgmType','measureNode',lock=True)
            mDistanceDag.doName(nameShapes = True)
            mDistanceDag.parent = mGroup.mNode#parent it
            mDistanceDag.overrideEnabled = 1
            mDistanceDag.overrideVisibility = 1

            #Connect things
            ATTR.connect(ml_pointOnCurveInfos[i].mNode+'.position',mDistanceShape.mNode+'.startPoint')
            ATTR.connect(ml_pointOnCurveInfos[i+1].mNode+'.position',mDistanceShape.mNode+'.endPoint')

            ml_distanceObjects.append(mDistanceDag)
            ml_distanceShapes.append(mDistanceShape)

            if mModule:#Connect hides if we have a module instance:
                ATTR.connect("{0}.gutsVis".format(mModule.rigNull.mNode),"{0}.overrideVisibility".format(mDistanceDag.mNode))
                ATTR.connect("{0}.gutsLock".format(mModule.rigNull.mNode),"{0}.overrideVisibility".format(overrideDisplayType.mNode))
                #cgmMeta.cgmAttr(mModule.rigNull.mNode,'gutsVis',lock=False).doConnectOut("%s.%s"%(mDistanceDag.mNode,'overrideVisibility'))
                #cgmMeta.cgmAttr(mModule.rigNull.mNode,'gutsLock',lock=False).doConnectOut("%s.%s"%(mDistanceDag.mNode,'overrideDisplayType'))    


        #>>>Hook up stretch/scale #========================================================================= 
        ml_distanceAttrs = []
        ml_resultAttrs = []

        #mi_jntScaleBufferNode.connectParentNode(mSegmentCurve.mNode,'segmentCurve','scaleBuffer')
        ml_mainMDs = []
        
        for i,mJnt in enumerate(ml_joints[:-1]):
            #progressBar_set(status = "node setup | '%s'"%l_joints[i], progress = i, maxValue = int_lenJoints)		    

            #Make some attrs
            mPlug_attrDist= cgmMeta.cgmAttr(mIKHandle.mNode,
                                            "distance_%s"%i,attrType = 'float',initialValue=0,lock=True,minValue = 0)
            mPlug_attrNormalBaseDist = cgmMeta.cgmAttr(mIKHandle.mNode,
                                                       "normalizedBaseDistance_%s"%i,attrType = 'float',
                                                       initialValue=0,lock=True,minValue = 0)			
            mPlug_attrNormalDist = cgmMeta.cgmAttr(mIKHandle.mNode,
                                                   "normalizedDistance_%s"%i,attrType = 'float',initialValue=0,lock=True,minValue = 0)		
            mPlug_attrResult = cgmMeta.cgmAttr(mIKHandle.mNode,
                                               "scaleResult_%s"%i,attrType = 'float',initialValue=0,lock=True,minValue = 0)	
            mPlug_attrTransformedResult = cgmMeta.cgmAttr(mIKHandle.mNode,
                                                          "scaledScaleResult_%s"%i,attrType = 'float',initialValue=0,lock=True,minValue = 0)	
            
            ATTR.datList_append(mIKHandle.mNode,'baseDist',ml_distanceShapes[i].distance)
            ATTR.set_hidden(mIKHandle.mNode,'baseDist_{0}'.format(i),True)
            
            if str_stretchBy.lower() in ['translate','trans','t']:
                #Let's build our args
                l_argBuild = []
                #distance by master
                l_argBuild.append("{0} = {1} / {2}".format(mPlug_attrNormalBaseDist.p_combinedShortName,
                                                           '{0}.baseDist_{1}'.format(mIKHandle.mNode,i),
                                                           "{0}.masterScale".format(mSegmentCurve.mNode)))
                l_argBuild.append("{0} = {1} / {2}".format(mPlug_attrNormalDist.p_combinedShortName,
                                                           mPlug_attrDist.p_combinedShortName,
                                                           "{0}.masterScale".format(mSegmentCurve.mNode)))			
                for arg in l_argBuild:
                    log.debug("|{0}| >> Building arg: {1}".format(_str_func,arg))
                    NodeF.argsToNodes(arg).doBuild()
                    
                #Still not liking the way this works with translate scale. looks fine till you add squash and stretch
                try:
                    mPlug_attrDist.doConnectIn('%s.%s'%(ml_distanceShapes[i].mNode,'distance'))		        
                    mPlug_attrNormalDist.doConnectOut('%s.t%s'%(ml_joints[i+1].mNode,str_orientation[0]))
                    #mPlug_attrNormalDist.doConnectOut('%s.t%s'%(ml_driverJoints[i+1].mNode,str_orientation[0]))    	    
                except Exception,error:
                    raise Exception,"[Failed to connect joint attrs by scale: {0} | error: {1}]".format(mJnt.mNode,error)		
                
            else:
                mi_mdNormalBaseDist = cgmMeta.cgmNode(nodeType='multiplyDivide')
                mi_mdNormalBaseDist.operation = 1
                mi_mdNormalBaseDist.doStore('cgmName',mJnt.mNode)
                mi_mdNormalBaseDist.addAttr('cgmTypeModifier','normalizedBaseDist')
                mi_mdNormalBaseDist.doName()

                ATTR.connect('%s.masterScale'%(mSegmentCurve.mNode),#>>
                             '%s.%s'%(mi_mdNormalBaseDist.mNode,'input1X'))
                ATTR.connect('{0}.baseDist_{1}'.format(mIKHandle.mNode,i),#>>
                             '%s.%s'%(mi_mdNormalBaseDist.mNode,'input2X'))	
                mPlug_attrNormalBaseDist.doConnectIn('%s.%s'%(mi_mdNormalBaseDist.mNode,'output.outputX'))

                #Create the normalized distance
                mi_mdNormalDist = cgmMeta.cgmNode(nodeType='multiplyDivide')
                mi_mdNormalDist.operation = 1
                mi_mdNormalDist.doStore('cgmName',mJnt.mNode)
                mi_mdNormalDist.addAttr('cgmTypeModifier','normalizedDist')
                mi_mdNormalDist.doName()

                ATTR.connect('%s.masterScale'%(mSegmentCurve.mNode),#>>
                             '%s.%s'%(mi_mdNormalDist.mNode,'input1X'))
                mPlug_attrDist.doConnectOut('%s.%s'%(mi_mdNormalDist.mNode,'input2X'))	
                mPlug_attrNormalDist.doConnectIn('%s.%s'%(mi_mdNormalDist.mNode,'output.outputX'))

                #Create the mdNode
                mi_mdSegmentScale = cgmMeta.cgmNode(nodeType='multiplyDivide')
                mi_mdSegmentScale.operation = 2
                mi_mdSegmentScale.doStore('cgmName',mJnt.mNode)
                mi_mdSegmentScale.addAttr('cgmTypeModifier','segmentScale')
                mi_mdSegmentScale.doName()
                mPlug_attrDist.doConnectOut('%s.%s'%(mi_mdSegmentScale.mNode,'input1X'))	
                mPlug_attrNormalBaseDist.doConnectOut('%s.%s'%(mi_mdSegmentScale.mNode,'input2X'))
                mPlug_attrResult.doConnectIn('%s.%s'%(mi_mdSegmentScale.mNode,'output.outputX'))	

                try:#Connect
                    mPlug_attrDist.doConnectIn('%s.%s'%(ml_distanceShapes[i].mNode,'distance'))		        
                    mPlug_attrResult.doConnectOut('%s.s%s'%(mJnt.mNode,str_orientation[0]))
                    #mPlug_attrResult.doConnectOut('%s.s%s'%(ml_driverJoints[i].mNode,str_orientation[0]))
                except Exception,error:raise Exception,"[Failed to connect joint attrs by scale: {0} | error: {1}]".format(mJnt.mNode,error)		    

                ml_mainMDs.append(mi_mdSegmentScale)#store the md



            #Append our data
            ml_distanceAttrs.append(mPlug_attrDist)
            ml_resultAttrs.append(mPlug_attrResult)

            """
                for axis in [str_orientation[1],str_orientation[2]]:
                    attributes.doConnectAttr('%s.s%s'%(mJnt.mNode,axis),#>>
                                             '%s.s%s'%(ml_driverJoints[i].mNode,axis))"""	 	


        
    #Connect last joint scale to second to last
    for axis in ['scaleX','scaleY','scaleZ']:
        ATTR.connect('%s.%s'%(ml_joints[-2].mNode,axis),#>>
                     '%s.%s'%(ml_joints[-1].mNode,axis))	 

    #mc.pointConstraint(ml_driverJoints[0].mNode,ml_joints[0].mNode,maintainOffset = False)
    
    #>> Connect and close =============================================================================
    #mSegmentCurve.connectChildNode(mi_jntScaleBufferNode,'scaleBuffer','segmentCurve')
    #mSegmentCurve.connectChildNode(mIKHandle,'ikHandle','segmentCurve')
    mSegmentCurve.msgList_append('ikHandles',mIKHandle,'segmentCurve')
    #mSegmentCurve.msgList_connect('drivenJoints',ml_joints,'segmentCurve')       
    mIKHandle.msgList_connect('drivenJoints',ml_joints,'ikHandle')       
    
    #mSegmentCurve.msgList_connect(ml_driverJoints,'driverJoints','segmentCurve')  
        
    """        
    except Exception,err:
        print(cgmGEN._str_hardLine)
        log.error("|{0}| >> Failure: {1}".format(_str_func, err.__class__))
        print("Local data>>>" + cgmGEN._str_subLine)        
        pprint.pprint(vars())  
        print("Local data<<<" + cgmGEN._str_subLine)                
        print("Errors...")
        for a in err.args:
            print(a)
        print(cgmGEN._str_subLine)        
        raise Exception,err"""

    #SplineIK Twist =======================================================================================
    d_twistReturn = rig_Utils.IKHandle_addSplineIKTwist(mIKHandle.mNode,b_advancedTwistSetup)
    mPlug_twistStart = d_twistReturn['mi_plug_start']
    mPlug_twistEnd = d_twistReturn['mi_plug_end']
    _res['mPlug_twistStart'] = mPlug_twistStart
    _res['mPlug_twistEnd'] = mPlug_twistEnd
    return _res




def addSplineTwist(ikHandle = None, midHandle = None, advancedTwistSetup = False, orientation = 'zyx'):
    """
    ikHandle(arg)
    advancedTwistSetup(bool) -- Whether to setup ramp setup or not (False)
    """
    _str_func = 'addSplineTwist'
    
    #>>> Data gather and arg check
    mIKHandle = cgmMeta.validateObjArg(ikHandle,'cgmObject',noneValid=False)
    mMidHandle = cgmMeta.validateObjArg(midHandle,'cgmObject',noneValid=True)
    
    if mIKHandle.getMayaType() != 'ikHandle':
        raise ValueError,("|{0}| >> Not an ikHandle ({2}). Type: {1}".format(_str_func, mIKHandle.getMayaType(), mIKHandle.p_nameShort))                                                    
    if mMidHandle and mMidHandle.getMayaType() != 'ikHandle':
        raise ValueError,("|{0}| >> Mid ({2}) not an ikHandle. Type: {1}".format(_str_func, mMidHandle.getMayaType(),mMidHandle.p_nameShort))                                                    

    ml_handles = [mIKHandle]
    if mMidHandle:
        ml_handles.append(mMidHandle)
        
        if advancedTwistSetup:
            log.warning("|{0}| >> advancedTwistSetup not supported with midTwist setup currently. Using no advanced setup.".format(_str_func))                                                        
            advancedTwistSetup = False
        
    mi_crv = cgmMeta.validateObjArg(ATTR.get_driver("%s.inCurve"%mIKHandle.mNode,getNode=True),'cgmObject',noneValid=False)
    
    pprint.pprint(vars())

    mPlug_start = cgmMeta.cgmAttr(mi_crv.mNode,'twistStart',attrType='float',keyable=True, hidden=False)
    mPlug_end = cgmMeta.cgmAttr(mi_crv.mNode,'twistEnd',attrType='float',keyable=True, hidden=False)
    d_return = {"mPlug_start":mPlug_start,"mPlug_end":mPlug_end}    
    
    if not advancedTwistSetup:
        mPlug_twist = cgmMeta.cgmAttr(mIKHandle.mNode,'twist',attrType='float',keyable=True, hidden=False)
    else:
        mi_ramp = cgmMeta.cgmNode(nodeType= 'ramp')
        mi_ramp.doStore('cgmName',mIKHandle.mNode)
        mi_ramp.doName()     
        mlPlugs_twist = []
        
        for mHandle in ml_handles:
            mHandle.dTwistControlEnable = True
            mHandle.dTwistValueType = 2
            mHandle.dWorldUpType = 7
            mPlug_twist = cgmMeta.cgmAttr(mHandle,'dTwistRampMult')
            mlPlugs_twist.append(mPlug_twist)
    
            #Fix Ramp
            ATTR.connect("{0}.outColor".format(mi_ramp.mNode),"{0}.dTwistRamp".format(mHandle.mNode))
            d_return['mRamp'] = mi_ramp    
        
    d_return['mPlug_twist']=mPlug_twist
    
    
    if midHandle:
        log.debug("|{0}| >> midHandle mode...".format(_str_func))    
        """
        $sumBase = chain_0.rotateZ + chain_1.rotateZ;
        test_mid_ikH.roll = $sumBase;
        test_mid_ikH.twist = resultCurve_splineIKCurve_splineIKCurve.twistEnd - $sumBase;        
        """

        mPlug_mid = cgmMeta.cgmAttr(mi_crv.mNode,'twistMid',attrType='float',keyable=True, hidden=False)
        mPlug_midResult = cgmMeta.cgmAttr(mi_crv.mNode,'twistMid_result',attrType='float',keyable=True, hidden=False)
        mPlug_midDiff = cgmMeta.cgmAttr(mi_crv.mNode,'twistMid_diff',attrType='float',keyable=True, hidden=False)
        mPlug_midDiv = cgmMeta.cgmAttr(mi_crv.mNode,'twistMid_div',attrType='float',keyable=True, hidden=False)
       
        #First Handle ----------------------------------------------------------------------------------------
        
        arg1 = "{0} = {1} - {2}".format(mPlug_midDiff.p_combinedShortName,
                                        mPlug_end.p_combinedShortName,
                                        mPlug_start.p_combinedShortName)    
        arg2 = "{0} = {1} / 2".format(mPlug_midDiv.p_combinedShortName,
                                      mPlug_midDiff.p_combinedShortName)
        arg3 = "{0} = {1} + {2}".format(mPlug_midResult.p_combinedShortName,
                                        mPlug_midDiv.p_combinedShortName,
                                        mPlug_mid.p_combinedShortName)
        
        for a in arg1,arg2,arg3:
            NodeF.argsToNodes(a).doBuild()
        
        d_return['mPlug_mid'] = mPlug_mid
        d_return['mPlug_midResult'] = mPlug_midResult
        
        mPlug_start.doConnectOut("{0}.roll".format(mIKHandle.mNode))     
        mPlug_midResult.doConnectOut("{0}.twist".format(mIKHandle.p_nameShort))
        

        #Second Handle --------------------------------------------------------------------------------
        mPlug_midSum = cgmMeta.cgmAttr(mi_crv.mNode,'twistMid_sum',attrType='float',keyable=True, hidden=False)
        mPlug_midTwist = cgmMeta.cgmAttr(mi_crv.mNode,'twistMid_twist',attrType='float',keyable=True, hidden=False)
        
        ml_joints = mIKHandle.msgList_get('drivenJoints',asMeta = True)
        mPlug_midSum.doConnectOut("{0}.roll".format(mMidHandle.p_nameShort))
        mPlug_midTwist.doConnectOut("{0}.twist".format(mMidHandle.p_nameShort))
        
        arg1 = "{0} = {1}".format(mPlug_midSum.p_combinedShortName,
                                  ' + '.join(["{0}.r{1}".format(mJnt.p_nameShort,orientation[0]) for mJnt in ml_joints]))
        log.debug(arg1)
        arg2 = "{0} = {1} - {2}".format(mPlug_midTwist.p_combinedShortName,
                                        mPlug_end.p_combinedShortName,
                                        mPlug_midSum.p_combinedShortName)
        for a in arg1,arg2:
            NodeF.argsToNodes(a).doBuild()
        
        """arg1 = "{0}.twist = if {1} > {2}: {3} else {4}".format(mMidHandle.p_nameShort,
                                                               mPlug_start.p_combinedName,
                                                               mPlug_end.p_combinedName,                                                               
                                                               mPlug_endMidDiffResult.p_combinedShortName,
                                                               mPlug_endMidDiffNegResult.p_combinedShortName)"""        
        
        #Second roll...
        
        
        """
        arg1 = "{0}.twist = {1} - {2}".format(mMidHandle.p_nameShort,
                                              mPlug_end.p_combinedShortName,
                                              mPlug_midNegResult.p_combinedShortName)
        """
        
        
    else:
        mPlug_start.doConnectOut("%s.roll"%mIKHandle.mNode)
        #ikHandle1.twist = (ikHandle1.roll *-.77) + curve4.twistEnd # to implement
        arg1 = "{0} = {1} - {2}".format(mPlug_twist.p_combinedShortName,
                                        mPlug_end.p_combinedShortName,
                                        mPlug_start.p_combinedShortName)
        NodeF.argsToNodes(arg1).doBuild()
        
        
    
    if advancedTwistSetup:
        mc.select(mi_ramp.mNode)
        for c in mc.ls("%s.colorEntryList[*]"%mi_ramp.mNode,flatten = True):
            log.debug( mc.removeMultiInstance( c, b = True) )
        mc.setAttr("%s.colorEntryList[0].color"%mi_ramp.mNode,0, 0, 0)
        mc.setAttr("%s.colorEntryList[1].color"%mi_ramp.mNode,1, 1, 1)
        mc.setAttr("%s.colorEntryList[1].position"%mi_ramp.mNode,1)

        mPlug_existingTwistType = cgmMeta.cgmAttr(mi_ramp,'interpolation')
        mPlug_twistType = cgmMeta.cgmAttr(mi_crv,'twistType', attrType = 'enum', enum = ":".join(mPlug_existingTwistType.p_enum))
        mPlug_twistType.doConnectOut(mPlug_existingTwistType.p_combinedShortName)	
    else:
        mPlug_existingTwistType = cgmMeta.cgmAttr(mIKHandle,'twistType')
        mPlug_twistType = cgmMeta.cgmAttr(mi_crv,'twistType', attrType = 'enum', enum = ":".join(mPlug_existingTwistType.p_enum))
        mPlug_twistType.twistType = 'linear'	
        
        for mHandle in ml_handles:
            mPlug_twistType.doConnectOut("{0}.twistType".format(mHandle.mNode))	
            
    return d_return






def addSplineTwistOLD(ikHandle, midHandle = None, advancedTwistSetup = False):
    """
    ikHandle(arg)
    advancedTwistSetup(bool) -- Whether to setup ramp setup or not (False)
    """
    #>>> Data gather and arg check
    mIKHandle = cgmMeta.validateObjArg(ikHandle,cgmMeta.cgmObject,noneValid=False)
    if mIKHandle.getMayaType() != 'ikHandle':
        raise StandardError,"IKHandle_fixTwist>>> '%s' object not 'ikHandle'. Found type: %s"%(mIKHandle.getShortName(),mIKHandle.getMayaType())

    mi_crv = cgmMeta.validateObjArg(ATTR.get_driver("%s.inCurve"%mIKHandle.mNode,getNode=True),cgmMeta.cgmObject,noneValid=False)
    log.debug(mi_crv.mNode)

    mPlug_start = cgmMeta.cgmAttr(mi_crv.mNode,'twistStart',attrType='float',keyable=True, hidden=False)
    mPlug_end = cgmMeta.cgmAttr(mi_crv.mNode,'twistEnd',attrType='float',keyable=True, hidden=False)
    #mPlug_equalizedRoll = cgmMeta.cgmAttr(mIKHandle.mNode,'result_twistEqualized',attrType='float',keyable=True, hidden=False)
    d_return = {"mi_plug_start":mPlug_start,"mi_plug_end":mPlug_end}    
    if not advancedTwistSetup:
        mPlug_twist = cgmMeta.cgmAttr(mIKHandle.mNode,'twist',attrType='float',keyable=True, hidden=False)	
    else:
        mIKHandle.dTwistControlEnable = True
        mIKHandle.dTwistValueType = 2
        mIKHandle.dWorldUpType = 7
        mPlug_twist = cgmMeta.cgmAttr(mIKHandle,'dTwistRampMult')
        mi_ramp = cgmMeta.cgmNode(nodeType= 'ramp')
        mi_ramp.doStore('cgmName',mIKHandle.mNode)
        mi_ramp.doName()

        #Fix Ramp
        ATTR.connect("%s.outColor"%mi_ramp.mNode,"%s.dTwistRamp"%mIKHandle.mNode)
        d_return['mi_ramp'] = mi_ramp

    mPlug_start.doConnectOut("%s.roll"%mIKHandle.mNode)
    d_return['mi_plug_twist']=mPlug_twist
    #ikHandle1.twist = (ikHandle1.roll *-.77) + curve4.twistEnd # to implement
    arg1 = "%s = %s - %s"%(mPlug_twist.p_combinedShortName,mPlug_end.p_combinedShortName,mPlug_start.p_combinedShortName)
    log.debug("arg1: '%s'"%arg1)    
    log.debug( NodeF.argsToNodes(arg1).doBuild() )       

    if advancedTwistSetup:
        mc.select(mi_ramp.mNode)
        log.debug( mc.attributeInfo("%s.colorEntryList"%mi_ramp.mNode) )
        for c in mc.ls("%s.colorEntryList[*]"%mi_ramp.mNode,flatten = True):
            log.debug(c)
            log.debug( mc.removeMultiInstance( c, b = True) )
        mc.setAttr("%s.colorEntryList[0].color"%mi_ramp.mNode,0, 0, 0)
        mc.setAttr("%s.colorEntryList[1].color"%mi_ramp.mNode,1, 1, 1)
        mc.setAttr("%s.colorEntryList[1].position"%mi_ramp.mNode,1)

        mPlug_existingTwistType = cgmMeta.cgmAttr(mi_ramp,'interpolation')
        mPlug_twistType = cgmMeta.cgmAttr(mi_crv,'twistType', attrType = 'enum', enum = ":".join(mPlug_existingTwistType.p_enum))
        mPlug_twistType.doConnectOut(mPlug_existingTwistType.p_combinedShortName)	
    else:
        mPlug_existingTwistType = cgmMeta.cgmAttr(mIKHandle,'twistType')
        mPlug_twistType = cgmMeta.cgmAttr(mi_crv,'twistType', attrType = 'enum', enum = ":".join(mPlug_existingTwistType.p_enum))
        mPlug_twistType.twistType = 'linear'	
        mPlug_twistType.doConnectOut(mPlug_existingTwistType.p_combinedShortName)	
    return d_return




def buildFKIK(fkJoints = None,
              ikJoints = None,
              blendJoints = None,
              settings = None,
              orientation = 'zyx',
              ikControl = None,
              ikMid = None,
              mirrorDirection = 'Left',
              globalScalePlug = 'PLACER.scaleY',
              fkGroup = None,
              ikGroup = None):

    ml_blendJoints = cgmMeta.validateObjListArg(blendJoints,'cgmObject')
    ml_fkJoints = cgmMeta.validateObjListArg(fkJoints,'cgmObject')
    ml_ikJoints = cgmMeta.validateObjListArg(ikJoints,'cgmObject')

    mi_settings = cgmMeta.validateObjArg(settings,'cgmObject')

    aimVector = VALID.simpleAxis("%s+"%orientation[0]).p_vector#dictionary.stringToVectorDict.get("%s+"%self._go._jointOrientation[0])
    upVector = VALID.simpleAxis("%s+"%orientation[1]).p_vector#dictionary.stringToVectorDict.get("%s+"%self._go._jointOrientation[1])
    outVector = VALID.simpleAxis("%s+"%orientation[2]).p_vector#dictionary.stringToVectorDict.get("%s+"%self._go._jointOrientation[2])


    mControlIK = cgmMeta.validateObjArg(ikControl,'cgmObject')
    mControlMidIK = cgmMeta.validateObjArg(ikMid,'cgmObject')
    mPlug_lockMid = cgmMeta.cgmAttr(mControlMidIK,'lockMid',attrType='float',defaultValue = 0,keyable = True,minValue=0,maxValue=1.0)


    #for more stable ik, we're gonna lock off the lower channels degrees of freedom
    for chain in [ml_ikJoints]:
        for axis in orientation[:2]:
            for i_j in chain[1:]:
                ATTR.set(i_j.mNode,"jointType%s"%axis.upper(),1)


    ml_toParentChains = []
    ml_fkAttachJoints = []   
    """
    self.ml_toParentChains = []
    self.ml_fkAttachJoints = []
    if self._go._str_mirrorDirection == 'Right':#mirror control setup
        self.ml_fkAttachJoints = self._go._i_rigNull.msgList_get('fkAttachJoints')
        self.ml_toParentChains.append(self.ml_fkAttachJoints)

    self.ml_toParentChains.extend([self.ml_ikJoints,self.ml_blendJoints])
    for chain in self.ml_toParentChains:
        chain[0].parent = self._go._i_constrainNull.mNode"""



    #def build_fkJointLength(self):      
    #for i,i_jnt in enumerate(self.ml_fkJoints[:-1]):
    #    rUtils.addJointLengthAttr(i_jnt,orientation=self._go._jointOrientation)

    #def build_pvIK(self):
    mPlug_globalScale = cgmMeta.validateAttrArg(globalScalePlug)['mi_plug']


    #Create no flip arm IK
    #We're gonna use the no flip stuff for the most part
    d_armPVReturn = rUtils.IKHandle_create(ml_ikJoints[0].mNode,ml_ikJoints[ikLen - 1].mNode,nameSuffix = 'PV',
                                           rpHandle=True, controlObject=mControlIK, addLengthMulti=True,
                                           globalScaleAttr=mPlug_globalScale.p_combinedName, stretch='translate',
                                           )

    mi_armIKHandlePV = d_armPVReturn['mi_handle']
    ml_distHandlesPV = d_armPVReturn['ml_distHandles']
    mRPHandlePV = d_armPVReturn['mRPHandle']
    mPlug_lockMid = d_armPVReturn['mPlug_lockMid']



    mi_armIKHandlePV.parent = mControlIK.mNode#armIK to ball		
    ml_distHandlesPV[-1].parent = mControlIK.mNode#arm distance handle to ball	
    ml_distHandlesPV[0].parent = mi_settings#hip distance handle to deform group
    ml_distHandlesPV[1].parent = mControlMidIK.mNode#elbow distance handle to midIK
    mRPHandlePV.parent = mControlMidIK


    #RP handle	
    #mRPHandlePV.doCopyNameTagsFromObject(self._go._mModule.mNode, ignore = ['cgmName','cgmType'])
    mRPHandlePV.addAttr('cgmName','elbowPoleVector',attrType = 'string')
    mRPHandlePV.doName()

    #Mid fix
    #=========================================================================================			
    mc.move(0,0,-25,mControlMidIK.mNode,r=True, rpr = True, ws = True, wd = True)#move out the midControl to fix the twist from

    #>>> Fix our ik_handle twist at the end of all of the parenting
    #rUtils.IKHandle_fixTwist(mi_armIKHandlePV)#Fix the twist

    log.info("rUtils.IKHandle_fixTwist('%s')"%mi_armIKHandlePV.getShortName())
    #Register our snap to point before we move it back
    i_ikMidMatch = RIGMETA.cgmDynamicMatch(dynObject=mControlMidIK,
                                           dynPrefix = "FKtoIK",
                                           dynMatchTargets=ml_blendJoints[1]) 	
    #>>> Reset the translations
    mControlMidIK.translate = [0,0,0]

    #Move the lock mid and add the toggle so it only works with show elbow on
    #mPlug_lockMid.doTransferTo(mControlMidIK.mNode)#move the lock mid	

    #Parent constain the ik wrist joint to the ik wrist
    #=========================================================================================				
    mc.orientConstraint(mControlIK.mNode,ml_ikJoints[ikLen-1].mNode, maintainOffset = True)	

    #Blend stuff
    #-------------------------------------------------------------------------------------
    mPlug_FKIK = cgmMeta.cgmAttr(mi_settings.mNode,'blend_FKIK',attrType='float',lock=False,keyable=True)

    if ml_fkAttachJoints:
        ml_fkUse = ml_fkAttachJoints
        for i,mJoint in enumerate(ml_fkAttachJoints):
            mc.pointConstraint(ml_fkJoints[i].mNode,mJoint.mNode,maintainOffset = False)
            #Connect inversed aim and up
            NodeF.connectNegativeAttrs(ml_fkJoints[i].mNode, mJoint.mNode,
                                       ["r%s"%orientation[0],"r%s"%orientation[1]]).go()
            cgmMeta.cgmAttr(ml_fkJoints[i].mNode,"r%s"%orientation[2]).doConnectOut("%s.r%s"%(mJoint.mNode,orientation[2]))
    else:
        ml_fkUse = ml_fkJoints

    rUtils.connectBlendChainByConstraint(ml_fkUse,ml_ikJoints,ml_blendJoints,
                                         driver = mPlug_FKIK.p_combinedName,l_constraints=['point','orient'])


    #>>> Settings - constrain
    #mc.parentConstraint(self.ml_blendJoints[0].mNode, self.mi_settings.masterGroup.mNode, maintainOffset = True)

    #>>> Setup a vis blend result
    mPlug_FKon = cgmMeta.cgmAttr(mi_settings,'result_FKon',attrType='float',defaultValue = 0,keyable = False,lock=True,hidden=True)	
    mPlug_IKon = cgmMeta.cgmAttr(mi_settings,'result_IKon',attrType='float',defaultValue = 0,keyable = False,lock=True,hidden=True)	

    NodeF.createSingleBlendNetwork(mPlug_FKIK.p_combinedName,
                                   mPlug_IKon.p_combinedName,
                                   mPlug_FKon.p_combinedName)

    mPlug_FKon.doConnectOut("%s.visibility"%fkGroup)
    mPlug_IKon.doConnectOut("%s.visibility"%ikGroup)	


    pprint.pprint(vars())
    return True


def ribbon_createSurface(jointList=[], createAxis = 'x', sectionSpans=1):
    """ 
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    ACKNOWLEDMENT:
    This is a modification of the brilliant technique I got from Matt's blog - 
    http://td-matt.blogspot.com/2011/01/spine-control-rig.html?showComment=1297462382914#c3066380136039163369

    DESCRIPTION:
    Lofts a surface from a joint list

    ARGUMENTS:
    jointList(list) - list of the joints you want to loft from
    outChannel(string)['x','y','z - the the extrude out direction

    RETURNS:
    surface(string)
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    """

    """ return a good length for out loft curves """
    try:
        _str_func = 'ribbon_createSurface'
        mAxis_out = VALID.simpleAxis(createAxis)
        crvUp = mAxis_out.p_string
        crvDn = mAxis_out.inverse.p_string
        
        f_distance = (DIST.get_distance_between_targets([jointList[0],jointList[-1]])/ len(jointList))/2
        
        l_crvs = []
        for j in jointList:
            crv =   mc.curve (d=1, ep = [DIST.get_pos_by_axis_dist(j, crvUp, f_distance),
                                         DIST.get_pos_by_axis_dist(j, crvDn, f_distance)],
                                   os=True)
            log.debug("|{0}| >> Created: {1}".format(_str_func,crv))
            l_crvs.append(crv)
            
        _res_body = mc.loft(l_crvs, reverseSurfaceNormals = True, ch = False, uniform = True, degree = 3, sectionSpans=sectionSpans)

        #_res_body = mc.loft(l_crvs, o = True, d = 1, po = 1 )
        #_inputs = mc.listHistory(_res_body[0],pruneDagObjects=True)
        #_tessellate = _inputs[0]
        
        #_d = {'format':2,#General
        #      'polygonType':1,#'quads'
        #      }
              
        #for a,v in _d.iteritems():
        #    ATTR.set(_tessellate,a,v)
        mc.delete(l_crvs)
        return _res_body
    except Exception,err:cgmGEN.cgmException(Exception,err)
    
    
def ribbon(jointList = None,
           useSurface = None,
           orientation = 'zyx',
           secondaryAxis = 'y+',
           loftAxis = 'x',
           baseName = None,
           connectBy = 'constraint',
           stretchBy = 'translate',
           squashStretchMain = 'arcLength',
           squashStretch = None, 
           sectionSpans = 1, 
           driverSetup = None,#...aim.stable
           msgDriver = None,#...msgLink on joint to a driver group for constaint purposes
           settingsControl = None,
           extraSquashControl = False,#...setup extra attributes
           specialMode = None,
           masterScalePlug = None,
           squashFactorMode = 'midPeak',
           squashFactorMin = 0.0,
           squashFactorMax = 1.0,
           #advancedTwistSetup = False,
           #extendTwistToEnd = False,
           #reorient = False,
           influences = None,
           moduleInstance = None,
           parentGutsTo = None):

    """
    Root of the segment setup.
    Inspiriation from Jason Schleifer's work as well as

    http://faithofthefallen.wordpress.com/2008/10/08/awesome-spine-setup/
    on twist methods.

    Latest update - April 30, 2018

    :parameters:
        jointList(joints - None) | List or metalist of joints
        useCurve(nurbsCurve - None) | Which curve to use. If None. One Created
        orientation(string - zyx) | What is the joints orientation
        secondaryAxis(maya axis arg(y+) | Only necessary when no module provide for orientating
        baseName(string - None) | baseName string
        connectBy(str)
        
        squashStretchMain(str)
            arcLength
            pointDist
            
        squashStretch(str)
            None
            simple - just base measure
            single - measure actual surface distance on the main axis
            both - add a second ribbon for the third axis
        
        stretchBy(string - trans/scale/None) | How the joint will scale
        
        sectionSpans(int) - default 2 - number of spans in the loft per section
        
        driverSetup(string) | Extra setup on driver
            None
            stable - two folicle stable setup
            stableBlend - two follicle with blend aim
            aim - aim along the chain
        
        squashFactorMode 
            max - just just use squashFactorMax
            min - just use reampScaleMin
            midPeak - ramp from zero to full | ex: [0.0, 0.5, 1.0, 1.0, 0.5, 0.0]
            
        squashFactorMax
            1.0 - default
        squashFactorMin
            0.0- default
            
        specialMode
            None
            noStartEnd
            
        masterScalePlug - ONLY matters for squash and stetch setup
            None - setup a plug on the surface for it
            'create' - make a measure curve. It'll be connected to the main surface on a message attr called segScaleCurve
            attribute arg - use this plug
            
            
        advancedTwistSetup(bool - False) | Whether to do the cgm advnaced twist setup
        addMidTwist(bool - True) | Whether to setup a mid twist on the segment
        
        influences(joints - None) | List or metalist of joints to skin our objects to
        moduleInstance(cgmModule - None) | cgmModule to use for connecting on build
        extendTwistToEnd(bool - False) | Whether to extned the twist to the end by default

    :returns:
        mIKHandle, mIKEffector, mIKSolver, mi_splineCurve
        

    :raises:
        Exception | if reached

    """   	 
    #try:
    _str_func = 'ribbon'
    ml_rigObjectsToConnect = []
    ml_rigObjectsToParent = []
    
    #try:
    #>>> Verify =============================================================================================
    ml_joints = cgmMeta.validateObjListArg(jointList,mType = 'cgmObject', mayaType=['joint'], noneValid = False)
    l_joints = [mJnt.p_nameShort for mJnt in ml_joints]
    int_lenJoints = len(ml_joints)#because it's called repeatedly
    
    mi_useSurface = cgmMeta.validateObjArg(useSurface,mayaType=['nurbsSurface'],noneValid = True)
    mi_mayaOrientation = VALID.simpleOrientation(orientation)
    str_orientation = mi_mayaOrientation.p_string
    str_secondaryAxis = VALID.stringArg(secondaryAxis,noneValid=True)
    str_baseName = VALID.stringArg(baseName,noneValid=True)
    
    if specialMode and specialMode not in ['noStartEnd']:
        raise ValueError,"Unknown special mode: {0}".format(specialMode)
    
    
    ml_influences = cgmMeta.validateObjListArg(influences,mType = 'cgmObject', noneValid = True)
    if ml_influences:
        l_influences = [mObj.p_nameShort for mObj in ml_influences]
        int_lenInfluences = len(l_influences)#because it's called repeatedly    
    
    
    #module -----------------------------------------------------------------------------------------------
    mModule = cgmMeta.validateObjArg(moduleInstance,noneValid = True)
    #try:mModule.isModule()
    #except:mModule = False

    mi_rigNull = False	
    if mModule:
        log.debug("|{0}| >> Module found. mModule: {1}...".format(_str_func,mModule))                                    
        mi_rigNull = mModule.rigNull	
        if str_baseName is None:
            str_baseName = mModule.getPartNameBase()#Get part base name	    
    if not str_baseName:str_baseName = 'testRibbon' 
    #...
    
    #str_stretchBy = VALID.stringArg(stretchBy,noneValid=True)		
    #b_advancedTwistSetup = VALID.boolArg(advancedTwistSetup)
    #b_extendTwistToEnd= VALID.boolArg(extendTwistToEnd)

    if int_lenJoints<3:
        pprint.pprint(vars())
        raise ValueError,"needs at least three joints"
    
    if parentGutsTo is None:
        mGroup = cgmMeta.cgmObject(name = 'newgroup')
        mGroup.addAttr('cgmName', str(str_baseName), lock=True)
        mGroup.addAttr('cgmTypeModifier','segmentStuff', lock=True)
        mGroup.doName()
    else:
        mGroup = cgmMeta.validateObjArg(parentGutsTo,'cgmObject',False)
        
        
    if mModule:
        mGroup.parent = mModule.rigNull

    #Good way to verify an instance list? #validate orientation             
    #> axis -------------------------------------------------------------
    axis_aim = VALID.simpleAxis("{0}+".format(str_orientation[0]))
    axis_aimNeg = axis_aim.inverse
    axis_up = VALID.simpleAxis("{0}+".format(str_orientation [1]))
    axis_out = VALID.simpleAxis("{0}+".format(str_orientation [2]))

    v_aim = axis_aim.p_vector#aimVector
    v_aimNeg = axis_aimNeg.p_vector#aimVectorNegative
    v_up = axis_up.p_vector   #upVector
    v_out = axis_out.p_vector
    
    str_up = axis_up.p_string
    
    loftAxis2 = False
    #Figure out our loft axis stuff
    if loftAxis not in  orientation:
        _lower_loftAxis = loftAxis.lower()
        if _lower_loftAxis in ['out','up']:
            if _lower_loftAxis == 'out':
                loftAxis = str_orientation[2]
            else:
                loftAxis = str_orientation[1]
        else:
            raise ValueError,"Not sure what to do with loftAxis: {0}".format(loftAxis)
    
    #Ramp values -------------------------------------------------------------------------
    if extraSquashControl:
        l_scaleFactors = MATH.get_blendList(int_lenJoints,squashFactorMax,squashFactorMin,squashFactorMode)
        
    #Squash stretch -------------------------------------------------------------------------
    b_squashStretch = False
    if squashStretch is not None:
        b_squashStretch = True
        if squashStretch == 'both':
            loftAxis2 = str_orientation[1]
            
        """
        mTransGroup = cgmMeta.cgmObject(name = 'newgroup')
        mTransGroup.addAttr('cgmName', str(str_baseName), lock=True)
        mTransGroup.addAttr('cgmTypeModifier','segmentTransStuff', lock=True)
        mTransGroup.doName()"""
        
        
        
    outChannel = str_orientation[2]#outChannel
    upChannel = str_orientation[1]
    #upChannel = '{0}up'.format(str_orientation[1])#upChannel
    l_param = []  
    
    
    mControlSurface2 = False
    ml_surfaces = []
    #>>> Ribbon Surface ===========================================================================================        
    if mi_useSurface:
        raise NotImplementedError,'Not done with passed surface'
    else:
        log.debug("|{0}| >> Creating surface...".format(_str_func))
        l_surfaceReturn = ribbon_createSurface(jointList,loftAxis,sectionSpans)
    
        mControlSurface = cgmMeta.validateObjArg( l_surfaceReturn[0],'cgmObject',setClass = True )
        mControlSurface.addAttr('cgmName',str(baseName),attrType='string',lock=True)    
        mControlSurface.addAttr('cgmType','controlSurface',attrType='string',lock=True)
        mControlSurface.doName()
        
        ml_surfaces.append(mControlSurface)
        
        if loftAxis2:
            log.debug("|{0}| >> Creating surface...".format(_str_func))
            l_surfaceReturn2 = ribbon_createSurface(jointList,loftAxis2,sectionSpans)
        
            mControlSurface2 = cgmMeta.validateObjArg( l_surfaceReturn[0],'cgmObject',setClass = True )
            mControlSurface2.addAttr('cgmName',str(baseName),attrType='string',lock=True)
            mControlSurface2.addAttr('cgmTypeModifier','up',attrType='string',lock=True)
            mControlSurface2.addAttr('cgmType','controlSurface',attrType='string',lock=True)
            mControlSurface2.doName()
    
            ml_surfaces.append(mControlSurface2)
    
    log.debug("mControlSurface: {0}".format(mControlSurface))
    
    
    mArcLenCurve = None
    if b_squashStretch and squashStretchMain == 'arcLength':
        log.debug("|{0}| >> Creating arc curve setup...".format(_str_func))

        plug = '{0}_segScale'.format(str_baseName)
        plug_curve = '{0}_arcLengthCurve'.format(str_baseName)
        plug_inverse = '{0}_segInverseScale'.format(str_baseName)
        
        crv = CORERIG.create_at(None,'curve',l_pos= [mJnt.p_position for mJnt in ml_joints])
        
        mCrv = cgmMeta.validateObjArg(crv,'cgmObject',setClass=True)
        mCrv.rename('{0}_measureCrv'.format( baseName))
        
        mArcLenCurve = mCrv
        
        mControlSurface.connectChildNode(mCrv,plug_curve,'ribbon')

        log.debug("|{0}| >> created: {1}".format(_str_func,mCrv)) 

        infoNode = CURVES.create_infoNode(mCrv.mNode)

        mInfoNode = cgmMeta.validateObjArg(infoNode,'cgmNode',setClass=True)
        mCrv.addAttr('baseDist', mInfoNode.arcLength,attrType='float',lock=True)
        mInfoNode.rename('{0}_{1}_measureCIN'.format( baseName,plug))

        log.debug("|{0}| >> baseDist: {1}".format(_str_func,mCrv.baseDist)) 

        #mPlug_masterScale = cgmMeta.cgmAttr(mCrv.mNode,plug,'float')
        mPlug_inverseScale = cgmMeta.cgmAttr(mCrv.mNode,plug_inverse,'float')
        
        l_argBuild=[]
        """
        l_argBuild.append("{0} = {1} / {2}".format(mPlug_masterScale.p_combinedShortName,
                                                   '{0}.arcLength'.format(mInfoNode.mNode),
                                                   "{0}.baseDist".format(mCrv.mNode)))"""
        l_argBuild.append("{0} = {2} / {1}".format(mPlug_inverseScale.p_combinedShortName,
                                                   '{0}.arcLength'.format(mInfoNode.mNode),
                                                   "{0}.baseDist".format(mCrv.mNode)))        
        
        
        for arg in l_argBuild:
            log.debug("|{0}| >> Building arg: {1}".format(_str_func,arg))
            NodeF.argsToNodes(arg).doBuild()                        
    
    if b_squashStretch and masterScalePlug is not None:
        log.debug("|{0}| >> Checking masterScalePlug: {1}".format(_str_func, masterScalePlug))        
        if masterScalePlug == 'create':
            log.debug("|{0}| >> Creating measure curve setup...".format(_str_func))
            
            plug = 'segMasterScale'
            plug_curve = 'segMasterMeasureCurve'
            crv = CORERIG.create_at(None,'curveLinear',l_pos= [ml_joints[0].p_position, ml_joints[1].p_position])
            mCrv = cgmMeta.validateObjArg(crv,'cgmObject',setClass=True)
            mCrv.rename('{0}_masterMeasureCrv'.format( baseName))
    
            mControlSurface.connectChildNode(mCrv,plug_curve,'rigNull')
    
            log.debug("|{0}| >> created: {1}".format(_str_func,mCrv)) 
    
            infoNode = CURVES.create_infoNode(mCrv.mNode)
    
            mInfoNode = cgmMeta.validateObjArg(infoNode,'cgmNode',setClass=True)
            mInfoNode.addAttr('baseDist', mInfoNode.arcLength,attrType='float')
            mInfoNode.rename('{0}_{1}_measureCIN'.format( baseName,plug))
    
            log.debug("|{0}| >> baseDist: {1}".format(_str_func,mInfoNode.baseDist)) 
    
            mPlug_masterScale = cgmMeta.cgmAttr(mControlSurface.mNode,plug,'float')
    
            l_argBuild=[]
            l_argBuild.append("{0} = {1} / {2}".format(mPlug_masterScale.p_combinedShortName,
                                                       '{0}.arcLength'.format(mInfoNode.mNode),
                                                       "{0}.baseDist".format(mInfoNode.mNode)))
            for arg in l_argBuild:
                log.debug("|{0}| >> Building arg: {1}".format(_str_func,arg))
                NodeF.argsToNodes(arg).doBuild()                
    
        else:
            if issubclass(type(masterScalePlug),cgmMeta.cgmAttr):
                mPlug_masterScale = masterScalePlug
            else:
                d_attr = cgmMeta.validateAttrArg(masterScalePlug)
                if not d_attr:
                    raise ValueError,"Ineligible masterScalePlug: {0}".format(masterScalePlug)
                mPlug_masterScale  = d_attr['mPlug']
            
        if not mPlug_masterScale:
            raise ValueError,"Should have a masterScale plug by now"
    
    if settingsControl:
        mSettings = cgmMeta.validateObjArg(settingsControl,'cgmObject')
    else:
        mSettings = mControlSurface
    
    if mModule:#if we have a module, connect vis
        mControlSurface.overrideEnabled = 1
        cgmMeta.cgmAttr(mModule.rigNull.mNode,'gutsVis',lock=False).doConnectOut("%s.%s"%(mControlSurface.mNode,'overrideVisibility'))
        cgmMeta.cgmAttr(mModule.rigNull.mNode,'gutsLock',lock=False).doConnectOut("%s.%s"%(mControlSurface.mNode,'overrideDisplayType'))    
        mControlSurface.parent = mModule.rigNull
    
    #>>> Follicles ===========================================================================================        
    log.debug("|{0}| >> Follicles...".format(_str_func)+cgmGEN._str_subLine)
    
    ml_follicles = []
    ml_follicleShapes = []
    ml_upGroups = []
    ml_aimDrivers = []
    ml_upTargets = []
    ml_folliclesStable = []
    ml_folliclesStableShapes = []
    
    minU = ATTR.get(mControlSurface.getShapes()[0],'minValueU')        
    #maxU = ATTR.get(mControlSurface.getShapes()[0],'maxValueU')
    #minV = ATTR.get(mControlSurface.getShapes()[0],'mimValueV')        
    #maxV = ATTR.get(mControlSurface.getShapes()[0],'maxValueV')
    f_offset = DIST.get_distance_between_targets(l_joints,True)
    
    range_joints = range(len(ml_joints))
    l_firstLastIndices = [range_joints[0],range_joints[-1]]
    
    for i,mJnt in enumerate(ml_joints):
        log.debug("|{0}| >> On: {1}".format(_str_func,mJnt))        
        
        mDriven = mJnt
        if specialMode == 'noStartEnd' and mJnt in [ml_joints[0],ml_joints[-1]]:
            pass
        else:
            if msgDriver:
                log.debug("|{0}| >> Checking msgDriver: {1}".format(_str_func,msgDriver))                
                mDriven = mJnt.getMessage(msgDriver,asMeta=True)
                if not mDriven:
                    raise ValueError,"Missing msgDriver: {0} | {1}".format(msgDriver,mJnt)
                mDriven = mDriven[0]
                log.debug("|{0}| >> Found msgDriver: {1} | {2}".format(_str_func,msgDriver,mDriven))
                
        log.debug("|{0}| >> Attaching mDriven: {1}".format(_str_func,mDriven))
        
        follicle,shape = RIGCONSTRAINTS.attach_toShape(mDriven.mNode, mControlSurface.mNode, None)
        mFollicle = cgmMeta.asMeta(follicle)
        mFollShape = cgmMeta.asMeta(shape)
        
        ml_follicleShapes.append(mFollShape)
        ml_follicles.append(mFollicle)
        
        mFollicle.parent = mGroup.mNode

        if mModule:#if we have a module, connect vis
            mFollicle.overrideEnabled = 1
            cgmMeta.cgmAttr(mModule.rigNull.mNode,'gutsVis',lock=False).doConnectOut("%s.%s"%(mFollicle.mNode,'overrideVisibility'))
            cgmMeta.cgmAttr(mModule.rigNull.mNode,'gutsLock',lock=False).doConnectOut("%s.%s"%(mFollicle.mNode,'overrideDisplayType'))    
            
        mDriver = mFollicle
        
        if specialMode == 'noStartEnd' and mJnt in [ml_joints[0],ml_joints[-1]]:
            log.debug("|{0}| >> noStartEnd skip: {1}".format(_str_func,mJnt))
            ml_aimDrivers.append(mDriver)
            ml_upGroups.append(False)
            ml_upTargets.append(False)                        
            continue
        
        if driverSetup:
            mDriver = mJnt.doCreateAt(setClass=True)
            mDriver.rename("{0}_aimDriver".format(mFollicle.p_nameBase))
            mDriver.parent = mFollicle
            mUpGroup = mDriver.doGroup(True,asMeta=True,typeModifier = 'up')
            
            ml_aimDrivers.append(mDriver)
            ml_upGroups.append(mUpGroup)
            
            if driverSetup in ['stable','stableBlend']:
                mUpDriver = mJnt.doCreateAt(setClass=True)
                mDriver.rename("{0}_upTarget".format(mFollicle.p_nameBase))                    
                pos = DIST.get_pos_by_axis_dist(mJnt.mNode, str_up, f_offset)
                mUpDriver.p_position = pos
                mUpDriver.p_parent = mUpGroup
                
                ml_upTargets.append(mUpDriver)
                
        #Simple contrain
        mc.parentConstraint([mDriver.mNode], mDriven.mNode, maintainOffset=True)
        
    if ml_aimDrivers:
        log.debug("|{0}| >> aimDrivers...".format(_str_func)+cgmGEN._str_subLine)            
        if driverSetup == 'aim':
            for i,mDriver in enumerate(ml_aimDrivers):
                if specialMode == 'noStartEnd' and i in l_firstLastIndices:
                    log.debug("|{0}| >> noStartEnd skip: {1}".format(_str_func,mDriver))                    
                    continue
                    
                v_aimUse = v_aim
                if mDriver == ml_aimDrivers[-1]:
                    s_aim = ml_follicles[-2].mNode
                    v_aimUse = v_aimNeg
                else:
                    s_aim = ml_follicles[i+1].mNode
            
                mc.aimConstraint(s_aim, ml_aimDrivers[i].mNode, maintainOffset = True, #skip = 'z',
                                 aimVector = v_aimUse, upVector = v_up, worldUpObject = ml_upGroups[i].mNode,
                                 worldUpType = 'objectrotation', worldUpVector = v_up)            
        else:
            for i,mDriver in enumerate(ml_aimDrivers):
                if specialMode == 'noStartEnd' and i in l_firstLastIndices:
                    log.debug("|{0}| >> noStartEnd skip: {1}".format(_str_func,mDriver))                    
                    continue                
                #We need to make new follicles
                l_stableFollicleInfo = NODES.createFollicleOnMesh( mControlSurface.mNode )
            
                mStableFollicle = cgmMeta.asMeta(l_stableFollicleInfo[1],'cgmObject',setClass=True)
                mStableFollicleShape = cgmMeta.asMeta(l_stableFollicleInfo[0],'cgmNode')
                mStableFollicle.parent = mGroup.mNode
                
                ml_folliclesStable.append(mStableFollicle)
                ml_folliclesStableShapes.append(ml_folliclesStableShapes)
                
                #> Name...
                #mStableFollicleTrans.doStore('cgmName',mObj.mNode)
                #mStableFollicleTrans.doStore('cgmTypeModifier','surfaceStable')            
                #mStableFollicleTrans.doName()
                mStableFollicle.rename('{0}_surfaceStable'.format(ml_joints[i].p_nameBase))
            
                mStableFollicleShape.parameterU = minU
                mStableFollicleShape.parameterV = ml_follicleShapes[i].parameterV
                
                if driverSetup == 'stable':
                    if mDriver in [ml_aimDrivers[0],ml_aimDrivers[-1]]:
                        #...now aim it
                        mc.aimConstraint(mStableFollicle.mNode, mDriver.mNode, maintainOffset = True, #skip = 'z',
                                         aimVector = v_aim, upVector = v_up, worldUpObject = ml_upTargets[i].mNode,
                                         worldUpType = 'object', worldUpVector = v_up)                     
                    else:
                        #was aimint at follicles... ml_follicles
                        mc.aimConstraint(ml_follicles[i+1].mNode, ml_aimDrivers[i].mNode, maintainOffset = True, #skip = 'z',
                                         aimVector = v_aim, upVector = v_up, worldUpObject = ml_upTargets[i].mNode,
                                         worldUpType = 'object', worldUpVector = v_up)
                else: #stableBlend....
                    if mDriver in [ml_aimDrivers[0],ml_aimDrivers[-1]]:
                        #...now aim it
                        mc.aimConstraint(mStableFollicle.mNode, mDriver.mNode, maintainOffset = True, #skip = 'z',
                                         aimVector = v_aim, upVector = v_up, worldUpObject = ml_upTargets[i].mNode,
                                         worldUpType = 'object', worldUpVector = v_up)
                    else:
                        mAimForward = mDriver.doCreateAt()
                        mAimForward.parent = mDriver.p_parent
                        mAimForward.doStore('cgmTypeModifier','forward')
                        mAimForward.doStore('cgmType','aimer')
                        mAimForward.doName()
                    

                        mAimBack = mDriver.doCreateAt()
                        mAimBack.parent = mDriver.p_parent
                        mAimBack.doStore('cgmTypeModifier','back')
                        mAimBack.doStore('cgmType','aimer')
                        mAimBack.doName()
                        
                        mc.aimConstraint(ml_follicles[i+1].mNode, mAimForward.mNode, maintainOffset = True, #skip = 'z',
                                         aimVector = v_aim, upVector = v_up, worldUpObject = ml_upTargets[i].mNode,
                                         worldUpType = 'object', worldUpVector = v_up)
                        mc.aimConstraint(ml_follicles[i-1].mNode, mAimBack.mNode, maintainOffset = True, #skip = 'z',
                                         aimVector = v_aimNeg, upVector = v_up, worldUpObject = ml_upTargets[i].mNode,
                                         worldUpType = 'object', worldUpVector = v_up)                        

                        mc.orientConstraint([mAimForward.mNode,mAimBack.mNode], ml_aimDrivers[i].mNode, maintainOffset=True)
                        #mc.aimConstraint(ml_follicles[i+1].mNode, ml_aimDrivers[i].mNode, maintainOffset = True, #skip = 'z',
                        #                 aimVector = v_aim, upVector = v_up, worldUpObject = ml_upTargets[i].mNode,
                        #                 worldUpType = 'object', worldUpVector = v_up)                                                            

                    
                
        """
        if mJnt != ml_joints[-1]:
            mUpLoc = mJnt.doLoc()#Make up Loc
            mLocRotateGroup = mJnt.doCreateAt()#group in place
            mLocRotateGroup.parent = i_follicleTrans.mNode
            mLocRotateGroup.doStore('cgmName',mJnt.mNode)	    
            mLocRotateGroup.addAttr('cgmTypeModifier','rotate',lock=True)
            mLocRotateGroup.doName()
        
            #Store the rotate group to the joint
            mJnt.connectChildNode(mLocRotateGroup,'rotateUpGroup','drivenJoint')
            mZeroGrp = cgmMeta.asMeta( mLocRotateGroup.doGroup(True),'cgmObject',setClass=True )
            mZeroGrp.addAttr('cgmTypeModifier','zero',lock=True)
            mZeroGrp.doName()
            #connect some other data
            mLocRotateGroup.connectChildNode(i_follicleTrans,'follicle','drivenGroup')
            mLocRotateGroup.connectChildNode(mLocRotateGroup.parent,'zeroGroup')
            mLocRotateGroup.connectChildNode(mUpLoc,'upLoc')
        
            mc.makeIdentity(mLocRotateGroup.mNode, apply=True,t=1,r=1,s=1,n=0)
        
            mUpLoc.parent = mLocRotateGroup.mNode
            mc.move(0,10,0,mUpLoc.mNode,os=True)	
            ml_upGroups.append(mUpLoc)
        
            if mModule:#if we have a module, connect vis
                mUpLoc.overrideEnabled = 1		
                cgmMeta.cgmAttr(mModule.rigNull.mNode,'gutsVis',lock=False).doConnectOut("%s.%s"%(mUpLoc.mNode,'overrideVisibility'))
                cgmMeta.cgmAttr(mModule.rigNull.mNode,'gutsLock',lock=False).doConnectOut("%s.%s"%(mUpLoc.mNode,'overrideDisplayType'))    
        
        else:#if last...
            pass"""
        
    if b_squashStretch:
        log.debug("|{0}| >> SquashStretch...".format(_str_func)+cgmGEN._str_subLine)
        
        if extraSquashControl:
            mPlug_segScale = cgmMeta.cgmAttr(mSettings.mNode,
                                             "{0}_segScale".format(str_baseName),
                                             attrType = 'float',
                                             hidden = False,                                                 
                                             initialValue=1.0,
                                             lock=False,
                                             minValue = 0)
            
        if squashStretchMain == 'arcLength':
            mPlug_inverseNormalized = cgmMeta.cgmAttr(mControlSurface.mNode,
                                             "{0}_normalInverse".format(str_baseName),
                                             attrType = 'float',
                                             hidden = False,)
                
            arg = "{0} = {1} * {2}".format(mPlug_inverseNormalized.p_combinedShortName,
                                           mPlug_inverseScale.p_combinedShortName,
                                           mPlug_masterScale.p_combinedShortName)
            NodeF.argsToNodes(arg).doBuild()
            
        
        log.debug("|{0}| >> Making our base dist stuff".format(_str_func))
        
        ml_distanceObjectsBase = []
        ml_distanceShapesBase = []
        
        ml_distanceObjectsActive = []
        ml_distanceShapesActive = []
        
        md_distDat = {}
        for k in ['aim','up','out']:
            md_distDat[k] = {}
            for k2 in 'base','active':
                md_distDat[k][k2] = {'mTrans':[],
                                     'mDist':[]}

        #mSegmentCurve.addAttr('masterScale',value = 1.0, minValue = 0.0001, attrType='float')
        ml_outFollicles = []
        if ml_folliclesStable:
            log.debug("|{0}| >> Found out follicles via stable...".format(_str_func))                
            ml_outFollicles = ml_folliclesStable
        else:
            raise ValueError,"Must create out follicles"
        
        #Up follicles =================================================================================
        ml_upFollicles = []
        ml_upFollicleShapes = []
        
        if mControlSurface2:
            log.debug("|{0}| >> up follicle setup...".format(_str_func,)+cgmGEN._str_subLine)
            
            for i,mJnt in enumerate(ml_joints):
                #We need to make new follicles
                l_FollicleInfo = NODES.createFollicleOnMesh( mControlSurface2.mNode )
            
                mUpFollicle = cgmMeta.asMeta(l_FollicleInfo[1],'cgmObject',setClass=True)
                mUpFollicleShape = cgmMeta.asMeta(l_FollicleInfo[0],'cgmNode')
                
                mUpFollicle.parent = mGroup.mNode
                
                ml_upFollicles.append(mUpFollicle)
                ml_upFollicleShapes.append(mUpFollicleShape)
                
                #> Name...
                mUpFollicle.rename('{0}_surfaceUp'.format(ml_joints[i].p_nameBase))
            
                mUpFollicleShape.parameterU = minU
                mUpFollicleShape.parameterV = ml_follicleShapes[i].parameterV
                
            
        def createDist(mJnt, typeModifier = None):
            mShape = cgmMeta.cgmNode( mc.createNode ('distanceDimShape') )        
            mObject = mShape.getTransform(asMeta=True) 
            mObject.doStore('cgmName',mJnt.mNode)
            if typeModifier:
                mObject.addAttr('cgmTypeModifier',typeModifier,lock=True)                
            mObject.addAttr('cgmType','measureNode',lock=True)
            mObject.doName(nameShapes = True)
            mObject.parent = mGroup.mNode#parent it
            mObject.overrideEnabled = 1
            mObject.overrideVisibility = 1
            
            if mModule:#Connect hides if we have a module instance:
                ATTR.connect("{0}.gutsVis".format(mModule.rigNull.mNode),"{0}.overrideVisibility".format(mObject.mNode))
                ATTR.connect("{0}.gutsLock".format(mModule.rigNull.mNode),"{0}.overrideDisplayType".format(mObject.mNode))
            
            return mObject,mShape
            
        if squashStretch != 'simple':
            for i,mJnt in enumerate(ml_joints):#Base measure ===================================================
                """
                log.debug("|{0}| >> Base measure for: {1}".format(_str_func,mJnt))
                
                mDistanceDag,mDistanceShape = createDist(mJnt, 'base')
                mDistanceDag.p_parent = mTransGroup
                
                #Connect things
                ATTR.connect(ml_follicles[i].mNode+'.translate',mDistanceShape.mNode+'.startPoint')
                ATTR.connect(ml_follicles[i+1].mNode+'.translate',mDistanceShape.mNode+'.endPoint')
                
                ATTR.break_connection(mDistanceShape.mNode+'.startPoint')
                ATTR.break_connection(mDistanceShape.mNode+'.endPoint')
                
                md_distDat['aim']['base']['mTrans'].append(mDistanceDag)
                md_distDat['aim']['base']['mDist'].append(mDistanceShape)
                """
                if mJnt == ml_joints[-1]:
                    #use the the last....
                    md_distDat['aim']['active']['mTrans'].append(mDistanceDag)
                    md_distDat['aim']['active']['mDist'].append(mDistanceShape)                
                else:
                    #Active measures ---------------------------------------------------------------------
                    log.debug("|{0}| >> Active measure for: {1}".format(_str_func,mJnt))
                    #>> Distance nodes
                    mDistanceDag,mDistanceShape = createDist(mJnt, 'active')
        
                    #Connect things
                    #.on loc = position
                    ATTR.connect(ml_follicles[i].mNode+'.translate',mDistanceShape.mNode+'.startPoint')
                    ATTR.connect(ml_follicles[i+1].mNode+'.translate',mDistanceShape.mNode+'.endPoint')
                    
                    #ml_distanceObjectsActive.append(mDistanceDag)
                    #ml_distanceShapesActive.append(mDistanceShape)
                    md_distDat['aim']['active']['mTrans'].append(mDistanceDag)
                    md_distDat['aim']['active']['mDist'].append(mDistanceShape)
    
            if ml_outFollicles or ml_upFollicles:
                for i,mJnt in enumerate(ml_joints):
                    if ml_outFollicles:
                        """
                        #Out Base ---------------------------------------------------------------------------------
                        log.debug("|{0}| >> Out base measure for: {1}".format(_str_func,mJnt))
                        
                        mDistanceDag,mDistanceShape = createDist(mJnt, 'baseOut')
                        mDistanceDag.p_parent = mTransGroup
    
                        #Connect things
                        ATTR.connect(ml_follicles[i].mNode+'.translate',mDistanceShape.mNode+'.startPoint')
                        ATTR.connect(ml_outFollicles[i].mNode+'.translate',mDistanceShape.mNode+'.endPoint')
                        
                        ATTR.break_connection(mDistanceShape.mNode+'.startPoint')
                        ATTR.break_connection(mDistanceShape.mNode+'.endPoint')
                        
                        md_distDat['out']['base']['mTrans'].append(mDistanceDag)
                        md_distDat['out']['base']['mDist'].append(mDistanceShape)
                        """
                        
                        #ml_distanceObjectsBase.append(mDistanceDag)
                        #ml_distanceShapesBase.append(mDistanceShape)
                        
                        #Out Active---------------------------------------------------------------------------------
                        log.debug("|{0}| >> Out active measure for: {1}".format(_str_func,mJnt))
                        
                        mDistanceDag,mDistanceShape = createDist(mJnt, 'activeOut')
                                        
                        #Connect things
                        ATTR.connect(ml_follicles[i].mNode+'.translate',mDistanceShape.mNode+'.startPoint')
                        ATTR.connect(ml_outFollicles[i].mNode+'.translate',mDistanceShape.mNode+'.endPoint')
                        
                        #ml_distanceObjectsBase.append(mDistanceDag)
                        #ml_distanceShapesBase.append(mDistanceShape)
                        md_distDat['out']['active']['mTrans'].append(mDistanceDag)
                        md_distDat['out']['active']['mDist'].append(mDistanceShape)
                    
                    if ml_upFollicles:
                        """
                        #Up Base ---------------------------------------------------------------------------------
                        log.debug("|{0}| >> Up base measure for: {1}".format(_str_func,mJnt))
                        
                        mDistanceDag,mDistanceShape = createDist(mJnt, 'baseUp')
                        mDistanceDag.p_parent = mTransGroup
    
                        #Connect things
                        ATTR.connect(ml_follicles[i].mNode+'.translate',mDistanceShape.mNode+'.startPoint')
                        ATTR.connect(ml_upFollicles[i].mNode+'.translate',mDistanceShape.mNode+'.endPoint')
                        
                        ATTR.break_connection(mDistanceShape.mNode+'.startPoint')
                        ATTR.break_connection(mDistanceShape.mNode+'.endPoint')
                        
                        md_distDat['up']['base']['mTrans'].append(mDistanceDag)
                        md_distDat['up']['base']['mDist'].append(mDistanceShape)
                        #ml_distanceObjectsBase.append(mDistanceDag)
                        #ml_distanceShapesBase.append(mDistanceShape)
                        """
                        
                        #Up Active---------------------------------------------------------------------------------
                        log.debug("|{0}| >> Up active measure for: {1}".format(_str_func,mJnt))
                        
                        mDistanceDag,mDistanceShape = createDist(mJnt, 'activeUp')
                                        
                        #Connect things
                        ATTR.connect(ml_follicles[i].mNode+'.translate',mDistanceShape.mNode+'.startPoint')
                        ATTR.connect(ml_upFollicles[i].mNode+'.translate',mDistanceShape.mNode+'.endPoint')
                        
                        #ml_distanceObjectsBase.append(mDistanceDag)
                        #ml_distanceShapesBase.append(mDistanceShape)
                        md_distDat['up']['active']['mTrans'].append(mDistanceDag)
                        md_distDat['up']['active']['mDist'].append(mDistanceShape)                


        
        
        #>>>Hook up stretch/scale #========================================================================= 
        if squashStretchMain == 'arcLength':
            log.debug("|{0}| >> arcLength aim stretch setup ".format(_str_func)+cgmGEN._str_subLine)
            for i,mJnt in enumerate(ml_joints):#Nodes =======================================================
                
                
                if extraSquashControl:
                    mPlug_aimResult = cgmMeta.cgmAttr(mControlSurface.mNode,
                                                      "{0}_aimScaleResult_{1}".format(str_baseName,i),
                                                      attrType = 'float',
                                                      initialValue=0,
                                                      lock=True,
                                                      minValue = 0)                    
                    """
                    mPlug_baseRes = cgmMeta.cgmAttr(mControlSurface.mNode,
                                                     "{0}_baseRes_{1}".format(str_baseName,i),
                                                     attrType = 'float')"""                    
                    mPlug_jointFactor = cgmMeta.cgmAttr(mSettings.mNode,
                                                        "{0}_factor_{1}".format(str_baseName,i),
                                                        attrType = 'float',
                                                        hidden = False,
                                                        initialValue=l_scaleFactors[i],
                                                        defaultValue=l_scaleFactors[i],
                                                        lock=False,
                                                        minValue = 0)
                    
                    mPlug_jointRes = cgmMeta.cgmAttr(mControlSurface.mNode,
                                                     "{0}_factorRes_{1}".format(str_baseName,i),
                                                     attrType = 'float')
                    
                    mPlug_jointDiff = cgmMeta.cgmAttr(mControlSurface.mNode,
                                                      "{0}_factorDiff_{1}".format(str_baseName,i),
                                                      attrType = 'float')
                    mPlug_jointMult = cgmMeta.cgmAttr(mControlSurface.mNode,
                                                      "{0}_factorMult_{1}".format(str_baseName,i),
                                                      attrType = 'float')                    
                    
                    #>> x + (y - x) * blend --------------------------------------------------------
                    mPlug_baseRes = mPlug_inverseNormalized
                    """
                    l_argBuild.append("{0} = {1} / {2}".format(mPlug_baseRes.p_combinedShortName,
                                                               mPlug_aimBaseNorm.p_combinedShortName,
                                                               "{0}.distance".format(mActive_aim.mNode)))"""
                    l_argBuild.append("{0} = 1 + {1}".format(mPlug_aimResult.p_combinedShortName,
                                                               mPlug_jointMult.p_combinedShortName))
                    l_argBuild.append("{0} = {1} - 1".format(mPlug_jointDiff.p_combinedShortName,
                                                             mPlug_baseRes.p_combinedShortName))
                    l_argBuild.append("{0} = {1} * {2}".format(mPlug_jointMult.p_combinedShortName,
                                                               mPlug_jointDiff.p_combinedShortName,
                                                               mPlug_jointRes.p_combinedShortName))
                    
                    
                    l_argBuild.append("{0} = {1} * {2}".format(mPlug_jointRes.p_combinedShortName,
                                                               mPlug_jointFactor.p_combinedShortName,
                                                               mPlug_segScale.p_combinedShortName))                    
    
                    
                else:
                    mPlug_aimResult = mPlug_inverseNormalized
                
                
                for arg in l_argBuild:
                    log.debug("|{0}| >> Building arg: {1}".format(_str_func,arg))
                    NodeF.argsToNodes(arg).doBuild()
                    
                mPlug_aimResult.doConnectOut('{0}.{1}'.format(mJnt.mNode,'scaleZ'))
            
                if squashStretch == 'simple':
                    for axis in ['scaleX','scaleY']:
                        mPlug_aimResult.doConnectOut('{0}.{1}'.format(mJnt.mNode,axis))
                        
                mPlug_aimResult.doConnectOut('{0}.{1}'.format(mJnt.mNode,'scaleZ'))
        
        else:
            for i,mJnt in enumerate(ml_joints):#Nodes =======================================================
                mActive_aim =  md_distDat['aim']['active']['mDist'][i]
    
                mPlug_aimResult = cgmMeta.cgmAttr(mControlSurface.mNode,
                                                  "{0}_aimScaleResult_{1}".format(str_baseName,i),
                                                  attrType = 'float',
                                                  initialValue=0,
                                                  lock=True,
                                                  minValue = 0)
                
                mPlug_aimBase = cgmMeta.cgmAttr(mControlSurface.mNode,
                                               "{0}_aimBase_{1}".format(str_baseName,i),
                                               attrType = 'float',
                                               lock=True,
                                               value=ATTR.get('{0}.distance'.format(mActive_aim.mNode)))
    
                mPlug_aimBaseNorm = cgmMeta.cgmAttr(mControlSurface.mNode,
                                                  "{0}_aimBaseNorm_{1}".format(str_baseName,i),
                                                  attrType = 'float',
                                                  initialValue=0,
                                                  lock=True,
                                                  minValue = 0)
                
                l_argBuild = []
                l_argBuild.append("{0} = {1} * {2}".format(mPlug_aimBaseNorm.p_combinedShortName,
                                                           mPlug_aimBase.p_combinedShortName,
                                                           mPlug_masterScale.p_combinedShortName,))
                
                
                #baseSquashScale = distBase / distActual
                #out scale = baseSquashScale * (outBase / outActual)
                #mBase_aim =  md_distDat['aim']['base']['mDist'][i]
                
    
                
                
                if extraSquashControl:
                    #mPlug_segScale
                    mPlug_baseRes = cgmMeta.cgmAttr(mControlSurface.mNode,
                                                     "{0}_baseRes_{1}".format(str_baseName,i),
                                                     attrType = 'float')                    
                    mPlug_jointFactor = cgmMeta.cgmAttr(mSettings.mNode,
                                                        "{0}_factor_{1}".format(str_baseName,i),
                                                        attrType = 'float',
                                                        hidden = False,
                                                        initialValue=l_scaleFactors[i],
                                                        defaultValue=l_scaleFactors[i],
                                                        lock=False,
                                                        minValue = 0)
                    mPlug_jointRes = cgmMeta.cgmAttr(mControlSurface.mNode,
                                                     "{0}_factorRes_{1}".format(str_baseName,i),
                                                     attrType = 'float')
                    
                    mPlug_jointDiff = cgmMeta.cgmAttr(mControlSurface.mNode,
                                                      "{0}_factorDiff_{1}".format(str_baseName,i),
                                                      attrType = 'float')
                    #mPlug_jointAdd = cgmMeta.cgmAttr(mControlSurface.mNode,
                    #                                  "{0}_factorAdd_{1}".format(str_baseName,i),
                    #                                  attrType = 'float')
                    mPlug_jointMult = cgmMeta.cgmAttr(mControlSurface.mNode,
                                                      "{0}_factorMult_{1}".format(str_baseName,i),
                                                      attrType = 'float')                    
                    
                    #>> x + (y - x) * blend --------------------------------------------------------
                    l_argBuild.append("{0} = {1} / {2}".format(mPlug_baseRes.p_combinedShortName,
                                                               mPlug_aimBaseNorm.p_combinedShortName,
                                                               "{0}.distance".format(mActive_aim.mNode)))
                    l_argBuild.append("{0} = 1 + {1}".format(mPlug_aimResult.p_combinedShortName,
                                                               mPlug_jointMult.p_combinedShortName))
                    l_argBuild.append("{0} = {1} - 1".format(mPlug_jointDiff.p_combinedShortName,
                                                             mPlug_baseRes.p_combinedShortName))
                    l_argBuild.append("{0} = {1} * {2}".format(mPlug_jointMult.p_combinedShortName,
                                                               mPlug_jointDiff.p_combinedShortName,
                                                               mPlug_jointRes.p_combinedShortName))
                    
                    
                    l_argBuild.append("{0} = {1} * {2}".format(mPlug_jointRes.p_combinedShortName,
                                                               mPlug_jointFactor.p_combinedShortName,
                                                               mPlug_segScale.p_combinedShortName))                    
    
                    
                else:
                    l_argBuild.append("{0} = {1} / {2}".format(mPlug_aimResult.p_combinedShortName,
                                                               mPlug_aimBaseNorm.p_combinedShortName,
                                                               "{0}.distance".format(mActive_aim.mNode)))
                
                
                for arg in l_argBuild:
                    log.debug("|{0}| >> Building arg: {1}".format(_str_func,arg))
                    NodeF.argsToNodes(arg).doBuild()
                    
                mPlug_aimResult.doConnectOut('{0}.{1}'.format(mJnt.mNode,'scaleZ'))
            
                if not ml_outFollicles:
                    for axis in ['scaleX','scaleY']:
                        mPlug_aimResult.doConnectOut('{0}.{1}'.format(mJnt.mNode,axis))                    
                mPlug_aimResult.doConnectOut('{0}.{1}'.format(mJnt.mNode,'scaleZ'))
            
        if squashStretch in ['single','both']:
            if ml_outFollicles or ml_upFollicles:
                for i,mJnt in enumerate(ml_joints):
                    if mJnt == ml_joints[-1]:
                        pass #...we'll pick up the last on the loop
                    else:
                        mPlug_aimResult = cgmMeta.cgmAttr(mControlSurface.mNode,
                                                          "{0}_aimScaleResult_{1}".format(str_baseName,i))
                        #mActive_aim =  md_distDat['aim']['active']['mDist'][i]                        
                        
                    
                    if ml_outFollicles:
                        #mBase_out =  md_distDat['out']['base']['mDist'][i]
                        mActive_out =  md_distDat['out']['active']['mDist'][i]
                        
                        mPlug_outResult = cgmMeta.cgmAttr(mControlSurface.mNode,
                                                          "{0}_outScaleResult_{1}".format(str_baseName,i),
                                                          attrType = 'float',
                                                          lock=True,
                                                          minValue = 0)
                        
                        mPlug_outBase = cgmMeta.cgmAttr(mControlSurface.mNode,
                                                        "{0}_outBaseScaleResult_{1}".format(str_baseName,i),
                                                        attrType = 'float',
                                                        value=ATTR.get('{0}.distance'.format(mActive_out.mNode)))
             
                        mPlug_outBaseNorm = cgmMeta.cgmAttr(mControlSurface.mNode,
                                                          "{0}_outBaseNorm_{1}".format(str_baseName,i),
                                                          attrType = 'float',
                                                          lock=True,
                                                          minValue = 0)
                        
                        mPlug_outBaseRes = cgmMeta.cgmAttr(mControlSurface.mNode,
                                                            "{0}_outBaseRes_{1}".format(str_baseName,i),
                                                            attrType = 'float',
                                                            lock=True)                    
                         
                        l_argBuild = []
                        l_argBuild.append("{0} = {1} * {2}".format(mPlug_outBaseNorm.p_combinedShortName,
                                                                   mPlug_outBase.p_combinedShortName,
                                                                   mPlug_masterScale.p_combinedShortName,))
                        
                        #baseSquashScale = distBase / distActual
                        #out scale = baseSquashScale * (outBase / outActual)
    
     
                        
                        l_argBuild.append("{0} = {1} / {2}".format(mPlug_outBaseRes.p_combinedShortName,
                                                                   '{0}.distance'.format(mActive_out.mNode),
                                                                   mPlug_outBaseNorm.p_combinedShortName,))
                        
                        l_argBuild.append("{0} = {1} * {2}".format(mPlug_outResult.p_combinedShortName,
                                                                   mPlug_aimResult.p_combinedShortName,
                                                                   mPlug_outBaseRes.p_combinedShortName))
                        
                        
                        for arg in l_argBuild:
                            log.debug("|{0}| >> Building arg: {1}".format(_str_func,arg))
                            NodeF.argsToNodes(arg).doBuild()
                            
                            
                        #out scale ---------------------------------------------------------------
                        for axis in ['scaleX','scaleY']:
                            mPlug_outResult.doConnectOut('{0}.{1}'.format(mJnt.mNode,axis))
                            
                    if ml_upFollicles:
                        #mBase_up =  md_distDat['up']['base']['mDist'][i]
                        mActive_up =  md_distDat['up']['active']['mDist'][i]
                        
                        mPlug_upResult = cgmMeta.cgmAttr(mControlSurface.mNode,
                                                          "{0}_upScaleResult_{1}".format(str_baseName,i),
                                                          attrType = 'float',
                                                          lock=True,
                                                          minValue = 0)
                        
                        mPlug_upBase = cgmMeta.cgmAttr(mControlSurface.mNode,
                                                       "{0}_upBaseScaleResult_{1}".format(str_baseName,i),
                                                       attrType = 'float',
                                                       value=ATTR.get('{0}.distance'.format(mActive_up.mNode)))
                        
                        mPlug_upBaseRes = cgmMeta.cgmAttr(mControlSurface.mNode,
                                                          "{0}_upBaseRes_{1}".format(str_baseName,i),
                                                          attrType = 'float',
                                                          lock=True,
                                                          minValue = 0)
            
                        mPlug_upBaseNorm = cgmMeta.cgmAttr(mControlSurface.mNode,
                                                          "{0}_upBaseNorm_{1}".format(str_baseName,i),
                                                          attrType = 'float',
                                                          lock=True,
                                                          minValue = 0)
                        
                        l_argBuild = []
                        l_argBuild.append("{0} = {1} * {2}".format(mPlug_upBaseNorm.p_combinedShortName,
                                                                   mPlug_upBase.p_combinedShortName,
                                                                   mPlug_masterScale.p_combinedShortName,))                    
                        
                        #baseSquashScale = distBase / distActual
                        #up scale = baseSquashScale * (upBase / upActual)
    
                        
    
                        
                        l_argBuild.append("{0} = {1} / {2}".format(mPlug_upBaseRes.p_combinedShortName,
                                                                   '{0}.distance'.format(mActive_up.mNode),
                                                                   mPlug_upBaseNorm.p_combinedShortName,))
                        
                        l_argBuild.append("{0} = {1} * {2}".format(mPlug_upResult.p_combinedShortName,
                                                                   mPlug_aimResult.p_combinedShortName,
                                                                   mPlug_upBaseRes.p_combinedShortName))
                        
                        
                        for arg in l_argBuild:
                            log.debug("|{0}| >> Building arg: {1}".format(_str_func,arg))
                            NodeF.argsToNodes(arg).doBuild()
                            
                            
                        #up scale ---------------------------------------------------------------
                        for axis in ['scaleY']:
                            mPlug_upResult.doConnectOut('{0}.{1}'.format(mJnt.mNode,axis))                


            
    #>>> Connect our iModule vis stuff
    if mModule:#if we have a module, connect vis
        log.debug("|{0}| >> mModule wiring...".format(_str_func)+cgmGEN._str_subLine)            
        
        for mObj in ml_rigObjectsToConnect:
            mObj.overrideEnabled = 1		
            cgmMeta.cgmAttr(mModule.rigNull.mNode,'gutsVis',lock=False).doConnectOut("%s.%s"%(mObj.mNode,'overrideVisibility'))
            cgmMeta.cgmAttr(mModule.rigNull.mNode,'gutsLock',lock=False).doConnectOut("%s.%s"%(mObj.mNode,'overrideDisplayType'))    
        for mObj in ml_rigObjectsToParent:
            mObj.parent = mModule.rigNull.mNode

    if ml_influences:
        log.debug("|{0}| >> Influences found. Attempting to skin...".format(_str_func)+cgmGEN._str_subLine)            
        
        max_influences = 2
        mode_tighten = 'twoBlend'
        blendLength = 5
        
        if int_lenInfluences > 2:
            mode_tighten = None
            blendLength = int(int_lenInfluences/2)
            max_influences = MATH.Clamp( blendLength, 2, 4)
            
        if mArcLenCurve:
            log.debug("|{0}| >> Skinning arcLen Curve: {1}".format(_str_func,mArcLenCurve))
            
            mSkinCluster = cgmMeta.validateObjArg(mc.skinCluster ([mObj.mNode for mObj in ml_influences],
                                                                  mArcLenCurve.mNode,
                                                                  tsb=True,
                                                                  maximumInfluences = max_influences,
                                                                  normalizeWeights = 1,dropoffRate=5.0),
                                                  'cgmNode',
                                                  setClass=True)
        
            mSkinCluster.doStore('cgmName', mArcLenCurve.mNode)
            mSkinCluster.doName()    
        
            #Tighten the weights...
            RIGSKIN.curve_tightenEnds(mArcLenCurve.mNode,
                                       hardLength = 2,
                                       blendLength=blendLength,
                                       mode=mode_tighten)
            
            
        for mSurf in ml_surfaces:
            log.debug("|{0}| >> Skinning surface: {1}".format(_str_func,mSurf))
            mSkinCluster = cgmMeta.validateObjArg(mc.skinCluster ([mObj.mNode for mObj in ml_influences],
                                                                  mSurf.mNode,
                                                                  tsb=True,
                                                                  maximumInfluences = max_influences,
                                                                  normalizeWeights = 1,dropoffRate=5.0),
                                                  'cgmNode',
                                                  setClass=True)
        
            mSkinCluster.doStore('cgmName', mSurf.mNode)
            mSkinCluster.doName()    
        
            #Tighten the weights...
            RIGSKIN.surface_tightenEnds(mSurf.mNode,
                                         hardLength = 2,
                                         blendLength=blendLength,
                                         mode=mode_tighten)
            
    
    
    _res = {'mlSurfaces':ml_surfaces}
    return _res


def handleHOLDER(jointList = None,
           useCurve = None,
           orientation = 'zyx',
           secondaryAxis = 'y+',
           baseName = None,
           stretchBy = 'translate',
           advancedTwistSetup = False,
           extendTwistToEnd = False,
           reorient = False,
           moduleInstance = None,
           parentGutsTo = None):
    """
    Root of the segment setup.
    Inspiriation from Jason Schleifer's work as well as

    http://faithofthefallen.wordpress.com/2008/10/08/awesome-spine-setup/
    on twist methods.

    Latest rewrite - July 2017

    :parameters:
        jointList(joints - None) | List or metalist of joints
        useCurve(nurbsCurve - None) | Which curve to use. If None. One Created
        orientation(string - zyx) | What is the joints orientation
        secondaryAxis(maya axis arg(y+) | Only necessary when no module provide for orientating
        baseName(string - None) | baseName string
        stretchBy(string - trans/scale/None) | How the joint will scale
        advancedTwistSetup(bool - False) | Whether to do the cgm advnaced twist setup
        addMidTwist(bool - True) | Whether to setup a mid twist on the segment
        moduleInstance(cgmModule - None) | cgmModule to use for connecting on build
        extendTwistToEnd(bool - False) | Whether to extned the twist to the end by default

    :returns:
        mIKHandle, mIKEffector, mIKSolver, mi_splineCurve
        

    :raises:
        Exception | if reached

    """ 
    _str_func = 'splineIK'
    #try:
    #>>> Verify =============================================================================================
    ml_joints = cgmMeta.validateObjListArg(jointList,mType = 'cgmObject', mayaType=['joint'], noneValid = False)
    l_joints = [mJnt.p_nameShort for mJnt in ml_joints]
    int_lenJoints = len(ml_joints)#because it's called repeatedly
    mi_useCurve = cgmMeta.validateObjArg(useCurve,mayaType=['nurbsCurve'],noneValid = True)

    mi_mayaOrientation = VALID.simpleOrientation(orientation)
    str_orientation = mi_mayaOrientation.p_string
    str_secondaryAxis = VALID.stringArg(secondaryAxis,noneValid=True)
    str_baseName = VALID.stringArg(baseName,noneValid=True)
    
    
    #module -----------------------------------------------------------------------------------------------
    mModule = cgmMeta.validateObjArg(moduleInstance,noneValid = True)
    try:mModule.isModule()
    except:mModule = False

    mi_rigNull = False	
    if mModule:
        log.debug("|{0}| >> Module found. mModule: {1}...".format(_str_func,mModule))                                    
        mi_rigNull = mModule.rigNull	
        if str_baseName is None:
            str_baseName = mModule.getPartNameBase()#Get part base name	    
    if not str_baseName:str_baseName = 'testSplineIK' 
    #...
    
    str_stretchBy = VALID.stringArg(stretchBy,noneValid=True)		
    b_advancedTwistSetup = VALID.boolArg(advancedTwistSetup)
    b_extendTwistToEnd= VALID.boolArg(extendTwistToEnd)

    if int_lenJoints<3:
        pprint.pprint(vars())
        raise ValueError,"needs at least three joints"
    
    if parentGutsTo is None:
        mGroup = cgmMeta.cgmObject(name = 'newgroup')
        mGroup.addAttr('cgmName', str(str_baseName), lock=True)
        mGroup.addAttr('cgmTypeModifier','segmentStuff', lock=True)
        mGroup.doName()
    else:
        mGroup = cgmMeta.validateObjArg(parentGutsTo,'cgmObject',False)

    #Good way to verify an instance list? #validate orientation             
    #> axis -------------------------------------------------------------
    axis_aim = VALID.simpleAxis("{0}+".format(str_orientation[0]))
    axis_aimNeg = axis_aim.inverse
    axis_up = VALID.simpleAxis("{0}+".format(str_orientation [1]))

    v_aim = axis_aim.p_vector#aimVector
    v_aimNeg = axis_aimNeg.p_vector#aimVectorNegative
    v_up = axis_up.p_vector   #upVector

    outChannel = str_orientation[2]#outChannel
    upChannel = '{0}up'.format(str_orientation[1])#upChannel
    l_param = []  


def handle(startJoint,
           endJoint,
           solverType = 'ikRPsolver',
           rpHandle = False,
           lockMid = True,
           addLengthMulti = False,
           stretch = False, globalScaleAttr = None,
           controlObject = None,
           baseName = None,
           orientation = 'zyx',
           nameSuffix = None,
           handles = [],#If one given, assumed to be mid, can't have more than length of joints
           moduleInstance = None):
    """
    @kws
    l_jointChain1(list) -- blend list 1
    l_jointChain2(list) -- blend list 2
    l_blendChain(list) -- result chain
    solverType -- 'ikRPsolver','ikSCsolver'
    baseName -- 
    nameSuffix -- add to nameBase
    rpHandle(bool/string) -- whether to have rphandle setup, object to use if string or MetaClass
    lockMid(bool) --
    driver(attr arg) -- driver attr
    globalScaleAttr(string/cgmAttr) -- global scale attr to connect in
    addLengthMulti(bool) -- whether to setup lengthMultipliers
    controlObject(None/string) -- whether to have control to put attrs on, object to use if string or MetaClass OR will use ikHandle
    channels(list) -- channels to blend
    stretch(bool/string) -- stretch options - translate/scale
    moduleInstance -- instance to connect stuff to

    """
    try:
        _str_func = 'handle'
        log.debug("|{0}| >> ...".format(_str_func))  
        
    
        ml_rigObjectsToConnect = []
        ml_rigObjectsToParent = []
    
        #>>> Data gather and arg check
        if solverType not in ['ikRPsolver','ikSCsolver']:
            raise ValueError,"|{0}| >> Invalid solverType: {1}".format(_str_func,solverType)
        
        
        mi_mayaOrientation = VALID.simpleOrientation(orientation)
        str_orientation = mi_mayaOrientation.p_string
        #str_secondaryAxis = VALID.stringArg(secondaryAxis,noneValid=True)
        str_baseName = VALID.stringArg(baseName,noneValid=True)
        
        #module -----------------------------------------------------------------------------------------------
        mModule = cgmMeta.validateObjArg(moduleInstance,noneValid = True)
        #try:mModule.isModule()
        #except:mModule = False
    
        mi_rigNull = False	
        if mModule:
            log.debug("|{0}| >> Module found. mModule: {1}...".format(_str_func,mModule))                                    
            mi_rigNull = mModule.rigNull	
            if str_baseName is None:
                str_baseName = mModule.getPartNameBase()#Get part base name	    
        if not str_baseName:str_baseName = 'testIK'     
    
        #Joint chain ======================================================================================
        mStart = cgmMeta.validateObjArg(startJoint,'cgmObject',noneValid=False)
        mEnd = cgmMeta.validateObjArg(endJoint,'cgmObject',noneValid=False)
        if not mEnd.isChildOf(mStart):
            raise ValueError,"|{0}| >> {1} not a child of {2}".format(_str_func,endJoint,startJoint)
            
        
        ml_jointChain = mStart.getListPathTo(mEnd,asMeta=True)
        #ml_jointChain = cgmMeta.validateObjListArg(l_jointChain,'cgmObject',noneValid=False)
        l_jointChain = [mObj.mNode for mObj in ml_jointChain]
        if len(ml_jointChain)<3 and solverType in ['rpSolver']:
            raise ValueError,"|{0}| >> {1} len less than 3 joints. solver: {2}".format(_str_func,len(ml_jointChain,solverType))
            
        _foundPrerred = False
        for mJnt in ml_jointChain:
            for attr in ['preferredAngleX','preferredAngleY','preferredAngleZ']:
                if mJnt.getAttr(attr):
                    log.debug("|{0}| >> Found preferred...".format(_str_func))                  
                    _foundPrerred = True
                    break
        
        #Attributes =====================================================================================
        #Master global control
        d_MasterGlobalScale = cgmMeta.validateAttrArg(globalScaleAttr,noneValid=True)    
        
        #Stretch
        if stretch and stretch not in ['translate','scale']:
            log.debug("|{0}| >> Invalid stretch arg: {1}. Using 'translate'".format(_str_func,stretch))                  
            stretch = 'translate'
        if stretch == 'scale':
            raise NotImplementedError,"|{0}| >> Scale method not done".format(_str_func)
            
        #Handles =======================================================================================
        ml_handles = cgmMeta.validateObjListArg(handles,'cgmObject',noneValid=True)
        if len(ml_handles)>len(ml_jointChain):#Check handle length to joint list
            raise ValueError,"|{0}| >> More handles than joints. joints: {1}| handles: {2}.".format(_str_func,len(ml_jointChain),len(ml_handles))
            
    
        mRPHandle = cgmMeta.validateObjArg(rpHandle,'cgmObject',noneValid=True)
        if mRPHandle and mRPHandle in ml_handles:
            raise NotImplementedError,"|{0}| >> rpHandle can't be a measure handle".format(_str_func)
            
    
        #Control object
        mControl = cgmMeta.validateObjArg(controlObject,'cgmObject',noneValid=True)
        if mControl:
            log.debug("|{0}| >> mControl: {1}.".format(_str_func,mControl))                  
    
        #Figure out our aimaxis
        #v_localAim = distance.returnLocalAimDirection(ml_jointChain[0].mNode,ml_jointChain[1].mNode)
        #str_localAim = dictionary.returnVectorToString(v_localAim)
        #str_localAimSingle = str_localAim[0]
        str_localAimSingle = orientation[0]
        #log.debug("create_IKHandle>>> vector aim: %s | str aim: %s"%(v_localAim,str_localAim))
    
    

        #Create IK handle ==================================================================================
        buffer = mc.ikHandle( sj=mStart.mNode, ee=mEnd.mNode,
                              solver = solverType, forceSolver = True,
                              snapHandleFlagToggle=True )  	
    
    
        #>>> Name
        log.debug(buffer)
        mIKHandle = cgmMeta.asMeta(buffer[0],'cgmObject',setClass=True)
        mIKHandle.addAttr('cgmName',str_baseName,attrType='string',lock=True)
        #mIKHandle.doStore('cgmType','IKHand')
        mIKHandle.doName()
    
        ml_rigObjectsToConnect.append(mIKHandle)
    
        mIKEffector = cgmMeta.asMeta(buffer[1],'cgmNode',setClass=True)
        mIKEffector.addAttr('cgmName',str_baseName,attrType='string',lock=True)    
        mIKEffector.doName()
    
        #>>> Control
        if not mControl:
            mControl = mIKHandle
        else:
            mIKHandle.parent = mControl
            
        #>>> Store our start and end
        mIKHandle.connectChildNode(mStart,'jointStart','ikOwner')
        mIKHandle.connectChildNode(mEnd,'jointEnd','ikOwner')
        
    
        #>>>Stetch #===============================================================================
        mPlug_lockMid = False  
        ml_distanceShapes = []
        ml_distanceObjects = []   
        mPlug_globalScale = False
        if stretch:
            log.debug("|{0}| >> Stretch setup...".format(_str_func))
            
            mPlug_autoStretch = cgmMeta.cgmAttr(mControl,'autoStretch',initialValue = 1, defaultValue = 1, keyable = True, attrType = 'float', minValue = 0, maxValue = 1)
            
            if len(ml_jointChain) == 3 and lockMid:
                log.debug("|{0}| >> MidLock setup possible...".format(_str_func))
                
                if lockMid:mPlug_lockMid = cgmMeta.cgmAttr(mControl,'lockMid',initialValue = 0, attrType = 'float', keyable = True, minValue = 0, maxValue = 1)
        
        
                if addLengthMulti:
                    mPlug_lengthUpr= cgmMeta.cgmAttr(mControl,'lengthUpr',attrType='float',value = 1, defaultValue = 1,minValue=0,keyable = True)
                    mPlug_lengthLwr = cgmMeta.cgmAttr(mControl,'lengthLwr',attrType='float',value = 1, defaultValue = 1,minValue=0,keyable = True)	
                    ml_multiPlugs = [mPlug_lengthUpr,mPlug_lengthLwr]
        
            #Check our handles for stretching
            if len(ml_handles)!= len(ml_jointChain):#we need a handle per joint for measuring purposes
                log.debug("create_IKHandle>>> Making handles")
                ml_buffer = ml_handles
                ml_handles = []
                for j in ml_jointChain:
                    m_match = False
                    for h in ml_buffer:
                        if MATH.is_vector_equivalent(j.getPosition(),h.getPosition()):
                            log.debug("create_IKHandle>>> '%s' handle matches: '%s'"%(h.getShortName(),j.getShortName()))
                            m_match = h
                    if not m_match:#make one
                        m_match = j.doLoc(nameLink = True)
                        m_match.addAttr('cgmTypeModifier','stretchMeasure')
                        m_match.doName()
                    ml_handles.append(m_match)
                    ml_rigObjectsToConnect.append(m_match)
    
                #>>>TODO Add hide stuff
        
                #>>>Do Handles
                mMidHandle = False   
                if ml_handles:
                    if len(ml_handles) == 1:
                        mMidHandle = ml_handles[0]
                    else:
                        mid = int((len(ml_handles))/2)
                        mMidHandle = ml_handles[mid]
                    
                    log.debug("|{0}| >> mid handle: {1}".format(_str_func,mMidHandle))
                        
    
    
            #Overall stretch
            mPlug_globalScale = cgmMeta.cgmAttr(mIKHandle.mNode,'masterScale',value = 1.0, lock =True, hidden = True)
    
    
            md_baseDistReturn = RIGCREATE.distanceMeasure(ml_handles[0].mNode,ml_handles[-1].mNode,baseName=str_baseName)
            
            md_baseDistReturn['mEnd'].p_parent = mControl
            
            ml_rigObjectsToParent.append(md_baseDistReturn['mDag'])
            mPlug_baseDist = cgmMeta.cgmAttr(mIKHandle.mNode,'ikDistBase' , attrType = 'float', value = md_baseDistReturn['mShape'].distance , lock =True , hidden = True)	
            mPlug_baseDistRaw = cgmMeta.cgmAttr(mIKHandle.mNode,'ikDistRaw' , value = 1.0 , lock =True , hidden = True)
            mPlug_baseDistRaw.doConnectIn("%s.distance"%md_baseDistReturn['mShape'].mNode)
            mPlug_baseDistNormal = cgmMeta.cgmAttr(mIKHandle.mNode,'result_ikBaseNormal',value = 1.0, lock =True, hidden = True)
            mPlug_ikDistNormal = cgmMeta.cgmAttr(mIKHandle.mNode,'result_ikDistNormal',value = 1.0, lock =True, hidden = True)	
            mPlug_ikScale = cgmMeta.cgmAttr(mIKHandle.mNode,'result_ikScale',value = 1.0, lock =True, hidden = True)
            mPlug_ikClampScale = cgmMeta.cgmAttr(mIKHandle.mNode,'result_ikClampScale',value = 1.0, lock =True, hidden = True)
            mPlug_ikClampMax = cgmMeta.cgmAttr(mIKHandle.mNode,'result_ikClampMax',value = 1.0, lock =True, hidden = True)
    
            #Normal base
            arg = "%s = %s * %s"%(mPlug_baseDistNormal.p_combinedShortName,
                                  mPlug_baseDist.p_combinedShortName,
                                  mPlug_globalScale.p_combinedShortName)
            NodeF.argsToNodes(arg).doBuild()
    
            #Normal Length
            arg = "%s = %s / %s"%(mPlug_ikDistNormal.p_combinedShortName,
                                  mPlug_baseDistRaw.p_combinedShortName,
                                  mPlug_globalScale.p_combinedShortName)
            NodeF.argsToNodes(arg).doBuild()	
    
            #ik scale
            arg = "%s = %s / %s"%(mPlug_ikScale.p_combinedShortName,
                                  mPlug_baseDistRaw.p_combinedShortName,
                                  mPlug_baseDistNormal.p_combinedShortName)
            NodeF.argsToNodes(arg).doBuild()	
    
            #ik max clamp
            """ This is for maya 2013 (at least) which honors the max over the  min """
            arg = "%s = if %s >= 1: %s else 1"%(mPlug_ikClampMax.p_combinedShortName,
                                                mPlug_ikScale.p_combinedShortName,
                                                mPlug_ikScale.p_combinedShortName)
            NodeF.argsToNodes(arg).doBuild()
    
            #ik clamp scale
            arg = "%s = clamp(1,%s,%s)"%(mPlug_ikClampScale.p_combinedShortName,
                                         mPlug_ikClampMax.p_combinedShortName,
                                         mPlug_ikScale.p_combinedShortName)
            NodeF.argsToNodes(arg).doBuild()	
    
            #Create our blend to stretch or not - blend normal base and stretch base
            mi_stretchBlend = cgmMeta.cgmNode(nodeType= 'blendTwoAttr')
            mi_stretchBlend.addAttr('cgmName','%s_stretchBlend'%(baseName),lock=True)
            mi_stretchBlend.doName()
            ATTR.set(mi_stretchBlend.mNode,"input[0]",1)
            mPlug_ikClampScale.doConnectOut("%s.input[1]"%mi_stretchBlend.mNode)
            mPlug_autoStretch.doConnectOut("%s.attributesBlender"%mi_stretchBlend.mNode)
    
            
            #Make our distance objects per segment
            #=========================================================================
            l_segments = LISTS.get_listPairs(ml_handles)
            for i,seg in enumerate(l_segments):#Make our measure nodes
                buffer =  RIGCREATE.distanceMeasure(seg[0].mNode,seg[-1].mNode,baseName="{0}_{1}".format(str_baseName,i))
                ml_distanceShapes.append(buffer['mShape'])
                ml_distanceObjects.append(buffer['mDag'])
                #>>>TODO Add hide stuff
            ml_rigObjectsToParent.extend(ml_distanceObjects)
            ml_rigObjectsToConnect.extend(ml_handles)
            
            for i,i_jnt in enumerate(ml_jointChain[:-1]):
                #Make some attrs
                mPlug_baseDist= cgmMeta.cgmAttr(mIKHandle.mNode,"baseDist_%s"%i,attrType = 'float' , value = ml_distanceShapes[i].distance , lock=True,minValue = 0)
                mPlug_rawDist = cgmMeta.cgmAttr(mIKHandle.mNode,"baseRaw_%s"%i,attrType = 'float', initialValue=0 , lock=True , minValue = 0)				  	    
                mPlug_normalBaseDist = cgmMeta.cgmAttr(mIKHandle.mNode,"baseNormal_%s"%i,attrType = 'float', initialValue=0 , lock=True , minValue = 0)			
                mPlug_normalDist = cgmMeta.cgmAttr(mIKHandle.mNode,"distNormal_%s"%i,attrType = 'float',initialValue=0,lock=True,minValue = 0)		
                mPlug_stretchDist = cgmMeta.cgmAttr(mIKHandle.mNode,"result_stretchDist_%s"%i,attrType = 'float',initialValue=0,lock=True,minValue = 0)			    
                mPlug_stretchNormalDist = cgmMeta.cgmAttr(mIKHandle.mNode,"result_stretchNormalDist_%s"%i,attrType = 'float',initialValue=0,lock=True,minValue = 0)			    	    
                mPlug_resultSegmentScale = cgmMeta.cgmAttr(mIKHandle.mNode,"segmentScale_%s"%i,attrType = 'float',initialValue=0,lock=True,minValue = 0)	
    
                #Raw distance in
                mPlug_rawDist.doConnectIn("%s.distance"%ml_distanceShapes[i].mNode)	  
    
                #Normal base distance
                arg = "%s = %s * %s"%(mPlug_normalBaseDist.p_combinedShortName,
                                      mPlug_baseDist.p_combinedName,
                                      mPlug_globalScale.p_combinedShortName)
                NodeF.argsToNodes(arg).doBuild()
    
                #Normal distance
                arg = "%s = %s / %s"%(mPlug_normalDist.p_combinedShortName,
                                      mPlug_rawDist.p_combinedName,
                                      mPlug_globalScale.p_combinedShortName)
                NodeF.argsToNodes(arg).doBuild()
    
                #Stretch Distance
                arg = "%s = %s * %s.output"%(mPlug_stretchDist.p_combinedShortName,
                                             mPlug_normalBaseDist.p_combinedName,
                                             mi_stretchBlend.getShortName())
                NodeF.argsToNodes(arg).doBuild()
    
                #Then pull the global out of the stretchdistance 
                arg = "%s = %s / %s"%(mPlug_stretchNormalDist.p_combinedShortName,
                                      mPlug_stretchDist.p_combinedName,
                                      mPlug_globalScale.p_combinedName)
                NodeF.argsToNodes(arg).doBuild()	    
    
                #Segment scale
                arg = "%s = %s / %s"%(mPlug_resultSegmentScale.p_combinedShortName,
                                      mPlug_normalDist.p_combinedName,
                                      mPlug_baseDist.p_combinedShortName)
                NodeF.argsToNodes(arg).doBuild()
    
                #Create our blend to stretch or not - blend normal base and stretch base
                mi_blend = cgmMeta.cgmNode(nodeType= 'blendTwoAttr')
                mi_blend.addAttr('cgmName','%s_stretch_to_lockMid'%(i_jnt.getBaseName()),lock=True)
                mi_blend.doName()
                if mPlug_lockMid:
                    mPlug_lockMid.doConnectOut("%s.attributesBlender"%mi_blend.mNode)
    
                if stretch == 'translate':
                    #Base Normal, Dist Normal
                    mPlug_stretchNormalDist.doConnectOut("%s.input[0]"%mi_blend.mNode)
                    mPlug_normalDist.doConnectOut("%s.input[1]"%mi_blend.mNode)
                    ATTR.connect("%s.output"%mi_blend.mNode,"%s.t%s"%(ml_jointChain[i+1].mNode,str_localAimSingle))
    
        #>>> addLengthMulti
        if addLengthMulti:
            log.debug("|{0}| >> addLengthMulti...".format(_str_func))
            
            if len(ml_jointChain[:-1]) == 2:
                #grab the plug
    
                i_mdLengthMulti = cgmMeta.cgmNode(mc.createNode('multiplyDivide'))
                i_mdLengthMulti.operation = 1
                i_mdLengthMulti.doStore('cgmName',baseName)
                i_mdLengthMulti.addAttr('cgmTypeModifier','lengthMulti')
                i_mdLengthMulti.doName()
    
                l_mdAxis = ['X','Y','Z']
                for i,i_jnt in enumerate(ml_jointChain[:-1]):
                    #grab the plug
                    mPlug_driven = cgmMeta.cgmAttr(ml_jointChain[i+1],'t%s'%str_localAimSingle)
                    plug = ATTR.break_connection(mPlug_driven.p_combinedName)
                    if not plug:raise StandardError,"create_IKHandle>>> Should have found a plug on: %s.t%s"%(ml_jointChain[i+1].mNode,str_localAimSingle)
    
                    ATTR.connect(plug,#>>
                                 '%s.input1%s'%(i_mdLengthMulti.mNode,l_mdAxis[i]))#Connect the old plug data
                    ml_multiPlugs[i].doConnectOut('%s.input2%s'%(i_mdLengthMulti.mNode,l_mdAxis[i]))#Connect in the mutliDriver	
                    mPlug_driven.doConnectIn('%s.output.output%s'%(i_mdLengthMulti.mNode,l_mdAxis[i]))#Connect it back to our driven
    
            else:
                log.error("|{0}| >> addLengthMulti only currently supports 2 segments. Found: {1}".format(_str_func,len(ml_jointChain[:-1])))
                
    
        #>>> rpSetup
        if solverType == 'ikRPsolver' and rpHandle:
            log.debug("|{0}| >> RP Handle setup...".format(_str_func))
            
            if not mRPHandle:
                #Make one
                mRPHandle = mMidHandle.doLoc()
                mRPHandle.addAttr('cgmTypeModifier','poleVector')
                mRPHandle.doName()
                ml_rigObjectsToConnect.append(mRPHandle)
            cBuffer = mc.poleVectorConstraint(mRPHandle.mNode,mIKHandle.mNode)
    
            #Fix rp
            #rotValue = mStart.getAttr('r%s'%str_localAimSingle)    
            #if not cgmMath.isFloatEquivalent(rotValue,0):#if we have a value, we need to fix it
                #IKHandle_fixTwist(mIKHandle)	
    
    
        #>>> Plug in global scale
        if d_MasterGlobalScale and mPlug_globalScale:
            d_MasterGlobalScale['mi_plug'].doConnectOut(mPlug_globalScale.p_combinedName)
    
        #>>> Connect our iModule vis stuff
        if mModule:#if we have a module, connect vis
            for mObj in ml_rigObjectsToConnect:
                mObj.overrideEnabled = 1		
                cgmMeta.cgmAttr(mModule.rigNull.mNode,'gutsVis',lock=False).doConnectOut("%s.%s"%(mObj.mNode,'overrideVisibility'))
                cgmMeta.cgmAttr(mModule.rigNull.mNode,'gutsLock',lock=False).doConnectOut("%s.%s"%(mObj.mNode,'overrideDisplayType'))    
            for mObj in ml_rigObjectsToParent:
                mObj.parent = mModule.rigNull.mNode
    
        #>>> Return dict
        d_return = {'mHandle':mIKHandle,'mEffector':mIKEffector}
        if mPlug_lockMid:
            d_return['mPlug_lockMid'] = mPlug_lockMid	
            d_return['ml_measureObjects']=ml_distanceObjects	
        if stretch:
            d_return['mPlug_autoStretch'] = mPlug_autoStretch
            d_return['ml_distHandles']=ml_handles
        if mRPHandle:
            d_return['mRPHandle'] = mRPHandle
        if addLengthMulti:
            d_return['ml_lengthMultiPlugs'] = ml_multiPlugs
    
        if not _foundPrerred:log.warning("create_IKHandle>>> No preferred angle values found. The chain probably won't work as expected: %s"%l_jointChain)
    
        return d_return   
    except Exception,err:cgmGEN.cgmException(Exception,err)



def handle_fixTwist(ikHandle, aimAxis = None):
    #>>> Data gather and arg check    
    _str_func = 'handle_fixTwist'
    log.debug("|{0}| >> ...".format(_str_func))
    
    mIKHandle = cgmMeta.validateObjArg(ikHandle,'cgmObject',noneValid=False)
    if mIKHandle.getMayaType() != 'ikHandle':
        raise ValueError,"|{0}| >> {1} not an 'ikHandle'. Type: ".format(_str_func,mIKHandle.mNode, mIKHandle.getMayaType())
        

    jointStart = mIKHandle.getMessage('jointStart')
    if not jointStart:
        raise ValueError,"|{0}| >> {1} | no jointStart dataFound".format(_str_func,mIKHandle.mNode, mIKHandle.getMayaType())

    mStartJoint = cgmMeta.validateObjArg(jointStart[0],'cgmObject',noneValid=False)

    #Find the aim axis
    if aimAxis == None:
        raise NotImplementedError,"Need aimAxis. Not done migrating solver"
        log.debug("|{0}| >> find aim axis...".format(_str_func))
        
        return 
        v_localAim = MATH.get_vector_of_two_points(mStartJoint.p_position, mStartJoint.getChildren(asMeta=True)[0].p_position)
        
        str_localAim = dictionary.returnVectorToString(v_localAim)
        str_localAimSingle = str_localAim[0]
        log.debug("IKHandle_fixTwist>>> vector aim: %s | str aim: %s"%(v_localAim,str_localAim))  

    #Check rotation:
    mPlug_rot = cgmMeta.cgmAttr(mStartJoint,'r'+aimAxis)
    #rotValue = mStartJoint.getAttr('r%s'%str_localAimSingle)
    #First we try our rotate value
    if not MATH.is_float_equivalent(mPlug_rot.value,0,2):
        log.debug("|{0}| >> Not zero...".format(_str_func))        
        mIKHandle.twist = 0
    if not MATH.is_float_equivalent(mPlug_rot.value,0,2):
        log.debug("|{0}| >> Trying inverse to start...".format(_str_func))                
        mIKHandle.twist = -mPlug_rot.value#try inversed driven joint rotate value first

    if not MATH.is_float_equivalent(mPlug_rot.value,0,2):#if we have a value, we need to fix it
        log.debug("|{0}| >> drivenAttr='{1}',driverAttr='{2}.twist',minIn = -180, maxIn = 180, maxIterations = 75,matchValue=0.0001".format(_str_func,mPlug_rot.p_combinedShortName,mIKHandle.p_nameShort))        
        
        RIGGEN.matchValue_iterator(drivenAttr="%s.r%s"%(mStartJoint.mNode,aimAxis),
                                   driverAttr="%s.twist"%mIKHandle.mNode,
                                   minIn = -170, maxIn = 180,
                                   maxIterations = 30,
                                   matchValue=0)
        log.debug("|{0}| >> drivenAttr='{1}',driverAttr='{2}.twist',minIn = -180, maxIn = 180, maxIterations = 75,matchValue=0.0001".format(_str_func,mPlug_rot.p_combinedShortName,mIKHandle.p_nameShort))        
        
        #log.debug("rUtils.matchValue_iterator(drivenAttr='%s.r%s',driverAttr='%s.twist',minIn = -180, maxIn = 180, maxIterations = 75,matchValue=0.0001)"%(mStartJoint.getShortName(),str_localAimSingle,mIKHandle.getShortName()))
    return True


def get_midIK_basePos(ml_handles = [], baseAxis = 'y+', markPos = False, forceMidToHandle=False):
    _str_func = 'get_midIK_basePos'
    log.debug("|{0}| >> ".format(_str_func)+ '-'*80)
    
    ml_handles = cgmMeta.validateObjListArg(ml_handles,'cgmObject')
    
    log.debug("|{0}| >> Using: {1}".format(_str_func,[mObj.p_nameBase for mObj in ml_handles]))
    
    #Mid dat... ----------------------------------------------------------------------
    _len_handles = len(ml_handles)
    if _len_handles == 1:
        mid=0
        mMidHandle = ml_handles[0]
    else:
        
        mid = int(_len_handles)/2
        mMidHandle = ml_handles[mid]
        
    log.debug("|{0}| >> mid: {1}".format(_str_func,mid))
    
    b_absMid = False
    if MATH.is_even(_len_handles) and not forceMidToHandle:
        log.debug("|{0}| >> absolute mid mode...".format(_str_func,mid))
        b_absMid = True
        
    
    #...Main vector -----------------------------------------------------------------------
    #mOrientHelper = self.mBlock.orientHelper
    vec_base = MATH.get_obj_vector(ml_handles[0], 'y+')
    log.debug("|{0}| >> Block up: {1}".format(_str_func,vec_base))
    
    #...Get vector -----------------------------------------------------------------------
    if b_absMid:
        crvCubic = CORERIG.create_at(ml_handles, create= 'curve')
        pos_mid = CURVES.getMidPoint(crvCubic)
        mc.delete(crvCubic)
    else:
        pos_mid = mMidHandle.p_position
        
    crv = CORERIG.create_at([ml_handles[0].mNode,ml_handles[-1].mNode], create= 'curveLinear')
    pos_close = DIST.get_closest_point(pos_mid, crv, markPos)[0]
    log.debug("|{0}| >> Pos close: {1} | Pos mid: {2}".format(_str_func,pos_close,pos_mid))
    
    if MATH.is_vector_equivalent(pos_mid,pos_close,3):
        log.debug("|{0}| >> Mid on linear line, using base vector".format(_str_func))
        vec_use = vec_base
    else:
        vec_use = MATH.get_vector_of_two_points(pos_close,pos_mid)
        mc.delete(crv)
    
    #...Get length -----------------------------------------------------------------------
    #dist_helper = 0
    #if ml_handles[-1].getMessage('pivotHelper'):
        #log.debug("|{0}| >> pivotHelper found!".format(_str_func))
        #dist_helper = max(POS.get_bb_size(ml_handles[-1].getMessage('pivotHelper')))
        
    dist_min = DIST.get_distance_between_points(ml_handles[0].p_position, pos_mid)/4.0
    dist_base = DIST.get_distance_between_points(pos_mid, pos_close)
    
    #...get new pos
    dist_use = MATH.Clamp(dist_base, dist_min, None)
    log.debug("|{0}| >> Dist min: {1} | dist base: {2} | use: {3}".format(_str_func,
                                                                          dist_min,
                                                                          dist_base,
                                                                          dist_use))
    
    pos_use = DIST.get_pos_by_vec_dist(pos_mid,vec_use,dist_use*2)
    pos_use2 = DIST.get_pos_by_vec_dist(pos_mid,vec_base,dist_use*2)
    
    reload(LOC)
    if markPos:
        LOC.create(position=pos_use,name='pos1')
        LOC.create(position=pos_use2,name='pos2')
    
    return pos_use