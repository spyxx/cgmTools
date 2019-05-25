"""
------------------------------------------
cgm.core.mrs.blocks.organic.eye
Author: Josh Burton
email: jjburton@cgmonks.com

Website : http://www.cgmonks.com
------------------------------------------

================================================================
"""
__MAYALOCAL = 'BROW'

# From Python =============================================================
import copy
import re
import pprint
import time
import os

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

# From Maya =============================================================
import maya.cmds as mc

# From Red9 =============================================================
from Red9.core import Red9_Meta as r9Meta
import Red9.core.Red9_AnimationUtils as r9Anim
#r9Meta.cleanCache()#<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< TEMP!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


import cgm.core.cgm_General as cgmGEN
from cgm.core.rigger import ModuleShapeCaster as mShapeCast

import cgm.core.cgmPy.os_Utils as cgmOS
import cgm.core.cgmPy.path_Utils as cgmPATH
import cgm.core.mrs.assets as MRSASSETS
path_assets = cgmPATH.Path(MRSASSETS.__file__).up().asFriendly()

import cgm.core.mrs.lib.ModuleControlFactory as MODULECONTROL
reload(MODULECONTROL)
from cgm.core.lib import curve_Utils as CURVES
import cgm.core.lib.rigging_utils as CORERIG
from cgm.core.lib import snap_utils as SNAP
import cgm.core.lib.attribute_utils as ATTR
import cgm.core.rig.joint_utils as JOINT
import cgm.core.classes.NodeFactory as NODEFACTORY
import cgm.core.lib.transform_utils as TRANS
import cgm.core.lib.distance_utils as DIST
import cgm.core.lib.position_utils as POS
import cgm.core.lib.math_utils as MATH
import cgm.core.rig.constraint_utils as RIGCONSTRAINT
import cgm.core.rig.general_utils as RIGGEN
import cgm.core.lib.constraint_utils as CONSTRAINT
import cgm.core.lib.locator_utils as LOC
import cgm.core.lib.rayCaster as RAYS
import cgm.core.lib.shape_utils as SHAPES
import cgm.core.mrs.lib.block_utils as BLOCKUTILS
import cgm.core.mrs.lib.builder_utils as BUILDERUTILS
import cgm.core.mrs.lib.shared_dat as BLOCKSHARE
import cgm.core.tools.lib.snap_calls as SNAPCALLS
import cgm.core.rig.ik_utils as IK
import cgm.core.cgm_RigMeta as cgmRIGMETA
import cgm.core.lib.nameTools as NAMETOOLS
import cgm.core.lib.surface_Utils as SURF
import cgm.core.lib.string_utils as STR

for m in DIST,POS,MATH,IK,CONSTRAINT,LOC,BLOCKUTILS,BUILDERUTILS,CORERIG,RAYS,JOINT,RIGCONSTRAINT,RIGGEN:
    reload(m)
    
# From cgm ==============================================================
from cgm.core import cgm_Meta as cgmMeta

#=============================================================================================================
#>> Block Settings
#=============================================================================================================
__version__ = 'alpha.10.31.2018'
__autoForm__ = False
__menuVisible__ = True
__faceBlock__ = True

#These are our base dimensions. In this case it is for human
__dimensions_by_type = {'box':[22,22,22],
                        'human':[15.2, 23.2, 19.7]}

__l_rigBuildOrder__ = ['rig_dataBuffer',
                       'rig_skeleton',
                       'rig_shapes',
                       'rig_controls',
                       'rig_frame',
                       'rig_cleanUp']




d_wiring_skeleton = {'msgLinks':[],
                     'msgLists':['moduleJoints','skinJoints']}
d_wiring_prerig = {'msgLinks':['moduleTarget','prerigNull','noTransPrerigNull']}
d_wiring_form = {'msgLinks':['formNull','noTransFormNull'],
                     }
d_wiring_extraDags = {'msgLinks':['bbHelper'],
                      'msgLists':[]}
_d_attrStateOn = {0:[],
                  1:[],
                  2:[],
                  3:[],
                  4:[]}

_d_attrStateOff = {0:[],
                   1:[],
                   2:['blockScale','sy'],
                   3:[],
                   4:[]}
#>>>Profiles ==============================================================================================
d_build_profiles = {}


d_block_profiles = {'default':{'baseSize':[17.6,7.2,8.4],},
                    'eyebrow':{'baseSize':[17.6,7.2,8.4],
                               'browType':'full',
                               'profileOptions':{},
                               'paramStart':.2,
                                'paramMid':.5,
                                'paramEnd':.7,                               
                               },
                    }

#>>>Attrs =================================================================================================
l_attrsStandard = ['side',
                   'position',
                   'baseAim',
                   'attachPoint',
                   'nameList',
                   'loftDegree',
                   'loftSplit',
                   'scaleSetup',
                   'visLabels',
                   'moduleTarget',]

d_attrsToMake = {'browType':'full:side',
                 'formForeheadNum':'int',
                 'formBrowNum':'int',
                 #'paramStart':'float',
                 #'paramMid':'float',
                 #'paramMid':'float',
                 #'paramEnd':'float',
                 'numSplit_u':'int',
                 'numSplit_v':'int',
                 'addEyeSqueeze':'bool',
                 'browSetup':'ribbon:undefined',
                 'numHandlesBrow':'int',
                 'numBrowJoints':'int',
                 'profileOptions':'string',
                 'controlBrowCenter':'bool',
                 'numBrowControl':'int',
                 'controlTemple':'bool',
                 'jointDepth':'float',
                 'controlOffset':'float',
                 
                 
}

d_defaultSettings = {'version':__version__,
                     'attachPoint':'end',
                     'side':'none',
                     'nameList':['brow','squeeze'],
                     'loftDegree':'cubic',
                     #'paramStart':.2,
                     #'paramMid':.5,
                     #'paramEnd':1.0,
                     'numSplit_u':5,
                     'numSplit_v':6,
                     'visLabels':True,
                     'formForeheadNum':1,
                     'formBrowNum':1,
                     'controlBrowCenter':True,
                     'numBrowControl':3,
                     'numBrowJoints':3,
                     'jointDepth':-.01,
                     'controlOffset':1,
                     #'baseSize':MATH.get_space_value(__dimensions[1]),
                     }

       
#=============================================================================================================
#>> Define
#=============================================================================================================
@cgmGEN.Timer
def define(self):
    _str_func = 'define'    
    log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
    log.debug("{0}".format(self))
    
    _short = self.mNode
    
    #Attributes =========================================================
    ATTR.set_alias(_short,'sy','blockScale')    
    self.setAttrFlags(attrs=['sx','sz','sz'])
    self.doConnectOut('sy',['sx','sz'])

    ATTR.set_min(_short, 'loftSplit', 1)
    
    #Cleaning =========================================================        
    _shapes = self.getShapes()
    if _shapes:
        log.debug("|{0}| >>  Removing old shapes...".format(_str_func))        
        mc.delete(_shapes)
        defineNull = self.getMessage('defineNull')
        if defineNull:
            log.debug("|{0}| >>  Removing old defineNull...".format(_str_func))
            mc.delete(defineNull)
    
    ml_handles = []
    
    #Make our handles creation data =======================================================
    d_pairs = {}
    d_creation = {}
    l_order = []
    d_curves = {}
    d_curveCreation = {}
    d_toParent = {}    
    
    #rigBlock Handle ===========================================================
    log.debug("|{0}| >>  RigBlock Handle...".format(_str_func))            
    _size = MATH.average(self.baseSize[1:])
    _crv = CURVES.create_fromName(name='locatorForm',#'axis3d',#'arrowsAxis', 
                                  direction = 'z+', size = _size/4)
    SNAP.go(_crv,self.mNode,)
    CORERIG.override_color(_crv, 'white')        
    CORERIG.shapeParent_in_place(self.mNode,_crv,False)
    mHandleFactory = self.asHandleFactory()
    self.addAttr('cgmColorLock',True,lock=True, hidden=True)
    mDefineNull = self.atUtils('stateNull_verify','define')
    
    mNoTransformNull = self.atUtils('noTransformNull_verify','define',forceNew=True)
    
    #Bounding sphere ==================================================================
    _bb_shape = CURVES.create_controlCurve(self.mNode,'cubeOpen', size = 1.0, sizeMode='fixed')
    mBBShape = cgmMeta.validateObjArg(_bb_shape, 'cgmObject',setClass=True)
    mBBShape.p_parent = mDefineNull    
    mBBShape.tz = -.5
    mBBShape.ty = .5
    
    
    CORERIG.copy_pivot(mBBShape.mNode,self.mNode)
    self.doConnectOut('baseSize', "{0}.scale".format(mBBShape.mNode))
    mHandleFactory.color(mBBShape.mNode,controlType='sub')
    mBBShape.setAttrFlags()
    
    mBBShape.doStore('cgmName', self)
    mBBShape.doStore('cgmType','bbVisualize')
    mBBShape.doName()    
    
    self.connectChildNode(mBBShape.mNode,'bbHelper')
    
    #...
    _browType = self.getEnumValueString('browType')
    
    if _browType == 'full':
        log.debug("|{0}| >>  full brow setup...".format(_str_func))
        _d_pairs = {}
        _d = {}
        l_sideKeys = ['peak_1','peak_2','peak_3',
                      'brow_1','brow_2','brow_3','brow_4',
                      'base_1','base_2','base_3','base_4'
                      ]
        for k in l_sideKeys:
            _d_pairs[k+'_left'] = k+'_right'
  
        d_pairs.update(_d_pairs)
        
        #Going to just store the right values and then just flip the 
        _d_scaleSpace = {
            'human':{'base':[0,-1.1,1],
                     'brow':[0,-.5,1],
                     'peak':[0,1,.6],
                     'base_1_right':[-.2,-1.1,1],
                     'base_2_right':[-.55,-1.1,.8],
                     'base_3_right':[-.8,-1.1,.5],
                     'base_4_right':[-1,-1,-1],
                     
                     'brow_1_right':[-.2,-.5,1],
                     'brow_2_right':[-.55,-.5,.8],
                     'brow_3_right':[-.8,-.5,.5],
                     'brow_4_right':[-1,-.7,-1],
                     
                     'peak_1_right':[-.2,1,.6],
                     'peak_2_right':[-.55,1,.25],
                     'peak_3_right':[-.8,1,-.5],
                     

                    },}
    
        _d['brow'] = {'color':'yellowWhite','tagOnly':1,'arrow':0,'jointLabel':1,'vectorLine':0}
        _d['peak'] = copy.copy(_d['brow'])
        _d['base'] = copy.copy(_d['brow'])

        
        for k in l_sideKeys:
            _d[k+'_left'] =  {'color':'blueWhite','tagOnly':1,'arrow':0,'jointLabel':1,'vectorLine':0}
            _d[k+'_right'] =  {'color':'redWhite','tagOnly':1,'arrow':0,'jointLabel':1,'vectorLine':0}

        _str_pose = 'human'
        
        for k,d in _d.iteritems():
            if 'left' in k:
                k_use = str(k).replace('left','right')
                _v = copy.copy(_d_scaleSpace[_str_pose].get(k_use))
                if _v:
                    _v[0] = -1 * _v[0]
            else:
                _v = _d_scaleSpace[_str_pose].get(k)
                
            if _v is not None:
                _d[k]['scaleSpace'] = _v
        
        _keys = _d.keys()
        _keys.sort()
        l_order.extend(_keys)
        d_creation.update(_d)
        #pprint.pprint(_d)
        #pprint.pprint(_d_scaleSpace)
        _d_curveCreation = {
            'browLine':{'keys':['brow_4_right','brow_3_right','brow_2_right','brow_1_right',
                                'brow',
                                'brow_1_left','brow_2_left','brow_3_left','brow_4_left'],'rebuild':0},
            'peakLine':{'keys':['peak_3_right','peak_2_right','peak_1_right',
                                'peak',
                                'peak_1_left','peak_2_left','peak_3_left'],'rebuild':0},
            'baseLine':{'keys':['base_4_right','base_3_right','base_2_right','base_1_right',
                                'base',
                                'base_1_left','base_2_left','base_3_left','base_4_left'],'rebuild':0},
            
            'browCenter':{'keys':['base','brow','peak',],'rebuild':0},
            'browStartRight':{'keys':['base_1_right','brow_1_right'],'rebuild':0},
            'browMidRight':{'keys':['base_2_right','brow_2_right','peak_1_right',],'rebuild':0},
            'browEdgeRight':{'keys':['base_3_right','brow_3_right','peak_2_right',],'rebuild':0},
            'browEndRight':{'keys':['base_4_right','brow_4_right','peak_3_right',],'rebuild':0},
            
            'browStartLeft':{'keys':['base_1_left','brow_1_left'],'rebuild':0},
            'browMidLeft':{'keys':['base_2_left','brow_2_left','peak_1_left',],'rebuild':0},
            'browEdgeLeft':{'keys':['base_3_left','brow_3_left','peak_2_left',],'rebuild':0},
            'browEndLeft':{'keys':['base_4_left','brow_4_left','peak_3_left',],'rebuild':0},            
            
            }
        
        d_curveCreation.update(_d_curveCreation)
        #pprint.pprint(vars())
        
        
    #make em...============================================================
    log.debug(cgmGEN.logString_sub(_str_func,'Make handles'))        
    
    #self,l_order,d_definitions,baseSize,mParentNull = None, mScaleSpace = None, rotVecControl = False,blockUpVector = [0,1,0]
    md_res = self.UTILS.create_defineHandles(self, l_order, d_creation, _size/6, mDefineNull, mBBShape)

    md_handles = md_res['md_handles']
    ml_handles = md_res['ml_handles']
    
    
    for k,p in d_toParent.iteritems():
        md_handles[k].p_parent = md_handles[p]
        

    
    #Mirror setup...
    idx_ctr = 0
    idx_side = 0
    d = {}
        
    for tag,mHandle in md_handles.iteritems():
        if cgmGEN.__mayaVersion__ >= 2018:
            mController = mHandle.controller_get()
            mController.visibilityMode = 2
            
        mHandle._verifyMirrorable()
        _center = True
        for p1,p2 in d_pairs.iteritems():
            if p1 == tag or p2 == tag:
                _center = False
                break
        if _center:
            log.debug("|{0}| >>  Center: {1}".format(_str_func,tag))    
            mHandle.mirrorSide = 0
            mHandle.mirrorIndex = idx_ctr
            idx_ctr +=1
        mHandle.mirrorAxis = "translateX,rotateY,rotateZ"

    #Self mirror wiring -------------------------------------------------------
    for k,m in d_pairs.iteritems():
        md_handles[k].mirrorSide = 1
        md_handles[m].mirrorSide = 2
        md_handles[k].mirrorIndex = idx_side
        md_handles[m].mirrorIndex = idx_side
        md_handles[k].doStore('mirrorHandle',md_handles[m])
        md_handles[m].doStore('mirrorHandle',md_handles[k])
        idx_side +=1

    #Curves -------------------------------------------------------------------------
    log.debug("|{0}| >>  Make the curves...".format(_str_func))    
    md_resCurves = self.UTILS.create_defineCurve(self, d_curveCreation, md_handles, mNoTransformNull)
    self.msgList_connect('defineHandles',ml_handles)#Connect    
    self.msgList_connect('defineSubHandles',ml_handles)#Connect
    self.msgList_connect('defineCurves',md_resCurves['ml_curves'])#Connect    
    
    md_curves = md_resCurves['md_curves']
    """
    mSurf = self.UTILS.create_simpleFormLoftMesh(self,
                                                 [mObj.mNode for mObj in [md_curves['upperLine'],
                                                                          md_curves['browLine'],
                                                                          md_curves['baseLine']]],
                                                 mDefineNull,
                                                 polyType = 'bezier',
                                                 d_rebuild = d.get('rebuild',{}),
                                                 baseName = 'brow',
                                                 transparent = 1,
                                                 #vDriver = "{0}.numLidSplit_v".format(_short),
                                                 #uDriver = "{0}.numLidSplit_u".format(_short),
                                                 **d.get('kws',{}))"""
    
    
    #Mid track curve
    
    
    
    return

        
    
    self.msgList_connect('defineSubHandles',ml_handles)#Connect
    
    
 
 

