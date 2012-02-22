#=================================================================================================================================================
#=================================================================================================================================================
#	guiFactory - a part of rigger
#=================================================================================================================================================
#=================================================================================================================================================
# 
# DESCRIPTION:
#   Tool to make standard guis for our tools
# 
# REQUIRES:
#   Maya
# 
# AUTHOR:
# 	Josh Burton (under the supervision of python guru (and good friend) David Bokser) - jjburton@gmail.com
#	http://www.joshburton.com
# 	Copyright 2011 Josh Burton - All Rights Reserved.
# 
# CHANGELOG:
#	0.1.12042011 - First version
#	0.1.12072011 - Added progress tracking
#
#=================================================================================================================================================
import maya.cmds as mc
import maya.mel as mel

from cgmBaseMelUI import *

mayaVersion = int(mc.about(file=True))

# Maya version check
if mayaVersion >= 2011:
    currentGenUI = True
else:
    currentGenUI = False

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Define our Colors
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Define our Templates
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
def initializeTemplates():
    guiBackgroundColor = [.45,.45,.45]
    guiHeaderColor = [.2,.2,.2]
    guiSubMenuColor = [.65,.65,.65]
    guiButtonColor = [.3,.3,.3]
    #guiHelpBackgroundColor = [ 0.89, 0.89, 0.89]
    guiHelpBackgroundColor = [0.8, 0.8, 0.8]
    #guiHelpBackgroundReservedColor = [0.392157, 0.392157, 0.392157]
    #guiHelpBackgroundLockedColor = [ 0.568627, 0, 0.0100545]
    #guiHelpBackgroundLockedColor = [ .5, .2, 0.1]
    guiHelpBackgroundReservedColor = [0.411765 , 0.411765 , 0.411765]
    guiHelpBackgroundLockedColor = [0.837, 0.399528, 0.01674]

    if mc.uiTemplate( 'cgmUITemplate', exists=True ):
        mc.deleteUI( 'cgmUITemplate', uiTemplate=True )
    mc.uiTemplate('cgmUITemplate')
    mc.separator(dt='cgmUITemplate', height = 10, style = 'none')
    mc.button(dt = 'cgmUITemplate', backgroundColor = guiButtonColor)
    mc.window(dt = 'cgmUITemplate', backgroundColor = guiBackgroundColor)
    mc.textField(dt = 'cgmUITemplate', backgroundColor = [1,1,1])
    mc.optionMenu(dt='cgmUITemplate',backgroundColor = guiButtonColor)
    mc.optionMenuGrp(dt ='cgmUITemplate', backgroundColor = guiButtonColor)

    # Define our header template
    if mc.uiTemplate( 'cgmUIHeaderTemplate', exists=True ):
        mc.deleteUI( 'cgmUIHeaderTemplate', uiTemplate=True )
    mc.uiTemplate('cgmUIHeaderTemplate')
    mc.text(dt='cgmUIHeaderTemplate', backgroundColor = guiHeaderColor)
    mc.separator(dt='cgmUIHeaderTemplate', height = 5, style = 'none',backgroundColor = guiHeaderColor)


    # Define our sub template
    if mc.uiTemplate( 'cgmUISubTemplate', exists=True ):
        mc.deleteUI( 'cgmUISubTemplate', uiTemplate=True )
    mc.uiTemplate('cgmUISubTemplate')
    mc.formLayout(dt='cgmUISubTemplate', backgroundColor = guiSubMenuColor)
    mc.text(dt='cgmUISubTemplate', backgroundColor = guiSubMenuColor)
    mc.separator(dt='cgmUISubTemplate', height = 2, style = 'none', backgroundColor = guiSubMenuColor)
    mc.rowLayout(dt='cgmUISubTemplate', backgroundColor = guiSubMenuColor)
    mc.rowColumnLayout(dt='cgmUISubTemplate', backgroundColor = guiSubMenuColor)
    mc.columnLayout(dt='cgmUISubTemplate', backgroundColor = guiSubMenuColor)

    # Define our instructional template
    if mc.uiTemplate( 'cgmUIInstructionsTemplate', exists=True ):
        mc.deleteUI( 'cgmUIInstructionsTemplate', uiTemplate=True )
    mc.uiTemplate('cgmUIInstructionsTemplate')
    mc.text(dt = 'cgmUIInstructionsTemplate', backgroundColor = guiHelpBackgroundColor)

    # Define our Reserved 
    if mc.uiTemplate( 'cgmUIReservedTemplate', exists=True ):
        mc.deleteUI( 'cgmUIReservedTemplate', uiTemplate=True )
    mc.uiTemplate('cgmUIReservedTemplate')
    mc.textField(dt = 'cgmUIReservedTemplate', backgroundColor = guiHelpBackgroundReservedColor)

    # Define our Locked 
    if mc.uiTemplate( 'cgmUILockedTemplate', exists=True ):
        mc.deleteUI( 'cgmUILockedTemplate', uiTemplate=True )
    mc.uiTemplate('cgmUILockedTemplate')
    mc.textField(dt = 'cgmUILockedTemplate', backgroundColor = guiHelpBackgroundLockedColor)


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Menu and sub menu functions
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
def returnWindowLayout(win):
    controls = mc.lsUI(l=True,controlLayouts=True)
    winControls = []
    if controls:
        for control in controls:
            if win in control:
                winControls.append(control)
    return winControls

