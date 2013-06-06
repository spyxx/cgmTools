"""
------------------------------------------
NodeFactory: cgm.core
Author: Josh Burton
email: jjburton@cgmonks.com

Website : http://www.cgmonks.com
------------------------------------------

Class Factory for building node networks
================================================================
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
from cgm.lib import (lists,
                     cgmMath,
                     search,
                     attributes)
reload(search)


def createAndConnectBlendColors(driverObj1, driverObj2, l_drivenObjs, driver = None, channels = ['translate','rotate']):
    """
    @kws
    driverObj1(string) -- 
    driverObj2(string) -- 
    l_drivenObj(list) -- result chain

    driver(attr arg) -- driver attr
    channels(list) -- channels to blend
    
    """
    mi_driverObj1 = cgmMeta.validateObjArg(driverObj1,cgmMeta.cgmObject,noneValid=False)
    mi_driverObj2 = cgmMeta.validateObjArg(driverObj2,cgmMeta.cgmObject,noneValid=False)
    ml_drivenObjs = cgmMeta.validateObjListArg(l_drivenObjs,cgmMeta.cgmObject,noneValid=False)
    d_driver = cgmMeta.validateAttrArg(driver,noneValid=True)
    mi_driver = False
    if d_driver:mi_driver = d_driver.get('mi_plug') or False
    if type(channels) not in [list,tuple]:channels = [channels]
    log.debug('driver1: %s'%mi_driverObj1.getShortName())
    log.debug('driver2: %s'%mi_driverObj2.getShortName())
    log.debug('driven: %s'%[i_o.getShortName() for i_o in ml_drivenObjs])

    log.debug('driver: %s'%mi_driver.p_combinedShortName)
    
    """
    if not len(mi_driverObj1) >= len(ml_drivenObj) or not len(mi_driverObj2) >= len(ml_drivenObj):
	raise StandardError,"createAndConnectBlendColors>>> Joint chains aren't equal lengths: i_driverObj1: %s | i_driverObj2: %s | l_drivenObj: %s"%(len(i_driverObj1),len(i_driverObj2),len(l_drivenObj))
    """
    l_channels = [c for c in channels if c in ['translate','rotate','scale']]
    if not l_channels:
	raise StandardError,"createAndConnectBlendColors>>> Need valid channels: %s"%channels

    ml_nodes = []
    
    #>>> Actual meat
    #===========================================================
    for i,i_obj in enumerate(ml_drivenObjs):
	log.debug(i_obj)
	for channel in l_channels:
	    i_node = cgmMeta.cgmNode(nodeType = 'blendColors')
	    i_node.addAttr('cgmName',"%s_to_%s"%(mi_driverObj1.getShortName(),mi_driverObj2.getShortName()))
	    i_node.addAttr('cgmTypeModifier',channel)
	    i_node.doName()
	    log.debug("createAndConnectBlendColors>>> %s || %s = %s | %s"%(mi_driverObj1.getShortName(),
	                                                             mi_driverObj2.getShortName(),
	                                                             i_obj.getShortName(),channel))
	    cgmMeta.cgmAttr(i_node,'color2').doConnectIn("%s.%s"%(mi_driverObj1.mNode,channel))
	    cgmMeta.cgmAttr(i_node,'color1').doConnectIn("%s.%s"%(mi_driverObj2.mNode,channel))
	    cgmMeta.cgmAttr(i_node,'output').doConnectOut("%s.%s"%(i_obj.mNode,channel))
	    
	    if mi_driver:
		cgmMeta.cgmAttr(i_node,'blender').doConnectIn(mi_driver.p_combinedName)
	    
	    ml_nodes.append(i_node)
	    
    return ml_nodes



def createSingleBlendNetwork(driver, result1, result2, maxValue = 1,minValue = 0, **kws):
    """
    Build a single blend network for things like an FK/IK blend where you want a 1 result for either option
    Attrs not required to exist, if they don't, it creates them.
    individual args should be sting 'obj.attr' or 2 len list in ['obj','attr'] format.
    
    driver1 attr
    result1 - attr you want as your 0 is 1
    result2 - attr you want as your 1
    """
    
    #Create the mdNode
    d_driver = cgmMeta.validateAttrArg(driver,**kws)
    d_result1 = cgmMeta.validateAttrArg(result1,lock=True,**kws)    
    d_result2 = cgmMeta.validateAttrArg(result2,lock=True,**kws) 
    
    for d in [d_driver,d_result1,d_result2]:
	d['mi_plug'].p_maxValue = maxValue
	d['mi_plug'].p_minValue = minValue
        
    #driver 1 is easy as it's a direct connect:
    d_driver['mi_plug'].doConnectOut(d_result1['combined'])
    
    #Create the node
    i_pma = cgmMeta.cgmNode(mc.createNode('plusMinusAverage'))
    i_pma.operation = 2#subtraction
    
    #Make our connections
    attributes.doSetAttr(i_pma.mNode,'input1D[0]',maxValue)
    #d_result1['mi_plug'].doConnectOut("%s.input1D[0]"%i_pma.mNode)    
    d_driver['mi_plug'].doConnectOut("%s.input1D[1]"%i_pma.mNode)
    
    attributes.doConnectAttr("%s.output1D"%i_pma.mNode,d_result2['combined'])
    
    i_pma.addAttr('cgmName',"_".join([d_result1['mi_plug'].attr,d_result2['mi_plug'].attr,]),lock=True)	
    i_pma.addAttr('cgmTypeModifier','blend',lock=True)
    i_pma.doName()   
    
    return {'d_result1':d_result1,'d_result2':d_result2}
    
   
    
class build_mdNetwork(object):
    """
    Build a md network. Most useful for for vis networks.
    
    @kws
    results(list) -- [{resultlist:,drivers:list,driven:list},...]
    >>result(list) -- obj,attr
    >>drivers(nested list) -- [[obj,attr]...]#len must be 2
    >>driven(nested list) -- [[obj,attr]...]#can be None
    [ {'result':obj1,resultAttr,'drivers':[[dObj,dAttr2],[dObj,dAttr2]],'driven' = None} ]
    
    results must have at least one driver
    1 drive r-- direct connect
    
    Example:
    from cgm.core.classes import NodeFactory as nf
    reload(nf)
    from cgm.core import cgm_Meta as cgmMeta
    arg = [{'result':[i_o,'result'],'drivers':[[i_o,'driver1'],[i_o,'driver2']],'driven':[[i_o,'driven1']]}]
    arg = [{'result':['null1','result'],'drivers':[['null1','driver1'],['null1','driver2']],'driven':[['null1','driven1']]}]
    arg = [{'result':[i_o,'leftSubControls'],'drivers':[[i_o,'left'],[i_o,'sub'],[i_o,'controls']]},
           {'result':[i_o,'rightSubControls'],'drivers':[[i_o,'right'],[i_o,'sub'],[i_o,'controls']]},
           {'result':[i_o,'leftControls'],'drivers':[[i_o,'left'],[i_o,'controls']]},
           {'result':[i_o,'rightControls'],'drivers':[[i_o,'right'],[i_o,'controls']]}
            ]
    
    i_o = cgmMeta.cgmNode('null1')
    nf.build_mdNetwork(arg)
    """
    compatibleAttrs = ['bool','int','enum']
    def __init__(self, arg, defaultAttrType = 'bool', operation = 1,*args,**kws):
	
        """Constructor"""
	self.d_iAttrs = {}#attr instances stores as {index:instance}
	self.l_iAttrs = []#Indices for iAttrs
	self.d_resultNetworksToBuild = {}#Index desctiptions of networks to build {target:[[1,2],3]}
	self.d_connectionsToMake = {}#Connections to make
	self.d_mdNetworksToBuild = {}#indexed to l_mdNetworkIndices
	self.l_mdNetworkIndices = []#Indices of md networks
	self.l_good_mdNetworks = []#good md networks by arg [1,2]
	self.d_good_mdNetworks = {}#md instances indexed to l_good_mdNetworks
	
	self.kw_operation = operation
	
        #>>>Keyword args	
        log.debug(">>> visNetwork.__init__")
	if kws:log.debug("kws: %s"%str(kws))
	if args:log.debug("args: %s"%str(args))
	
	#>>>Check arg
	self.validateArg(arg,defaultAttrType = defaultAttrType,*args,**kws)
	log.debug("resultNetworks: %s"%self.d_resultNetworksToBuild)
	
	#>>>Build network
	log.debug("Building mdNetworks: %s"%self.d_mdNetworksToBuild)
	log.debug("Building mdNetworks indices: %s"%self.l_mdNetworkIndices)
	for i,k in enumerate(self.l_iAttrs):
	    log.debug("%s >> %s"%(i,self.d_iAttrs[i].p_combinedName))
	
	for resultIndex in self.d_mdNetworksToBuild.keys():#For each stored index dict key
	    #To do, add a check to see if a good network exists before making another
	    iNetwork = self.validateMDNetwork(resultIndex)
	    
	    #if iNetwork:
		#self.d_iAttrs[resultIndex].doConnectIn(iNetwork.)
     
	#a = cgmMeta.cgmAttr()
	#a.p_combinedName
	#>>>Connect stuff
	log.debug("Making connections: %s"%self.d_connectionsToMake)	
	for sourceIndex in self.d_connectionsToMake.keys():#For each stored index dict key
	    source = self.d_iAttrs.get(sourceIndex)#Get the source attr's instance
	    log.debug("source: '%s'"%source.p_combinedName)	    
	    for targetIndex in self.d_connectionsToMake.get(sourceIndex):#for each target of that source
		target = self.d_iAttrs.get(targetIndex)#Get the instance
		log.debug("target: '%s'"%target.p_combinedName)	    		
		#source.doConnectOut(target.p_combinedName)#Connect
		attributes.doConnectAttr(source.p_combinedName,target.p_combinedName)
	    
    def validateArg(self,arg,defaultAttrType,*args,**kws):
	assert type(arg) is list,"Argument must be list"
	#>>> 
	def validateObjAttr(obj,attr,defaultAttrType):
	    """
	    Return a cgmAttr if everything checks out
	    """
	    log.debug("verifyObjAttr: '%s',%s'"%(obj,attr))
	    if type(attr) not in [str,unicode]:
		log.warning("attr arg must be string: '%s'"%attr)
		return False
	    try:#Try to link an instance
		obj.mNode
		i_obj = obj
	    except:#Else try to initialize
		if mc.objExists(obj):
		    log.debug("initializing '%s'"%obj)
		    i_obj = cgmMeta.cgmNode(obj)	    				
		else:
		    log.debug("'%s' doesn't exist" %obj)
		    return False
	    #Check attr
	    if not i_obj.hasAttr(attr):
		log.debug("...making attr: '%s'"%attr)
		i_obj.addAttr(attr,attrType = defaultAttrType,initialValue=1)
	    
	    return self.register_iAttr(i_obj,attr)
	#========================================================
	for i,a in enumerate(arg):
	    iDrivers = []
	    iDriven = []
	    iResult = False
	    bufferArg = {}
	    log.debug("Checking: %s"%a)
	    if type(a) is dict:
		log.debug("...is dict")
		if 'result' and 'drivers' in a.keys():
		    log.debug("...found necessary keys")
		    if type(a.get('result')) is list and len(a.get('result'))==2:
		        log.debug("...Checking 'result'")			
			obj = a.get('result')[0]
			attr = a.get('result')[1]
			index = validateObjAttr(obj,attr,defaultAttrType)
			self.d_iAttrs[index].p_locked = True
			self.d_iAttrs[index].p_hidden = True			
			iResult = index
			log.debug("iResult: %s"%iResult)
		    if type(a.get('drivers')) is list:
			for pair in a.get('drivers'):
			    if len(pair) == 2:
				log.debug("driver: %s"%pair)				
				obj = pair[0]
				attr = pair[1]		
				iDrivers.append(validateObjAttr(obj,attr,defaultAttrType))
			log.debug("iDrivers: %s"%iDrivers)
		    if type(a.get('driven')) is list:
			for pair in a.get('driven'):
			    if len(pair) == 2:
				log.debug("driven: %s"%pair)				
				obj = pair[0]
				attr = pair[1]	
				index = validateObjAttr(obj,attr,defaultAttrType)
				self.d_iAttrs[index].p_locked = True
				self.d_iAttrs[index].p_hidden = True
				iDriven.append(index)
			log.debug("iDriven %s"%iDriven)
		
		if type(iResult) is int and iDrivers:
		    log.debug('Storing arg data')
		    
		    if len(iDrivers) == 1:
			self.d_connectionsToMake[iDrivers[0]]=[iResult]		
		    elif len(iDrivers) == 2:
			if iDrivers in self.l_mdNetworkIndices:
			    log.debug("Go ahead and connect it")
			else:
			    self.l_mdNetworkIndices.append(iDrivers)#append the drivers
			    index = self.l_mdNetworkIndices.index(iDrivers)
			    self.d_mdNetworksToBuild[iResult] = [iDrivers]
		    else:
			log.debug('asdf')
			
			buffer = iDrivers[:2]
			if buffer not in self.l_mdNetworkIndices:
			    self.l_mdNetworkIndices.append(buffer)#append the drivers
			    index = self.l_mdNetworkIndices.index(buffer)
			    self.d_mdNetworksToBuild[iResult] = [buffer]
			for n in iDrivers[2:]:#Figure out the md's to build
			    buffer = [buffer]
			    buffer.append(n)
			    if buffer not in self.l_mdNetworkIndices:
				self.l_mdNetworkIndices.append(buffer)#append the drivers
				index = self.l_mdNetworkIndices.index(buffer)
				self.d_mdNetworksToBuild[iResult] = buffer
 
		    #>>> network
		    self.d_resultNetworksToBuild[iResult]=iDrivers
		    if iDriven:
			self.d_connectionsToMake[iResult]=iDriven
			
    def validateMDNetwork(self,buildNetworkIndex):
	"""
	arg should be in the form of [[int,int],int...int]
	the first arg should always be a pair as the base md node paring, the remainging ones are daiy chained form that
	"""
	def verifyMDNetwork(source1Index, source2Index):
	    """
	    If it doesn't exist, make it, otherwise, register the connection
	    """
	    log.debug("Creating mdNetwork: %s"%arg[0])
	    source1 = self.d_iAttrs[source1Index]#get the sources
	    source2 = self.d_iAttrs[source2Index]
	    log.debug("source1: %s"%source1.p_combinedName)
	    log.debug("source2: %s"%source2.p_combinedName)
	    
	    #se if this connection exists now that we know the connectors
	    i_md = None	    
	    matchCandidates = []
	    source1Driven = source1.getDriven(obj=True)	    
	    if source1.getDriven():
		log.debug("1Driven: %s"%source1Driven)
		for c in source1Driven:
		    if search.returnObjectType(c) == 'multiplyDivide':
			matchCandidates.append(c)
	    source2Driven = source2.getDriven(obj=True)
	    if matchCandidates and source2Driven:
		log.debug("matchCandidates: %s"%matchCandidates)		
		log.debug("2Driven: %s"%source2Driven)		
		for c in source2Driven:
		    if c in matchCandidates:
			log.debug("Found existing md node: %s"%c)
			i_md = cgmMeta.cgmNode(c)#Iniitalize the match
			if i_md.operation != self.kw_operation:
			    i_md.operation = self.kw_operation
			    log.warning("Operation of existing node '%s' has been changed: %s"%(i_md.getShortName(),self.kw_operation))
			break

	    if i_md is None:
		i_md = cgmMeta.cgmNode(name = 'test',nodeType = 'multiplyDivide')#make the node	
		i_md.operation = self.kw_operation
		source1.doConnectOut("%s.input1X"%i_md.mNode)
		source2.doConnectOut("%s.input2X"%i_md.mNode)
		#Name it
		source1Name = source1.p_combinedName
		source1Name = ''.join(source1Name.split('|')[-1].split(':')[-1].split('_'))
		source2Name = source2.p_combinedName
		source2Name = ''.join(source2Name.split('|')[-1].split(':')[-1].split('_'))    
		i_md.doStore('cgmName',"%s_to_%s"%(source1Name,source2Name))
		i_md.doName()
	    
	    #Store to our good network and the output attr
	    self.l_good_mdNetworks.append(arg[0])#append it to get our index lib
	    index = self.l_good_mdNetworks.index(arg[0])#get index
	    self.d_good_mdNetworks[index]=i_md#store the instance
	    i_mdBuffer = i_md
	    self.i_mdOutAttrIndex = self.register_iAttr(i_md,'outputX')
	    log.debug("self.i_mdOutAttrIndex: %s"%self.i_mdOutAttrIndex)
	    
	log.debug(">>> in build_mdNetwork.validateMDNetwork")
	arg = self.d_mdNetworksToBuild.get(buildNetworkIndex)
	log.debug("arg: %s"%arg)
	
	if type(arg) is not list:
	    log.error("validateMDNetwork args must be a list")
	    return False
	if len(arg)>2 and type(arg[0]) is not list and len(arg[0]) == 2:
	    log.error("validateMDNetwork arg[0] must be a list with 2 keys")
	    return False    
	#Let's get the first mdNode checked
	i_mdBuffer = False
	self.i_mdOutAttrIndex = None
	
	#Need to add check to see if the network exists from sourc
	if arg[0] not in self.l_good_mdNetworks:
	    log.debug("creating first md node")
	    verifyMDNetwork(arg[0][0],arg[0][1])
	else:
	    log.debug("Finding exsiting network")
	    nodeIndex = self.l_good_mdNetworks.index(arg[0])
	    log.debug("nodeIndex: %s"%nodeIndex)
	    i_md = self.d_good_mdNetworks[nodeIndex]#get the md instance
	    log.debug("i_md: '%s'"%i_md.getShortName())	    
	    self.i_mdOutAttrIndex = self.register_iAttr(i_md,'outputX')
  
	for connection in arg[1:]:
	    log.debug("self.i_mdOutAttrIndex: %s"%self.i_mdOutAttrIndex)	    
	    log.debug("...Adding connection: %s"%connection)
	    if self.i_mdOutAttrIndex is None:
		raise ValueError,"self.i_mdOutAttrIndex is :%s"%self.i_mdOutAttrIndex
	    if connection not in self.d_iAttrs.keys():
		raise ValueError,"connection index not in self.l_iAttrs: %s"%connection		
	    verifyMDNetwork(self.i_mdOutAttrIndex ,connection)
	
	if self.i_mdOutAttrIndex is not None:#Register our connection to make
	    log.debug("adding connection: %s = [%s]"%(self.i_mdOutAttrIndex,buildNetworkIndex))
	    self.d_connectionsToMake[self.i_mdOutAttrIndex]=[buildNetworkIndex]
    
    def register_iAttr(self, i_obj,attr):
	"""
	i_obj - cgmNode,cgmObject
	attr(string) - attr name to register
	"""
	combinedName = "%s.%s"%(i_obj.mNode,attr)
	if not mc.objExists(combinedName):
	    log.error("Cannot register nonexistant attr: %s"%combinedName)
	    return False	
	if not combinedName in self.l_iAttrs:
	    i_attr = cgmMeta.cgmAttr(i_obj,attr,keyable = False)
	    log.debug("iAttr: %s"%i_attr)
	    self.l_iAttrs.append(combinedName)
	    self.d_iAttrs[self.l_iAttrs.index(combinedName)] = i_attr
	    
	return self.l_iAttrs.index(combinedName)
    

d_operator_to_NodeType = {'clamp':['clamp('],
                          'setRange':['setRange('],
                          'condition':[' == ',' != ',' > ',' < ',' >= ',' <= '],
                          'multiplyDivide':[' * ',' / ',' ^ '],
                          'plusMinusAverage':[' + ',' - ',' >< ']}#>< we're using for average
d_function_to_Operator = {'==':0,'!=':1,'>':2,'>=':3,'<':4,'<=':5,#condition
                          '*':1,'/':2,'^':3,#md
                          '+':1,'-':2,'><':3}#pma
d_nodeType_to_limits = {'condition':{'maxDrivers':2},
                        'multiplyDivide':{'maxDrivers':2},
                        'clamp':{'maxDrivers':3,'minDrivers':2},
                        'setRange':{'maxDrivers':5,'minDrivers':5},
                        'plusMinusAverage':{'maxDrivers':False}}
d_nodeType_to_DefaultAttrType = {'condition':'int',
                                 'multiplyDivide':'float',
                                 'clamp':'float',
                                 'setRange':'float',
                                 'plusMinusAverage':'float'}
d_nodeType_to_input = {'condition':['firstTerm','secondTerm'],
                       'multiplyDivide':['input1X','input2X'],
                       'clamp':['minR','maxR','inputR'],
                       'setRange':['minX','maxX','oldMinX','oldMaxX','valueX'],
                       'plusMinusAverage':'input1D'}
d_nodeType_to_output = {'condition':'outColorR',
                       'multiplyDivide':'outputX',
                       'clamp':'outputR',
                       'setRange':'outValueX',
                       'plusMinusAverage':'output1D'}
d_nodeType_to_resultSplit = {'condition':';',
                             'multiplyDivide':'=',
                             'plusMinusAverage':'=',
                             'setRange':'=',
                             'clamp':'='}
d_functionStringSwaps = {'.':'_attr_', ' ':'',',':'_',
                         '+':'_add_','-':'_minus_','><':'_avg_',#pma                                                 
                         '==':'_isEqualTo_','!=':'_isNotEqualTo_','>':'_isGreaterThan_','>=':'_isGreaterOrEqualTo_','<':'_isLessThan_','<=':'_isLessThanOrEqualTo_',#condition
                         '*':'_multBy_','/':'_divBy_','^':'_pow_',}#md
l_extraConditionArgs = ['if ','elif ']
l_NotImplementedTo_NodalArg = ['{','}']

class argsToNodes(object):
    """
    --From the crazy mind of Josh
    More expression like node building. Syntax is super important.
    Attributes are validated via cgmMeta.validateAttrArg()
    
    Supports:
    >>Condition nodes -- if,>,<...
    >>MultiplyDivide -- *,/,etc
    >>PlusMinusAverage -- +,-,><. >< is our average symbol
    
    Split results by ';' for condtion args and with = for others. Separate multiple results with ','
    
    Condtion networks assume a 0 if False, 1 if True setup
    
    TODO:
    --Implemented condtion then/else results. It will be by ':' when ready
    --Implement ()
    --implement ramps and other things
    --Node verification like mdNetwork builder so it doesn't rebuild all the time
        
    @Ussage
    from cgm.core.classes import NodeFactory as nFactory
    reload(nFactory)
    
    nFactory.argsToNodes(arg).doBuild() #Buildd
    nFactory.argsToNodes(arg)#Logic only
    
    Examples. Assuming you have an object called 'worldCenter_loc'
    arg = "worldCenter_loc.sumResult1 = worldCenter_loc.tx + worldCenter_loc.ty + worldCenter_loc.tz"
    arg = "worldCenter_loc.simpleSum = 1 + 2 + 3"#Working
    arg = "worldCenter_loc.simpleAv = 1 >< 2 >< 3 "#Working
    arg = "worldCenter_loc.inverseMultThree = 3 * -worldCenter_loc.ty"#Working
    arg = "worldCenter_loc.simpleMathResult = 4 - 2"#Working
    arg = "worldCenter_loc.ty = -worldCenter_loc.ty "#Working
    arg = "worldCenter_loc.multResult = worldCenter_loc.ty * 3"#Working
    arg = "worldCenter_loc.sumResult = worldCenter_loc.ty + 3 + worldCenter_loc.ty"#Working
    arg = "worldCenter_loc.result2 = if worldCenter_loc.ty > 3"#Working
    
    
    """
    compatibleAttrs = ['bool','int','enum']
    def __init__(self, arg, *args,**kws):
        """Constructor"""
	self.d_iAttrs = {}#attr instances stores as {index:instance}
	self.l_attrs = []#Indices for iAttrs
	self.ml_attrs = []
	self.d_resultNetworksToVerify = {}#Index desctiptions of networks to build {target:[[1,2],3]}
	self.d_connectionsToMake = {}#Connections to make
	self.d_networksToBuild = {'condition':[],
	                          'multiplyDivide':[],
	                          'plusMinusAverage':[],
	                          'clamp':[],
	                          'setRange':[],
	                          }#indexed to l_mdNetworkIndices
	self.l_good_nodeNetworks = []#good md networks by arg [1,2]
	self.d_good_nodeNetworks = {}#md instances indexed to l_good_mdNetworks
	self.d_good_connections= {}#connections 
	
	self.l_clampNetworkArgs = []
	self.l_setRangeNetworkArgs = []	
	self.l_condNetworkArgs = []
	self.l_mdNetworkArgs = []
	self.l_pmaNetworkArgs = []
	self.l_directConnectArgs = []
	self.d_good_NetworkOuts = {}
	self.validateArg(arg,*args,**kws)#Validate Arg

	if self.d_networksToBuild:
	    log.debug(">> d_networksToBuild: '%s'"%self.d_networksToBuild)	    
	if self.d_connectionsToMake:
	    log.debug(">> d_connectionsToMake: '%s'"%self.d_connectionsToMake)
	    
    #@r9General.Timer
    def doBuild(self):
	l_args = []
	ml_outPlugs = []
	l_outPlugs = []
	
	for nodeType in self.d_networksToBuild.keys():
	    if self.d_networksToBuild[nodeType]:
		log.debug("argsToNodes>> d_networksToBuild: '%s'"%nodeType)
		for n in self.d_networksToBuild[nodeType]:
		    log.debug(">>>> %s"%n)
		    self.verify_nodalNetwork(n,nodeType)
		    
	for resultKey in self.d_connectionsToMake.keys():
	    if self.d_connectionsToMake[resultKey].get('nodeType') == 'directConnect':
		log.debug("direct Connect mode!")
		if type(self.d_connectionsToMake[resultKey].get('driver')) is not int:
		    raise StandardError,"Cannot make a connection. No driver indexed: %s"%self.d_connectionsToMake[resultKey]
		for i in self.d_connectionsToMake[resultKey]['driven']:
		    driverIndex = self.d_connectionsToMake[resultKey].get('driver')
		    self.ml_attrs[i].doConnectIn(self.ml_attrs[driverIndex].p_combinedName)
		    if self.ml_attrs[i].isUserDefined():
			self.ml_attrs[i].p_hidden = True
		    self.ml_attrs[i].p_locked = True	
		    
	    else:#Reg mode
		if resultKey not in self.d_good_nodeNetworks.keys():
		    log.warning("resultKey not found: %s"%resultKey)
		else:
		    arg = resultKey
		    l_args.append(arg)
		    try:outIndex = self.d_good_NetworkOuts[arg]
		    except:raise StandardError,"Failed to find out network plug for: '%s'"%arg
		    mi_outPlug = self.ml_attrs[outIndex]
		    ml_outPlugs.append(mi_outPlug)
		    l_outPlugs.append(mi_outPlug.p_combinedName)
		    #let's lock and hide our result attrs
		    for i in self.d_connectionsToMake[resultKey]['driven']:
			log.debug(i)
			log.debug(self.d_good_nodeNetworks[resultKey].mNode)
			log.debug(self.d_connectionsToMake[resultKey])		    
			log.debug(d_nodeType_to_output[self.d_connectionsToMake[resultKey]['nodeType']])
			self.ml_attrs[i].doConnectIn("%s.%s"%(self.d_good_nodeNetworks[resultKey].mNode,
			                                      d_nodeType_to_output[self.d_connectionsToMake[resultKey]['nodeType']]))	    
			
			if self.ml_attrs[i].isUserDefined():
			    self.ml_attrs[i].p_hidden = True
			self.ml_attrs[i].p_locked = True
		    
	#Build our return dict
	#{l_args:[],l_outPlugs:[]indexed to args
	ml_nodes = [self.d_good_nodeNetworks.get(key) for key in self.d_good_nodeNetworks.keys()]
	l_nodes = [i_node.mNode for i_node in ml_nodes]
	
	return {'l_args':l_args,'l_outPlugs':l_outPlugs,'ml_outPlugs':ml_outPlugs,'ml_nodes':ml_nodes,'l_nodes':l_nodes}
    
    def cleanArg(self,arg):
	#Clean an are of extra spaces
	#print arg
	buffer = arg.split(' ')
	start = 0
	end = len(list(arg))
	for i,n in enumerate(buffer):
	    if n != '':
		start = i
		break
	buffer.reverse()    
	for i,n in enumerate(buffer):
	    if n != '':
		end = len(buffer)-i
		break
	buffer.reverse()	
	return  ' '.join(buffer[start:end])
    
    def validateArg(self,arg,*args,**kws):
	log.debug("argsToNodes.validateArg>> Arg: '%s'"%(arg))	
	if type(arg) in [list,tuple]:
	    raise NotImplementedError,"argsToNodes.validateArg>> list type arg not ready"
	elif type(arg) != str:
	    try: arg = str(arg)
	    except:
		raise StandardError,"argsToNodes.validateArg>> Arg type must be str. Couldn't convert Type: %s"%type(arg)
	
	if ' and ' in arg:#I was a moron and had 'and' before. Lots of things have 'and' like 'handle'....
	    log.warning("argsToNodes.validateArg>> ' and ' not implemented. Splitting and processing the former part of arg. arg: %s"%arg)	    
	    arg = arg.split(' and ')[0]	    
	    log.warning("argsToNodes.validateArg>> New arg: %s"%arg)
	
	argBuffer = []
	if ' .' in arg:	#First we need to split if we have periods
	    splitBuffer = arg.split(' .')
	    log.debug("argsToNodes.validateArg>> '.' split: %s"%splitBuffer)
	    argBuffer = splitBuffer
	else:
	    argBuffer = [arg]
	    
	log.debug("argsToNodes.validateArg>> argBuffer: %s"%(argBuffer))
	try:#Arg checks
	    for i,a in enumerate(argBuffer):
		for k in l_NotImplementedTo_NodalArg:
		    if k in arg:
			raise NotImplementedError,"argsToNodes.validateArg>> '%s' not implemented | '%s'"%(k,a)
    
		foundMatch = False
		log.debug("argsToNodes.validateArg>> On a: %s"%(a))
		for k in d_operator_to_NodeType['setRange']:
		    if k in a:
			foundMatch = True
			log.debug("argsToNodes.validateArg>> setRange arg found: %s"%a)
			try:
			    if self.validate_subArg(a,'setRange'):
				log.debug("argsToNodes.validateArg>> setRange arg verified: %s"%a)				
				self.l_clampNetworkArgs.append(a)
				break
			    else:
				log.debug("argsToNodes.validateArg>> setRange arg failed: %s"%a)							
			except StandardError,error:
			    raise StandardError,error 	    
		for k in d_operator_to_NodeType['clamp']:
		    if k in a:
			foundMatch = True
			log.debug("argsToNodes.validateArg>> clamp arg found: %s"%a)
			try:
			    if self.validate_subArg(a,'clamp'):
				log.debug("argsToNodes.validateArg>> clamp arg verified: %s"%a)				
				self.l_clampNetworkArgs.append(a)
				break
			    else:
				log.debug("argsToNodes.validateArg>> clamp arg failed: %s"%a)							
			except StandardError,error:
			    raise StandardError,error  	    
		for k in d_operator_to_NodeType['condition'] + l_extraConditionArgs:
		    if k in a:
			foundMatch = True
			log.debug("argsToNodes.validateArg>> cond arg found: %s"%a)
			try:
			    if self.validate_subArg(a,'condition'):
				log.debug("argsToNodes.validateArg>> cond arg verified: %s"%a)				
				self.l_condNetworkArgs.append(a)
				break
			    else:
				log.debug("argsToNodes.validateArg>> cond arg failed: %s"%a)							
			except StandardError,error:
			    raise StandardError,error  
		for k in d_operator_to_NodeType['multiplyDivide']:
		    if k in a:
			foundMatch = True		    
			try:
			    log.debug("argsToNodes.validateArg>> md arg(%s) found: %s"%(k,a))	
			    if self.validate_subArg(a,'multiplyDivide'):
				self.l_mdNetworkArgs.append(a)
				break
			    else:
				log.debug("argsToNodes.validateArg>> md arg failed: %s"%a)				    
			except StandardError,error:
			    raise StandardError,error  	   
		for k in d_operator_to_NodeType['plusMinusAverage']:
		    if k in a:
			foundMatch = True		    
			try:
			    log.debug("argsToNodes.validateArg>> pma arg(%s) found: %s"%(k,a))				    
			    if self.validate_subArg(a,'plusMinusAverage'):
				self.l_pmaNetworkArgs.append(a)
				break
			    else:
				log.debug("argsToNodes.validateArg>> pma arg found: %s"%a)				    
			except StandardError,error:
			    raise StandardError,error  
		if not foundMatch and '-' in a:
		    foundMatch = True
		    if self.validate_subArg(a,'multiplyDivide'):
			self.l_mdNetworkArgs.append(arg)
			break
		    else:
			log.debug("argsToNodes.validateArg>> inverse check: %s"%arg)
		if not foundMatch and '=' in a:
		    log.debug("Finding direct connect...")
		    if self.validate_subArg(a,'directConnect'):
			self.l_directConnectArgs.append(arg)
			break
		    else:
			log.debug("argsToNodes.validateArg>> inverse check: %s"%arg)
		if not self.d_networksToBuild:
		    raise StandardError,"argsToNodes.validateArg>> Found nothing to do! | %s"%a
	except StandardError,error:
	    raise StandardError,"argsToNodes.validateArg>> arg get error | %s"%error
    def verify_attr(self,arg,nodeType = False,originalArg = False):
	"""
	Check an arg, return an index to the i_attr list after registering
	if necessary or the command if it's a valid driver
	"""
	arg = self.cleanArg(arg)#get rid of pesky spaces that may have made it through
	if nodeType:
	    kws = {}
	    defaultAttrType = d_nodeType_to_DefaultAttrType.get(nodeType) or False
	    if defaultAttrType:
		kws['defaultType'] = defaultAttrType
		log.debug("KWS:   %s"%kws)
		
	if '-' in arg:#Looking for inverses
	    if not originalArg:
		raise StandardError,"argsToNodes.verify_attr>> original arg required with '-' mode!"	    				
	    if not nodeType:
		raise StandardError,"argsToNodes.verify_attr>> nodeType required with '-' mode!"	    		
	    log.debug("argsToNodes.verify_attr>> '-' Mode!: %s"%arg)	    
	    #We have to make a sub attr connection to inverse this value
	    #First register the attr
	    d_driver = cgmMeta.validateAttrArg(arg.split('-')[1],noneValid=True,**kws)
	    
	    if not d_driver:
		raise StandardError,"argsToNodes.verify_attr>> '-' Mode fail!"	    
	    if d_driver['mi_plug'].p_combinedName not in self.l_attrs:
		log.debug("argsToNodes.verify_attr>> Adding: %s"%d_driver['combined'])
		self.l_attrs.append(d_driver['mi_plug'].p_combinedName)		
		self.ml_attrs.append(d_driver['mi_plug'])
		index = len(self.ml_attrs)-1
	    else:
		log.debug("argsToNodes.verify_attr>> Found. Returning index")		
		index = self.l_attrs.index(d_driver['mi_plug'].p_combinedName)#return the index
	    
	    d_validSubArg = {'arg':self.cleanArg(arg),'callArg':originalArg,'drivers':[index,'-1'],'operation':1}
	    self.d_networksToBuild['multiplyDivide'].append(d_validSubArg)#append to build
	    return unicode(self.cleanArg(arg))#unicoding for easy type check on later call
	
	arg_isNumber = True#Simple check to see if this part of the arg is a number
	try:float(arg)
	except:arg_isNumber = False
	
	if arg_isNumber:
	    for i in range(9):
		if str(i) in arg:
		    log.debug("argsToNodes.verify_driver>> Valid string driver: %s"%arg)				    
		    return self.cleanArg(arg)
	else:
	    d_driver = cgmMeta.validateAttrArg(arg,noneValid=False,**kws)
	    log.debug("verify_attr>> d_driver: %s"%d_driver)
	    if d_driver['mi_plug'].p_combinedName not in self.l_attrs:
		log.debug("argsToNodes.verify_attr>> Adding: %s"%d_driver['combined'])
		self.l_attrs.append(d_driver['mi_plug'].p_combinedName)		
		self.ml_attrs.append(d_driver['mi_plug'])
		return len(self.l_attrs)-1
	    else:
		log.debug("argsToNodes.verify_attr>> Found. Returning index")		
		return self.l_attrs.index(d_driver['mi_plug'].p_combinedName)#return the index
	
	log.debug("argsToNodes.verify_driver>> Invalid Driver: %s"%arg)		
	return None
	
    def validate_subArg(self,arg, nodeType = 'condition'):
	log.debug("argsToNodes.validate_subArg>> '%s' validate: '%s'"%(nodeType,arg))
	#First look for a result connection to register
	if nodeType != 'directConnect' and nodeType not in d_operator_to_NodeType.keys():
	    raise StandardError,"argsToNodes.validate_subArg>> unknown nodeType: '%s'"%nodeType
	resultArg = []
	thenArg = []
	log.debug(1)
	try:#Result split
	    #splitter = d_nodeType_to_resultSplit[nodeType]
	    splitter = ' = '
	    if splitter in arg:
		spaceSplit = arg.split(' ')
		splitBuffer = arg.split(splitter)#split by ';'
		if len(splitBuffer)>2:
		    raise StandardError,"argsToNodes.validate_subArg>> Too many splits for arg: %s"%splitBuffer		
		resultArg = splitBuffer[0]
		arg = splitBuffer[1]
		log.debug("argsToNodes.validate_subArg>> result args: %s"%resultArg)
	except StandardError,error:
	    log.error(error)
	    raise StandardError, "argsToNodes.validate_subArg>> resultSplit failure: %s"%(arg)
	
	try:#If then
	    for nodeT in ['clamp','setRange']:
		if nodeType == nodeT:
		    firstSplit = arg.split('%s('%nodeT)
		    arg = firstSplit[1]
		    secondSplit = arg.split(')')
		    arg = secondSplit[0]
	    if nodeType == 'condition' and ':' in arg:
		thenSplit = arg.split(':')
		if len(thenSplit)>2:
		    raise StandardError,"argsToNodes.validate_subArg>> Too many thenSplits for arg: ':' | %s"%thenSplit	
		thenArg = thenSplit[1]
		arg = thenSplit[0]	    
	except StandardError,error:
	    log.error(error)
	    raise StandardError, "argsToNodes.validate_subArg>> thenSplit failure: %s"%(arg)
	
	    
	try:#Function Split
	    log.debug("argsToNodes.validate_subArg>> %s validate: '%s'"%(nodeType,arg))
	    l_buffer = arg.split(' ')#split by space
	    log.debug("l_buffer: %s"%l_buffer)
	    splitBuffer = []
	    for n in l_buffer:
		if n !='':
		    splitBuffer.append(n)#get rid of ''
	    l_funcs = []
	    if nodeType not in ['directConnect','clamp','setRange']:
		for function in d_operator_to_NodeType[nodeType]:
		    if function in arg:#See if we have the function
			if len(arg.split(function))>2 and nodeType == 'condition':
			     raise StandardError,"argsToNodes.validate_subArg>> Bad arg. Too many functions in arg: %s"%(function)
			l_funcs.append(function)
	    elif nodeType in ['clamp','setRange']:
		splitBuffer = arg.split(',')
		log.debug("clamp type split: %s"%splitBuffer)	
	    if not l_funcs and '-' not in arg and nodeType not in ['directConnect','setRange','clamp']:
		raise StandardError, "argsToNodes.validate_subArg>> No function of type '%s' found: %s"%(nodeType,d_operator_to_NodeType[nodeType])	    
	    elif len(l_funcs)!=1 and '-' not in arg and nodeType not in ['directConnect','setRange','clamp']:#this is to grab an simple inversion
		log.warning("argsToNodes.validate_subArg>> Bad arg. Too many functions in arg: %s"%(l_funcs))
	    if l_funcs:l_funcs = [l_funcs[0].split(' ')[1]]
	except StandardError,error:
	    log.error(error)
	    raise StandardError, "argsToNodes.validate_subArg>> functionSplit failure: %s"%(arg)
	
	log.debug("validate_subArg>> l_funcs: %s"%l_funcs)
	log.debug("validate_subArg>> splitBuffer: %s"%splitBuffer)
	try:#Validate our function factors
	    l_drivers = []
	    if l_funcs:
		first = True
		for i,n in enumerate(splitBuffer):
		    if n == l_funcs[0]:#if it's our func, grab the one one before and after
			if first:
			    l_drivers.append(splitBuffer[i-1])	
			    first = False			    
			l_drivers.append(splitBuffer[i+1])
	    elif nodeType in ['clamp','setRange']:
		l_drivers = splitBuffer
	    else:
		l_drivers.append(splitBuffer[0])
		
	    l_validDrivers = []
	    for d in l_drivers:
		log.debug("Checking driver: %s"%d)
		d_return = self.verify_attr(d,nodeType,arg)
		if d_return is None:raise StandardError, "argsToNodes.validate_subArg>> driver failure: %s"%(d)
		else:l_validDrivers.append(d_return)
	    
	    log.debug("l_validDrivers: %s"%l_validDrivers)
	    #need to rework for more drivers
	    if nodeType != 'directConnect':
		maxDrivers = d_nodeType_to_limits[nodeType].get('maxDrivers')
		if maxDrivers and len(l_validDrivers)>maxDrivers:
		    raise StandardError, "argsToNodes.validate_subArg>> Too many drivers (max - %s): %s"%(maxDrivers,l_validDrivers)
	    
	    if l_funcs:#we  use normal start
		d_validArg = {'arg':self.cleanArg(arg),'oldArg':arg,'drivers':l_validDrivers,'operation':d_function_to_Operator[l_funcs[0]]}
	    elif nodeType in ['directConnect','clamp','setRange']:
		d_validArg = {'arg':self.cleanArg(arg),'oldArg':arg,'drivers':l_validDrivers}		
	    else:#we have a special case
		d_validArg = {'arg':self.cleanArg(arg),'oldArg':arg}		
	    log.debug("argsToNodes.validate_subArg>> Drivers: %s"%(l_validDrivers))
	
	except StandardError,error:
	    log.error(error)
	    raise StandardError, "argsToNodes.validate_subArg>> sub arg failure: %s"%(arg)
    
	then_indices = []
	if thenArg:
	    log.debug("Then arg: %s"%thenArg)	    
	    if 'else' in thenArg:
		thenBuffer = thenArg.split('else')
	    else:
		thenBuffer = [thenArg]
	    if len(thenBuffer)>2:
		raise StandardError, "argsToNodes.validate_subArg>> thenBuffer > 2: %s"%(thenBuffer)		
	    for arg in thenBuffer:
		#try to validate
		a_return = self.verify_attr(arg,nodeType)
		if a_return is not None:
		    then_indices.append(a_return)
	    for i,n in enumerate(then_indices):
		if i==0:
		    d_validArg['True']=n
		else:
		    d_validArg['False']=n		    
		
	try:#Results build
	    results_indices = []
	    if resultArg:
		if ',' in resultArg:
		    resultBuffer = resultArg.split(',')
		else:
		    resultBuffer = [resultArg]
		for arg in resultBuffer:
		    #try to validate
		    a_return = self.verify_attr(arg,nodeType)
		    if a_return is not None:
			if d_validArg.get('drivers') and a_return in d_validArg['drivers']:
			    raise StandardError,"argsToNodes.validate_subArg>> Same attr cannot be in drivers and driven of same node arg!"
			results_indices.append(a_return)
			
	    #Build our arg 
	    if results_indices:
		if d_validArg.get('drivers'):
		    d_validArg['results']=results_indices
		log.debug("argsToNodes.validate_subArg>> Results indices: %s "%(results_indices))	
		self.d_connectionsToMake[d_validArg['arg']] = {'driven':results_indices,'nodeType':nodeType}
	    log.debug("d_validArg: %s"%d_validArg)
	    
	    if d_validArg.get('drivers'):
		if len(d_validArg['drivers']) > 1 and nodeType:#just need a connecton mapped
		    self.d_networksToBuild[nodeType].append(d_validArg)#append to build
		elif nodeType == 'directConnect' and len(d_validArg['drivers']) == 1:
		    self.d_connectionsToMake[d_validArg['arg']]['driver'] = d_validArg['drivers'][0]
		    #self.d_networksToBuild[nodeType].append(d_validArg)#append to build		    
		    #self.d_good_connections[d_validArg['arg']]=self.ml_attrs[d_validArg['drivers'][0]]#store the instance		    
		else:
		    raise StandardError, "argsToNodes.validate_subArg>> Too few drivers : %s"%(l_validDrivers)
	except StandardError,error:
	    log.error(error)
	    raise StandardError, "argsToNodes.validate_subArg>> results build failure: %s"%(arg)
    
	return True
    
    def verify_nodalNetwork(self,d_arg,nodeType = 'condition',fastCheck = True):
	"""
	arg should be in the form of [[int,int],int...int]
	the first arg should always be a pair as the base md node paring, the remainging ones are daiy chained form that
	#Fast check only checks connected nodes and not all nodes of that type
	"""
	def verifyDriver(self,arg):
	    if type(arg) == unicode:
		#We should have already done this one
		if arg not in self.d_good_NetworkOuts.keys():
		    raise StandardError,"Not built yet: '%s'"%arg
		log.debug(arg)
		d = self.ml_attrs[ self.d_good_NetworkOuts[arg] ]
		return d
		
	    elif type(arg) == int:
		d = self.ml_attrs[arg]
		return d
	    elif '.' in arg:
		return float(arg)#Float value
	    else:
		return int(arg)#Int value
	    
	def verifyNode(d_arg,nodeType):
	    """
	    If it doesn't exist, make it, otherwise, register the connection
	    """
	    log.debug("argsToNodes.verifyNode>> Creating: %s | type: %s"%(d_arg,nodeType))
	    ml_drivers = []
	    ml_nodeDrivers = []
	    if not d_arg.get('drivers'):
		return False
	    log.debug("arg from d_arg: %s"%d_arg['arg'])
	    l_driverNames = []
	    try:#Get our drivers
		for v in d_arg['drivers']:
		    if type(v) == unicode:
			#We should have already done this one
			if v not in self.d_good_NetworkOuts.keys():
			    raise StandardError,"Not built yet: '%s'"%v
			log.debug(v)
			d = self.ml_attrs[ self.d_good_NetworkOuts[v] ]
			ml_drivers.append(d)
			ml_nodeDrivers.append(d)
		    elif type(v) == int:
			d = self.ml_attrs[v]
			ml_drivers.append(d)
			ml_nodeDrivers.append(d)			
		    elif '.' in v:
			ml_drivers.append(float(v))#Float value
		    else:
			ml_drivers.append(int(v))#Int value
		log.debug("argsToNodes.verifyNode>> drivers: %s"%ml_drivers )
		log.debug("argsToNodes.verifyNode>> driversNames: %s"%l_driverNames )
	    except StandardError,error:
		log.error("argsToNodes.verifyNode>> arg driver initialiation fail%s")
		raise StandardError,error    
	    
	    i_node= None 
	    
	    #TODO: add verification
	    #See if this connection exists now that we know the connectors.
	    #The goal is to run the exact same command twice and not get new nodes.
	    #First see if we have at least one node type driver to check from as it's fastest
	    l_matchCandidates = {}
	    l_remainingDrivers = []
	    
	    if ml_nodeDrivers:
		for i,d in enumerate(ml_nodeDrivers):
		    if issubclass(type(d),cgmMeta.cgmAttr):
			l_driven = mc.listConnections(d.p_combinedName,type = nodeType)
			if l_driven:#if we have some driven
			    l_matchCandidates = l_driven
			    break
	    if not l_matchCandidates and not fastCheck:
		l_matchCandidates = mc.ls(type=nodeType)
	    log.debug("argsToNodes.verifyNode>> l_matchCandidates: %s"%l_matchCandidates)
	    
	    if l_matchCandidates:
		matchFound = False
		for cnt,n in enumerate(l_matchCandidates):
		    falseCnt = []
		    i_nodeTmp = cgmMeta.cgmNode(n)
		    log.debug('i_nodeTmp: %s'%i_nodeTmp)
		    if d_arg.get('operation') and i_nodeTmp.operation != d_arg['operation']:
			log.debug("argsToNodes.verifyNode>> match fail:operation: %s != %s"%(i_nodeTmp.operation,d_arg['operation']))					    					    			
			matchFound = False	
			falseCnt.append(1)			
			#break
		    for i,d in enumerate(ml_drivers):
			log.debug("Checking driver: %s"%d)
			if issubclass(type(d),cgmMeta.cgmAttr):
			    if nodeType == 'plusMinusAverage':
				plugCall = mc.listConnections("%s.%s[%s]"%(i_nodeTmp.mNode,d_nodeType_to_input[nodeType],i),plugs=True)				
				log.debug("pma plugCall: %s"%plugCall)				
				if plugCall:
				    i_plug = cgmMeta.validateAttrArg(plugCall[0])
				    if i_plug.get('mi_plug'):
					if i_plug['mi_plug'].obj.mNode != d.obj.mNode:
					    log.debug("argsToNodes.verifyNode>> match fail: obj.mNode: %s != %s"%(i_plug['mi_plug'].obj.mNode,d.obj.mNode))					    					    
					    falseCnt.append(1)					    
					    #break
					if i_plug['mi_plug'].p_nameLong != d.p_nameLong:
					    log.debug("argsToNodes.verifyNode>> match fail: p_nameLong: %s != %s"%(i_plug['mi_plug'].p_nameLong,d.p_nameLong))					    					    					    
					    matchFound = False	
					    falseCnt.append(1)					    
					    #break
				else:
				    #We should have had a driver connection for a match
				    log.debug("argsToNodes.verifyNode>> should have had connections")					    					    					    
				    matchFound = False	
				    falseCnt.append(1)					    
			    else:
				plugCall = mc.listConnections("%s.%s"%(i_nodeTmp.mNode,d_nodeType_to_input[nodeType][i]),plugs=True)
				log.debug("plugCall: %s"%plugCall)
				if plugCall:
				    i_plug = cgmMeta.validateAttrArg(plugCall[0])
				    if i_plug.get('mi_plug'):
					if i_plug['mi_plug'].obj.mNode != d.obj.mNode:
					    log.debug("argsToNodes.verifyNode>> match fail: obj.mNode: %s != %s"%(i_plug['mi_plug'].obj.mNode,d.obj.mNode))					    
					    matchFound = False	
					    falseCnt.append(1)					    					    
					    #break
					if i_plug['mi_plug'].p_nameLong != d.p_nameLong:
					    log.debug("argsToNodes.verifyNode>> match fail: p_nameLong: %s != %s"%(i_plug['mi_plug'].p_nameLong,d.p_nameLong))					    					    
					    matchFound = False	
					    falseCnt.append(1)					    
					    #break
				else:
				    #We should have had a driver connection for a match
				    log.debug("argsToNodes.verifyNode>> should have had connections")					    					    					    
				    matchFound = False	
				    falseCnt.append(1)	
				#d.doConnectOut("%s.%s"%(i_node.mNode,d_nodeType_to_input[nodeType][i]))
			else:
			    if nodeType == 'plusMinusAverage':
				v = mc.getAttr("%s.input1D[%s]"%(i_nodeTmp.mNode,i))
				log.debug("%s.input1D[%s]"%(i_nodeTmp.mNode,i))
				log.debug("d: %s"%d)												
				log.debug("pma v: %s"%v)
				if not cgmMath.isFloatEquivalent(v,d):
				    log.debug("argsToNodes.verifyNode>> match fail: getAttr: %s != %s"%(v,d))
				    matchFound = False	
				    falseCnt.append(1)				    
				    #break
			    else:
				v = mc.getAttr("%s.%s"%(i_nodeTmp.mNode,d_nodeType_to_input[nodeType][i]))
				log.debug("d: %s"%d)								
				log.debug("v: %s"%v)				
				if not cgmMath.isFloatEquivalent(v,d):
				    log.debug("argsToNodes.verifyNode>> match fail: getAttr: %s != %s"%(v,d))
				    matchFound = False	
				    falseCnt.append(1)				    
				    #break	
		    log.debug("falseCnt: %s"%falseCnt)
		    if falseCnt:
			log.debug("Driver %s failed for '%s'"%(d,i_nodeTmp.getShortName()))
		    if not falseCnt:
			matchFound=True
			break#If we got this point, we're good
		if matchFound:
		    log.debug("Match found: %s"%i_nodeTmp.mNode)
		    i_node = i_nodeTmp
			
	    if i_node is None:
		i_node = cgmMeta.cgmNode(nodeType = nodeType)#make the node
		try:
		    if d_arg.get('operation'):i_node.operation = d_arg['operation']
		except:raise StandardError,"Failed to set operation!"
		
		#Name it  
		#if d_arg.get('callArg'):key = d_arg.get('callArg')
		buffer = d_arg['arg']
		#buffer = "_to_".join(l_driverNames)
		l_buffer = []
		for k in d_functionStringSwaps.keys():
		    if k in buffer:
			for i,n in enumerate(buffer.split(' ')):
			    for k in d_functionStringSwaps.keys():
				if n == k:n = d_functionStringSwaps[k]
			    if '.' in n:
				n = '_'.join(n.split('.'))
			    if ',' in n:
				n = '_'.join(n.split(','))
			    if '-' in n:
				b = list(n)
				for p,k in enumerate(b):
				    if k == '-':
					b[p]='_inv'				    
				n = ''.join(b)
			    l_buffer.append(n)
			
			break
		log.debug(l_buffer)
		if not l_buffer:l_buffer = buffer
		try:
		    if int(l_buffer[0]) in range(10):
			l_buffer.insert(0,'_')
		except:pass
		i_node.doStore('cgmName',"%s"%("".join(l_buffer)))
		i_node.doStore('creationArg',"%s"%d_arg['arg'])		
		i_node.doName()
		
		
		if nodeType == 'condition':
		    log.debug("d_arg: %s"%d_arg)
		    if d_arg.get('True') is not None:
			d = verifyDriver(self,d_arg.get('True'))			
			log.debug("True arg: %s"%d_arg.get('True'))
			log.debug("True verified to: %s"%verifyDriver(self,d_arg.get('True')))
			if issubclass(type(d),cgmMeta.cgmAttr):
			    d.doConnectOut("%s.colorIfTrueR"%(i_node.mNode))			    			    
			else:
			    mc.setAttr("%s.colorIfTrueR"%(i_node.mNode),d)			
			#i_node.colorIfTrueR = verifyDriver(self,d_arg.get('True'))
		    else:i_node.colorIfTrueR = 1
		    if d_arg.get('False') is not None:
			d = verifyDriver(self,d_arg.get('False'))
			log.debug("False arg: %s"%d_arg.get('False'))
			log.debug("False verified to: %s"%verifyDriver(self,d_arg.get('False')))	
			if issubclass(type(d),cgmMeta.cgmAttr):
			    d.doConnectOut("%s.colorIfFalseR"%(i_node.mNode))			    			    
			else:
			    mc.setAttr("%s.colorIfFalseR"%(i_node.mNode),d)						
			#i_node.colorIfTrueR = verifyDriver(self,d_arg.get('False'))		    
		    else:i_node.colorIfFalseR = 0
		    
		    
		#Make our connections
		for i,d in enumerate(ml_drivers):
		    if issubclass(type(d),cgmMeta.cgmAttr):
			if nodeType == 'plusMinusAverage':
			    d.doConnectOut("%s.%s[%s]"%(i_node.mNode,d_nodeType_to_input[nodeType],i))			    
			else:
			    d.doConnectOut("%s.%s"%(i_node.mNode,d_nodeType_to_input[nodeType][i]))
		    else:
			if nodeType == 'plusMinusAverage':
			    mc.setAttr("%s.%s[%s]"%(i_node.mNode,d_nodeType_to_input[nodeType],i),d)		
			else:
			    mc.setAttr("%s.%s"%(i_node.mNode,d_nodeType_to_input[nodeType][i]),d)
			

		
	    #Store to our good network and the output attr
	    #if d_arg.get('callArg'):key = d_arg.get('callArg')
	    key = d_arg.get('arg')
	    self.l_good_nodeNetworks.append(key)#append it to get our index lib
	    index = self.l_good_nodeNetworks.index(key)#get index
	    log.debug("Storing: %s"%i_node)
	    log.debug("To: %s"%key)
	    log.debug("self.l_good_nodeNetworks: %s"%self.l_good_nodeNetworks)	    
	    self.d_good_nodeNetworks[key]=i_node#store the instance
	    log.debug(self.d_good_nodeNetworks)
	    
	    #register our out plug
	    index = self.verify_attr("%s.%s"%(i_node.mNode,d_nodeType_to_output[nodeType]),key)
	    self.d_good_NetworkOuts[key] = index
	    
	log.debug("argsToNodes>> verify_nodalNetwork: %s"%d_arg)
	if type(d_arg) is not dict:
	    log.error("verify_nodalNetwork args must be a dict")
	    return False	    
	
	i_nodeBuffer = False
	self.outAttrIndex = None
	
	#Need to add check to see if the network exists from sourc
	if d_arg not in self.l_good_nodeNetworks:
	    log.debug("argsToNodes>> Checking: %s"%d_arg)
	    verifyNode(d_arg,nodeType)
	    
	"""
	if self.i_mdOutAttrIndex is not None:#Register our connection to make
	    log.debug("adding connection: %s = [%s]"%(self.i_mdOutAttrIndex,buildNetworkIndex))
	    self.d_connectionsToMake[self.i_mdOutAttrIndex]=[buildNetworkIndex]"""
	   

def test_argsToNodes(deleteObj = True):
    """
    arg = "worldCenter_loc.condResult = if worldCenter_loc.ty == 3:5 else 2"#Working
    """
    i_obj = cgmMeta.cgmObject(name = 'awesomeArgObj_loc')
    str_obj = i_obj.getShortName()
    
    try:#Logic
	arg = "%s.condResult = if %s.ty == 3:5 else 1"%(str_obj,str_obj)
	d_return = argsToNodes(arg).doBuild()
	log.debug(d_return['ml_outPlugs'])
	assert d_return['l_nodes'], "Should have made something"
	assert len(d_return['l_nodes']) == 1, "Only one nodes should be made. Found: %s"%len(d_return['l_nodes'])
	assert d_return['ml_nodes'][0].getMayaType() == 'condition',"%s != condition"%d_return['ml_nodes'][0].getMayaType()
	
	plugCall = mc.listConnections("%s.condResult"%(i_obj.mNode),plugs=True,scn = True)
	assert d_return['ml_nodes'][0].operation == 0, "Operation not 1"	
	combinedName = d_return['ml_outPlugs'][0].p_combinedName
	assert str(plugCall[0]) == d_return['ml_outPlugs'][0].p_combinedName,"Connections don't match: %s | %s"%(plugCall[0],combinedName)
	
	i_obj.ty = 3
	assert i_obj.condResult == 5,"condResult should be 5"
	i_obj.ty = 1
	assert i_obj.condResult == 1,"condResult should be 1"
	
    except StandardError,error:
	log.error("test_argsToNodes>>Condition Failure! '%s'"%(error))
	raise StandardError,error  
    
    try:#Mult inversion
	arg = "%s.inverseMultThree = 3 * -%s.tx"%(str_obj,str_obj)
	d_return = argsToNodes(arg).doBuild()
	log.debug(d_return['ml_outPlugs'])
	assert d_return['l_nodes'], "Should have made something"
	assert len(d_return['l_nodes']) == 2, "Only two nodes should be made. Found: %s"%len(d_return['l_nodes'])
	assert d_return['ml_nodes'][0].getMayaType() == 'multiplyDivide',"%s != md"%d_return['ml_nodes'][0].getMayaType()
	assert d_return['ml_nodes'][1].getMayaType() == 'multiplyDivide',"%s != md"%d_return['ml_nodes'][1].getMayaType()
	
	plugCall = mc.listConnections("%s.inverseMultThree"%(i_obj.mNode),plugs=True,scn = True)
	assert d_return['ml_nodes'][-1].operation == 1, "Operation not 1"	
	combinedName = d_return['ml_outPlugs'][-1].p_combinedName
	assert str(plugCall[0]) == d_return['ml_outPlugs'][-1].p_combinedName,"Connections don't match: %s | %s"%(plugCall[0],combinedName)
	assert i_obj.inverseMultThree == 3* -i_obj.tx,"Inversion doesn't match"
	
    except StandardError,error:
	log.error("test_argsToNodes>>Inversion mult 3 Failure! '%s'"%(error))
	raise StandardError,error      
    
    try:#Simple inversion 
	arg = "%s.simpleInversion = -%s.tx"%(str_obj,str_obj)
	d_return = argsToNodes(arg).doBuild()
	log.debug(d_return['ml_outPlugs'])
	assert d_return['l_nodes'], "Should have made something"
	assert len(d_return['l_nodes']) == 1, "Only one node should be made. Found: %s"%len(d_return['l_nodes'])
	assert d_return['ml_outPlugs'][0].obj.getMayaType() == 'multiplyDivide',"%s != pma"%d_return['ml_outPlugs'][0].obj.getMayaType()
	plugCall = mc.listConnections("%s.simpleInversion"%(i_obj.mNode),plugs=True,scn = True)
	assert d_return['ml_nodes'][0].operation == 1, "Operation not 1"	
	combinedName = d_return['ml_outPlugs'][0].p_combinedName
	assert str(plugCall[0]) == d_return['ml_outPlugs'][0].p_combinedName,"Connections don't match: %s | %s"%(plugCall[0],combinedName)
	assert i_obj.simpleInversion == -i_obj.tx,"Inversion doesn't match"
	
    except StandardError,error:
	log.error("test_argsToNodes>>Simple inversion Failure! '%s'"%(error))
	raise StandardError,error  
    
    try:#Simple Average 
	arg = "%s.sumAverage1 = 4 >< 4 >< 4"%(str_obj)
	d_return = argsToNodes(arg).doBuild()
	assert d_return['l_nodes'], "Should have made something"
	assert len(d_return['l_nodes']) == 1, "Only one node should be made. Found: %s"%len(d_return['l_nodes'])
	assert d_return['ml_outPlugs'][0].obj.getMayaType() == 'plusMinusAverage',"%s != pma"%d_return['ml_outPlugs'][0].obj.getMayaType()
	assert d_return['ml_nodes'][0].operation == 3, "Operation not 3"
	
	assert i_obj.sumAverage1 == 4,"Average is wrong: 4 != %s"%i_obj.sumAverage1
	
    except StandardError,error:
	log.error("test_argsToNodes>>Simple sum Failure! '%s'"%(error))
	raise StandardError,error      
    
    try:#Test direct connect
	arg = "%s.directConnect = %s.ty"%(str_obj,str_obj)
	argsToNodes(arg).doBuild()
	log.debug(mc.listConnections("%s.directConnect"%str_obj,source = True))
	plugCall = mc.listConnections("%s.directConnect"%(i_obj.mNode),plugs=True)	
	assert plugCall[0] == '%s.translateY'%i_obj.getShortName(),log.error("Direct connect failed")
    except StandardError,error:
	log.error("test_argsToNodes>>Single Connect Failure! '%s'"%(error))
	raise StandardError,error   
    
    try:#Multi direct connect
	arg = "%s.directConnect, %s.ry = %s.ty"%(str_obj,str_obj,str_obj)
	argsToNodes(arg).doBuild()
	log.debug(mc.listConnections("%s.directConnect"%str_obj,source = True))
	plugCall = mc.listConnections("%s.directConnect"%(i_obj.mNode),plugs=True)	
	assert plugCall[0] == '%s.translateY'%i_obj.getShortName(),log.error("Direct connect failed: directConnect")
	plugCall = mc.listConnections("%s.rotateY"%(i_obj.mNode),plugs=True,scn = True)	
	log.debug(plugCall)
	assert plugCall[0] == '%s.translateY'%i_obj.getShortName(),log.error("Direct connect failed: rotateY")
	
    except StandardError,error:
	log.error("test_argsToNodes>>Multi Connect Failure! '%s'"%(error))
	raise StandardError,error  
    
    try:#Simple sum 
	i_obj.tx = 1
	i_obj.ty = 2
	i_obj.tz = 3
	arg = "%s.sumResult1 = %s.tx - %s.ty - %s.tz"%(str_obj,str_obj,str_obj,str_obj)
	d_return = argsToNodes(arg).doBuild()
	log.debug(d_return['ml_outPlugs'])
	assert d_return['l_nodes'], "Should have made something"
	assert len(d_return['l_nodes']) == 1, "Only one node should be made. Found: %s"%len(d_return['l_nodes'])
	assert d_return['ml_outPlugs'][0].obj.getMayaType() == 'plusMinusAverage',"%s != pma"%d_return['ml_outPlugs'][0].obj.getMayaType()
	plugCall = mc.listConnections("%s.sumResult1"%(i_obj.mNode),plugs=True,scn = True)
	assert d_return['ml_nodes'][0].operation == 2, "Operation not 2"	
	combinedName = d_return['ml_outPlugs'][0].p_combinedName
	assert str(plugCall[0]) == d_return['ml_outPlugs'][0].p_combinedName,"Connections don't match: %s | %s"%(plugCall[0],combinedName)
	assert i_obj.sumResult1 == i_obj.tx - i_obj.ty - i_obj.tz,"Sum doesn't match"
	
    except StandardError,error:
	log.error("test_argsToNodes>>Simple sum Failure! '%s'"%(error))
	raise StandardError,error   
    
    try:#clamp 
	i_obj.tz = 3
	arg = "%s.clampResult = clamp(0,1,%s.tz"%(str_obj,str_obj)
	d_return = argsToNodes(arg).doBuild()
	log.debug(d_return['ml_outPlugs'])
	assert d_return['l_nodes'], "Should have made something"
	assert len(d_return['l_nodes']) == 1, "Only one node should be made. Found: %s"%len(d_return['l_nodes'])
	assert d_return['ml_outPlugs'][0].obj.getMayaType() == 'clamp',"%s != clamp"%d_return['ml_outPlugs'][0].obj.getMayaType()
	plugCall = mc.listConnections("%s.clampResult"%(i_obj.mNode),plugs=True,scn = True)
	combinedName = d_return['ml_outPlugs'][0].p_combinedName
	assert str(plugCall[0]) == d_return['ml_outPlugs'][0].p_combinedName,"Connections don't match: %s | %s"%(plugCall[0],combinedName)
	assert i_obj.clampResult == 1,"Value 1 fail"
	i_obj.tz = .5
	assert i_obj.clampResult == .5,"Value 2 fail"
	
    except StandardError,error:
	log.error("test_argsToNodes>>Clamp fail! '%s'"%(error))
	raise StandardError,error       
    
    try:#setRange 
	i_obj.tz = 5
	arg = "%s.setRangeResult = setRange(0,1,0,10,%s.tz"%(str_obj,str_obj)
	d_return = argsToNodes(arg).doBuild()
	log.debug(d_return['ml_outPlugs'])
	assert d_return['l_nodes'], "Should have made something"
	assert len(d_return['l_nodes']) == 1, "Only one node should be made. Found: %s"%len(d_return['l_nodes'])
	assert d_return['ml_outPlugs'][0].obj.getMayaType() == 'setRange',"%s != setRange"%d_return['ml_outPlugs'][0].obj.getMayaType()
	plugCall = mc.listConnections("%s.setRangeResult"%(i_obj.mNode),plugs=True,scn = True)
	combinedName = d_return['ml_outPlugs'][0].p_combinedName
	assert str(plugCall[0]) == d_return['ml_outPlugs'][0].p_combinedName,"Connections don't match: %s | %s"%(plugCall[0],combinedName)
	assert i_obj.setRangeResult == .5,"Value 1 fail"
	i_obj.tz = 10
	assert i_obj.setRangeResult == 1,"Value 2 fail"
	
    except StandardError,error:
	log.error("test_argsToNodes>>setRangeResult failure! '%s'"%(error))
	raise StandardError,error   
    
    if deleteObj:i_obj.delete()
    """
    for arg in ["awesomeArgObj_loc.tx + awesomeArgObj_loc.ty + awesomeArgObj_loc.tz = awesomeArgObj_loc.sumResult1",
                "1 + 2 + 3 = awesomeArgObj_loc.simpleSum",#Working
                "1 >< 2 >< 3 = awesomeArgObj_loc.simpleAv",#Working
                "3 * -awesomeArgObj_loc.ty = awesomeArgObj_loc.inverseMultThree",#Working
                "4 - 2 = awesomeArgObj_loc.simpleMathResult",#Working
                "-awesomeArgObj_loc.ty = awesomeArgObj_loc.ty",#Working
                "awesomeArgObj_loc.ty * 3 = awesomeArgObj_loc.multResult",#Working
                "awesomeArgObj_loc.ty + 3 + awesomeArgObj_loc.ty = awesomeArgObj_loc.sumResult",#Working
                "if awesomeArgObj_loc.ty > 3;awesomeArgObj_loc.result2"]:
	try:nodeF.argsToNodes(arg).doBuild()
	except StandardError,error:
	    log.error("test_argsToNodes>>arg fail! %s"%arg)
	    raise StandardError,error  """

class build_conditionNetworkFromGroup(object):
    def __init__(self, group, chooseAttr = 'switcher', controlObject = None, connectTo = 'visibility',*args,**kws):
	"""Constructor"""
	self.d_iAttrs = {}#attr instances stores as {index:instance}
	self.l_iAttrs = []#Indices for iAttrs
	self.d_resultNetworksToBuild = {}#Index desctiptions of networks to build {target:[[1,2],3]}
	self.i_group = False
	self.i_control = False
	self.connectToAttr = connectTo
	self.i_attr = False
	
        #>>>Keyword args	
        log.debug(">>> build_conditionNetworkFromGroup.__init__")
	if kws:log.debug("kws: %s"%str(kws))
	if args:log.debug("args: %s"%str(args))
	
	#Check our group
	if not mc.objExists(group):
	    log.error("Group doesn't exist: '%s'"%group)
	    return
	elif not search.returnObjectType(group) == 'group':
	    log.error("Object is not a group: '%s'"%search.returnObjectType(group))
	    return
	self.i_group = cgmMeta.cgmObject(group)
	if not self.i_group.getChildren():
	    log.error("No children detected: '%s'"%group)
	    return	
	
	#Check our control
	if controlObject is None or not mc.objExists(controlObject):
	    log.error("No suitable control object found: '%s'"%controlObject)
	    return
	else:
	    i_controlObject = cgmMeta.cgmNode(controlObject)
	    self.i_attr = cgmMeta.cgmAttr(i_controlObject,chooseAttr,attrType = 'enum',initialValue = 1)
	if self.buildNetwork(*args,**kws):
	    log.debug("Chooser Network good to go")
	
    def buildNetwork(self,*args,**kws):
	if kws:log.debug("kws: %s"%str(kws))
	if args:log.debug("args: %s"%str(args))
	
	children = self.i_group.getChildren()
	children.insert(0,'none')
	
	#Make our attr
	if len(children) == 2:
	    self.i_attr.doConvert('bool')#Like bool better
	    #self.i_attr.setEnum('off:on')
	else:
	    self.i_attr.setEnum(':'.join(children))
	
	for i,c in enumerate(children[1:]):
	    i_c = cgmMeta.cgmNode(c)
	    #see if the node exists
	    condNodeTest = attributes.returnDriverObject('%s.%s'%(c,self.connectToAttr))
	    if condNodeTest:
		i_node = cgmMeta.cgmNode(condNodeTest)
	    else:
		if mc.objExists('%s_condNode'%c):
		    mc.delete('%s_condNode'%c)
		i_node = cgmMeta.cgmNode(name = 'tmp', nodeType = 'condition') #Make our node
	    
	    i_node.addAttr('cgmName', i_c.getShortName(), attrType = 'string')
	    i_node.addAttr('cgmType','condNode')
	    i_node.doName()
	    i_node.secondTerm = i+1
	    attributes.doSetAttr(i_node.mNode,'colorIfTrueR',1)
	    attributes.doSetAttr(i_node.mNode,'colorIfFalseR',0)
	    #i_node.colorIfTrueR = 1
	    #i_node.colorIfTrueR = 0
	    
	    self.i_attr.doConnectOut('%s.firstTerm'%i_node.mNode)
	    attributes.doConnectAttr('%s.outColorR'%i_node.mNode,'%s.%s'%(c,self.connectToAttr))
	
	return True
		
def createAverageNode(drivers,driven = None,operation = 3):
    #Create the mdNode
    log.debug(1)    
    if type(drivers) not in [list,tuple]:raise StandardError,"createAverageNode>>> drivers arg must be list"
    l_driverReturns = []
    for d in drivers:
	l_driverReturns.append(cgmMeta.validateAttrArg(d))
    d_driven = False
    if driven is not None:
	d_driven = cgmMeta.validateAttrArg(driven)
    
    if d_driven:
	drivenCombined =  d_driven['combined']
	log.debug("drivenCombined: %s"%drivenCombined)
    log.debug(2)
    #Create the node
    i_pma = cgmMeta.cgmNode(mc.createNode('plusMinusAverage'))
    i_pma.operation = operation
    l_objs = []
    #Make our connections
    for i,d in enumerate(l_driverReturns):
	log.debug("Driver %s: %s"%(i,d['combined']))
	attributes.doConnectAttr(d['combined'],'%s.input1D[%s]'%(i_pma.mNode,i),True)
	l_objs.append(mc.ls(d['obj'],sn = True)[0])#Get the name
    log.debug(3)
    
    i_pma.addAttr('cgmName',"_".join(l_objs),lock=True)	
    i_pma.addAttr('cgmTypeModifier','twist',lock=True)
    i_pma.doName()

    if driven is not None:
	attributes.doConnectAttr('%s.output1D'%i_pma.mNode,drivenCombined,True)
	
    return i_pma

def groupToConditionNodeSet(group,chooseAttr = 'switcher', controlObject = None, connectTo = 'visibility'):
    """
    Hack job for the gig to make a visibility switcher for all the first level of children of a group
    """
    children = search.returnChildrenObjects(group) #Check for children

    if not children: #If none, break out
	guiFactory("'%s' has no children! Aborted."%group)
	return False
    if controlObject is None:
	controlObject = group
    
    #Make our attr
    a = AttrFactory.AttrFactory(controlObject,chooseAttr,'enum')
    children.insert(0,'none')
    print children
    if len(children) == 2:
	a.setEnum('off:on')
    else:
	a.setEnum(':'.join(children))
    
    for i,c in enumerate(children[1:]):
	#print i
	#print c
	#see if the node exists
	condNodeTest = attributes.returnDriverObject('%s.%s'%(c,connectTo))
	if condNodeTest:
	    buffer = condNodeTest
	else:
	    if mc.objExists('%s_condNode'%c):
		mc.delete('%s_condNode'%c)
	    buffer = nodes.createNamedNode('%s_picker'%c,'condition') #Make our node
	#print buffer
	attributes.doSetAttr(buffer,'secondTerm',i+1)
	attributes.doSetAttr(buffer,'colorIfTrueR',1)
	attributes.doSetAttr(buffer,'colorIfFalseR',0)
	
	a.doConnectOut('%s.firstTerm'%buffer)
	attributes.doConnectAttr('%s.outColorR'%buffer,'%s.%s'%(c,connectTo))