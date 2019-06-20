# -*- coding: utf-8 -*-

import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import collections
import threading

from PySpectralRadar import *

#-------------------------------------------------------------------------------

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
        print('Distance between points in orthogonal crosses: '+str(d)+' mm')
        print(str(len(X))+' total points.')

        return posRepeated, X, Y

#-------------------------------------------------------------------------------

print('\n----------------------------------')
print('PySpectralRadar Figure-8 Scanner')
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

FALSE = BOOL(0)
TRUE = BOOL(1)

size = 0.95
# ascans = 200
repeats = 1

fig8pos, X, Y = generateIdealFigureEightPositions(size,30,rpt=repeats)

scanPattern = createFreeformScanPattern(probe,fig8pos,len(X)*repeats,1,FALSE)
rotateScanPattern(scanPattern,40.0)

print('\n----------------------------------')
print('Created scan pattern: 10X figure-8.')
print('----------------------------------\n')

acq = AcquisitionType

print('\n----------------------------------')
print('Tried to start measurement. Created data objects.')
print('----------------------------------\n')

rawDataHandle = createRawData()
complexDataHandle = createComplexData()

rpt = 10000

def AcqThread():

    i = rpt

    startMeasurement(dev,scanPattern,acq.Acquisition_AsyncContinuous)

    while i > 0:
        setComplexDataOutput(proc,complexDataHandle)
        getRawData(dev,rawDataHandle)
        executeProcessing(proc,rawDataHandle)

        if i == rpt:
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

        holder = np.empty(rawDim,dtype=np.uint16)
        copyRawDataContent(rawDataHandle,holder)

        cholder = np.empty(complexDim,dtype=np.complex64)
        copyComplexDataContent(complexDataHandle,cholder)

        QUEUE.append(holder)

        i -= 1

    stopMeasurement(dev)


QUEUE = collections.deque()

fig = plt.figure()

window = np.hanning(2048)

def animate(i):

    disp = np.zeros([1024,30],dtype=np.float32)
    plt.cla()
    if len(QUEUE) > 0:

        latest = QUEUE.popleft()

        if latest.size > 0:

            fig8 = np.empty([2048,30],dtype=np.uint16)

            raw = latest.flatten()

            i = 0
            for n in np.arange(16,46):
                fig8[:,i] = raw[2048*n:2048*n+2048]
                i += 1

            bscan = np.empty([1024,30])

            for n in range(30):
                bscan[:,n] = 20*np.log10(abs(np.real(np.fft.ifft((fig8[:,n] - np.mean(fig8,axis=1))*window)[1024::])))

            disp = bscan

    return plt.imshow(disp,aspect=0.1)



Acquisition = threading.Thread(target=AcqThread)
Acquisition.start()

ani = FuncAnimation(fig, animate, interval=1)
plt.show()

clearScanPattern(scanPattern)
clearRawData(rawDataHandle)
closeProcessing(proc)
closeProbe(probe)
closeDevice(dev)

print(np.shape(QUEUE))

print('\n----------------------------------')
print('Cleared objects from memory.')
print('----------------------------------')