def doOptionMenuList(optionList):
    optionMenuItem = mc.optionMenu( ut ='cgmUITemplate' )
    returnList = []
    for item in optionList:
        returnList.append( mc.menuItem(label=item) )
    return [optionMenuItem,returnList]


def doOptionMenuGroupList(label,optionList, extraLabel = False):
    if extraLabel:
        optionMenuItem = mc.optionMenuGrp(label = label, ut ='cgmUITemplate', extraLabel = extraLabel )
    else:
        optionMenuItem = mc.optionMenuGrp(label = label, ut ='cgmUITemplate' )
    returnList = []
    for item in optionList:
        returnList.append( mc.menuItem(label=item) )
    return [optionMenuItem,returnList]

def doCheckGrp(label = 'Text here',checked = False):
    columnWidth = (len(list(label)) * 10)
    buffer = mc.checkBoxGrp( label=label, cw=[1,columnWidth], adjustableColumn = 2, columnAttach2 = ['left','right'], width = 100)
    if defaultText:
        mc.checkBoxGrp(buffer, edit=True, text=defaultText)
    return buffer

def doRadioButtonMenuList(optionList,defaultItemIndex = 0):
    """
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    DESCRIPTION:
    makes a menu list from an option list. Example usage:

    fontList = ['Arial','Times']
    fontMenuItems = guiFactory.doRadioButtonMenuList(fontList)
    for item in fontMenuItems:
    cnt = fontMenuItems.index(item)
    mc.menuItem(item, edit=True, command=('%s%s%s' %("cgmRiggingToolsWin.textObjectFont = '",fontList[cnt],"'")) ) 


    REQUIRES:
    optionList(list) - list of options
    defaultItemIndex(int) - what you want the default option to be (defaults to 0)

    RETURNS:
    menuList(list)
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>    
    """
    returnList = []
    cnt = 0
    for item in optionList:
        if cnt == defaultItemIndex:
            returnList.append( mc.menuItem( label=item, rb=True) ) 
        else:
            returnList.append( mc.menuItem( label=item, rb=False) )
        cnt += 1
    return returnList

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Standard functions
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
def warning(message):
    try:
        mc.warning(message)
    except:
        if "'" in list(message):
            mel.eval('%s%s%s' %("$messageVar =  '", message,"'")) 
        else:
            mel.eval('%s%s%s' %('$messageVar =  "', message,'"')) 
        mel.eval('warning $messageVar')

