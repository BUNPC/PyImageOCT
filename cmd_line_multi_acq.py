# -*- coding: utf-8 -*-

from src.main.python.PySpectralRadar import *

#-------------------------------------------------------------------------------

centerLambda = 0.001310 #mm
NA = 0.28 #10X

def generateIdealFigureEightPositions(xsize,alinesPerX,rpt=1):

    if rpt > 0:

        t = np.linspace(0,2*np.pi,100,dtype=np.float32)
        cross = np.linspace(-xsize,xsize,alinesPerX)
        cross1 = np.array([cross[::-1],cross[::-1]])
        cross2 = np.array([cross,-cross])
        d = np.sqrt((cross1[0][0]-cross1[0][1])**2+(cross1[1][0]-cross1[1][1])**2)
        x = 2*xsize*np.cos(t)
        y = ((2*xsize)/1.7)*np.sin(2*t)
        x1 = x[x>xsize+0.001*xsize]
        x2 = x[x<-xsize-0.001*xsize]
        y1 = y[x>xsize+0.001*xsize]
        y2 = y[x<-xsize-0.001*xsize]

        X = np.concatenate([x1[0:16],cross1[0],x2,cross2[0],x1[17::]])
        Y = np.concatenate([y1[0:16],cross1[1],y2,cross2[1],y1[17::]])

        pos = np.empty(int(2*len(X)), dtype=np.float32)
        pos[0::2] = X
        pos[1::2] = Y
        posRepeated = np.tile(pos,rpt)

        print('Figure-8 scan pattern generated...')
        print(str(len(cross1[0]))+' points in each orthogonal cross...')
        print('Distance between points in orthogonal crosses: '+str(d)+' mm, '+str((centerLambda/NA)/d)+' per spot.')
        print(str(len(X))+' total points.')

        return posRepeated, X, Y

def generateFigureEightPositions(size,alinesPer8,rpt=1,outputText=False):
    '''
    Generates 1D list of positon pairs for use with SpectralRadar 3.X
    createFreeformScanPattern, which takes units of mm, therefore size argument
    is also in mm. By default, the figure-8 has dim 1 mm x 0.5 mm.
    '''
    if rpt > 0:
        t = np.linspace(0,2*np.pi,alinesPer8,dtype=np.float32)
        x = size*np.cos(t)
        y = (size/2)*np.sin(2*t)
        pos = np.empty(int(2*alinesPer8), dtype=np.float32)
        pos[0::2] = x
        pos[1::2] = y
        posRepeated = np.tile(pos,rpt)
        if outputText:
            np.savetxt('scanPatternPos.txt',posRepeated)
        return posRepeated.astype(np.float32)

#-------------------------------------------------------------------------------

print('\n----------------------------------')
print('PySpectralRadar Raw/Complex Data Acq')
print('----------------------------------\n')

###input('\nPress ENTER to initiate device handle...')

dev = initDevice()

###input('\nPress ENTER to set device parameters...')

triggerType = Device_TriggerType
setTriggerMode(dev,triggerType.Trigger_FreeRunning)
setTriggerTimeoutSec(dev,5)

print('\n----------------------------------')
print('Set trigger mode to free running, timeout = 5 s')
print('----------------------------------\n')

###input('\nPress ENTER to initiate probe handle...')

probe = initProbe(dev,'ProbeLKM10-LV')

###input('\nPress ENTER to initiate processing handle...')

proc = createProcessingForDevice(dev)

setCameraPreset(dev,probe,proc,0)
print('\n----------------------------------')
print('Set camera preset = 0')
print('----------------------------------\n')

###input('\nPress ENTER to initiate acquisition...')
aperspot = ['2','6','10']
sizes = [0.032,0.0106,0.0064]

for i in range(len(sizes)):

    size = sizes[i] #Ideal fig8 size parameter
    xLen = 40
    repeats = 500

    idealPos, X, Y = generateIdealFigureEightPositions(size,40,rpt=repeats)
    posArr = np.stack([X,Y])

    print('\n----------------------------------')
    print('Scan pattern size:')
    print(idealPos.size)
    print('----------------------------------\n')

    scanPattern = createFreeformScanPattern(probe,idealPos,len(X)*repeats,1,FALSE)
    rotateScanPattern(scanPattern,45.0)

    print('\n----------------------------------')
    print('Created scan pattern: figure-8.')
    print('----------------------------------\n')

    acq = AcquisitionType
    startMeasurement(dev,scanPattern,acq.Acquisition_AsyncContinuous)
    rawDataHandle = createRawData()
    complexDataHandle = createComplexData()
    setComplexDataOutput(proc,complexDataHandle)

    print('\n----------------------------------')
    print('Tried to start measurement and execute processing. Created data objects.')
    print('----------------------------------\n')

    getRawData(dev,rawDataHandle)
    executeProcessing(proc,rawDataHandle)

    stopMeasurement(dev)
    print('\n----------------------------------')
    print('Stopped measurement.')
    print('----------------------------------\n')

    prop = RawDataPropertyInt
    rawSize1 = getRawDataPropertyInt(rawDataHandle,prop.RawData_Size1)
    rawSize2 = getRawDataPropertyInt(rawDataHandle,prop.RawData_Size2)
    rawSize3 = getRawDataPropertyInt(rawDataHandle,prop.RawData_Size3)
    rawNumberOfElements = getRawDataPropertyInt(rawDataHandle,prop.RawData_NumberOfElements)

    rawDim = [rawSize1,rawSize2,rawSize3]

    prop2 = DataPropertyInt
    complexSize1 = getComplexDataPropertyInt(complexDataHandle,prop2.Data_Size1)
    complexSize2 = getComplexDataPropertyInt(complexDataHandle,prop2.Data_Size2)
    complexSize3 = getComplexDataPropertyInt(complexDataHandle,prop2.Data_Size3)
    complexNumberOfElements = getComplexDataPropertyInt(complexDataHandle,prop2.Data_NumberOfElements)
    complexBytes = getComplexDataPropertyInt(complexDataHandle,prop2.Data_BytesPerElement)

    complexDim = [complexSize1,complexSize2,complexSize3]

    print('\n----------------------------------')
    print('Complex data dimensions:')
    print(complexDim)
    print('Raw data number of bytes per element:')
    print(complexBytes)
    print('----------------------------------\n')

    holder = np.empty(rawDim,dtype=np.uint16)
    copyRawDataContent(rawDataHandle,holder)

    cholder = np.empty(complexDim,dtype=np.complex64)
    copyComplexDataContent(complexDataHandle,cholder)

    print('\n----------------------------------')
    print('Complex data:')
    print(cholder)
    print('----------------------------------\n')

    expStr = aperspot[i]+'_x'

    complexFilename = 'fig8_6_complex_'+expStr
    rawFilename = 'fig8_6_raw_'+expStr
    positionsFilename = 'fig8_6_pos_'+expStr

    np.save(complexFilename,cholder)
    np.save(rawFilename,holder)
    np.save(positionsFilename,posArr)
    print('\n----------------------------------')
    print('Saved raw data array as .npy')
    print('----------------------------------\n')


clearScanPattern(scanPattern)
clearRawData(rawDataHandle)
clearComplexData(complexDataHandle)
closeProcessing(proc)
closeProbe(probe)
closeDevice(dev)
print('\n----------------------------------')
print('Cleared objects from memory.')
print('----------------------------------')

print('Done with multi-acquisition!')