#=============================================================================================================
#>> Form
#=============================================================================================================
def mirror_self(self,primeAxis = 'Left'):
    _str_func = 'mirror_self'
    _idx_state = self.blockState
    
    log.debug("|{0}| >> define...".format(_str_func)+ '-'*80)
    ml_mirrorHandles = self.msgList_get('defineSubHandles')
    r9Anim.MirrorHierarchy().makeSymmetrical([mObj.mNode for mObj in ml_mirrorHandles],
                                             mode = '',primeAxis = primeAxis.capitalize() )        

    if _idx_state > 0:
        log.debug("|{0}| >> form...".format(_str_func)+ '-'*80)
        ml_mirrorHandles = self.msgList_get('formHandles')
        r9Anim.MirrorHierarchy().makeSymmetrical([mObj.mNode for mObj in ml_mirrorHandles],
                                                     mode = '',primeAxis = primeAxis.capitalize() )
    if _idx_state > 1:
        log.debug("|{0}| >> prerig...".format(_str_func)+ '-'*80)        
        ml_mirrorHandles = self.msgList_get('prerigHandles')
        r9Anim.MirrorHierarchy().makeSymmetrical([mObj.mNode for mObj in ml_mirrorHandles],
                                                 mode = '',primeAxis = primeAxis.capitalize() )        
    

def mirror_form(self,primeAxis = 'Left'):
    _str_func = 'mirror_form'    
    log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
    log.debug("{0}".format(self))
    
    ml_mirrorHandles = self.msgList_get('formHandles')
    
    r9Anim.MirrorHierarchy().makeSymmetrical([mObj.mNode for mObj in ml_mirrorHandles],
                                             mode = '',primeAxis = primeAxis.capitalize() )
    
def mirror_prerig(self,primeAxis = 'Left'):
    _str_func = 'mirror_form'    
    log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
    log.debug("{0}".format(self))
    
    ml_mirrorHandles = self.msgList_get('prerigHandles')
    
    r9Anim.MirrorHierarchy().makeSymmetrical([mObj.mNode for mObj in ml_mirrorHandles],
                                             mode = '',primeAxis = primeAxis.capitalize() )    

def formDelete(self):
    _str_func = 'formDelete'
    log.debug("|{0}| >> ...".format(_str_func)+ '-'*80)
    log.debug("{0}".format(self))
    ml_defSubHandles = self.msgList_get('defineSubHandles')
    for mObj in ml_defSubHandles:
        mObj.template = False    
        mObj.v=1
        
    for mObj in self.msgList_get('defineCurves'):
        mObj.template=0
        mObj.v=1
            
    try:self.defineLoftMesh.template = False
    except:pass
    self.bbHelper.v = True
    
@cgmGEN.Timer
def form(self):
    try:    
        _str_func = 'form'
        log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
        log.debug("{0}".format(self))
        
        _short = self.p_nameShort
        _baseNameAttrs = ATTR.datList_getAttrs(self.mNode,'nameList')
        
        #Initial checks ===============================================================================
        log.debug("|{0}| >> Initial checks...".format(_str_func)+ '-'*40)    

        #Create temple Null  ==================================================================================
        mFormNull = BLOCKUTILS.formNull_verify(self)
        mNoTransformNull = self.atUtils('noTransformNull_verify','form')
        
        mHandleFactory = self.asHandleFactory()
        
        self.bbHelper.v = False
        _size = MATH.average(self.baseSize[1:]) * .2
        
        d_handleTags = {}
        md_loftCurves = {}
        md_curves = []
        
        #Brow Handles  ==================================================================================
        log.debug("|{0}| >> Brow Handles...".format(_str_func)+ '-'*40)

        
        if self.browType == 0:#Full brow
            log.debug("|{0}| >>  Full Brow...".format(_str_func))
            
            #Gather all our define dhandles and curves -----------------------------
            log.debug("|{0}| >> Get our define curves/handles...".format(_str_func)+ '-'*40)    
    
            md_handles = {}
            md_dCurves = {}
            d_defPos = {}
            
            ml_defineHandles = self.msgList_get('defineSubHandles')
            for mObj in ml_defineHandles:
                md_handles[mObj.handleTag] = mObj
                d_defPos[mObj.handleTag] = mObj.p_position
                mObj.v=0
                
            for mObj in self.msgList_get('defineCurves'):
                md_dCurves[mObj.handleTag] = mObj
                mObj.template=1
                mObj.v=0
            
            #
            d_pairs = {}
            d_creation = {}
            l_order = []
            d_curveCreation = {}
            ml_subHandles = []
            md_loftCreation = {}
            d_curveKeys = {}
            l_curveKeys = []
            d_sections = {'brow':{'crvs':['baseLine','browLine'],
                                  'numAttr':'formBrowNum'},
                          'fore':{'crvs':['browLine','peakLine'],
                                  'numAttr':'formForeheadNum'}}
            
            _done = []
            
            d_sectionPos = {}
            for iii,section in enumerate(['brow','fore']):
                log.debug(cgmGEN.logString_sub(_str_func,section + '...'))
                #We need to get positions lists per line
                l_posLists = []
                _d_section = d_sections[section]
                
                _res_tmp = mc.loft([md_dCurves[k].mNode for k in _d_section['crvs']],
                                   o = True, d = 1, po = 0, c = False,u=False, autoReverse=0,ch=True)
                                    
                str_meshShape = TRANS.shapes_get(_res_tmp[0])[0]
                l_knots = SURF.get_dat(str_meshShape, uKnots=True)['uKnots']
                
                _count = self.getMayaAttr(_d_section['numAttr'])
                
                if _count:
                    l_uValues = MATH.get_splitValueList(l_knots[0],l_knots[1],2+_count)
                else:
                    l_uValues = l_knots
                
                for v in l_uValues:
                    if iii and v == l_uValues[0]:
                        continue
                    
                    _crv = mc.duplicateCurve("{0}.u[{1}]".format(str_meshShape,v), ch = 0, rn = 0, local = 0)[0]
                    
                    if iii:
                        _split = 7
                    else:
                        _split = 11
                        
                    _l_pos = CURVES.getUSplitList(_crv,_split,rebuild=1)
                        
                    #_l_source = mc.ls("{0}.{1}[*]".format(_crv,'ep'),flatten=True,long=True)
                    #_l_pos = []
                    #for i,ep in enumerate(_l_source):
                        #p = POS.get(ep)
                        #_l_pos.append(p)
                        ##LOC.create(position=p,name='{0}_loc'.format(i))
                    #_done.append(k)
                    l_posLists.append(_l_pos)
                    mc.delete(_crv)                
                
                """
                for k in _d_section['crvs']:
                    if k in _done:
                        continue
                    
                    mCrv = md_dCurves[k]
                    _l_source = mc.ls("{0}.{1}[*]".format(mCrv.mNode,'ep'),flatten=True,long=True)
                    _l_pos = []
                    for i,ep in enumerate(_l_source):
                        p = POS.get(ep)
                        _l_pos.append(p)
                        #LOC.create(position=p,name='{0}_loc'.format(i))
                    _done.append(k)
                    l_posLists.append(_l_pos)"""
                
                """
                if _count:
                    log.debug(cgmGEN.logString_msg(_str_func,section + 'section split'))

                    
                    l_uValues.pop(0)
                    l_uValues.pop(-1)
                    
                    for v in l_uValues:
                        _crv = mc.duplicateCurve("{0}.u[{1}]".format(str_meshShape,v), ch = 0, rn = 0, local = 0)[0]
                        
                        _l_source = mc.ls("{0}.{1}[*]".format(_crv,'ep'),flatten=True,long=True)
                        _l_pos = []
                        for i,ep in enumerate(_l_source):
                            p = POS.get(ep)
                            _l_pos.append(p)
                            #LOC.create(position=p,name='{0}_loc'.format(i))
                        _done.append(k)
                        l_posLists.insert(1,_l_pos)
                        mc.delete(_crv)"""
                        
                mc.delete(_res_tmp)
                
                #Now we have our positions, we need to setup our handle sets
                for i,l_pos in enumerate(l_posLists):
                    _idx = MATH.get_midIndex(len(l_pos))
                    _right = l_pos[:_idx]
                    _left = l_pos[_idx+1:]
                    _mid = l_pos[_idx]

                    key_center = '{0}_{1}_center'.format(section,i+1)
                    l_keys_left = []
                    l_keys_right = []                   
                    
                    d_creation[key_center] =  {'color':'yellowWhite','tagOnly':1,'arrow':0,'jointLabel':1,'vectorLine':0,'pos':_mid}
                    

                    for ii,v in enumerate(_right):
                        k = '{0}_{1}_{2}'.format(section,i+1,ii+1)
                        
                        
                        d_creation[k+'_left'] =  {'color':'blueWhite','tagOnly':1,'arrow':0,'jointLabel':1,'vectorLine':0,'pos':_left[ii]}
                        d_creation[k+'_right'] =  {'color':'redWhite','tagOnly':1,'arrow':0,'jointLabel':1,'vectorLine':0,'pos':v}
                        
                        l_keys_right.append(k+'_right')
                        l_keys_left.append(k+'_left')
                        
                        #LOC.create(position=v,name=k+'_right_loc')
                        #LOC.create(position=_left[ii],name=k+'_left_loc')

                    
                    l_keys = l_keys_right + [key_center] + l_keys_left
                                           
                    
                    key_curve = '{0}_{1}'.format(section,i+1)
                    d_curveKeys[key_curve]= l_keys
                    l_curveKeys.append(key_curve)
                    
                    
                    d_curveCreation[key_curve] = {'keys':l_keys,
                                                  'rebuild':1}
                    
                    l_keys_left.reverse()
                    for i,k in enumerate(l_keys_left):
                        d_pairs[k] = l_keys_right[i]                           
                    
                d_sectionPos[section] = l_posLists
            
            l_order = d_creation.keys()
  
            #LoftDeclarations....
            md_loftCreation['brow'] = {'keys':l_curveKeys,
                                         'rebuild':{'spansU':5,'spansV':5},
                                         'kws':{'noRebuild':1}}

            md_res = self.UTILS.create_defineHandles(self, l_order, d_creation, _size, 
                                                     mFormNull,statePlug = 'form')
            
            ml_subHandles.extend(md_res['ml_handles'])
            md_handles.update(md_res['md_handles'])
            
 
            md_res = self.UTILS.create_defineCurve(self, d_curveCreation, md_handles, mNoTransformNull,'formCurve')
            md_resCurves = md_res['md_curves']
            
            for k,d in md_loftCreation.iteritems():
                ml_curves = [md_resCurves[k2] for k2 in d['keys']]
                for mObj in ml_curves:
                    mObj.v=False
                
                self.UTILS.create_simpleFormLoftMesh(self,
                                                     [mObj.mNode for mObj in ml_curves],
                                                     mFormNull,
                                                     polyType = 'faceLoft',
                                                     d_rebuild = d.get('rebuild',{}),
                                                     baseName = k,
                                                     transparent = False,
                                                     vDriver = "{0}.numSplit_v".format(_short),
                                                     uDriver = "{0}.numSplit_u".format(_short),
                                                     **d.get('kws',{}))

            for tag,mHandle in md_handles.iteritems():
                if cgmGEN.__mayaVersion__ >= 2018:
                    mController = mHandle.controller_get()
                    mController.visibilityMode = 2
                    
            #Mirror indexing -------------------------------------
            log.debug("|{0}| >> Mirror Indexing...".format(_str_func)+'-'*40) 
            
            idx_ctr = 0
            idx_side = 0
            d = {}
            
            for tag,mHandle in md_handles.iteritems():
                if mHandle in ml_defineHandles:
                    continue
                
                mHandle._verifyMirrorable()
                _center = True
                for p1,p2 in d_pairs.iteritems():
                    if p1 == tag or p2 == tag:
                        _center = False
                        break
                if _center:
                    log.debug("|{0}| >>  Center: {1}".format(_str_func,tag))    
                    mHandle.mirrorSide = 0
                    mHandle.mirrorIndex = idx_ctr
                    idx_ctr +=1
                mHandle.mirrorAxis = "translateX,rotateY,rotateZ"
        
            #Self mirror wiring -------------------------------------------------------
            for k,m in d_pairs.iteritems():
                try:
                    md_handles[k].mirrorSide = 1
                    md_handles[m].mirrorSide = 2
                    md_handles[k].mirrorIndex = idx_side
                    md_handles[m].mirrorIndex = idx_side
                    md_handles[k].doStore('mirrorHandle',md_handles[m])
                    md_handles[m].doStore('mirrorHandle',md_handles[k])
                    idx_side +=1        
                except Exception,err:
                    log.error('Mirror error: {0}'.format(err))
                        
            self.msgList_connect('formHandles',ml_subHandles)#Connect
            self.msgList_connect('formCurves',md_res['ml_curves'])#Connect        
            return                        

    except Exception,err:
        cgmGEN.cgmExceptCB(Exception,err)