def doWindow(winName,toolName,menuBarOption = True, toolBoxOption = False, sizeableOption = True, widthHeightOption = (255,400), minimizeButtonOption = False, maximizeButtonOption = False, iconNameOption = 'shortName'):
    if currentGenUI:
        return mc.window(winName, title= toolName, menuBar = menuBarOption, toolbox = toolBoxOption, sizeable = sizeableOption,widthHeight = widthHeightOption, minimizeButton = minimizeButtonOption, maximizeButton = maximizeButtonOption, iconName=iconNameOption, backgroundColor = [.45,.45,.45],resizeToFitChildren=True)
    else:
        return mc.window(winName, title= toolName, menuBar = menuBarOption, toolbox = toolBoxOption, sizeable = sizeableOption, widthHeight = widthHeightOption, minimizeButton = minimizeButtonOption, maximizeButton = maximizeButtonOption, iconName=iconNameOption)

def resetUI(uiModule, uiWindow):    
    mc.deleteUI(uiWindow, window=True)
    import uiModule
    uiModule.run()
    #print ('%s%s%s%s%s%s%s' %("'python(","'",uiWin,' = ',uiModule,".toolUI()')","'"))
    #mel.eval('%s%s%s%s%s%s%s' %("'python(","'",uiWin,' = ',uiModule,".toolUI()')","'"))

def showAbout(uiWin):
    window = mc.window( title="About", iconName='About', widthHeight=(200, 55),backgroundColor = guiBackgroundColor )
    mc.columnLayout( adjustableColumn=True )
    mc.text(label=uiWin.toolName, ut = 'cgmUIHeaderTemplate')
    mc.separator(ut='cgmUIHeaderTemplate')
    mc.separator(ut='cgmUITemplate')
    mc.separator(ut='cgmUITemplate')
    mc.separator(ut='cgmUITemplate')
    mc.text(label='')
    mc.button(label='Visit Website', ut = 'cgmUITemplate', command=('import webbrowser;webbrowser.open("http://www.joshburton.com")') )
    mc.button(label='Close', ut = 'cgmUITemplate', command=('mc.deleteUI(\"' + window + '\", window=True)') )
    mc.setParent( '..' )
    mc.showWindow( window )

def toggleModeState(OptionSelection,OptionList,OptionVarName,ListOfContainers):
    """ 
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    DESCRIPTION:
    Toggle for turning off and on the visbility of a list of containers

    REQUIRES:
    optionSelection(string) - this should point to the variable holding a (bool) value
    optionList(list) - the option selection must be in the optionList

    RETURNS:
    locatorName(string)
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    """
    visOn = OptionList.index(OptionSelection)
    mc.optionVar(sv=(OptionVarName,OptionSelection))

    cnt = 0
    for Container in ListOfContainers:
        if cnt == visOn:
            #Container(e=True,vis=True)
            setUIObjectVisibility(Container,True)
        else:
            #Container(e=True,vis=False)
            setUIObjectVisibility(Container,False)
        cnt+=1

        
        
def toggleMenuShowState(stateToggle, listOfItems):
    """ 
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    DESCRIPTION:
    Toggle for turning off and on the visibility of a menu section

    REQUIRES:
    stateToggle(string) - this should point to the variable holding a (bool) value
    listOfItems(list) - list of menu item names to change

    RETURNS:
    locatorName(string)
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    """
    if stateToggle:
        newState = False
    else:
        newState = True

    for item in listOfItems:
        uiType = mc.objectTypeUI(item)
        if uiType == 'staticText':
            mc.text(item, edit = True, visible = newState)	    
        elif uiType == 'separator':
            mc.separator(item, edit = True, visible = newState)
        elif uiType == 'rowLayout':
            mc.rowLayout(item, edit = True, visible = newState)
        elif uiType == 'rowColumnLayout':
            mc.rowColumnLayout(item, edit = True, visible = newState)
        elif uiType == 'columnLayout':
            mc.columnLayout(item, edit = True, visible = newState)
        elif uiType == 'formLayout':
            mc.formLayout(item, edit = True, visible = newState)
            #print ('%s%s%s%s%s%s%s' % ('"python(mc.',uiType,"('",item,"', edit = True, visible = ",newState,'))"'))
            #mel.eval(('%s%s%s%s%s%s%s' % ('"python(mc.',uiType,"('",item,"', edit = True, visible = ",newState,'))"')))
            #mc.separator(item, edit = True, visible = newState)    
        else:
            warning('%s%s%s' %('No idea what ', item, ' is'))
    return newState

