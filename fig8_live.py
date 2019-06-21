# -*- coding: utf-8 -*-

import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import collections
import threading
import numba
from scipy.interpolate import interp1d as interp1

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

size = .032
N = 40
repeats = 1
intpDk = -0.19
apod = np.hanning(2048)
k = np.linspace(1-intpDk/2, 1+intpDk/2, 2048)
lam = 1/k[::-1]
interpIndices = np.linspace( min(lam), max(lam), 2048)

xsection1 = np.arange(16,56)
xsection2 = np.arange(88,128)

fig8pos, X, Y = generateIdealFigureEightPositions(size,N,rpt=repeats)

scanPattern = createFreeformScanPattern(probe,fig8pos,len(X)*repeats,1,FALSE)
rotateScanPattern(scanPattern,30.0)

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

        if (i % 9) == 0:
            PREVIEW.append(holder)

        i -= 1

    stopMeasurement(dev)


PREVIEW = collections.deque()

fig = plt.figure()

window = np.hanning(2048)

# @numba.jit
def process(raw):

    proc = np.empty([1024,N],dtype=np.complex64)
    fig8 = np.empty([2048,N],dtype=np.uint16)
    flat = raw.flatten()

    i = 0
    for n in xsection1:
        fig8[:,i] = flat[2048*n:2048*n+2048]
        i += 1

    dc = np.mean(fig8,axis=1)

    for n in range(N):
        corr = (fig8[:,n] - dc) * apod
        proc[:,n] = np.fft.ifft(corr)[1024:2048].astype(np.complex64)

    return proc

def animate(i):

    disp = np.zeros([1024,N],dtype=np.float32)
    plt.cla()
    if len(PREVIEW) > 10:

        latest = PREVIEW.popleft()

        if latest.size > 0:

            bscan = process(latest)

            disp = 20*np.log10(abs(np.real(bscan)))

    return plt.imshow(disp,aspect=0.5,cmap='gray',origin='lower')



Acquisition = threading.Thread(target=AcqThread)
Acquisition.start()

ani = FuncAnimation(fig, animate, interval=1)
plt.show()

clearScanPattern(scanPattern)
clearRawData(rawDataHandle)
closeProcessing(proc)
closeProbe(probe)
closeDevice(dev)

print('\n----------------------------------')
print('Cleared objects from memory.')
print('----------------------------------')