#=============================================================================================================
#>> Prerig
#=============================================================================================================
def prerigDelete(self):
    try:self.moduleEyelid.delete()
    except:pass
    
    for a in 'blockScale','translate','rotate':
        ATTR.set_lock(self.mNode, a, False)    
    
    
def create_handle(self,tag,pos,mJointTrack=None,
                  trackAttr=None,visualConnection=True,
                  nameEnd = 'BrowHandle'):
    mHandle = cgmMeta.validateObjArg( CURVES.create_fromName('circle', size = _size_sub), 
                                      'cgmObject',setClass=1)
    mHandle.doSnapTo(self)

    mHandle.p_position = pos

    mHandle.p_parent = mStateNull
    mHandle.doStore('cgmName',tag)
    mHandle.doStore('cgmType','formHandle')
    mHandle.doName()

    mHandleFactory.color(mHandle.mNode,controlType='sub')

    self.connectChildNode(mHandle.mNode,'{0}nameEnd'.format(tag),'block')

    return mHandle

    #joinHandle ------------------------------------------------
    mJointHandle = cgmMeta.validateObjArg( CURVES.create_fromName('jack',
                                                                  size = _size_sub*.75),
                                           'cgmObject',
                                           setClass=1)

    mJointHandle.doStore('cgmName',tag)    
    mJointHandle.doStore('cgmType','jointHelper')
    mJointHandle.doName()                

    mJointHandle.p_position = pos
    mJointHandle.p_parent = mStateNull


    mHandleFactory.color(mJointHandle.mNode,controlType='sub')
    mHandleFactory.addJointLabel(mJointHandle,tag)
    mHandle.connectChildNode(mJointHandle.mNode,'jointHelper','handle')

    mTrackGroup = mJointHandle.doGroup(True,True,
                                       asMeta=True,
                                       typeModifier = 'track',
                                       setClass='cgmObject')

    if trackAttr and mJointTrack:
        mPointOnCurve = cgmMeta.asMeta(CURVES.create_pointOnInfoNode(mJointTrack.mNode,turnOnPercentage=True))

        mPointOnCurve.doConnectIn('parameter',"{0}.{1}".format(self.mNode,trackAttr))

        mTrackLoc = mJointHandle.doLoc()

        mPointOnCurve.doConnectOut('position',"{0}.translate".format(mTrackLoc.mNode))

        mTrackLoc.p_parent = mNoTransformNull
        mTrackLoc.v=False
        mc.pointConstraint(mTrackLoc.mNode,mTrackGroup.mNode)                    


    elif mJointTrack:
        mLoc = mHandle.doLoc()
        mLoc.v=False
        mLoc.p_parent = mNoTransformNull
        mc.pointConstraint(mHandle.mNode,mLoc.mNode)

        res = DIST.create_closest_point_node(mLoc.mNode,mJointTrack.mNode,True)
        #mLoc = cgmMeta.asMeta(res[0])
        mTrackLoc = cgmMeta.asMeta(res[0])
        mTrackLoc.p_parent = mNoTransformNull
        mTrackLoc.v=False
        mc.pointConstraint(mTrackLoc.mNode,mTrackGroup.mNode)


    mAimGroup = mJointHandle.doGroup(True,True,
                                     asMeta=True,
                                     typeModifier = 'aim',
                                     setClass='cgmObject')
    mc.aimConstraint(mLidRoot.mNode,
                     mAimGroup.mNode,
                     maintainOffset = False, weight = 1,
                     aimVector = [0,0,-1],
                     upVector = [0,1,0],
                     worldUpVector = [0,1,0],
                     worldUpObject = self.mNode,
                     worldUpType = 'objectRotation' )                          


    if visualConnection:
        log.debug("|{0}| >> visualConnection ".format(_str_func, tag))
        trackcrv,clusters = CORERIG.create_at([mLidRoot.mNode,
                                               mJointHandle.mNode],#ml_handleJoints[1]],
                                              'linearTrack',
                                              baseName = '{0}_midTrack'.format(tag))

        mTrackCrv = cgmMeta.asMeta(trackcrv)
        mTrackCrv.p_parent = mNoTransformNull
        mHandleFactory.color(mTrackCrv.mNode, controlType = 'sub')

        for s in mTrackCrv.getShapes(asMeta=True):
            s.overrideEnabled = 1
            s.overrideDisplayType = 2

    return mHandle