def setUIObjectVisibility(item, visState):
    """ 
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    DESCRIPTION:
    Toggle for turning off and on the visibility of a menu section

    REQUIRES:
    stateToggle(string) - this should point to the variable holding a (bool) value
    listOfItems(list) - list of menu item names to change

    RETURNS:
    locatorName(string)
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    """
    uiType = mc.objectTypeUI(item)
    
    if uiType == 'staticText':
        mc.text(item, edit = True, visible = visState)	    
    elif uiType == 'separator':
        mc.separator(item, edit = True, visible = visState)
    elif uiType == 'rowLayout':
        mc.rowLayout(item, edit = True, visible = visState)
    elif uiType == 'rowColumnLayout':
        mc.rowColumnLayout(item, edit = True, visible = visState)
    elif uiType == 'columnLayout':
        mc.columnLayout(item, edit = True, visible = visState)
    elif uiType == 'formLayout':
        mc.formLayout(item, edit = True, visible = visState)
        #print ('%s%s%s%s%s%s%s' % ('"python(mc.',uiType,"('",item,"', edit = True, visible = ",visState,'))"'))
        #mel.eval(('%s%s%s%s%s%s%s' % ('"python(mc.',uiType,"('",item,"', edit = True, visible = ",visState,'))"')))
        #mc.separator(item, edit = True, visible = visState)    
    else:
        warning('%s%s%s' %('No idea what ', item, ' is'))
        

def toggleMenuState(stateToggle):
    """ 
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    DESCRIPTION:
    Toggle for a menu item

    REQUIRES:
    stateToggle(string) - this should point to the variable holding a (bool) value
    listOfItems(list) - list of menu item names to change

    RETURNS:
    locatorName(string)
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    """
    if stateToggle:
        newState = False
    else:
        newState = True

    return newState	


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Load to fields
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
def doLoadSingleObjectToTextField(textFieldObject,variableToSet = False):
    selected = []
    bufferList = []
    selected = (mc.ls (sl=True,flatten=True))
    if selected:
        if len(selected) >= 2:
            warning('Only one object can be loaded')
        else:
            textFieldObject(edit=True,ut = 'cgmUILockedTemplate', text = selected[0],editable = False )
            if variableToSet:
                mc.optionVar(sv=(variableToSet,selected[0]))
    else:
        textFieldObject(edit=True,text = '')
        if variableToSet:
            mc.optionVar(remove = variableToSet)
        warning('You must select something.')


def doLoadMultipleObjectsToTextField(textFieldObject,objectsToLoad = False, variableToSet = False):
    if not objectsToLoad:
        objectsToLoad = (mc.ls (sl=True,flatten=True))
        
    if objectsToLoad:
        textFieldObject(edit=True,ut = 'cgmUILockedTemplate', text = ';'.join(objectsToLoad),editable = False )
        if variableToSet:
            mc.optionVar(clearArray = variableToSet)
            for item in objectsToLoad:
                mc.optionVar(sva=(variableToSet,item))
    else:
        textFieldObject(edit=True,text = '')
        if variableToSet:
            mc.optionVar(clearArray = variableToSet)
        warning('You must select something.')

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Standard functions
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
def lineSplitter(text, size):
    lineList = []
    wordsList = text.split(' ')
    baseCnt = 0
    cnt = 0
    max = len(wordsList)
    while cnt < max:
        buffer = ' '.join(wordsList[baseCnt:cnt + 1])
        if len(buffer) < size:
            cnt+=1
        else:
            baseCnt = cnt+1
            cnt = baseCnt
            lineList.append(buffer)
    if baseCnt < max:
        lineList.append(' '.join(wordsList[baseCnt:]))
    return lineList


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Text Fields
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
def doTextFieldGrp(label = 'Text here',defaultText = False):
    columnWidth = (len(list(label)) * 10)
    buffer = mc.textFieldGrp( label=label, cw=[1,columnWidth], adjustableColumn = 2, columnAttach2 = ['left','right'], width = 100)
    if defaultText:
        mc.textFieldGrp(buffer, edit=True, text=defaultText)
    return buffer

def doTextFieldButtonGrp():
    return mc.textFieldButtonGrp( label='Label', text='Text', buttonLabel='Button' )

def doLoadToTextField(label = False, commandText = 'guiFactory.warning("Fix this")'):
    if label:
        return mc.textFieldButtonGrp(label = label, buttonLabel='<<<', ut = 'cgmUITemplate', width = 50, recomputeSize = False, command=commandText )
    else:
        return mc.textFieldButtonGrp(buttonLabel='<<<', ut = 'cgmUITemplate', width = 50, recomputeSize = False, command=commandText )
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Buttons
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
def doButton2(parent, labelText, commandText = 'guiFactory.warning("Fix this")',annotationText = '',*a,**kw):
    if currentGenUI:
        return 	MelButton(parent,l=labelText,ut = 'cgmUITemplate', 
                                 c= commandText,
                                 annotation = annotationText,*a,**kw)
    else:
        return MelButton(parent,l=labelText, backgroundColor = [.75,.75,.75], 
                         c= commandText,
                         annotation = annotationText,*a,**kw)


def doButton(labelText, commandText = 'guiFactory.warning("Fix this")'):
    if currentGenUI:
        return mc.button(label= labelText, ut = 'cgmUITemplate', command=commandText )
    else:
        return mc.button(label= labelText, backgroundColor = [.75,.75,.75],command=commandText )

def doLoadToFieldButton(commandText = 'guiFactory.warning("Fix this")'):
    if currentGenUI:
        return mc.button(label='<<<', ut = 'cgmUITemplate', width = 50, recomputeSize = False, command=commandText )
    else:
        return mc.button(label='<<<', backgroundColor = [.75,.75,.75], width = 50, command=commandText )

def doReturnFontFromDialog(currentFont):
    fontChoice = mc.fontDialog()
    if fontChoice:
        return fontChoice
    else:
        warning("No font selected. You're stuck with " + currentFont)
        return currentFont

def doToggleIntOptionVariable(variable):
    varState = mc.optionVar( q= variable )
    mc.optionVar( iv=(variable, not varState))	

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Text and line breaks
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
def header(text, align = 'center',overrideUpper =False):
    if not overrideUpper:
        text = text.upper()
    if currentGenUI:
        return mc.text(text, al = align, ut = 'cgmUIHeaderTemplate')
    else:
        return mc.text(('%s%s%s' %('>>> ',text,' <<<')), al = align)

def headerBreak():
    if currentGenUI:
        return mc.separator(ut='cgmUIHeaderTemplate')
    else:
        return mc.separator(style='double')

def lineBreak():
    if currentGenUI:
        return mc.separator(ut='cgmUITemplate')
    else:
        return mc.separator(ut='cgmUITemplate')

def lineSubBreak(vis=True):
    if currentGenUI:
        return mc.separator(ut='cgmUISubTemplate',vis=vis)
    else:
        return mc.separator(style='single',vis=vis)

def sectionBreak():
    if currentGenUI:
        return mc.separator(ut='cgmUISubTemplate')
    else:
        return mc.separator(style='single')		