def prerig(self):
    try:
        _str_func = 'prerig'
        log.debug("|{0}| >>  {1}".format(_str_func,self)+ '-'*80)
        self.blockState = 'prerig'
        _side = self.UTILS.get_side(self)
        
        self.atUtils('module_verify')
        mStateNull = self.UTILS.stateNull_verify(self,'prerig')
        mNoTransformNull = self.atUtils('noTransformNull_verify','prerig')
        
        #mRoot = self.getMessageAsMeta('rootHelper')
        mHandleFactory = self.asHandleFactory()
        
        ml_handles = []
        md_handles = {'brow':{'center':[],
                              'left':[],
                              'right':[]}}
        md_jointHandles = {'brow':{'center':[],
                              'left':[],
                              'right':[]}}
        
        for a in 'blockScale','translate','rotate':
            ATTR.set_lock(self.mNode, a, True)
        
        #Get base dat =============================================================================    
        mBBHelper = self.bbHelper
        mBrowLoft = self.getMessageAsMeta('browFormLoft')
        
        _size = MATH.average(self.baseSize[1:])
        _size_base = _size * .25
        _size_sub = _size_base * .5
        
        idx_ctr = 0
        idx_side = 0
        
 
        #Anchors =====================================================================================
        log.debug(cgmGEN.logString_sub('anchors'))
        
        def create_anchor(self, pos,mSurface,tag,k,side=None,controlType = 'main',nameDict=None, size = _size_sub):
            mHandle = cgmMeta.validateObjArg(self.doCreateAt(),'cgmControl',setClass=1)
            
            #Position 
            datClose = DIST.get_closest_point_data(mSurface.mNode, targetPoint=pos)
            pClose = datClose['position']
            
            mHandle.p_position = pClose
            
            mc.delete(mc.normalConstraint(mSurface.mNode, mHandle.mNode,
                                aimVector = [0,0,1], upVector = [0,1,0],
                                worldUpObject = self.mNode,
                                worldUpType = 'objectrotation', 
                                worldUpVector = [0,1,0]))
            
            pBall = DIST.get_pos_by_axis_dist(mHandle.mNode,'z+',self.controlOffset * 2)
            
            mBall = cgmMeta.validateObjArg( CURVES.create_fromName('semiSphere', size = size), 
                                              'cgmControl',setClass=1)
            mBall.doSnapTo(mHandle)
            mBall.p_position = pBall
            
            _crvLinear = CORERIG.create_at(create='curveLinear',
                                           l_pos=[pClose,pBall])
            
            CORERIG.shapeParent_in_place(mHandle.mNode, mBall.mNode,False)
            CORERIG.shapeParent_in_place(mHandle.mNode, _crvLinear,False)            
  
            mHandle._verifyMirrorable()
            
            mHandle.p_parent = mStateNull
            
            if nameDict:
                RIGGEN.store_and_name(mHandle,nameDict)
            else:
                mHandle.doStore('cgmName',tag)
                mHandle.doStore('cgmType','anchor')
                mHandle.doName()
                
            _key = tag
            if k:
                _key = _key+k.capitalize()
                
            mHandleFactory.color(mHandle.mNode, side = side, controlType=controlType)

            return mHandle
            
        #we need to generate some positions
        md_handles = {}
        ml_handlesAll = []
        md_mirrorDat = {'center':[],
                        'left':[],
                        'right':[]}
        md_dCurves = {}
        d_defPos = {}
        
        md_defineHandles = {}
        ml_defineHandles = self.msgList_get('defineSubHandles')
        for mObj in ml_defineHandles:
            md_defineHandles[mObj.handleTag] = mObj
            d_defPos[mObj.handleTag] = mObj.p_position
            mObj.v=0
            
        d_anchorDat = {'brow':{'center':{'main':['base','brow']}}}
        md_anchors = {}
        
        for side in 'left','right':
            d_anchorDat['brow'][side] = {}
            _d = d_anchorDat['brow'][side]
            _d["start"] = ['base_1_{0}'.format(side),'brow_1_{0}'.format(side)]
            _d["mid"] = ['base_2_{0}'.format(side),'brow_2_{0}'.format(side)]
            _d["end"] = ['base_3_{0}'.format(side),'brow_3_{0}'.format(side)]
            
            if self.controlTemple:
                _d["temple"]= ['base_4_{0}'.format(side),'brow_4_{0}'.format(side)]
            
            
        #pprint.pprint(d_anchorDat)
        #Get positions...
        _d = {'cgmName':'browCenter',
              'cgmType':'preHandle'}
        
        for section,sectionDat in d_anchorDat.iteritems():
            md_anchors[section] = {}
            for side,sideDat in sectionDat.iteritems():
                md_anchors[section][side] = {}
                for tag,dat in sideDat.iteritems():
                    _dUse = copy.copy(_d)
                    _dUse['cgmName'] = 'brow'+STR.capFirst(tag)
                    _dUse['cgmDirection'] = side
                    
                    l_pos = []
                    for key in dat:
                        l_pos.append(md_defineHandles[key].p_position)
                        
                    posBase = DIST.get_average_position(l_pos)
                    #LOC.create(position=posBase, name = tag+side)
                    
                    md_anchors[section][side][tag] = create_anchor(self,posBase, mBrowLoft, tag, None, side,nameDict=_dUse,size= _size_sub/2)
        
        
        
        #...get my anchors in lists...
        md_anchorsLists = {}
        
        for section,sectionDat in d_anchorDat.iteritems():
            md_anchorsLists[section] = {}
            
            for side,dat in sectionDat.iteritems():
                if side == 'center':
                    md_anchorsLists[section]['center'] =  [md_anchors[section][side]['main']]
                    md_mirrorDat['center'].extend(md_anchorsLists[section]['center'])
                    ml_handlesAll.extend(md_anchorsLists[section]['center'])
                    
                else:
                    md_anchorsLists[section][side] =  [md_anchors[section][side]['start'],
                                              md_anchors[section][side]['mid'],
                                              md_anchors[section][side]['end']]
                    
                    md_mirrorDat[side].extend(md_anchorsLists[section][side])
                    ml_handlesAll.extend(md_anchorsLists[section][side])


        #...make our driver curves...
        log.debug(cgmGEN.logString_msg('driver curves'))
        d_curveCreation = {}
        for section,sectionDat in md_anchorsLists.iteritems():
            for side,dat in sectionDat.iteritems():
                if side == 'center':
                    pass
                else:
                    d_curveCreation[section+STR.capFirst(side)+'Driver'] = {'ml_handles': dat,
                                             'rebuild':0}
                
        md_res = self.UTILS.create_defineCurve(self, d_curveCreation, {}, mNoTransformNull,'preCurve')
        md_resCurves = md_res['md_curves']
        ml_resCurves = md_res['ml_curves']
        
        

        #Handles ====================================================================================
        def create_handle(pos, mSurface, tag, k, side,
                          controlType = 'main',
                          mainShape = 'squareRounded',
                          subShape = 'sphere',
                          size = _size_sub,
                          offset = 1,
                          mStateNull = mStateNull,
                          mNoTransformNull = mNoTransformNull,
                          mDriver = None,
                          aimGroup = 0,nameDict = None):
            
            #Main handle ==================================================================================
            #Create...
            mHandle = cgmMeta.validateObjArg( CURVES.create_fromName(mainShape, size = size), 
                                              'cgmControl',setClass=1)
            mHandle._verifyMirrorable()
            mHandle.doSnapTo(self)
            mHandle.p_parent = mStateNull
            
            mHandle.p_position = pos
            
            #Name...
            if nameDict:
                dUse = copy.copy(nameDict)
                dUse['cgmType'] = 'prerigHandle'
                
                RIGGEN.store_and_name(mHandle,dUse)
            else:
                mHandle.doStore('cgmName',tag)
                mHandle.doStore('cgmType','prerigHandle')
                mHandle.doName()
                
                
            _key = tag
            if k:
                _key = _key+k.capitalize()
            """
            mMasterGroup = mHandle.doGroup(True,True,
                                           asMeta=True,
                                           typeModifier = 'master',
                                           setClass='cgmObject')"""


            mHandleFactory.color(mHandle.mNode,side = side, controlType=controlType)
            mStateNull.connectChildNode(mHandle, _key+'prerigHelper','block')
            
            mc.delete(mc.normalConstraint(mSurface.mNode, mHandle.mNode,
                                    aimVector = [0,0,1], upVector = [0,1,0],
                                    worldUpObject = self.mNode,
                                    worldUpType = 'objectrotation', 
                                    worldUpVector = [0,1,0]))
            
            #Main handle ==================================================================================
            #Create...
            mJointHelper = cgmMeta.validateObjArg( CURVES.create_fromName('sphere', size = size/2), 
                                              'cgmControl',setClass=1)
            mJointHelper._verifyMirrorable()
            mJointHelper.doSnapTo(self)
            mJointHelper.p_parent = mStateNull
            
            mJointHelper.p_position = pos
            
            #Name...
            if nameDict:
                dUse = copy.copy(nameDict)
                dUse['cgmType'] = 'jointHelper'                
                RIGGEN.store_and_name(mJointHelper,dUse)
            else:
                mJointHelper.doStore('cgmName',tag)
                mJointHelper.doStore('cgmType','jointHelper')
                mJointHelper.doName()
                
                

            """
            mMasterGroup = mJointHelper.doGroup(True,True,
                                           asMeta=True,
                                           typeModifier = 'master',
                                           setClass='cgmObject')"""


            mHandleFactory.color(mJointHelper.mNode,side = side, controlType=controlType)
            mStateNull.connectChildNode(mHandle, _key+'jointHelper','block')
            

            #Attach group... -------------------------------------------------------------------------------
            mTrack = mHandle.doCreateAt()
            mTrack.rename("{0}_surfaceDriver".format(mHandle.p_nameBase))
            mTrack.p_parent = mNoTransformNull
        
            _res = RIGCONSTRAINT.attach_toShape(mTrack.mNode,mSurface.mNode,'conPoint',driver= mDriver)
            md = _res[-1]
            mFollicle = md['mFollicle']
            for k in ['mDriverLoc','mFollicle']:
                md[k].p_parent = mNoTransformNull
                md[k].v = False
                
            mDepth = mTrack.doCreateAt(setClass=1)
            mDepth.rename("{0}_depthDriver".format(mHandle.p_nameBase))
            mDepth.p_parent = mTrack
            
            mJointHelper.p_parent = mDepth
            
            mPush = mTrack.doCreateAt(setClass=1)
            mPush.rename("{0}_pushDriver".format(mHandle.p_nameBase))
            
            mPush.p_parent = mTrack
            
            mJointHelper.p_parent = mDepth            
            mHandle.p_parent = mPush
            
                
            ATTR.connect('{0}.jointDepth'.format(self.mNode), "{0}.tz".format(mDepth.mNode))
            ATTR.connect('{0}.controlOffset'.format(self.mNode), "{0}.tz".format(mPush.mNode))
            

            if aimGroup:
                mHandle.doGroup(True,True,
                                asMeta=True,
                                typeModifier = 'aim',
                                setClass='cgmObject')
        
        
            return mHandle,mJointHelper
        
        
        
        log.debug(cgmGEN.logString_sub('Handles'))
        md_jointHandles = {}
        
        _d = {'cgmName':''}
        
        #...get our driverSetup
        for section,sectionDat in md_anchorsLists.iteritems():
            log.debug(cgmGEN.logString_msg(section))
            
            md_handles[section] = {}
            md_jointHandles[section] = {}

            for side,dat in sectionDat.iteritems():
                log.debug(cgmGEN.logString_msg(side))
                
                md_handles[section][side] = []
                md_jointHandles[section][side] = []
                
                _ml_handles = []
                _ml_jointHelpers = []                
                
                tag = section+STR.capFirst(side)
                
                if side == 'center':
                    d_use = copy.copy(_d)
                    d_use['cgmName'] = tag
                    d_use['cgmIterator'] = 0
                    mAnchor = md_anchorsLists[section][side][0]
                    p = mAnchor.p_position
                    
                    mHandle, mJointHelper = create_handle(p,mBrowLoft,tag,None,side,mDriver=mAnchor,nameDict=d_use)
                    
                    _ml_handles.append(mHandle)
                    _ml_jointHelpers.append(mJointHelper)
                
                else:
                    mCrv = md_resCurves.get(tag+'Driver')
                    if mCrv:
                        l_pos = CURVES.getUSplitList(mCrv.mNode, self.numBrowControl)
                        mCrv.v=False
                        d_use = copy.copy(_d)
                        d_use['cgmName'] = tag

                        for i,p in enumerate(l_pos):
                            d_use['cgmIterator'] = i
                            
                            mDriver = self.doCreateAt(setClass=1)#self.doLoc()#
                            mDriver.rename("{0}_{1}_{2}_driver".format(side,section,i))
                            mDriver.p_position = p
                            mDriver.p_parent = mStateNull
                            
                            _res = RIGCONSTRAINT.attach_toShape(mDriver.mNode,mCrv.mNode,'conPoint')
                            TRANS.parent_set(_res[0], mNoTransformNull.mNode)
                            
                            mHandle, mJointHelper = create_handle(p,mBrowLoft,tag,None,side,mDriver=mDriver,nameDict= d_use)
                            
                            _ml_handles.append(mHandle)
                            _ml_jointHelpers.append(mJointHelper)
                            
                mStateNull.msgList_connect('{0}PrerigHandles'.format(tag),_ml_handles)
                mStateNull.msgList_connect('{0}jointHandles'.format(tag),_ml_jointHelpers)
                md_mirrorDat[side].extend(_ml_handles + _ml_jointHelpers)
                md_handles[section][side] = _ml_handles
                md_jointHandles[section][side] = _ml_jointHelpers
                
                ml_handlesAll.extend(_ml_handles)
                
        
        #CURVES ==========================================================================
        log.debug(cgmGEN.logString_sub('curves'))
        
        #Make our visual joint curves for helping see things
        d_visCurves = {}
        md_browJointHelpers = md_jointHandles['brow']
        for side in 'left','right':
            d_visCurves['brow'+STR.capFirst(side)] = {'ml_handles': md_jointHandles['brow'][side],
                                                      'rebuild':0}            
        
        md_res = self.UTILS.create_defineCurve(self, d_visCurves, {}, mNoTransformNull,'preCurve')
        md_resCurves = md_res['md_curves']
        ml_resCurves = md_res['ml_curves']        
                        
        
        #Mirror setup --------------------------------
        log.debug(cgmGEN.logString_sub('mirror'))
        idx_ctr = 0
        idx_side = 0
        
        log.debug(cgmGEN.logString_msg('mirror | center'))
        for mHandle in md_mirrorDat['center']:
            mHandle._verifyMirrorable()
            mHandle.mirrorSide = 0
            mHandle.mirrorIndex = idx_ctr
            idx_ctr +=1
            mHandle.mirrorAxis = "translateX,rotateY,rotateZ"

        log.debug(cgmGEN.logString_msg('mirror | sides'))
            
        for i,mHandle in enumerate(md_mirrorDat['left']):
            mLeft = mHandle 
            mRight = md_mirrorDat['right'][i]
            
            for mObj in mLeft,mRight:
                mObj._verifyMirrorable()
                mObj.mirrorAxis = "translateX,rotateY,rotateZ"
                mObj.mirrorIndex = idx_side
            mLeft.mirrorSide = 1
            mRight.mirrorSide = 2
            mLeft.doStore('mirrorHandle',mRight)
            mRight.doStore('mirrorHandle',mLeft)            
            idx_side +=1
 
        #Close out ======================================================================================
        self.msgList_connect('prerigHandles', ml_handlesAll)
        
        self.blockState = 'prerig'
        return
    
    
    except Exception,err:
        cgmGEN.cgmExceptCB(Exception,err)