def instructions(text, align = 'center', vis = False, maxLineLength = 35):
    # yay, accounting for word wrap...
    if currentGenUI:
        buffer = mc.text(text, ut = 'cgmUIInstructionsTemplate',al = 'center', ww = True, visible = vis)
        return [buffer]
    else:
        instructions = []
        textLines = lineSplitter(text, maxLineLength)
        instructions.append(mc.separator(style='single', visible = vis))
        for line in textLines:
            instructions.append(mc.text(line, h = 15, al = align, visible = vis))
        instructions.append(mc.separator(style='single', visible = vis))

        return instructions

def oldVersionInstructions(text, align = 'center'):
    # yay, accounting for word wrap...
    if currentGenUI:
        return [mc.text(text, ut = 'cgmUIInstructionsTemplate',al = 'center', ww = True, visible = False)]
    else:
        instructions = []
        textLines = lineSplitter(text, 35)
        instructions.append(mc.text(label = '>>> Warning <<<', visible = False))
        for line in textLines:
            instructions.append(mc.text(line, al = align, visible = False))
        instructions.append(mc.separator(style='single', visible = False))

        return instructions

def textBlock(text, align = 'center'):
    # yay, accounting for word wrap...
    if currentGenUI:
        return [mc.text(text,al = 'center', ww = True, visible = True)]
    else:
        textBlock = []
        textLines = lineSplitter(text, 50)
        textBlock.append(mc.separator(style = 'single', visible = True))
        for line in textLines:
            textBlock.append(mc.text(line, al = align, visible = True))
        textBlock.append(mc.separator(style = 'single', visible = True))
        return textBlock


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Progress Tracking
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
def doProgressWindow(winName='Progress Window',statusMessage = 'Progress...',startingProgress = 0, interruptableState = True):
    return mc.progressWindow(title= winName,
                             progress=startingProgress,
                             status= statusMessage,
                             isInterruptable=interruptableState )

def doUpdateProgressWindow(statusMessage,stepInterval,stepRange,reportItem=False):
    """ 
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    DESCRIPTION:
    Tools to do a maya progress window. This function and doEndMayaProgressBar are a part of a set. 

    REQUIRES:
    statusMessage(string) - starting status message
    stepInterval(int)
    stepRange(int)
    reportItem(string/bool) - If you want a percentage to be shown, put False(default - False)

    RETURNS:
    mayaMainProgressBar(string)
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    """

    maxRange = int(stepRange)
    percent = (float(stepInterval)/maxRange)
    progressAmount = int(percent * 100)

    # Check if the dialog has been cancelled
    if mc.progressWindow(query=True, isCancelled=True ) :
        if reportItem != False:
            warning('%s%s' %('Stopped at ',str(reportItem)))
            return 'break'
        else:
            warning('%s%s%s' %('Stopped at ',str(progressAmount),'%'))
            return 'break'

    # Check if end condition has been reached
    if mc.progressWindow( query=True, progress=True ) >= 100 :
        return 'break'

    if reportItem != False:
        mc.progressWindow(edit=True, progress=progressAmount, status=(statusMessage+  str(reportItem)) )
    else:
        mc.progressWindow(edit=True, progress=progressAmount, status=(statusMessage+ `stepInterval` ) )

def doCloseProgressWindow():
    mc.progressWindow(endProgress=1)
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>        

def doStartMayaProgressBar(stepMaxValue = 100, statusMessage = 'Calculating....',interruptableState = True):
    """ 
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    DESCRIPTION:
    Tools to do a maya progress bar. This function and doEndMayaProgressBar are a part of a set. Example 
    usage:

    mayaMainProgressBar = guiFactory.doStartMayaProgressBar(int(number))
    for n in range(int(number)):
    if mc.progressBar(mayaMainProgressBar, query=True, isCancelled=True ) :
    break
    mc.progressBar(mayaMainProgressBar, edit=True, status = (n), step=1)

    guiFactory.doEndMayaProgressBar(mayaMainProgressBar)

    REQUIRES:
    stepMaxValue(int) - max number of steps (defualt -  100)
    statusMessage(string) - starting status message
    interruptableState(bool) - is it interuptible or not (default - True)

    RETURNS:
    mayaMainProgressBar(string)
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    """
    mayaMainProgressBar = mel.eval('$tmp = $gMainProgressBar');
    mc.progressBar( mayaMainProgressBar,
                    edit=True,
                    beginProgress=True,
                    isInterruptable=interruptableState,
                    status=statusMessage,
                    maxValue= stepMaxValue )
    return mayaMainProgressBar