def prerigBAK(self):
    try:
        _str_func = 'prerig'
        log.debug("|{0}| >>  {1}".format(_str_func,self)+ '-'*80)
        self.blockState = 'prerig'
        _side = self.UTILS.get_side(self)
        
        self.atUtils('module_verify')
        mStateNull = self.UTILS.stateNull_verify(self,'prerig')
        mNoTransformNull = self.atUtils('noTransformNull_verify','prerig')
        
        #mRoot = self.getMessageAsMeta('rootHelper')
        mHandleFactory = self.asHandleFactory()
        
        ml_handles = []
        md_handles = {'brow':{'center':[],
                              'left':[],
                              'right':[]}}
        md_jointHandles = {'brow':{'center':[],
                              'left':[],
                              'right':[]}}
        #Get base dat =============================================================================    
        mBBHelper = self.bbHelper
        mBrowLoft = self.getMessageAsMeta('browFormLoft')
        
        _size = MATH.average(self.baseSize[1:])
        _size_base = _size * .25
        _size_sub = _size_base * .5
        
        idx_ctr = 0
        idx_side = 0
        
        def create_handle(mHelper, mSurface, tag, k, side, controlType = 'main', aimGroup = 1,nameDict = None):
            mHandle = cgmMeta.validateObjArg( CURVES.create_fromName('squareRounded', size = _size_sub), 
                                              'cgmControl',setClass=1)
            mHandle._verifyMirrorable()
            
            mHandle.doSnapTo(self)
            mHandle.p_parent = mStateNull
            
            if nameDict:
                RIGGEN.store_and_name(mHandle,nameDict)
            else:
                mHandle.doStore('cgmName',tag)
                mHandle.doStore('cgmType','prerigHandle')
                mHandle.doName()
                
                
            _key = tag
            if k:
                _key = _key+k.capitalize()
            mMasterGroup = mHandle.doGroup(True,True,
                                           asMeta=True,
                                           typeModifier = 'master',
                                           setClass='cgmObject')
        
            mc.pointConstraint(mHelper.mNode,mMasterGroup.mNode,maintainOffset=False)
        
            mHandleFactory.color(mHandle.mNode,side = side, controlType=controlType)
            mStateNull.connectChildNode(mHandle, _key+'prerigHelper','block')
        
            mc.normalConstraint(mSurface.mNode, mMasterGroup.mNode,
                                aimVector = [0,0,1], upVector = [0,1,0],
                                worldUpObject = self.mNode,
                                worldUpType = 'objectrotation', 
                                worldUpVector = [0,1,0])
        
            if aimGroup:
                mHandle.doGroup(True,True,
                                asMeta=True,
                                typeModifier = 'aim',
                                setClass='cgmObject')
        
        
            mHandle.tz = _size_sub
            
            return mHandle
        
        def create_jointHelper(mPos, mSurface, tag, k, side, nameDict=None, aimGroup = 1):
            
            mHandle = cgmMeta.validateObjArg( CURVES.create_fromName('axis3d', size = _size_sub * .5), 
                                              'cgmControl',setClass=1)
            mHandle._verifyMirrorable()
            
            mHandle.doSnapTo(self)
            mHandle.p_parent = mStateNull
            if nameDict:
                RIGGEN.store_and_name(mHandle,nameDict)
                _dCopy = copy.copy(nameDict)
                _dCopy.pop('cgmType')
                mJointLabel = mHandleFactory.addJointLabel(mHandle,NAMETOOLS.returnCombinedNameFromDict(_dCopy))
                
            else:
                mHandle.doStore('cgmName',tag)
                mHandle.doStore('cgmType','jointHelper')
                mHandle.doName()
            
            _key = tag
            if k:
                _key = "{0}_{1}".format(tag,k)
            
            
            
            mMasterGroup = mHandle.doGroup(True,True,
                                           asMeta=True,
                                           typeModifier = 'master',
                                           setClass='cgmObject')
    
            mc.pointConstraint(mPos.mNode,mMasterGroup.mNode,maintainOffset=False)
    
            #mHandleFactory.color(mHandle.mNode,side = side, controlType='sub')
            mStateNull.connectChildNode(mHandle, _key+'prerigHelper','block')
    
            mc.normalConstraint(mSurface.mNode, mMasterGroup.mNode,
                                aimVector = [0,0,1], upVector = [0,1,0],
                                worldUpObject = self.mNode,
                                worldUpType = 'objectrotation', 
                                worldUpVector = [0,1,0])
    
            if aimGroup:
                mHandle.doGroup(True,True,
                                asMeta=True,
                                typeModifier = 'aim',
                                setClass='cgmObject')
    

            return mHandle        
        
        #Handles =====================================================================================
        log.debug("|{0}| >> Brow Handles..".format(_str_func)+'-'*40)
        
        _d = {'cgmName':'browCenter',
              'cgmType':'handleHelper'}
        
        mBrowCenterDefine = self.defineBrowcenterHelper
        md_handles['browCenter'] = [create_handle(mBrowCenterDefine,mBrowLoft,
                                                  'browCenter',None,'center',nameDict = _d)]
        md_handles['brow']['center'].append(md_handles['browCenter'])
        md_handles['browCenter'][0].mirrorIndex = idx_ctr
        idx_ctr +=1
        mStateNull.msgList_connect('browCenterPrerigHandles',md_handles['browCenter'])
        
        _d_nameHandleSwap = {'start':'inner',
                             'end':'outer'}
        for tag in ['browLeft','browRight']:
            _d['cgmName'] = tag
        
            for k in ['start','mid','end']:
                _d['cgmNameModifier'] = _d_nameHandleSwap.get(k,k)
                
                if 'Left' in tag:
                    _side = 'left'
                elif 'Right' in tag:
                    _side = 'right'
                else:
                    _side = 'center'
                
                if _side in ['left','right']:
                    _d['cgmDirection'] = _side
                    
                if k == 'mid':
                    _control = 'sub'
                else:
                    _control = 'main'
                    
                mFormHelper = self.getMessageAsMeta(tag+k.capitalize()+'formHelper')
                
                mHandle = create_handle(mFormHelper,mBrowLoft,tag,k,_side,controlType = _control,nameDict = _d)
                md_handles['brow'][_side].append(mHandle)
                ml_handles.append(mHandle)
            mStateNull.msgList_connect('{0}PrerigHandles'.format(tag),md_handles['brow'][_side])


        #Joint helpers ------------------------
        log.debug("|{0}| >> Joint helpers..".format(_str_func)+'-'*40)
        _d = {'cgmName':'brow',
              'cgmDirection':'center',
              'cgmType':'jointHelper'}        
        
        mFullCurve = self.getMessageAsMeta('browLineloftCurve')
        md_jointHandles['browCenter'] = [create_jointHelper(mBrowCenterDefine,mBrowLoft,'center',None,
                                                            'center',nameDict=_d)]
        md_jointHandles['brow']['center'].append(md_jointHandles['browCenter'])
        md_jointHandles['browCenter'][0].mirrorIndex = idx_ctr
        idx_ctr +=1
        mStateNull.msgList_connect('browCenterJointHandles',md_jointHandles['browCenter'])
        

        for tag in ['browLeft','browRight']:
            mCrv = self.getMessageAsMeta("{0}JointCurve".format(tag))
            if 'Left' in tag:
                _side = 'left'
            elif 'Right' in tag:
                _side = 'right'
            else:
                _side = 'center'            
            
            if _side in ['left','right']:
                _d['cgmDirection'] = _side
                
            _factor = 100/(self.numBrowJoints-1)
            
            for i in range(self.numBrowJoints):
                log.debug("|{0}| >>  Joint Handle: {1}|{2}...".format(_str_func,tag,i))            
                _d['cgmIterator'] = i
                
                mLoc = cgmMeta.asMeta(self.doCreateAt())
                mLoc.rename("{0}_{1}_jointTrackHelper".format(tag,i))
            
                #self.connectChildNode(mLoc, tag+k.capitalize()+'formHelper','block')
                mPointOnCurve = cgmMeta.asMeta(CURVES.create_pointOnInfoNode(mCrv.mNode,
                                                                             turnOnPercentage=True))
            
                mPointOnCurve.parameter = (_factor * i)/100.0
                mPointOnCurve.doConnectOut('position',"{0}.translate".format(mLoc.mNode))
            
                mLoc.p_parent = mNoTransformNull
                
            
                res = DIST.create_closest_point_node(mLoc.mNode,mFullCurve.mNode,True)
                #mLoc = cgmMeta.asMeta(res[0])
                mTrackLoc = cgmMeta.asMeta(res[0])
                mTrackLoc.p_parent = mNoTransformNull
                mTrackLoc.v=False
                
                mHandle = create_jointHelper(mTrackLoc,mBrowLoft,tag,i,_side,nameDict=_d)
                md_jointHandles['brow'][_side].append(mHandle)
                ml_handles.append(mHandle)
                
            
        
        #Aim pass ------------------------------------------------------------------------
        for side in ['left','right']:
            #Handles -------
            ml = md_handles['brow'][side]
            for i,mObj in enumerate(ml):
                mObj.mirrorIndex = idx_side + i
                mObj.mirrorAxis = "translateX,rotateY,rotateZ"
                
                if side == 'left':
                    _aim = [-1,0,0]
                    mObj.mirrorSide = 1                    
                else:
                    _aim = [1,0,0]
                    mObj.mirrorSide = 2
                    
                _up = [0,0,1]
                _worldUp = [0,0,1]
                
                if i == 0:
                    mAimGroup = mObj.aimGroup
                    mc.aimConstraint(md_handles['browCenter'][0].masterGroup.mNode,
                                     mAimGroup.mNode,
                                     maintainOffset = False, weight = 1,
                                     aimVector = _aim,
                                     upVector = _up,
                                     worldUpVector = _worldUp,
                                     worldUpObject = mObj.masterGroup.mNode,
                                     worldUpType = 'objectRotation' )                                
                else:

                    mAimGroup = mObj.aimGroup
                    mc.aimConstraint(ml[i-1].masterGroup.mNode,
                                     mAimGroup.mNode,
                                     maintainOffset = False, weight = 1,
                                     aimVector = _aim,
                                     upVector = _up,
                                     worldUpVector = _worldUp,
                                     worldUpObject = mObj.masterGroup.mNode,
                                     worldUpType = 'objectRotation' )
                    
            mStateNull.msgList_connect('brow{0}PrerigHandles'.format(side.capitalize()), ml)
            
        idx_side = idx_side + i + 1
        log.info(idx_side)
        
        for side in ['left','right']:
            #Joint Helpers ----------------
            ml = md_jointHandles['brow'][side]
            for i,mObj in enumerate(ml):
                if side == 'left':
                    _aim = [1,0,0]
                    mObj.mirrorSide = 1
                else:
                    _aim = [-1,0,0]
                    mObj.mirrorSide = 2
                    
                mObj.mirrorIndex = idx_side + i
                mObj.mirrorAxis = "translateX,rotateY,rotateZ"
                _up = [0,0,1]
                _worldUp = [0,0,1]
                if mObj == ml[-1]:
                    _vAim = [_aim[0]*-1,_aim[1],_aim[2]]
                    mAimGroup = mObj.aimGroup
                    mc.aimConstraint(ml[i-1].masterGroup.mNode,
                                     mAimGroup.mNode,
                                     maintainOffset = False, weight = 1,
                                     aimVector = _vAim,
                                     upVector = _up,
                                     worldUpVector = _worldUp,
                                     worldUpObject = mObj.masterGroup.mNode,
                                     worldUpType = 'objectRotation' )                    
                else:
                    mAimGroup = mObj.aimGroup
                    mc.aimConstraint(ml[i+1].masterGroup.mNode,
                                     mAimGroup.mNode,
                                     maintainOffset = False, weight = 1,
                                     aimVector = _aim,
                                     upVector = _up,
                                     worldUpVector = _worldUp,
                                     worldUpObject = mObj.masterGroup.mNode,
                                     worldUpType = 'objectRotation' )
                    
            mStateNull.msgList_connect('brow{0}JointHandles'.format(side.capitalize()), ml)
        
        #Mirror setup --------------------------------
        """
        for mHandle in ml_handles:
            mHandle._verifyMirrorable()
            _str_handle = mHandle.p_nameBase
            if 'Center' in _str_handle:
                mHandle.mirrorSide = 0
                mHandle.mirrorIndex = idx_ctr
                idx_ctr +=1
            mHandle.mirrorAxis = "translateX,rotateY,rotateZ"
    
        #Self mirror wiring -------------------------------------------------------
        for k,m in _d_pairs.iteritems():
            md_handles[k].mirrorSide = 1
            md_handles[m].mirrorSide = 2
            md_handles[k].mirrorIndex = idx_side
            md_handles[m].mirrorIndex = idx_side
            md_handles[k].doStore('mirrorHandle',md_handles[m])
            md_handles[m].doStore('mirrorHandle',md_handles[k])
            idx_side +=1        """
        
        #Close out ======================================================================================
        self.msgList_connect('prerigHandles', ml_handles)
        
        self.blockState = 'prerig'
        return
    
    
    except Exception,err:
        cgmGEN.cgmExceptCB(Exception,err)
        
#=============================================================================================================
#>> Skeleton
#=============================================================================================================
def skeleton_check(self):
    return True

def skeleton_build(self, forceNew = True):
    _short = self.mNode
    _str_func = '[{0}] > skeleton_build'.format(_short)
    log.debug("|{0}| >> ...".format(_str_func)) 
    
    _radius = self.atUtils('get_shapeOffset') * .25# or 1
    ml_joints = []
    
    mModule = self.atUtils('module_verify')
    
    mRigNull = mModule.rigNull
    if not mRigNull:
        raise ValueError,"No rigNull connected"
    
    mPrerigNull = self.prerigNull
    if not mPrerigNull:
        raise ValueError,"No prerig null"
    
    mRoot = self.UTILS.skeleton_getAttachJoint(self)
    
    #>> If skeletons there, delete -------------------------------------------------------------------------- 
    _bfr = mRigNull.msgList_get('moduleJoints',asMeta=True)
    if _bfr:
        log.debug("|{0}| >> Joints detected...".format(_str_func))            
        if forceNew:
            log.debug("|{0}| >> force new...".format(_str_func))                            
            mc.delete([mObj.mNode for mObj in _bfr])
        else:
            return _bfr
        
    _baseNameAttrs = ATTR.datList_getAttrs(self.mNode,'nameList')
    _l_baseNames = ATTR.datList_get(self.mNode, 'nameList')

    
    if self.browType == 0:#Full brow
        log.debug("|{0}| >>  Full Brow...".format(_str_func))
        
 
        
        for side in 'left','right','center':
            _cap = side.capitalize()
            ml_new = []            
            if side == 'center':
                ml_base = mPrerigNull.msgList_get('brow{0}JointHandles'.format(_cap))
                for mObj in ml_base:
                    mJnt = mObj.doCreateAt('joint')
                    mJnt.doCopyNameTagsFromObject(mObj.mNode,ignore = ['cgmType'])
                    mJnt.doStore('cgmType','skinJoint')
                    mJnt.doName()
                    ml_new.append(mJnt)
                    ml_joints.append(mJnt)
                    JOINT.freezeOrientation(mJnt.mNode)
                    
                    mJnt.p_parent = mRoot

            else:
                'browLeftPreCurve'
                
                if self.numBrowControl == self.numBrowJoints:
                   ml_base = mPrerigNull.msgList_get('brow{0}JointHandles'.format(_cap))
                    for mObj in ml_base:
                        mJnt = mObj.doCreateAt('joint')
                        mJnt.doCopyNameTagsFromObject(mObj.mNode,ignore = ['cgmType'])
                        mJnt.doStore('cgmType','skinJoint')
                        mJnt.doName()
                        ml_new.append(mJnt)
                        ml_joints.append(mJnt)
                        JOINT.freezeOrientation(mJnt.mNode)
                        
                        mJnt.p_parent = mRoot
                else:
                    mCrv = self.getMessageAsMeta("brow{0}PreCurve".format(_cap))
                    raise NotImplemented,"Not done yet."
                    
            mPrerigNull.msgList_connect('brow{0}Joints'.format(_cap), ml_new)
            
                
    #>> ===========================================================================
    mRigNull.msgList_connect('moduleJoints', ml_joints)
    self.msgList_connect('moduleJoints', ml_joints)
    #self.atBlockUtils('skeleton_connectToParent')

    for mJnt in ml_joints:
        mJnt.displayLocalAxis = 1
        mJnt.radius = _radius
    for mJnt in ml_joints:mJnt.rotateOrder = 5
        
    return ml_joints    
    
    #...orient ----------------------------------------------------------------------------
    p_aim = mOrientHelper.getPositionByAxisDistance('z+',10.0)
    SNAP.aim_atPoint(mEyeJoint.mNode,p_aim,'z+')
    JOINT.freezeOrientation(mEyeJoint.mNode)
    
    name(mEyeJoint,_d_base)
    ml_joints.append(mEyeJoint)
    
    mPrerigNull.connectChildNode(mEyeJoint.mNode,'eyeJoint')
    
    mRoot = mEyeJoint
    #>> Eye =================================================================================== 
    if self.hasEyeOrb:
        mEyeOrbJoint = mEyeJoint.doDuplicate()
        self.copyAttrTo(_baseNameAttrs[1],mEyeOrbJoint.mNode,'cgmName',driven='target')
        name(mEyeOrbJoint,_d_base)
        
        mEyeJoint.p_parent = mEyeOrbJoint
        ml_joints.insert(0,mEyeOrbJoint)
        mPrerigNull.connectChildNode(mEyeOrbJoint.mNode,'eyeOrbJoint')
        mRoot = mEyeOrbJoint

    if len(ml_joints) > 1:
        ml_joints[0].getParent(asMeta=1).radius = ml_joints[-1].radius * 5
        
    if self.setupLid:#=====================================================
        _setupLid = self.getEnumValueString('setupLid')
        log.debug("|{0}| >> EyeLid setup: {1}.".format(_str_func,_setupLid))
        
        #'lidRootHelper'
        
        mLidsHelper = self.getMessageAsMeta('lidsHelper')
        _d_lids = copy.copy(_d_base)
        
        _d_lids['cgmNameModifier'] = 'lid'
        
        if _setupLid == 'clam':
            
            for a in ['upr','lwr']:
                log.debug("|{0}| >> Creating lid joint: {1}.".format(_str_func,a))
                _a = '{0}LidHandle'.format(a)
                mHandle = self.getMessageAsMeta(_a)
                mJointHandle = mHandle.jointHelper
                
                mJoint = mJointHandle.doCreateAt('joint')
                mJoint.parent = mRoot
                
                mJoint.doStore('cgmName',a)
                name(mJoint,_d_lids)
                
                JOINT.freezeOrientation(mJoint.mNode)
                
                log.debug("|{0}| >> joint: {1} | {2}.".format(_str_func,mJoint,mJoint.parent))                
                ml_joints.append(mJoint)
                mPrerigNull.connectChildNode(mJoint.mNode,'{0}LidJoint'.format(a))

        else:
            log.error("Don't have setup for eyelidType: {0}".format(_setupLid))
            
    
    mRigNull.msgList_connect('moduleJoints', ml_joints)
    self.msgList_connect('moduleJoints', ml_joints)
    self.atBlockUtils('skeleton_connectToParent')

    for mJnt in ml_joints:
        mJnt.displayLocalAxis = 1
        mJnt.radius = _radius
        
    return ml_joints    

    return
    

    
    
    
    #>> Head ===================================================================================
    log.debug("|{0}| >> Head...".format(_str_func))
    p = POS.get( ml_prerigHandles[-1].jointHelper.mNode )
    mHeadHelper = ml_formHandles[0].orientHelper
    
    #...create ---------------------------------------------------------------------------
    mHead_jnt = cgmMeta.cgmObject(mc.joint (p=(p[0],p[1],p[2])))
    mHead_jnt.parent = False
    #self.copyAttrTo(_baseNameAttrs[-1],mHead_jnt.mNode,'cgmName',driven='target')
    
    #...orient ----------------------------------------------------------------------------
    #cgmMeta.cgmObject().getAxisVector
    CORERIG.match_orientation(mHead_jnt.mNode, mHeadHelper.mNode)
    JOINT.freezeOrientation(mHead_jnt.mNode)
    
    #...name ----------------------------------------------------------------------------
    #mHead_jnt.doName()
    #mHead_jnt.rename(_l_namesToUse[-1])
    for k,v in _l_namesToUse[-1].iteritems():
        mHead_jnt.doStore(k,v)
    mHead_jnt.doName()
    
    if self.neckBuild:#...Neck =====================================================================
        log.debug("|{0}| >> neckBuild...".format(_str_func))
        if len(ml_prerigHandles) == 2 and self.neckJoints == 1:
            log.debug("|{0}| >> Single neck joint...".format(_str_func))
            p = POS.get( ml_prerigHandles[0].jointHelper.mNode )
            
            mBaseHelper = ml_prerigHandles[0].orientHelper
            
            #...create ---------------------------------------------------------------------------
            mNeck_jnt = cgmMeta.cgmObject(mc.joint (p=(p[0],p[1],p[2])))
            
            #self.copyAttrTo(_baseNameAttrs[0],mNeck_jnt.mNode,'cgmName',driven='target')
            
            #...orient ----------------------------------------------------------------------------
            #cgmMeta.cgmObject().getAxisVector
            TRANS.aim_atPoint(mNeck_jnt.mNode,
                              mHead_jnt.p_position,
                              'z+', 'y+', 'vector',
                              vectorUp=mHeadHelper.getAxisVector('z-'))
            JOINT.freezeOrientation(mNeck_jnt.mNode)
            
            #mNeck_jnt.doName()
            
            mHead_jnt.p_parent = mNeck_jnt
            ml_joints.append(mNeck_jnt)
            
            #mNeck_jnt.rename(_l_namesToUse[0])
            for k,v in _l_namesToUse[0].iteritems():
                mNeck_jnt.doStore(k,v)
            mNeck_jnt.doName()
        else:
            log.debug("|{0}| >> Multiple neck joint...".format(_str_func))
            
            _d = self.atBlockUtils('skeleton_getCreateDict', self.neckJoints +1)
            
            mOrientHelper = ml_prerigHandles[0].orientHelper
            
            ml_joints = JOINT.build_chain(_d['positions'][:-1], parent=True, worldUpAxis= mOrientHelper.getAxisVector('z-'))
            
            for i,mJnt in enumerate(ml_joints):
                #mJnt.rename(_l_namesToUse[i])
                for k,v in _l_namesToUse[i].iteritems():
                    mJnt.doStore(k,v)
                mJnt.doName()                
            
            #self.copyAttrTo(_baseNameAttrs[0],ml_joints[0].mNode,'cgmName',driven='target')
            
        mHead_jnt.p_parent = ml_joints[-1]
        ml_joints[0].parent = False
    else:
        mHead_jnt.parent = False
        #mHead_jnt.rename(_l_namesToUse[-1])
        
    ml_joints.append(mHead_jnt)
    
    for mJnt in ml_joints:
        mJnt.displayLocalAxis = 1
        mJnt.radius = _radius
    if len(ml_joints) > 1:
        mHead_jnt.radius = ml_joints[-1].radius * 5

    mRigNull.msgList_connect('moduleJoints', ml_joints)
    self.msgList_connect('moduleJoints', ml_joints)
    self.atBlockUtils('skeleton_connectToParent')
    
    return ml_joints


#=============================================================================================================
#>> rig
#=============================================================================================================
#NOTE - self here is a rig Factory....

d_preferredAngles = {}#In terms of aim up out for orientation relative values, stored left, if right, it will invert
d_rotateOrders = {}

#Rig build stuff goes through the rig build factory ------------------------------------------------------
@cgmGEN.Timer
def rig_prechecks(self):
    _str_func = 'rig_prechecks'
    log.debug(cgmGEN.logString_start(_str_func))
    
    mBlock = self.mBlock
    
    str_browSetup = mBlock.getEnumValueString('browSetup')
    if str_browSetup not in ['ribbon']:
        self.l_precheckErrors.append("Brow setup not completed: {0}".format(str_browSetup))
    
    str_browType = mBlock.getEnumValueString('browType')
    if str_browType not in ['full']:
        self.l_precheckErrors.append("Brow setup not completed: {0}".format(str_browType))
                
    if mBlock.scaleSetup:
        self.l_precheckErrors.append("Scale setup not complete")

@cgmGEN.Timer
def rig_dataBuffer(self):
    _short = self.d_block['shortName']
    _str_func = 'rig_dataBuffer'
    log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
    log.debug("{0}".format(self))
    
    mBlock = self.mBlock
    mModule = self.mModule
    mRigNull = self.mRigNull
    mPrerigNull = mBlock.prerigNull
    self.mPrerigNull = mPrerigNull
    ml_handleJoints = mPrerigNull.msgList_get('handleJoints')
    mMasterNull = self.d_module['mMasterNull']
    
    mEyeFormHandle = mBlock.bbHelper
    
    self.mRootFormHandle = mEyeFormHandle
    ml_formHandles = [mEyeFormHandle]
    
    self.b_scaleSetup = mBlock.scaleSetup
    
    self.str_browSetup = False
    if mBlock.browSetup:
        self.str_browSetup  = mBlock.getEnumValueString('browSetup')
        
    #Logic checks ========================================================================

    
    #Offset ============================================================================ 
    self.v_offset = self.mPuppet.atUtils('get_shapeOffset')
    """
    str_offsetMode = ATTR.get_enumValueString(mBlock.mNode,'offsetMode')
    
    if not mBlock.getMayaAttr('offsetMode'):
        log.debug("|{0}| >> default offsetMode...".format(_str_func))
        self.v_offset = self.mPuppet.atUtils('get_shapeOffset')
    else:
        str_offsetMode = ATTR.get_enumValueString(mBlock.mNode,'offsetMode')
        log.debug("|{0}| >> offsetMode: {1}".format(_str_func,str_offsetMode))
        
        l_sizes = []
        for mHandle in ml_formHandles:
            _size_sub = POS.get_bb_size(mHandle,True)
            l_sizes.append( MATH.average(_size_sub) * .1 )            
        self.v_offset = MATH.average(l_sizes)"""
    log.debug("|{0}| >> self.v_offset: {1}".format(_str_func,self.v_offset))    
    log.debug(cgmGEN._str_subLine)
    
    #Size =======================================================================================
    self.v_baseSize = [mBlock.blockScale * v for v in mBlock.baseSize]
    self.f_sizeAvg = MATH.average(self.v_baseSize)
    log.debug("|{0}| >> size | self.v_baseSize: {1} | self.f_sizeAvg: {2}".format(_str_func,
                                                                                  self.v_baseSize,
                                                                                  self.f_sizeAvg ))
    
    #Settings =============================================================================
    mModuleParent =  self.d_module['mModuleParent']
    if mModuleParent:
        mSettings = mModuleParent.rigNull.settings
    else:
        log.debug("|{0}| >>  using puppet...".format(_str_func))
        mSettings = self.d_module['mMasterControl'].controlVis

    log.debug("|{0}| >> mSettings | self.mSettings: {1}".format(_str_func,mSettings))
    self.mSettings = mSettings
    
    log.debug("|{0}| >> self.mPlug_visSub_moduleParent: {1}".format(_str_func,
                                                                    self.mPlug_visSub_moduleParent))
    log.debug("|{0}| >> self.mPlug_visDirect_moduleParent: {1}".format(_str_func,
                                                                       self.mPlug_visDirect_moduleParent))
    
    #DynParents =============================================================================
    #self.UTILS.get_dynParentTargetsDat(self)
    #log.debug(cgmGEN._str_subLine)
    
    #rotateOrder =============================================================================
    _str_orientation = self.d_orientation['str']
    _l_orient = [_str_orientation[0],_str_orientation[1],_str_orientation[2]]
    self.ro_base = "{0}{1}{2}".format(_str_orientation[1],_str_orientation[2],_str_orientation[0])
    self.ro_head = "{2}{0}{1}".format(_str_orientation[0],_str_orientation[1],_str_orientation[2])
    self.ro_headLookAt = "{0}{2}{1}".format(_str_orientation[0],_str_orientation[1],_str_orientation[2])
    log.debug("|{0}| >> rotateOrder | self.ro_base: {1}".format(_str_func,self.ro_base))
    log.debug("|{0}| >> rotateOrder | self.ro_head: {1}".format(_str_func,self.ro_head))
    log.debug("|{0}| >> rotateOrder | self.ro_headLookAt: {1}".format(_str_func,self.ro_headLookAt))
    log.debug(cgmGEN._str_subLine)
    

    return True