def doEndMayaProgressBar(mayaMainProgressBar):
    mc.progressBar(mayaMainProgressBar, edit=True, endProgress=True)

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>        
def doProgressBar(winName,trackedList,statusMessage):
    mc.progressBar()




#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Reporting
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
def doPrintReportStart():
    return '#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> Start >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>'

def doPrintReportEnd():
    return '#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> End >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>'


#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Rows and columns
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>





























#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# Tabs And Forms
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
def doEvenRowOfColumns(numberOfColumns = 3,useTemplateOption = False):
    form = mc.formLayout(numberOfDivisions=100,backgroundColor = [0,.5,2])
    columnOffsetOptions = {2:[(1,'both',3),(2,'right',3)],
                           3:[(1,'left',3),(2,'both',5),(3,'right',3)],
                           4:[(1,'left',3),(2,'both',5),(3,'both',5),(4,'right',3)],
                           5:[(1,'left',3),(2,'both',5),(3,'both',5),(4,'both',5),(5,'right',3)],
                           6:[(1,'left',3),(2,'both',5),(3,'both',5),(4,'both',5),(5,'both',5),(6,'right',3)]
                           }
    """
    if currentGenUI:
	if useTemplateOption:
	    bufferRowColumnLayout =  mc.rowColumnLayout(numberOfRows=1, ut = useTemplateOption, columnOffset=columnOffsetOptions[numberOfColumns] )

	else:
	    bufferRowColumnLayout = mc.rowColumnLayout(numberOfRows=1, columnOffset=columnOffsetOptions[numberOfColumns] )
    else:
	bufferRowColumnLayout = mc.rowColumnLayout(numberOfRows=1, columnOffset=columnOffsetOptions[numberOfColumns] )
    """
    bufferRowColumnLayout = mc.rowColumnLayout(backgroundColor = [0.8,.5,5], numberOfRows=1, columnOffset=columnOffsetOptions[numberOfColumns] )
    mc.formLayout(form, edit = True,
                  attachForm = [(bufferRowColumnLayout,'left',0),
                                (bufferRowColumnLayout,'top',0),
                                (bufferRowColumnLayout,'right',0)])
    return bufferRowColumnLayout


def doEvenRowOfColumns6():
    if currentGenUI:
        return mc.rowColumnLayout(numberOfRows=1, columnOffset= [(1,'left',3),(2,'both',5),(3,'both',5),(4,'both',5),(5,'both',5),(6,'right',3)])
    else:
        return mc.rowColumnLayout(numberOfRows=1)
def doEvenRowOfColumns3():
    if currentGenUI:
        return mc.rowColumnLayout(numberOfRows=1, columnOffset= [(1,'left',3),(2,'both',5),(3,'right',3)])
    else:
        return mc.rowColumnLayout(numberOfRows=1)
def doEvenRowOfColumns2(useTemplate = False):
    if currentGenUI:
        if useTemplate:
            return mc.rowColumnLayout(ut = useTemplate, numberOfRows=1, columnOffset= [(1,'both',3),(2,'right',3)])
        else:
            return mc.rowColumnLayout(numberOfRows=1, columnOffset= [(1,'both',3),(2,'right',3)])
    else:
        return mc.rowColumnLayout(numberOfRows=1)	

def doTabs(toolName):
    mc.tabLayout((toolName + 'cgmRiggingToolsTabs'),innerMarginWidth=5, innerMarginHeight=5)

def doFormLayout():
    if currentGenUI:
        return mc.formLayout(numberOfDivisions=100, ut = 'cgmUISubTemplate')
    else:
        return mc.formLayout(numberOfDivisions=100 )