@cgmGEN.Timer
def rig_skeleton(self):
    _short = self.d_block['shortName']
    
    _str_func = 'rig_skeleton'
    log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
    log.debug("{0}".format(self))
        
    mBlock = self.mBlock
    mRigNull = self.mRigNull
    mPrerigNull = mBlock.prerigNull
    
    ml_jointsToConnect = []
    ml_jointsToHide = []
    ml_joints = mRigNull.msgList_get('moduleJoints')
    self.d_joints['ml_moduleJoints'] = ml_joints
    
    
    BLOCKUTILS.skeleton_pushSettings(ml_joints, self.d_orientation['str'],
                                     self.d_module['mirrorDirection'])
                                     #d_rotateOrders, d_preferredAngles)
    
    
    #Rig Joints =================================================================================
    ml_rigJoints = BLOCKUTILS.skeleton_buildDuplicateChain(mBlock,
                                                           ml_joints,
                                                           'rig',
                                                           self.mRigNull,
                                                           'rigJoints',
                                                           'rig',
                                                           cgmType = False,
                                                           blockNames=False)
    
    ml_segmentJoints = BLOCKUTILS.skeleton_buildDuplicateChain(mBlock,ml_joints, None,
                                                               mRigNull,'segmentJoints','seg',
                                                               cgmType = 'segJnt')    
    ml_jointsToHide.extend(ml_segmentJoints)        
    
    #Brow joints ================================================================================
    log.debug("|{0}| >> Brow Joints...".format(_str_func)+ '-'*40)
    
    #Need to sort our joint lists:
    md_skinJoints = {'brow':{}}
    md_rigJoints = {'brow':{}}
    md_segJoints = {'brow':{}}
    
    for k in ['center','left','right']:
        log.debug("|{0}| >> {1}...".format(_str_func,k))        
        ml_skin = self.mPrerigNull.msgList_get('brow{0}Joints'.format(k.capitalize()))
        md_skinJoints['brow'][k] = ml_skin
        ml_rig = []
        ml_seg = []
        
        for mJnt in ml_skin:
            mRigJoint = mJnt.getMessageAsMeta('rigJoint')
            ml_rig.append(mRigJoint)
            
            mSegJoint = mJnt.getMessageAsMeta('segJoint')
            ml_seg.append(mSegJoint)
            mSegJoint.p_parent = False
            
            mRigJoint.p_parent = mSegJoint
            
        md_rigJoints['brow'][k] = ml_rig
        md_segJoints['brow'][k] = ml_seg
        
    """
    for i,mJnt in enumerate(ml_rigJoints):
        mJnt.parent = ml_segmentJoints[i]
        mJnt.connectChildNode(ml_segmentJoints[i],'driverJoint','sourceJoint')#Connect
    ml_jointsToHide.extend(ml_segmentJoints)        
        """
    log.debug(cgmGEN._str_subLine)
    
    #Brow joints ================================================================================
    log.debug("|{0}| >> Brow Handles...".format(_str_func)+ '-'*40)    
    mBrowCurve = mBlock.getMessageAsMeta('browLineloftCurve')
    _BrowCurve = mBrowCurve.getShapes()[0]
    md_handles = {'brow':{}}
    md_handleShapes = {'brow':{}}
    
    for k in ['center','left','right']:
        log.debug("|{0}| >> {1}...".format(_str_func,k))        
        ml_helpers = self.mPrerigNull.msgList_get('brow{0}PrerigHandles'.format(k.capitalize()))    
        ml_new = []
        for mHandle in ml_helpers:
            mJnt = mHandle.doCreateAt('joint')
            mJnt.doCopyNameTagsFromObject(mHandle.mNode,ignore = ['cgmType'])
            #mJnt.doStore('cgmType','dag')
            mJnt.doName()
            ml_new.append(mJnt)
            ml_joints.append(mJnt)
            JOINT.freezeOrientation(mJnt.mNode)
            mJnt.p_parent = False
            mJnt.p_position = mHandle.masterGroup.p_position
            #DIST.get_closest_point(mHandle.mNode,_BrowCurve,True)[0]

        md_handles['brow'][k] = ml_new
        md_handleShapes['brow'][k] = ml_helpers
        
        ml_jointsToHide.extend(ml_new)
    log.debug(cgmGEN._str_subLine)
    
    self.md_rigJoints = md_rigJoints
    self.md_skinJoints = md_skinJoints
    self.md_segJoints = md_segJoints
    self.md_handles = md_handles
    self.md_handleShapes = md_handleShapes
    
    #...joint hide -----------------------------------------------------------------------------------
    for mJnt in ml_jointsToHide:
        try:mJnt.drawStyle =2
        except:mJnt.radius = .00001
            
    #...connect... 
    self.fnc_connect_toRigGutsVis( ml_jointsToConnect )        
    return

@cgmGEN.Timer
def rig_shapes(self):
    try:
        _short = self.d_block['shortName']
        _str_func = 'rig_shapes'
        log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
        log.debug("{0}".format(self))
        
    
        mBlock = self.mBlock
        #_baseNameAttrs = ATTR.datList_getAttrs(mBlock.mNode,'nameList')    
        mHandleFactory = mBlock.asHandleFactory()
        mRigNull = self.mRigNull
        mPrerigNull = self.mPrerigNull
        
        ml_rigJoints = mRigNull.msgList_get('rigJoints')
        
        #Brow center ================================================================================
        mBrowCenter = self.md_handles['brow']['center'][0].doCreateAt()
        mBrowCenterShape = self.md_handleShapes['brow']['center'][0].doDuplicate(po=False)
        mBrowCenterShape.scale = [1.5,1.5,1.5]
        
        mBrowCenter.doStore('cgmName','browMain')
        mBrowCenter.doName()
        
        CORERIG.shapeParent_in_place(mBrowCenter.mNode,
                                     mBrowCenterShape.mNode,False)
        
        mRigNull.connectChildNode(mBrowCenter,'browMain','rigNull')#Connect
        
        
        #Handles ================================================================================
        log.debug("|{0}| >> Handles...".format(_str_func)+ '-'*80)
        for k,d in self.md_handles.iteritems():
            log.debug("|{0}| >> {1}...".format(_str_func,k)+ '-'*40)
            for side,ml in d.iteritems():
                log.debug("|{0}| >> {1}...".format(_str_func,side)+ '-'*10)
                for i,mHandle in enumerate(ml):
                    log.debug("|{0}| >> {1}...".format(_str_func,mHandle))
                    CORERIG.shapeParent_in_place(mHandle.mNode,
                                                 self.md_handleShapes[k][side][i].mNode)
                    
                    if side == 'center':
                        mHandleFactory.color(mHandle.mNode,side='center',controlType='sub')
                        
                    
        #Direct ================================================================================
        log.debug("|{0}| >> Direct...".format(_str_func)+ '-'*80)
        for k,d in self.md_rigJoints.iteritems():
            log.debug("|{0}| >> {1}...".format(_str_func,k)+ '-'*40)
            for side,ml in d.iteritems():
                log.debug("|{0}| >> {1}...".format(_str_func,side)+ '-'*10)
                for i,mHandle in enumerate(ml):
                    log.debug("|{0}| >> {1}...".format(_str_func,mHandle))
                    crv = CURVES.create_fromName(name='cube',
                                                 direction = 'z+',
                                                 size = mHandle.radius*2)
                    SNAP.go(crv,mHandle.mNode)
                    mHandleFactory.color(crv,side=side,controlType='sub')
                    CORERIG.shapeParent_in_place(mHandle.mNode,
                                                 crv,keepSource=False)
        for mJnt in ml_rigJoints:
            try:
                mJnt.drawStyle =2
            except:
                mJnt.radius = .00001                
        return
    except Exception,error:
        cgmGEN.cgmExceptCB(Exception,error,msg=vars())


@cgmGEN.Timer
def rig_controls(self):
    try:
        _short = self.d_block['shortName']
        _str_func = 'rig_controls'
        log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
        log.debug("{0}".format(self))
      
        mRigNull = self.mRigNull
        mBlock = self.mBlock
        ml_controlsAll = []#we'll append to this list and connect them all at the end
        mRootParent = self.mDeformNull
        ml_segmentHandles = []
        
        #mPlug_visSub = self.atBuilderUtils('build_visSub')
        mPlug_visDirect = self.mPlug_visDirect_moduleParent
        mPlug_visSub = self.mPlug_visSub_moduleParent
        
        """
        cgmMeta.cgmAttr(self.mSettings,'visDirect_{0}'.format(self.d_module['partName']),
                                          value = True,
                                          attrType='bool',
                                          defaultValue = False,
                                          keyable = False,hidden = False)"""        
        
        
        
        
        mBrowMain = mRigNull.browMain
        _d = MODULECONTROL.register(mBrowMain,
                                    mirrorSide= self.d_module['mirrorDirection'],
                                    mirrorAxis="translateX,rotateY,rotateZ",
                                    makeAimable = False)
        ml_controlsAll.append(_d['mObj'])
        ml_segmentHandles.append(_d['mObj'])
        
        #Handles ================================================================================
        log.debug("|{0}| >> Handles...".format(_str_func)+ '-'*80)
        for k,d in self.md_handles.iteritems():
            log.debug("|{0}| >> {1}...".format(_str_func,k)+ '-'*40)
            for side,ml in d.iteritems():
                log.debug("|{0}| >> {1}...".format(_str_func,side)+ '-'*10)
                for i,mHandle in enumerate(ml):
                    log.debug("|{0}| >> {1}...".format(_str_func,mHandle))
                    _d = MODULECONTROL.register(mHandle,
                                                mirrorSide= side,
                                                mirrorAxis="translateX,rotateY,rotateZ",
                                                makeAimable = False)
                    
                    ml_controlsAll.append(_d['mObj'])
                    ml_segmentHandles.append(_d['mObj'])
                    
        #Direct ================================================================================
        log.debug("|{0}| >> Direct...".format(_str_func)+ '-'*80)
        for k,d in self.md_rigJoints.iteritems():
            log.debug("|{0}| >> {1}...".format(_str_func,k)+ '-'*40)
            for side,ml in d.iteritems():
                log.debug("|{0}| >> {1}...".format(_str_func,side)+ '-'*10)
                for i,mHandle in enumerate(ml):
                    log.debug("|{0}| >> {1}...".format(_str_func,mHandle))
                    _d = MODULECONTROL.register(mHandle,
                                                typeModifier='direct',
                                                mirrorSide= side,
                                                mirrorAxis="translateX,rotateY,rotateZ",
                                                makeAimable = False)
                    
                    mObj = _d['mObj']
                    
                    ml_controlsAll.append(_d['mObj'])
                    
                    ATTR.set_hidden(mObj.mNode,'radius',True)        
                    if mObj.hasAttr('cgmIterator'):
                        ATTR.set_hidden(mObj.mNode,'cgmIterator',True)        
                
                    for mShape in mObj.getShapes(asMeta=True):
                        ATTR.connect(mPlug_visDirect.p_combinedShortName, "{0}.overrideVisibility".format(mShape.mNode))                    

       
        

            
        #Close out...
        mHandleFactory = mBlock.asHandleFactory()
        for mCtrl in ml_controlsAll:
            ATTR.set(mCtrl.mNode,'rotateOrder',self.ro_base)
            
            if mCtrl.hasAttr('radius'):
                ATTR.set(mCtrl.mNode,'radius',0)        
            
            ml_pivots = mCtrl.msgList_get('spacePivots')
            if ml_pivots:
                log.debug("|{0}| >> Coloring spacePivots for: {1}".format(_str_func,mCtrl))
                for mPivot in ml_pivots:
                    mHandleFactory.color(mPivot.mNode, controlType = 'sub')            
        """
        if mHeadIK:
            ATTR.set(mHeadIK.mNode,'rotateOrder',self.ro_head)
        if mHeadLookAt:
            ATTR.set(mHeadLookAt.mNode,'rotateOrder',self.ro_headLookAt)
            """
        mRigNull.msgList_connect('controlsFace',ml_controlsAll)
        mRigNull.msgList_connect('handleJoints',ml_segmentHandles,'rigNull')        
        mRigNull.msgList_connect('controlsAll',ml_controlsAll)
        mRigNull.moduleSet.extend(ml_controlsAll)
        mRigNull.faceSet.extend(ml_controlsAll)
        
    except Exception,error:
        cgmGEN.cgmExceptCB(Exception,error,msg=vars())


@cgmGEN.Timer
def rig_frame(self):
    _short = self.d_block['shortName']
    _str_func = ' rig_rigFrame'
    
    log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
    log.debug("{0}".format(self))    

    mBlock = self.mBlock
    mRigNull = self.mRigNull
    mRootParent = self.mDeformNull
    mModule = self.mModule
    
    
    mBrowMain = mRigNull.browMain
    mBrowMain.masterGroup.p_parent = self.mDeformNull
    
    #Parenting ============================================================================
    log.debug("|{0}| >>Parenting...".format(_str_func)+ '-'*80)
    
    for k,d in self.md_handles.iteritems():
        log.debug("|{0}| >> {1}...".format(_str_func,k)+ '-'*40)
        for side,ml in d.iteritems():
            log.debug("|{0}| >> {1}...".format(_str_func,side)+ '-'*10)
            for i,mHandle in enumerate(ml):
                mHandle.masterGroup.p_parent = self.mDeformNull
                
    for k,d in self.md_segJoints.iteritems():
        log.debug("|{0}| >> {1}...".format(_str_func,k)+ '-'*40)
        for side,ml in d.iteritems():
            log.debug("|{0}| >> {1}...".format(_str_func,side)+ '-'*10)
            for i,mHandle in enumerate(ml):
                mHandle.p_parent = self.mDeformNull
        
    
    #Brow Ribbon ============================================================================
    log.debug("|{0}| >> Brow ribbon...".format(_str_func)+ '-'*80)
    
    md_seg = self.md_segJoints
    md_brow = md_seg['brow']
    ml_right = copy.copy(md_brow['right'])
    ml_center = md_brow['center']
    ml_left = md_brow['left']
    ml_right.reverse()
    
    ml_ribbonJoints = ml_right + ml_center + ml_left
    
    md_handles = self.md_handles
    md_brow = md_handles['brow']
    ml_rightHandles = copy.copy(md_brow['right'])
    ml_centerHandles = md_brow['center']
    ml_leftHandles = md_brow['left']
    ml_rightHandles.reverse()    
    
    
    ml_skinDrivers = ml_rightHandles + ml_centerHandles + ml_leftHandles
    
    d_ik = {'jointList':[mObj.mNode for mObj in ml_ribbonJoints],
            'baseName' : self.d_module['partName'] + '_ikRibbon',
            'orientation':'xyz',
            'loftAxis' : 'z',
            'tightenWeights':False,
            'driverSetup':'stableBlend',
            'squashStretch':None,
            'connectBy':'constraint',
            'squashStretchMain':'arcLength',
            'paramaterization':'fixed',#mBlock.getEnumValueString('ribbonParam'),
            #masterScalePlug:mPlug_masterScale,
            #'settingsControl': mSettings.mNode,
            'extraSquashControl':True,
            'influences':ml_skinDrivers,
            'moduleInstance' : self.mModule}    
    
    
    res_ribbon = IK.ribbon(**d_ik)
    
    #Setup some constraints============================================================================
    md_brow['center'][0].masterGroup.p_parent = mBrowMain
    
    mc.pointConstraint([md_brow['left'][0].mNode, md_brow['right'][0].mNode],
                       md_brow['center'][0].masterGroup.mNode,
                       maintainOffset=True)
    
    
    for side in ['left','right']:
        ml = md_brow[side]
        ml[0].masterGroup.p_parent = mBrowMain
        mc.pointConstraint([ml[0].mNode, ml[-1].mNode],
                           ml[1].masterGroup.mNode,
                           maintainOffset=True)
        
        
        
    #pprint.pprint(vars())

    return


@cgmGEN.Timer
def rig_cleanUp(self):
    _short = self.d_block['shortName']
    _str_func = 'rig_cleanUp'
    log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
    log.debug("{0}".format(self))
    
    mBlock = self.mBlock
    mRigNull = self.mRigNull
    
    mMasterControl= self.d_module['mMasterControl']
    mMasterDeformGroup= self.d_module['mMasterDeformGroup']    
    mMasterNull = self.d_module['mMasterNull']
    mModuleParent = self.d_module['mModuleParent']
    mPlug_globalScale = self.d_module['mPlug_globalScale']
    

    #Settings =================================================================================
    #log.debug("|{0}| >> Settings...".format(_str_func))
    #mSettings.visDirect = 0
    
    #mPlug_FKIK = cgmMeta.cgmAttr(mSettings,'FKIK')
    #mPlug_FKIK.p_defaultValue = 1
    #mPlug_FKIK.value = 1
        
    #Lock and hide =================================================================================
    ml_controls = mRigNull.msgList_get('controlsAll')
    self.UTILS.controls_lockDown(ml_controls)
    
    if not mBlock.scaleSetup:
        log.debug("|{0}| >> No scale".format(_str_func))
        ml_controlsToLock = copy.copy(ml_controls)
        for mCtrl in ml_controlsToLock:
            ATTR.set_standardFlags(mCtrl.mNode, ['scale'])
    else:
        log.debug("|{0}| >>  scale setup...".format(_str_func))
        
        
    self.mDeformNull.dagLock(True)

    #Close out ===============================================================================================
    mRigNull.version = self.d_block['buildVersion']
    mBlock.blockState = 'rig'
    mBlock.UTILS.set_blockNullFormState(mBlock)
    self.UTILS.rigNodes_store(self)


def create_simpleMesh(self,  deleteHistory = True, cap=True):
    _str_func = 'create_simpleMesh'
    log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
    log.debug("{0}".format(self))
    
    #>> Head ===================================================================================
    log.debug("|{0}| >> Head...".format(_str_func))
    
    mGroup = self.msgList_get('headMeshProxy')[0].getParent(asMeta=True)
    l_headGeo = mGroup.getChildren(asMeta=False)
    ml_headStuff = []
    for i,o in enumerate(l_headGeo):
        log.debug("|{0}| >> geo: {1}...".format(_str_func,o))                    
        if ATTR.get(o,'v'):
            log.debug("|{0}| >> visible head: {1}...".format(_str_func,o))            
            mObj = cgmMeta.validateObjArg(mc.duplicate(o, po=False, ic = False)[0])
            ml_headStuff.append(  mObj )
            mObj.p_parent = False
        

    if self.neckBuild:#...Neck =====================================================================
        log.debug("|{0}| >> neckBuild...".format(_str_func))    
        ml_neckMesh = self.UTILS.create_simpleLoftMesh(self,deleteHistory,cap)
        ml_headStuff.extend(ml_neckMesh)
        
    _mesh = mc.polyUnite([mObj.mNode for mObj in ml_headStuff],ch=False)
    _mesh = mc.rename(_mesh,'{0}_0_geo'.format(self.p_nameBase))
    
    return cgmMeta.validateObjListArg(_mesh)

def asdfasdfasdf(self, forceNew = True, skin = False):
    """
    Build our proxyMesh
    """
    _short = self.d_block['shortName']
    _str_func = 'build_proxyMesh'
    log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
    log.debug("{0}".format(self))
    
    mBlock = self.mBlock
    mRigNull = self.mRigNull
    mHeadIK = mRigNull.headIK
    mSettings = mRigNull.settings
    mPuppetSettings = self.d_module['mMasterControl'].controlSettings
    
    ml_rigJoints = mRigNull.msgList_get('rigJoints',asMeta = True)
    if not ml_rigJoints:
        raise ValueError,"No rigJoints connected"

    #>> If proxyMesh there, delete --------------------------------------------------------------------------- 
    _bfr = mRigNull.msgList_get('proxyMesh',asMeta=True)
    if _bfr:
        log.debug("|{0}| >> proxyMesh detected...".format(_str_func))            
        if forceNew:
            log.debug("|{0}| >> force new...".format(_str_func))                            
            mc.delete([mObj.mNode for mObj in _bfr])
        else:
            return _bfr
        
    #>> Head ===================================================================================
    log.debug("|{0}| >> Head...".format(_str_func))
    if directProxy:
        log.debug("|{0}| >> directProxy... ".format(_str_func))
        _settings = self.mRigNull.settings.mNode
        
    
    mGroup = mBlock.msgList_get('headMeshProxy')[0].getParent(asMeta=True)
    l_headGeo = mGroup.getChildren(asMeta=False)
    l_vis = mc.ls(l_headGeo, visible = True)
    ml_headStuff = []
    
    for i,o in enumerate(l_vis):
        log.debug("|{0}| >> visible head: {1}...".format(_str_func,o))
        
        mObj = cgmMeta.validateObjArg(mc.duplicate(o, po=False, ic = False)[0])
        ml_headStuff.append(  mObj )
        mObj.parent = ml_rigJoints[-1]
        
        ATTR.copy_to(ml_rigJoints[-1].mNode,'cgmName',mObj.mNode,driven = 'target')
        mObj.addAttr('cgmIterator',i)
        mObj.addAttr('cgmType','proxyGeo')
        mObj.doName()
        
        if directProxy:
            CORERIG.shapeParent_in_place(ml_rigJoints[-1].mNode,mObj.mNode,True,False)
            CORERIG.colorControl(ml_rigJoints[-1].mNode,_side,'main',directProxy=True)        
        
    if mBlock.neckBuild:#...Neck =====================================================================
        log.debug("|{0}| >> neckBuild...".format(_str_func))


def build_proxyMesh(self, forceNew = True, puppetMeshMode = False):
    """
    Build our proxyMesh
    """
    raise ValueError,"This needs to be reworked to new block call"
    _short = self.d_block['shortName']
    _str_func = 'build_proxyMesh'
    log.debug("|{0}| >>  ".format(_str_func)+ '-'*80)
    log.debug("{0}".format(self))
    
     
    mBlock = self.mBlock
    mRigNull = self.mRigNull
    m#Settings = mRigNull.settings
    mPuppetSettings = self.d_module['mMasterControl'].controlSettings
    mPrerigNull = mBlock.prerigNull
    #directProxy = mBlock.proxyDirect
    
    _side = BLOCKUTILS.get_side(self.mBlock)
    
    ml_rigJoints = mRigNull.msgList_get('rigJoints',asMeta = True)
    if not ml_rigJoints:
        raise ValueError,"No rigJoints connected"
    self.v_baseSize = [mBlock.blockScale * v for v in mBlock.baseSize]
    
    #>> If proxyMesh there, delete --------------------------------------------------------------------------- 
    if puppetMeshMode:
        _bfr = mRigNull.msgList_get('puppetProxyMesh',asMeta=True)
        if _bfr:
            log.debug("|{0}| >> puppetProxyMesh detected...".format(_str_func))            
            if forceNew:
                log.debug("|{0}| >> force new...".format(_str_func))                            
                mc.delete([mObj.mNode for mObj in _bfr])
            else:
                return _bfr        
    else:
        _bfr = mRigNull.msgList_get('proxyMesh',asMeta=True)
        if _bfr:
            log.debug("|{0}| >> proxyMesh detected...".format(_str_func))            
            if forceNew:
                log.debug("|{0}| >> force new...".format(_str_func))                            
                mc.delete([mObj.mNode for mObj in _bfr])
            else:
                return _bfr
        
    ml_proxy = []
    ml_curves = []
    #Brow -------------
    mUprCurve = mBlock.getMessageAsMeta('browUprloftCurve')
    mUprUse = mUprCurve.doDuplicate(po=False)
    mUprUse.p_parent = mRigNull.constrainNull
    mUprCurve.v=False
    ml_curves.append(mUprUse)
    md_rigJoints = {'brow':{}}
    for k in ['center','left','right']:
        log.debug("|{0}| >> {1}...".format(_str_func,k))        
        ml_skin = mPrerigNull.msgList_get('brow{0}Joints'.format(k.capitalize()))
        ml_rig = []
        for mJnt in ml_skin:
            mRigJoint = mJnt.getMessageAsMeta('rigJoint')
            ml_rig.append(mRigJoint)        
        md_rigJoints['brow'][k] = ml_rig
        
    ml_right = copy.copy(md_rigJoints['brow']['right'])
    ml_right.reverse()
    ml_followJoints = ml_right + md_rigJoints['brow']['center'] + md_rigJoints['brow']['left']

    
    _crv = mc.curve(d=1,p=[mObj.p_position for mObj in ml_followJoints])
    mCrv = cgmMeta.validateObjArg(_crv,'cgmObject',setClass=True)
    mCrv.p_parent = mRigNull
    mCrv.rename('{0}_proxyBrowCurve'.format(self.d_module['partName']))            
    mCrv.v=False
    ml_curves.append(mCrv)

    l_clusters = []
    for i,cv in enumerate(mCrv.getComponents('cv')):
        _res = mc.cluster(cv, n = 'test_{0}_{1}_pre_cluster'.format(self.d_module['partName'],i))
        TRANS.parent_set( _res[1],ml_followJoints[i].mNode)
        l_clusters.append(_res)
        ATTR.set(_res[1],'visibility',False)

    #pprint.pprint(l_clusters)
    mc.rebuildCurve(mCrv.mNode, d=3, keepControlPoints=False,ch=1,s=8,
                    n="{0}_reparamRebuild".format(self.d_module['partName']))    

    #Loft ------------------------------------------------
    _res_body = mc.loft([mCrv.mNode,mUprUse.mNode], 
                        o = True, d = 1, po = 3, c = False,ch=True,autoReverse=False)
    mLoftSurface = cgmMeta.validateObjArg(_res_body[0],'cgmObject',setClass= True)
    _loftNode = _res_body[1]
    _inputs = mc.listHistory(mLoftSurface.mNode,pruneDagObjects=True)
    _rebuildNode = _inputs[0]            
    mLoftSurface = cgmMeta.validateObjArg(_res_body[0],'cgmObject',setClass= True)

    #if polyType == 'bezier':
    mc.reverseSurface(mLoftSurface.mNode, direction=1,rpo=True)

    _d = {'keepCorners':False}#General}


    mLoftSurface.overrideEnabled = 1
    mLoftSurface.overrideDisplayType = 2

    mLoftSurface.p_parent = self.mModule
    mLoftSurface.resetAttrs()

    mLoftSurface.doStore('cgmName',"{0}_{1}brow".format(self.d_module['partName'],k),attrType='string')
    mLoftSurface.doStore('cgmType','proxy')
    mLoftSurface.doName()
    log.info("|{0}| loft node: {1}".format(_str_func,_loftNode))             



    #mLoft = mBlock.getMessageAsMeta('{0}LidFormLoft'.format(tag))
    #mMesh = mLoft.doDuplicate(po=False, ic=False)
    #mDag = mRigJoint.doCreateAt(setClass='cgmObject')
    #CORERIG.shapeParent_in_place(mDag.mNode, mMesh.mNode,False)
    #mDag.p_parent = mRigJoint
    ml_proxy.append(mLoftSurface)
        



    for mProxy in ml_proxy:
        CORERIG.colorControl(mProxy.mNode,_side,'main',transparent=False,proxy=True)
        mc.makeIdentity(mProxy.mNode, apply = True, t=1, r=1,s=1,n=0,pn=1)

        #Vis connect -----------------------------------------------------------------------
        mProxy.overrideEnabled = 1
        ATTR.connect("{0}.proxyVis".format(mPuppetSettings.mNode),"{0}.visibility".format(mProxy.mNode) )
        ATTR.connect("{0}.proxyLock".format(mPuppetSettings.mNode),"{0}.overrideDisplayType".format(mProxy.mNode) )
        for mShape in mProxy.getShapes(asMeta=1):
            str_shape = mShape.mNode
            mShape.overrideEnabled = 0
            #ATTR.connect("{0}.proxyVis".format(mPuppetSettings.mNode),"{0}.visibility".format(str_shape) )
            ATTR.connect("{0}.proxyLock".format(mPuppetSettings.mNode),"{0}.overrideDisplayTypes".format(str_shape) )
            
    #if directProxy:
    #    for mObj in ml_rigJoints:
    #        for mShape in mObj.getShapes(asMeta=True):
                #mShape.overrideEnabled = 0
    #            mShape.overrideDisplayType = 0
    #            ATTR.connect("{0}.visDirect".format(_settings), "{0}.overrideVisibility".format(mShape.mNode))
        
        

    
    mRigNull.msgList_connect('proxyMesh', ml_proxy + ml_curves)




















